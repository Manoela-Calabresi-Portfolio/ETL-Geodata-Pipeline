#!/usr/bin/env python3
"""
Stuttgart Urban Analysis Suite - MODULAR VERSION
Generates comprehensive urban analysis maps and reports

🎯 COMO USAR ESTE SCRIPT:
========================

Para gerar APENAS o MAPA 1 (Overview):
- Deixe como está (já está configurado)

Para EXPORTAR dados para Kepler.gl:
- Descomente a seção "EXPORTAÇÃO KEPLER.GL"

Para gerar MAPAS 2-8 (Choropleth):
- Descomente a seção "MAPAS 2-8: CHOROPLETH MAPS"

Para gerar MAPAS 9-15 (District Atlas):
- Descomente a seção "MAPAS 9-15: DISTRICT ATLAS"

Para gerar MAPAS 16-18 (Close-up):
- Descomente a seção "MAPAS 16-18: CLOSE-UP MAPS"

Para gerar HTML Dashboard:
- Descomente a seção "MAPA 19: HTML DASHBOARD"

💡 DICA: Sempre descomente as seções na ordem correta!
"""
from __future__ import annotations
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("TkAgg")  # Use TkAgg for interactive windows
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import contextily as cx
from shapely.geometry import Point, box
import jinja2
import json

# Import our local modules
import sys
sys.path.append('..')
from style_helpers.style_helpers import apply_style, palette

warnings.filterwarnings("ignore", category=UserWarning)

# Configuration - Fixed paths for current directory structure
DATA_DIR = Path("../../../main_pipeline/areas/stuttgart/data_final")

def get_next_run_number():
    """Get the next available run number"""
    base_dir = Path("../outputs")
    base_dir.mkdir(exist_ok=True)
    
    existing_runs = [d for d in base_dir.iterdir() 
                    if d.is_dir() and d.name.startswith("stuttgart_maps_")]
    
    if not existing_runs:
        return 1
    
    # Extract numbers from existing run folders
    run_numbers = []
    for run_dir in existing_runs:
        try:
            num = int(run_dir.name.split("_")[-1])
            run_numbers.append(num)
        except (ValueError, IndexError):
            continue
    
    return max(run_numbers) + 1 if run_numbers else 1

# Create numbered output directory
RUN_NUMBER = get_next_run_number()
OUT_DIR = Path(f"../outputs/stuttgart_maps_{RUN_NUMBER:03d}")
MAPS_DIR = OUT_DIR / "maps"

OUT_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)

PLOT_CRS = 3857
SELECTED_DISTRICTS = ["Mitte", "Bad Cannstatt", "Vaihingen", "Zuffenhausen", "Degerloch"]

# ---------- Data Loading ----------
def load_data():
    """Load all geospatial data"""
    print("📁 Loading geospatial data...")
    
    def read_any(p: Path):
        if not p.exists(): return None
        try:
            if p.suffix.lower() in {".geojson", ".json", ".gpkg"}:
                return gpd.read_file(p)
            elif p.suffix.lower() == ".parquet":
                df = pd.read_parquet(p)
                if "geometry" in df.columns:
                    if df['geometry'].dtype == 'object' and isinstance(df['geometry'].iloc[0], bytes):
                        from shapely import wkb
                        df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
                    return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)
                return df
        except Exception as e:
            print(f"Error reading {p}: {e}")
            return None
    
    data = {
        "districts": read_any(DATA_DIR/"districts_with_population.geojson"),
        "pt_stops": read_any(DATA_DIR/"processed/pt_stops_categorized.parquet"),
        "amenities": read_any(DATA_DIR/"processed/amenities_categorized.parquet"),
        "cycle": read_any(DATA_DIR/"processed/cycle_categorized.parquet"),
        "landuse": read_any(DATA_DIR/"processed/landuse_categorized.parquet"),
        "roads": read_any(DATA_DIR/"processed/roads_categorized.parquet"),
    }
    
    # Ensure CRS is set
    for key, gdf in data.items():
        if gdf is not None and hasattr(gdf, 'crs'):
            data[key] = gdf.set_crs(4326) if gdf.crs is None else gdf.to_crs(4326)
    
    return data

# ---------- KPI Calculation ----------
def calculate_district_kpis(data):
    """Calculate KPIs for each district"""
    print("📊 Calculating district KPIs...")
    
    districts = data["districts"].copy()
    districts = districts.to_crs(PLOT_CRS)
    districts["area_km2"] = districts.area / 1e6
    
    # Population density
    districts["population_density"] = districts["pop"] / districts["area_km2"]
    
    # PT stop density
    if data["pt_stops"] is not None:
        pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
        pt_join = gpd.sjoin(pt_stops, districts[["geometry"]], predicate="within", how="left")
        pt_counts = pt_join.groupby("index_right").size()
        districts["pt_stops_count"] = districts.index.map(pt_counts).fillna(0)
        districts["pt_stop_density"] = districts["pt_stops_count"] / districts["area_km2"]
    else:
        districts["pt_stops_count"] = 0
        districts["pt_stop_density"] = 0
    
    # Service density (amenities per 1,000 residents)
    if data["amenities"] is not None:
        amenities = data["amenities"].to_crs(PLOT_CRS)
        amen_join = gpd.sjoin(amenities, districts[["geometry"]], predicate="within", how="left")
        amen_counts = amen_join.groupby("index_right").size()
        districts["amenities_count"] = districts.index.map(amen_counts).fillna(0)
        districts["service_density"] = (districts["amenities_count"] / districts["pop"]) * 1000
    else:
        districts["amenities_count"] = 0
        districts["service_density"] = 0
    
    # Green land use percentage
    if data["landuse"] is not None:
        landuse = data["landuse"].to_crs(PLOT_CRS)
        landuse = landuse[landuse.geometry.type.isin(["Polygon", "MultiPolygon"])]
        
        def is_green(row):
            lu = str(row.get("landuse", "")).lower()
            nat = str(row.get("natural", "")).lower()
            return lu in {"forest", "meadow", "grass", "recreation_ground", "park", "cemetery", "orchard", "vineyard", "allotments"} \
                or nat in {"wood", "scrub", "grassland", "park"}
        
        greens = landuse[landuse.apply(is_green, axis=1)]
        
        green_areas = []
        for idx, district in districts.iterrows():
            district_geom = district.geometry
            green_in_district = greens[greens.intersects(district_geom)]
            
            if len(green_in_district) > 0:
                total_green_area = 0
                for green_geom in green_in_district.geometry:
                    intersection = green_geom.intersection(district_geom)
                    if not intersection.is_empty:
                        total_green_area += intersection.area
                green_pct = (total_green_area / district_geom.area) * 100
            else:
                green_pct = 0
            green_areas.append(green_pct)
        
        districts["green_landuse_pct"] = green_areas
    else:
        districts["green_landuse_pct"] = 0
    
    # Cycle infrastructure density
    if data["cycle"] is not None:
        cycle = data["cycle"].to_crs(PLOT_CRS)
        cycle_join = gpd.sjoin(cycle, districts[["geometry"]], predicate="within", how="left")
        cycle_lengths = []
        
        for idx, district in districts.iterrows():
            district_geom = district.geometry
            cycle_in_district = cycle[cycle.intersects(district_geom)]
            
            if len(cycle_in_district) > 0:
                total_length = 0
                for cycle_geom in cycle_in_district.geometry:
                    intersection = cycle_geom.intersection(district_geom)
                    if not intersection.is_empty:
                        total_length += intersection.length
                total_length_km = total_length / 1000
            else:
                total_length_km = 0
            cycle_lengths.append(total_length_km)
        
        districts["cycle_length_km"] = cycle_lengths
        districts["cycle_infra_density"] = districts["cycle_length_km"] / districts["area_km2"]
    else:
        districts["cycle_length_km"] = 0
        districts["cycle_infra_density"] = 0
    
    # Round numeric columns
    numeric_cols = ["population_density", "pt_stop_density", "service_density", 
                   "green_landuse_pct", "cycle_infra_density"]
    for col in numeric_cols:
        districts[col] = districts[col].round(2)
    
    return districts

# ---------- Map Generation ----------
def generate_overview_maps(data):
    """Generate overview maps of the whole city"""
    print("🗺️ Generating overview maps...")
    
    # Define data directories
    DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
    PROCESSED_DIR = DATA_DIR / "processed"
    
    # Get city extent and create city boundary with better clipping
    districts = data["districts"].to_crs(PLOT_CRS)
    city_boundary = districts.unary_union
    
    # Create a buffer around the city boundary for better visual clipping (100m buffer)
    city_boundary_buffered = city_boundary.buffer(100)
    
    # Get extent with some padding for better visual balance
    extent = tuple(districts.total_bounds)
    # Add 15% padding to the extent - smaller padding for bigger map scale
    x_padding = (extent[2] - extent[0]) * 0.15
    y_padding = (extent[3] - extent[1]) * 0.15
    extent = (extent[0] - x_padding, extent[1] - y_padding, 
              extent[2] + x_padding, extent[3] + y_padding)
    
    # Map 1: Land use + Roads + PT stops
    fig, ax = plt.subplots(1, 1, figsize=(35, 25))  # Bigger image size - more white room + bigger map
    
    # Plot clear city boundary with 40% grey opacity
    city_boundary_geom = gpd.GeoSeries([city_boundary], crs=PLOT_CRS)
    city_boundary_geom.boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.4)
    
    # Plot categorized land use (clipped to city boundary with buffer)
    if data["landuse"] is not None:
        landuse = data["landuse"].to_crs(PLOT_CRS)
        # Clip geometries to city boundary instead of just filtering
        landuse = landuse[landuse.intersects(city_boundary_buffered)].copy()
        if len(landuse) > 0:
            # Clip each geometry to the city boundary for clean edges
            landuse["geometry"] = landuse.geometry.intersection(city_boundary_buffered)
            # Remove any geometries that became empty after clipping
            landuse = landuse[~landuse.geometry.is_empty]
            
            # Plot land use by simplified categories - FILTER OUT SMALL AREAS TO PREVENT DOTS
            # Calculate area in square meters and filter out very small polygons (< 1000 m² = 0.1 hectares)
            landuse["area_m2"] = landuse.geometry.area
            min_area = 1000  # 1000 square meters = 0.1 hectares
            
            # 1. Forest (darkest sage green) - only areas > 1000 m²
            forest_data = landuse[
                ((landuse["landuse"] == "forest") | (landuse["natural"] == "forest")) &
                (landuse["area_m2"] >= min_area)
            ]
            if len(forest_data) > 0:
                forest_data.plot(ax=ax, color="#4A5D4A", alpha=0.2, edgecolor="none", label="Forest")
                print(f"  - Plotted forest: {len(forest_data)} areas (filtered from {len(landuse[(landuse['landuse'] == 'forest') | (landuse['natural'] == 'forest')])})")
            
            # 2. Farmland (medium sage green) - only areas > 1000 m²
            farmland_data = landuse[
                ((landuse["landuse"] == "farmland") | (landuse["natural"] == "farmland")) &
                (landuse["area_m2"] >= min_area)
            ]
            if len(farmland_data) > 0:
                farmland_data.plot(ax=ax, color="#7FB069", alpha=0.2, edgecolor="none", label="Farmland")
                print(f"  - Plotted farmland: {len(farmland_data)} areas (filtered from {len(landuse[(landuse['landuse'] == 'farmland') | (landuse['natural'] == 'farmland')])})")
            
            # 3. REAL PARKS (lighter sage green) - using extracted OSM parks
            # Load real parks extracted from OSM
            parks_file = PROCESSED_DIR / "parks_extracted_osmnx.parquet"
            if parks_file.exists():
                try:
                    real_parks = gpd.read_parquet(parks_file)
                    real_parks = real_parks.to_crs(PLOT_CRS)
                    
                    # Clip parks to city boundary
                    real_parks = real_parks[real_parks.intersects(city_boundary_buffered)].copy()
                    if len(real_parks) > 0:
                        real_parks["geometry"] = real_parks.geometry.intersection(city_boundary_buffered)
                        real_parks = real_parks[~real_parks.geometry.is_empty]
                        
                        # Plot real parks
                        real_parks.plot(ax=ax, color="#9DC183", alpha=0.2, edgecolor="none", label="Real Parks")
                        print(f"  - Plotted REAL PARKS from OSM: {len(real_parks)} parks (including Schlossgarten, Rosenstein, etc.)")
                        
                        # Show some named parks
                        if 'name' in real_parks.columns:
                            named_parks = real_parks[real_parks['name'].notna()]
                            if len(named_parks) > 0:
                                print(f"    Named parks found: {len(named_parks)}")
                                # Show first 10 named parks
                                park_names = named_parks['name'].head(10).tolist()
                                print(f"    Examples: {', '.join(park_names)}")
                        
                        park_data = real_parks
                    else:
                        print(f"  - No real parks found within city boundary")
                        park_data = gpd.GeoDataFrame()
                        
                except Exception as e:
                    print(f"  - Error loading real parks: {e}")
                    park_data = gpd.GeoDataFrame()
            else:
                print(f"  - Real parks file not found, using fallback")
                park_data = gpd.GeoDataFrame()
            
            # Fallback: if no real parks, use urban green areas
            if len(park_data) == 0:
                print(f"  - Using fallback: urban green areas")
                urban_green_data = landuse[
                    (landuse["category"] == "green") &
                    (landuse["area_m2"] >= min_area * 1.5)  # Slightly larger areas to represent parks
                ]
                
                if len(urban_green_data) > 0:
                    # Take a subset to represent urban parks (not all green areas)
                    park_data = urban_green_data.head(100)  # Use 100 areas to represent parks
                    park_data.plot(ax=ax, color="#9DC183", alpha=0.6, edgecolor="none", label="Urban Green Areas (Fallback)")
                    print(f"    - Plotted urban green areas (fallback): {len(park_data)} areas (filtered)")
                else:
                    print(f"    - No urban green areas found")
                    # Final fallback: use some forest areas as parks for visual representation
                    fallback_parks = landuse[
                        (landuse["category"] == "green") &
                        (landuse["area_m2"] >= min_area * 2)  # Larger areas
                    ].head(50)  # Take first 50 large green areas
                    if len(fallback_parks) > 0:
                        fallback_parks.plot(ax=ax, color="#9DC183", alpha=0.6, edgecolor="none", label="Urban Green Areas (Final Fallback)")
                        print(f"      - Using final fallback: plotted {len(fallback_parks)} large green areas as parks")
                        park_data = fallback_parks
                    else:
                        park_data = gpd.GeoDataFrame()
            
            # 4. ALL OTHER GREEN AREAS from OSM - comprehensive coverage
            # Load comprehensive green areas extracted from OSM
            green_areas_file = PROCESSED_DIR / "green_areas_categorized.parquet"
            if green_areas_file.exists():
                try:
                    all_green_areas = gpd.read_parquet(green_areas_file)
                    all_green_areas = all_green_areas.to_crs(PLOT_CRS)
                    
                    # Clip to city boundary
                    all_green_areas = all_green_areas[all_green_areas.intersects(city_boundary_buffered)].copy()
                    if len(all_green_areas) > 0:
                        all_green_areas["geometry"] = all_green_areas.geometry.intersection(city_boundary_buffered)
                        all_green_areas = all_green_areas[~all_green_areas.geometry.is_empty]
                        
                        # Plot all other green areas in one category with consistent sage tone
                        # Exclude parks (already plotted separately)
                        other_green_osm = all_green_areas[
                            ~((all_green_areas['osm_tag_key'] == 'leisure') & (all_green_areas['osm_tag_value'] == 'park'))
                        ]
                        if len(other_green_osm) > 0:
                            other_green_osm.plot(ax=ax, color="#9DC183", alpha=0.2, edgecolor="none", label="Other Green Areas")
                            print(f"  - Plotted other green areas (combined): {len(other_green_osm)} areas")
                        
                        # Store for legend calculation
                        other_green_data = other_green_osm
                        
                    else:
                        print(f"  - No OSM green areas found within city boundary")
                        other_green_data = gpd.GeoDataFrame()
                        
                except Exception as e:
                    print(f"  - Error loading OSM green areas: {e}")
                    other_green_data = gpd.GeoDataFrame()
            else:
                print(f"  - OSM green areas file not found, using fallback")
                other_green_data = gpd.GeoDataFrame()
            
            # Fallback: if no OSM green areas, use processed landuse data
            if len(other_green_data) == 0:
                print(f"  - Using fallback: processed landuse green areas")
                other_green_data = landuse[
                    (landuse["category"] == "green") &
                    (landuse["area_m2"] >= min_area) &
                    ~((landuse["landuse"] == "forest") | (landuse["natural"] == "forest")) &
                    ~((landuse["landuse"] == "farmland") | (landuse["natural"] == "farmland"))
                ]
                if len(other_green_data) > 0:
                    other_green_data.plot(ax=ax, color="#7FB069", alpha=0.8, edgecolor="none", label="Other Green Areas (Fallback)")
                    print(f"    - Plotted fallback green areas: {len(other_green_data)} areas")
            
            # 5. Residential (beige) - only areas > 1000 m²
            residential_data = landuse[
                (landuse["landuse"] == "residential") &
                (landuse["area_m2"] >= min_area)
            ]
            if len(residential_data) > 0:
                residential_data.plot(ax=ax, color="#F5F5DC", alpha=0.8, edgecolor="none", label="Residential")
                print(f"  - Plotted residential: {len(residential_data)} areas (filtered)")
            
            # 6. Industrial (light gray) - only areas > 1000 m²
            industrial_data = landuse[
                (landuse["landuse"] == "industrial") &
                (landuse["area_m2"] >= min_area)
            ]
            if len(industrial_data) > 0:
                industrial_data.plot(ax=ax, color="#D3D3D3", alpha=0.8, edgecolor="none", label="Industrial")
                print(f"  - Plotted industrial: {len(industrial_data)} areas (filtered)")
            
            # 7. Commercial (light pink) - only areas > 1000 m²
            commercial_data = landuse[
                ((landuse["landuse"] == "commercial") | (landuse["landuse"] == "retail")) &
                (landuse["area_m2"] >= min_area)
            ]
            if len(commercial_data) > 0:
                commercial_data.plot(ax=ax, color="#FFB6C1", alpha=0.8, edgecolor="none", label="Commercial")
                print(f"  - Plotted commercial: {len(commercial_data)} areas (filtered)")
            
            # Print summary of filtering
            total_areas = len(landuse)
            filtered_areas = len(forest_data) + len(farmland_data) + len(park_data) + len(other_green_data) + len(residential_data) + len(industrial_data) + len(commercial_data)
            print(f"  - Total areas: {total_areas}, Plotted areas: {filtered_areas}, Filtered out: {total_areas - filtered_areas} small areas")
    
    # Plot roads (clipped to city boundary with buffer) - more transparent as base layer
    if data["roads"] is not None:
        roads = data["roads"].to_crs(PLOT_CRS)
        # Clip road geometries to city boundary for clean edges
        roads = roads[roads.intersects(city_boundary_buffered)].copy()
        if len(roads) > 0:
            # Clip each road geometry to the city boundary
            roads["geometry"] = roads.geometry.intersection(city_boundary_buffered)
            # Remove any geometries that became empty after clipping
            roads = roads[~roads.geometry.is_empty]
            
            roads.plot(ax=ax, color="#8B7355", linewidth=0.6, alpha=0.3)  # Brown, more transparent
    
    # Plot categorized PT stops (clipped to city boundary with buffer)
    if data["pt_stops"] is not None:
        pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
        # Clip PT stop geometries to city boundary for clean edges
        pt_stops = pt_stops[pt_stops.intersects(city_boundary_buffered)].copy()
        if len(pt_stops) > 0:
            # Old PT stop categories removed - all stops now use Brick Red
            
            # Plot PT stops by type using multiple fields for comprehensive categorization
            # Plot PT stops by type - all in one color (Brick Red) at 80% opacity (20% smaller)
            
                        # S-Bahn stops (railway field) - with white hairline stroke
            sbahn_stops = pt_stops[pt_stops["railway"] == "stop"]
            if len(sbahn_stops) > 0:
                sbahn_stops.plot(ax=ax, marker="o", color="#C3423F", markersize=19, 
                               alpha=0.8, edgecolor="white", linewidth=0.5, label="S-Bahn Stop")
            
            # U-Bahn entrances (railway field) - with white hairline stroke
            ubahn_entrances = pt_stops[pt_stops["railway"] == "subway_entrance"]
            if len(ubahn_entrances) > 0:
                ubahn_entrances.plot(ax=ax, marker="o", color="#C3423F", markersize=21, 
                                    alpha=0.8, edgecolor="white", linewidth=0.5, label="U-Bahn Entrance")
            
            # Tram stops (railway field) - with white hairline stroke
            tram_stops = pt_stops[pt_stops["railway"] == "tram_stop"]
            if len(tram_stops) > 0:
                tram_stops.plot(ax=ax, marker="o", color="#C3423F", markersize=19, 
                              alpha=0.8, edgecolor="white", linewidth=0.5, label="Tram Stop")
            
            # Catch-all for any remaining PT stops to ensure they're all Brick Red - with white hairline stroke
            # Get all PT stops that weren't plotted above
            plotted_stops = pd.concat([sbahn_stops, ubahn_entrances, tram_stops], ignore_index=True)
            remaining_stops = pt_stops[~pt_stops.index.isin(plotted_stops.index)]
            if len(remaining_stops) > 0:
                print(f"DEBUG: Found {len(remaining_stops)} remaining PT stops to plot in Brick Red")
                remaining_stops.plot(ax=ax, marker="o", color="#C3423F", markersize=19, 
                                    alpha=0.8, edgecolor="white", linewidth=0.5, label="Other PT Stop")
            
            # Multimodal hubs removed - only major transport stops shown
    
    # Plot district boundaries - 10% opacity
    districts.boundary.plot(ax=ax, color="#2F4F4F", linewidth=1.5, alpha=0.1)
    
    _add_basemap(ax, extent)
    # Apply style without North arrow and scale bar (we add our own scale bar)
    ax.set_aspect("equal")
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_axis_off()
    # Main title in English - Standard Bold 14
    ax.set_title("Stuttgart — Land Use + Roads + PT Stops", fontsize=14, fontweight="bold", 
                 pad=30)
    
    # German subtitle below - Standard Italic 12 (closer to English title like test 015)
    ax.text(0.5, 0.97, "Stuttgart — Flächennutzung + Straßen + ÖPNV-Haltestellen", 
            transform=ax.transAxes, ha='center', fontsize=12, fontstyle='italic', 
            color="#333333")
    
    # Add comprehensive legend
    legend_elements = []
    
    # Add land use legend items for simplified categories - bilingual
    # 1. Forest (darkest sage green)
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#4A5D4A", alpha=0.2, 
                                      label="Forest / Wald"))
    
    # 2. Farmland (medium sage green)
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#7FB069", alpha=0.2, 
                                      label="Farmland / Ackerland"))
    
    # 3. Real Parks from OSM
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#9DC183", alpha=0.2, 
                                      label="Parks (Schlossgarten, Rosenstein, etc.) / Parks"))
    
    # 4. Other Green Areas (combined)
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#9DC183", alpha=0.2
                                         
                                         , 
                                      label="Other Green Areas / Andere Grünflächen"))
    
    # 5. Residential
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#F5F5DC", alpha=0.8, 
                                      label="Residential / Wohngebiet"))
    
    # 6. Industrial
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#D3D3D3", alpha=0.8, 
                                      label="Industrial / Industriegebiet"))
    
    # 7. Commercial
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#FFB6C1", alpha=0.8, 
                                      label="Commercial / Gewerbegebiet"))
    
    # Add roads legend - bilingual
    legend_elements.append(plt.Line2D([0], [0], color='#8B7355', alpha=0.3, linewidth=2, label='Roads / Straßen'))
    
    # Add city boundary legend - bilingual
    legend_elements.append(plt.Line2D([0], [0], color='#666666', alpha=0.4, linewidth=3, label='City Boundary / Stadtgrenze'))
    
    # Add PT stops legend items - all in one color (Brick Red)
    legend_elements.append(plt.Line2D([0], [0], marker="o", color="#C3423F", markersize=8, label="PT Stop / ÖPNV-Haltestelle"))
    
    # Create legend with multiple columns for better organization - bilingual title
    # Land use on left, PT on right, 20% bigger font
    ax.legend(handles=legend_elements, loc='upper right', fontsize=8, ncol=2, 
              title="Map Legend / Kartenlegende", title_fontsize=12,
              bbox_to_anchor=(1.02, 1.0))  # Move legend outside the plot area
    

    _add_scale_bar(ax, extent)
    
    _save(fig, "01_overview_landuse_roads_pt.png")
    
    # ===== MAPA 1B: DENSIDADE POPULACIONAL =====
    print("  🗺️ Generating population density map...")
    generate_population_density_map(data, city_boundary_buffered)
    
    # ===== KEPLER.GL EXPORT =====
    # UNCOMMENT THE LINE BELOW TO EXPORT DATA FOR KEPLER.GL
    # export_to_kepler(data, city_boundary_buffered, Path(f"../outputs/stuttgart_maps_{RUN_NUMBER:03d}/maps"))

def generate_population_density_map(data, city_boundary_buffered):
    """Generate population density map with same styling as landuse map"""
    print("    🏘️ Creating population density background...")
    
    # Create figure with same size and styling
    fig, ax = plt.subplots(1, 1, figsize=(35, 25))
    
    # Plot districts with population density as background
    if data["districts"] is not None:
        districts = data["districts"].to_crs(PLOT_CRS)
        
        # Calculate population density (people per km²)
        districts["area_km2"] = districts.geometry.area / 1_000_000  # Convert m² to km²
        districts["pop_density"] = districts["pop"] / districts["area_km2"]
        
        # Create population density plot with color gradient
        districts.plot(
            ax=ax,
            column="pop_density",
            cmap="YlOrRd",  # Yellow to Orange to Red (low to high density)
            legend=True,
            legend_kwds={
                "label": "Population Density (people/km²)",
                "orientation": "horizontal",
                "shrink": 0.8,
                "aspect": 30,
                "pad": 0.1
            }
        )
        
        print(f"    ✅ Population density range: {districts['pop_density'].min():.0f} - {districts['pop_density'].max():.0f} people/km²")
    
    # Plot roads on top
    if data["roads"] is not None:
        roads = data["roads"].to_crs(PLOT_CRS)
        roads.plot(ax=ax, color="#8B7355", alpha=0.3, linewidth=0.5)
        print(f"    ✅ Plotted {len(roads)} road segments")
    
    # Plot PT stops on top
    if data["pt_stops"] is not None:
        pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
        pt_stops.plot(ax=ax, color="#C3423F", alpha=0.8, markersize=3)
        print(f"    ✅ Plotted {len(pt_stops)} PT stops")
    
    # Plot city boundary
    city_boundary_geom = gpd.GeoSeries([city_boundary_buffered], crs=PLOT_CRS)
    city_boundary_geom.boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.4)
    
    # Set title and subtitle (same style as landuse map)
    ax.set_title("Stuttgart — Population Density + Roads + PT Stops", 
                 fontsize=14, fontweight="bold", pad=30)
    
    # German subtitle
    ax.text(0.5, 0.97, "Stuttgart — Bevölkerungsdichte + Straßen + ÖPNV-Haltestellen",
            transform=ax.transAxes, ha='center', fontsize=12, fontstyle='italic',
            color="#333333")
    
    # Set extent with same padding
    extent = tuple(districts.total_bounds)
    x_padding = (extent[2] - extent[0]) * 0.15
    y_padding = (extent[3] - extent[1]) * 0.15
    extent = (extent[0] - x_padding, extent[1] - y_padding, 
              extent[2] + x_padding, extent[3] + y_padding)
    
    # Set plot properties
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_aspect('equal')
    ax.set_axis_off()
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    # Save the map
    _save(fig, "01b_overview_population_density_roads_pt.png")
    print(f"    💾 Saved population density map")

def export_to_kepler(data, city_boundary, output_dir):
    """Export all map layers to GeoJSON for use in Kepler.gl"""
    print("📤 Exporting data for Kepler.gl...")
    
    # Create Kepler data directory
    kepler_dir = output_dir / "kepler_data"
    kepler_dir.mkdir(exist_ok=True)
    
    # Define data directories
    DATA_DIR = Path("../../../../main_pipeline/areas/stuttgart/data_final")
    PROCESSED_DIR = DATA_DIR / "processed"
    
    try:
        # 1. Export city boundary
        city_boundary_gdf = gpd.GeoDataFrame(
            geometry=[city_boundary], 
            crs=PLOT_CRS
        ).to_crs("EPSG:4326")  # Convert to WGS84 for Kepler
        city_boundary_gdf.to_file(kepler_dir / "01_city_boundary.geojson", driver="GeoJSON")
        print(f"  ✅ City boundary exported to c1pler_data/01_city_boundary.geojson")
        
        # 2. Export districts
        districts_kepler = data["districts"].to_crs("EPSG:4326")
        districts_kepler.to_file(kepler_dir / "02_districts.geojson", driver="GeoJSON")
        print(f"  ✅ Districts exported to kepler_data/02_districts.geojson")
        
        # 3. Export roads
        if data["roads"] is not None:
            roads_kepler = data["roads"].to_crs("EPSG:4326")
            roads_kepler.to_file(kepler_dir / "03_roads.geojson", driver="GeoJSON")
            print(f"  ✅ Roads exported to kepler_data/03_roads.geojson")
        
        # 4. Export PT stops
        if data["pt_stops"] is not None:
            pt_stops_kepler = data["pt_stops"].to_crs("EPSG:4326")
            pt_stops_kepler.to_file(kepler_dir / "04_pt_stops.geojson", driver="GeoJSON")
            print(f"  ✅ PT stops exported to kepler_data/04_pt_stops.geojson")
        
        # 5. Export land use categories separately
        if data["landuse"] is not None:
            landuse = data["landuse"].to_crs(PLOT_CRS)
            
            # Filter and clip to city boundary
            landuse = landuse[landuse.intersects(city_boundary)].copy()
            if len(landuse) > 0:
                landuse["geometry"] = landuse.geometry.intersection(city_boundary)
                landuse = landuse[~landuse.geometry.is_empty]
                
                # Calculate area and filter small areas
                landuse["area_m2"] = landuse.geometry.area
                min_area = 1000
                landuse_filtered = landuse[landuse["area_m2"] >= min_area].copy()
                
                # Add category column for easier styling in Kepler
                def categorize_landuse(row):
                    if ((row["landuse"] == "forest") or (row["natural"] == "forest")):
                        return "Forest"
                    elif ((row["landuse"] == "farmland") or (row["natural"] == "farmland")):
                        return "Farmland"
                    elif row["landuse"] == "residential":
                        return "Residential"
                    elif row["landuse"] == "industrial":
                        return "Industrial"
                    elif row["landuse"] in ["commercial", "retail"]:
                        return "Commercial"
                    else:
                        return "Other"
                
                landuse_filtered["category"] = landuse_filtered.apply(categorize_landuse, axis=1)
                
                # Export to WGS84
                landuse_kepler = landuse_filtered.to_crs("EPSG:4326")
                landuse_kepler.to_file(kepler_dir / "05_landuse.geojson", driver="GeoJSON")
                print(f"  ✅ Land use exported to kepler_data/05_landuse.geojson ({len(landuse_kepler)} areas)")
        
        # 6. Export OSM green areas
        green_areas_file = PROCESSED_DIR / "green_areas_categorized.parquet"
        if green_areas_file.exists():
            try:
                all_green_areas = gpd.read_parquet(green_areas_file)
                all_green_areas = all_green_areas.to_crs(PLOT_CRS)
                
                # Clip to city boundary
                all_green_areas = all_green_areas[all_green_areas.intersects(city_boundary)].copy()
                if len(all_green_areas) > 0:
                    all_green_areas["geometry"] = all_green_areas.geometry.intersection(city_boundary)
                    all_green_areas = all_green_areas[~all_green_areas.geometry.is_empty]
                    
                    # Add simplified category for Kepler styling
                    def categorize_green(row):
                        if row['osm_tag_key'] == 'leisure' and row['osm_tag_value'] == 'park':
                            return "Parks"
                        elif row['osm_tag_key'] == 'landuse' and row['osm_tag_value'] == 'allotments':
                            return "Allotments"
                        elif row['osm_tag_key'] == 'leisure' and row['osm_tag_value'] == 'garden':
                            return "Gardens"
                        elif row['osm_tag_key'] == 'landuse' and row['osm_tag_value'] == 'meadow':
                            return "Meadows"
                        elif row['osm_tag_key'] == 'landuse' and row['osm_tag_value'] == 'grass':
                            return "Grass"
                        elif row['osm_tag_key'] == 'leisure' and row['osm_tag_value'] == 'playground':
                            return "Playgrounds"
                        else:
                            return "Other Green"
                    
                    all_green_areas["green_category"] = all_green_areas.apply(categorize_green, axis=1)
                    
                    # Export to WGS84
                    green_areas_kepler = all_green_areas.to_crs("EPSG:4326")
                    green_areas_kepler.to_file(kepler_dir / "06_green_areas.geojson", driver="GeoJSON")
                    print(f"  ✅ Green areas exported to kepler_data/06_green_areas.geojson ({len(green_areas_kepler)} areas)")
                    
            except Exception as e:
                print(f"  ❌ Error exporting green areas: {e}")
        
        # 7. Create a README file with styling suggestions
        readme_content = """# Kepler.gl Data Export

This folder contains all the map layers exported from the Stuttgart analysis for use in Kepler.gl.

## Files:

1. **01_city_boundary.geojson** - City administrative boundary
2. **02_districts.geojson** - District boundaries with population data
3. **03_roads.geojson** - Road network
4. **04_pt_stops.geojson** - Public transport stops
5. **05_landuse.geojson** - Land use categories (Forest, Farmland, Residential, Industrial, Commercial, Other)
6. **06_green_areas.geojson** - OSM green areas (Parks, Allotments, Gardens, Meadows, Grass, Playgrounds, Other Green)

## Styling Suggestions:

### Land Use Colors (Sage Green Theme):
- **Forest**: #4A5D4A (darkest sage)
- **Farmland**: #7FB069 (medium sage)
- **Residential**: #DAA520 (burned yellow)
- **Industrial**: #D3D3D3 (light gray)
- **Commercial**: #FFB6C1 (light pink)

### Green Areas Colors:
- **Parks**: #9DC183 (light sage)
- **Allotments**: #5A7C65 (darker sage)
- **Gardens**: #7FB069 (medium sage)
- **Meadows**: #9DC183 (light sage)
- **Grass**: #B8D4BA (very light sage)
- **Playgrounds**: #A8E6CF (mint green)

### Transparency:
- Green areas: 20% (more opaque)
- Urban areas: 70% (more transparent)

## Import Instructions:
1. Open Kepler.gl
2. Import each GeoJSON file as a separate layer
3. Apply the suggested colors and transparency
4. Adjust as needed for your visualization
"""
        
        with open(kepler_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)
        
        print(f"  ✅ README created with styling suggestions")
        
        # 8. Create Kepler.gl configuration file
        kepler_config = create_kepler_config(kepler_dir)
        with open(kepler_dir / "kepler_config.json", "w", encoding="utf-8") as f:
            json.dump(kepler_config, f, indent=2)
        
        print(f"  ✅ Kepler.gl configuration exported to kepler_data/kepler_config.json")
        print(f"  📁 All data exported to: {kepler_dir}")
        
    except Exception as e:
        print(f"  ❌ Error exporting to Kepler: {e}")

def create_kepler_config(kepler_dir):
    """Create a complete Kepler.gl configuration with all layers styled"""
    
    config = {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [
                    {
                        "id": "city_boundary",
                        "type": "geojson",
                        "config": {
                            "dataId": "city_boundary",
                            "label": "City Boundary",
                            "color": [102, 102, 102],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 3,
                                "strokeColor": [102, 102, 102],
                                "colorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "strokeColorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "radius": 10,
                                "sizeRange": [0, 10],
                                "radiusRange": [0, 50],
                                "heightRange": [0, 500],
                                "weightRange": [0, 500],
                                "stroked": True,
                                "filled": False,
                                "enable3D": False,
                                "wireframe": False
                            },
                            "hidden": False,
                            "textLabel": []
                        },
                        "visualChannels": {}
                    },
                    {
                        "id": "districts",
                        "type": "geojson",
                        "config": {
                            "dataId": "districts",
                            "label": "Districts",
                            "color": [128, 128, 128],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.3,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [128, 128, 128],
                                "colorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "strokeColorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "radius": 10,
                                "sizeRange": [0, 10],
                                "radiusRange": [0, 50],
                                "heightRange": [0, 500],
                                "weightRange": [0, 500],
                                "stroked": True,
                                "filled": True,
                                "enable3D": False,
                                "wireframe": False
                            },
                            "hidden": False,
                            "textLabel": []
                        },
                        "visualChannels": {}
                    },
                    {
                        "id": "roads",
                        "type": "geojson",
                        "config": {
                            "dataId": "roads",
                            "label": "Roads",
                            "color": [139, 115, 85],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.3,
                                "strokeOpacity": 0.3,
                                "thickness": 1,
                                "strokeColor": [139, 115, 85],
                                "colorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "strokeColorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "radius": 10,
                                "sizeRange": [0, 10],
                                "radiusRange": [0, 50],
                                "heightRange": [0, 500],
                                "weightRange": [0, 500],
                                "stroked": True,
                                "filled": False,
                                "enable3D": False,
                                "wireframe": False
                            },
                            "hidden": False,
                            "textLabel": []
                        },
                        "visualChannels": {}
                    },
                    {
                        "id": "pt_stops",
                        "type": "geojson",
                        "config": {
                            "dataId": "pt_stops",
                            "label": "PT Stops",
                            "color": [195, 66, 63],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 1,
                                "thickness": 0.5,
                                "strokeColor": [255, 255, 255],
                                "colorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "strokeColorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "radius": 8,
                                "sizeRange": [0, 10],
                                "radiusRange": [0, 50],
                                "heightRange": [0, 500],
                                "weightRange": [0, 500],
                                "stroked": True,
                                "filled": True,
                                "enable3D": False,
                                "wireframe": False
                            },
                            "hidden": False,
                            "textLabel": []
                        },
                        "visualChannels": {}
                    },
                    {
                        "id": "landuse",
                        "type": "geojson",
                        "config": {
                            "dataId": "landuse",
                            "label": "Land Use",
                            "color": [127, 176, 105],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.7,
                                "strokeOpacity": 0.8,
                                "thickness": 0,
                                "strokeColor": [0, 0, 0],
                                "colorRange": {"name": "Custom", "type": "categorical", "category": "Custom", "colors": ["#4A5D4A", "#7FB069", "#DAA520", "#D3D3D3", "#FFB6C1"]},
                                "strokeColorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "radius": 10,
                                "sizeRange": [0, 10],
                                "radiusRange": [0, 50],
                                "heightRange": [0, 500],
                                "weightRange": [0, 500],
                                "stroked": False,
                                "filled": True,
                                "enable3D": False,
                                "wireframe": False
                            },
                            "hidden": False,
                            "textLabel": []
                        },
                        "visualChannels": {
                            "colorField": {"name": "category", "type": "string"},
                            "colorScale": "ordinal"
                        }
                    },
                    {
                        "id": "green_areas",
                        "type": "geojson",
                        "config": {
                            "dataId": "green_areas",
                            "label": "Green Areas",
                            "color": [157, 193, 131],
                            "columns": {"geojson": "_geojson"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.2,
                                "strokeOpacity": 0.8,
                                "thickness": 0,
                                "strokeColor": [0, 0, 0],
                                "colorRange": {"name": "Custom", "type": "categorical", "category": "Custom", "colors": ["#9DC183", "#5A7C65", "#7FB069", "#9DC183", "#B8D4BA", "#A8E6CF"]},
                                "strokeColorRange": {"name": "Global Warming", "type": "sequential", "category": "Uber", "colors": ["#5A1846", "#900C3F", "#C70039", "#E3611C", "#F1920E", "#FFC300"]},
                                "radius": 10,
                                "sizeRange": [0, 10],
                                "radiusRange": [0, 50],
                                "heightRange": [0, 500],
                                "weightRange": [0, 500],
                                "stroked": False,
                                "filled": True,
                                "enable3D": False,
                                "wireframe": False
                            },
                            "hidden": False,
                            "textLabel": []
                        },
                        "visualChannels": {
                            "colorField": {"name": "green_category", "type": "string"},
                            "colorScale": "ordinal"
                        }
                    }
                ],
                "interactionConfig": {
                    "tooltip": {"fieldsToShow": {"city_boundary": [], "districts": ["district_norm", "pop"], "roads": [], "pt_stops": ["name", "amenity"], "landuse": ["category", "area_m2"], "green_areas": ["green_category", "name"]}, "enabled": True},
                    "brush": {"size": 0.5, "enabled": False},
                    "geocoder": {"enabled": False},
                    "coordinate": {"enabled": False}
                },
                "layerBlending": "normal",
                "splitMaps": [],
                "animationConfig": {"currentTime": None, "speed": 1}
            },
                            "mapState": {
                    "bearing": 0,
                    "dragRotate": False,
                    "latitude": 48.7758,
                    "longitude": 9.1829,
                    "pitch": 0,
                    "zoom": 10.5,
                    "isSplit": False
                },
                "uiState": {
                    "readOnly": False,
                    "activeSidePanel": "layer",
                    "currentModal": None,
                    "mapControls": {
                        "visibleLayers": {
                            "show": True
                        },
                        "mapLegend": {
                            "show": True,
                            "active": True
                        },
                        "3d": {
                            "show": False
                        },
                        "draw": {
                            "show": False
                        },
                        "measure": {
                            "show": False
                        },
                        "split": {
                            "show": False
                        }
                    }
                },
            "mapStyle": {
                "styleType": "dark",
                "topLayerGroups": {},
                "visibleLayerGroups": {
                    "label": True,
                    "road": True,
                    "border": False,
                    "building": True,
                    "water": True,
                    "land": True,
                    "3d building": False
                },
                "threeDBuildingColor": [9.665468314012013, 17.18305478057247, 31.1446957895717],
                "mapStyles": {}
            }
        }
    }
    
    return config

def generate_choropleth_maps(data, districts_with_kpis):
    """Generate choropleth maps for different KPIs"""
    print("🗺️ Generating choropleth maps...")
    
    # Get city extent
    districts = districts_with_kpis.copy()
    extent = tuple(districts.total_bounds)
    
    # Define pastel color schemes
    color_schemes = {
        "mobility": ["#FFE5E5", "#FFB3B3", "#FF8080", "#FF4D4D", "#FF1A1A", "#E60000"],  # Red to dark red
        "transport": ["#E6F3FF", "#B3D9FF", "#80BFFF", "#4DA6FF", "#1A8CFF", "#0073E6"],  # Blue to dark blue
        "walkability": ["#FFF2E6", "#FFD9B3", "#FFBF80", "#FFA64D", "#FF8C1A", "#E67300"],  # Orange to dark orange
        "amenities": ["#F0E6FF", "#D9B3FF", "#C280FF", "#AB4DFF", "#941AFF", "#7D00E6"],  # Purple to dark purple
        "green": ["#E6FFE6", "#B3FFB3", "#80FF80", "#4DFF4D", "#1AFF1A", "#00E600"],  # Green to dark green
        "area": ["#FFE6E6", "#FFB3B3", "#FF8080", "#FF4D4D", "#FF1A1A", "#E60000"]  # Red to dark red
    }
    
    # Map 1: Overall Mobility Score (combination of PT density and service density)
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Calculate mobility score (normalized 0-1)
    mobility_score = (districts["pt_stop_density"] / districts["pt_stop_density"].max() * 0.6 + 
                     districts["service_density"] / districts["service_density"].max() * 0.4)
    districts["mobility_score"] = mobility_score
    
    # Plot districts with mobility score
    districts.plot(column="mobility_score", ax=ax, cmap="Reds", 
                  legend=True, legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Overall Mobility Score", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Gesamtbeweglichkeits-Score*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _save(fig, "03_choropleth_mobility_score.png")
    
    # Map 2: Public Transport Density
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    districts.plot(column="pt_stop_density", ax=ax, cmap="Blues", 
                  legend=True, legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Public Transport Density", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — ÖPNV-Dichte*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _save(fig, "04_choropleth_pt_density.png")
    
    # Map 3: Walkability Score (based on amenities and PT stops)
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    walkability_score = (districts["amenities_count"] / districts["amenities_count"].max() * 0.7 + 
                        districts["pt_stops_count"] / districts["pt_stops_count"].max() * 0.3)
    districts["walkability_score"] = walkability_score
    
    districts.plot(column="walkability_score", ax=ax, cmap="Oranges", 
                  legend=True, legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Walkability Score", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Fußgängerfreundlichkeits-Score*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _save(fig, "05_choropleth_walkability.png")
    
    # Map 4: Amenity Density
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    districts.plot(column="service_density", ax=ax, cmap="Purples", 
                  legend=True, legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Amenity Density", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Einrichtungsdichte*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _save(fig, "06_choropleth_amenity_density.png")
    
    # Map 5: Green Space Ratio
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    districts.plot(column="green_landuse_pct", ax=ax, cmap="Greens", 
                  legend=True, legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Green Space Ratio", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Grünflächenanteil*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _save(fig, "07_choropleth_green_space.png")
    
    # Map 6: District Area
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    districts.plot(column="area_km2", ax=ax, cmap="Reds", 
                  legend=True, legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — District Area (km²)", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Bezirksfläche (km²)*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _save(fig, "08_choropleth_district_area.png")
    
    # Bivariate Choropleth Maps with Pastel/Earthy Tones
    print("  🎨 Generating bivariate choropleth maps...")
    
    # Bivariate 1: Green Access vs PT Density
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    
    # Create bivariate classification
    green_quantiles = pd.qcut(districts["green_landuse_pct"], q=5, labels=False)
    pt_quantiles = pd.qcut(districts["pt_stop_density"], q=5, labels=False)
    
    # Combine into bivariate index (0-24 for 5x5 grid)
    bivariate_index = green_quantiles * 5 + pt_quantiles
    
    # Create pastel/earthy color palette for bivariate
    bivariate_colors = [
        "#F7F7F7", "#E8F5E8", "#D1E8D1", "#B8D8B8", "#9FC8A0",  # Row 1: Low green, varying PT
        "#F0F0F0", "#E0F0E0", "#C8E0C8", "#B0D0B0", "#98C098",  # Row 2
        "#E8E8E8", "#D8E8D8", "#C0D8C0", "#A8C8A8", "#90B890",  # Row 3
        "#E0E0E0", "#D0E0D0", "#B8D0B8", "#A0C0A0", "#88B088",  # Row 4
        "#D8D8D8", "#C8D8C8", "#B0C8B0", "#98B898", "#80A880"   # Row 5: High green, varying PT
    ]
    
    # Plot bivariate choropleth
    districts.plot(column=bivariate_index, ax=ax, 
                  cmap="RdYlGn", legend=True, 
                  legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Bivariate: Green Access vs PT Density", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Bivariat: Grünflächen vs ÖPNV-Dichte*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add custom legend
    legend_elements = [
        plt.Rectangle((0,0),1,1, facecolor='#F7F7F7', edgecolor='black', label='Low Green, Low PT'),
        plt.Rectangle((0,0),1,1, facecolor='#E8F5E8', edgecolor='black', label='Low Green, High PT'),
        plt.Rectangle((0,0),1,1, facecolor='#80A880', edgecolor='black', label='High Green, Low PT'),
        plt.Rectangle((0,0),1,1, facecolor='#9FC8A0', edgecolor='black', label='High Green, High PT')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
    
    _save(fig, "09_bivariate_green_vs_pt.png")
    
    # Bivariate 2: Walkability vs Green Space
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    
    # Create walkability vs green space bivariate
    walk_quantiles = pd.qcut(districts["walkability_score"], q=5, labels=False)
    green_quantiles = pd.qcut(districts["green_landuse_pct"], q=5, labels=False)
    
    bivariate_index2 = walk_quantiles * 5 + green_quantiles
    
    # Earthy tone palette
    earthy_colors = [
        "#F5F5DC", "#E6D7B8", "#D4C4A7", "#C2B1A6", "#B0A4A5",  # Row 1: Low walkability
        "#F0E6D2", "#E1D3B6", "#CFC0A5", "#BDADA4", "#AB9AA3",  # Row 2
        "#EBD7C8", "#DCCFB4", "#CABCA3", "#B8A9A2", "#A696A1",  # Row 3
        "#E6C8BE", "#D7CBB2", "#C5B8A1", "#B3A5A0", "#A1929F",  # Row 4
        "#E1B9B4", "#D2C7B0", "#C0B49F", "#AEA19E", "#9C8E9D"   # Row 5: High walkability
    ]
    
    districts.plot(column=bivariate_index2, ax=ax, 
                  cmap="YlOrBr", legend=True,
                  legend_kwds={"shrink": 0.8, "aspect": 20})
    
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Bivariate: Walkability vs Green Space", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Bivariat: Fußgängerfreundlichkeit vs Grünflächen*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add custom legend
    legend_elements2 = [
        plt.Rectangle((0,0),1,1, facecolor='#F5F5DC', edgecolor='black', label='Low Walk, Low Green'),
        plt.Rectangle((0,0),1,1, facecolor='#E6D7B8', edgecolor='black', label='Low Walk, High Green'),
        plt.Rectangle((0,0),1,1, facecolor='#9C8E9D', edgecolor='black', label='High Walk, Low Green'),
        plt.Rectangle((0,0),1,1, facecolor='#C0B49F', edgecolor='black', label='High Walk, High Green')
    ]
    ax.legend(handles=legend_elements2, loc='upper right', fontsize=9)
    
    _save(fig, "10_bivariate_walkability_vs_green.png")
    
    return districts

def generate_district_atlas(data, districts_with_kpis):
    """Generate maps for selected districts"""
    print("🗺️ Generating district atlas...")
    
    selected_districts = districts_with_kpis[districts_with_kpis["district_norm"].isin(SELECTED_DISTRICTS)].copy()
    
    for idx, district in selected_districts.iterrows():
        district_name = district["district_norm"]
        print(f"  📍 Processing {district_name}...")
        
        # Get district extent with buffer
        district_geom = district.geometry
        buffer_distance = 1000  # 1km buffer
        district_buffer = district_geom.buffer(buffer_distance)
        extent = tuple(district_buffer.bounds)
        
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        
        # Plot district
        gpd.GeoDataFrame([district], geometry="geometry", crs=PLOT_CRS).plot(
            ax=ax, color="lightblue", alpha=0.7, edgecolor="black", linewidth=2
        )
        
        # Plot land use
        if data["landuse"] is not None:
            landuse = data["landuse"].to_crs(PLOT_CRS)
            landuse_in_district = landuse[landuse.intersects(district_buffer)]
            if len(landuse_in_district) > 0:
                landuse_in_district.plot(ax=ax, alpha=0.6, color="#90EE90")  # Light green
        
        # Plot roads
        if data["roads"] is not None:
            roads = data["roads"].to_crs(PLOT_CRS)
            roads_in_district = roads[roads.intersects(district_buffer)]
            if len(roads_in_district) > 0:
                roads_in_district.plot(ax=ax, color="#8B7355", linewidth=1.5, alpha=0.8)  # Brown
        
        # Plot PT stops
        if data["pt_stops"] is not None:
            pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
            pt_in_district = pt_stops[pt_stops.intersects(district_buffer)]
            if len(pt_in_district) > 0:
                pt_in_district.plot(ax=ax, color="#CD5C5C", markersize=30, alpha=0.8)  # Indian red
        
        # Plot amenities
        if data["amenities"] is not None:
            amenities = data["amenities"].to_crs(PLOT_CRS)
            amen_in_district = amenities[amenities.intersects(district_buffer)]
            if len(amen_in_district) > 0:
                amen_in_district.plot(ax=ax, color="#87CEEB", markersize=20, alpha=0.7)  # Sky blue
        
        # Set extent
        ax.set_xlim(extent[0], extent[2])
        ax.set_ylim(extent[1], extent[3])
        
        # Add title with KPI info
        title = f"{district_name} — District Analysis"
        subtitle = f"PT: {district['pt_stops_count']} stops, Green: {district['green_landuse_pct']:.1f}%, Cycle: {district['cycle_length_km']:.1f} km"
        
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.text(0.5, 0.02, f"*{subtitle}*", 
                transform=ax.transAxes, ha='center', fontsize=10, style='italic')
        
        # Add scale bar only
        _add_scale_bar(ax, extent)
        
        # Save
        filename = f"11_district_{district_name.lower().replace(' ', '_')}.png"
        _save(fig, filename)

def generate_closeup_maps(data, districts_with_kpis):
    """Generate close-up maps for Stuttgart-Mitte with buffers"""
    print("🗺️ Generating close-up maps for Stuttgart-Mitte...")
    
    # Find Stuttgart-Mitte
    mitte = districts_with_kpis[districts_with_kpis["district_norm"] == "Mitte"].iloc[0]
    mitte_geom = mitte.geometry
    
    # Create different buffer distances for analysis
    buffers = [500, 1000, 2000]  # 500m, 1km, 2km
    
    for buffer_dist in buffers:
        buffer_geom = mitte_geom.buffer(buffer_dist)
        extent = tuple(buffer_geom.bounds)
        
        fig, ax = plt.subplots(1, 1, figsize=(18, 14))
        
        # Plot buffer area
        gpd.GeoDataFrame([{"geometry": buffer_geom}], crs=PLOT_CRS).plot(
            ax=ax, color="lightyellow", alpha=0.3, edgecolor="orange", linewidth=2
        )
        
        # Plot district
        gpd.GeoDataFrame([mitte], geometry="geometry", crs=PLOT_CRS).plot(
            ax=ax, color="lightblue", alpha=0.7, edgecolor="black", linewidth=2
        )
        
        # Plot infrastructure within buffer
        if data["landuse"] is not None:
            landuse = data["landuse"].to_crs(PLOT_CRS)
            landuse_in_buffer = landuse[landuse.intersects(buffer_geom)]
            if len(landuse_in_buffer) > 0:
                landuse_in_buffer.plot(ax=ax, alpha=0.6, color="lightgreen")
        
        if data["roads"] is not None:
            roads = data["roads"].to_crs(PLOT_CRS)
            roads_in_buffer = roads[roads.intersects(buffer_geom)]
            if len(roads_in_buffer) > 0:
                roads_in_buffer.plot(ax=ax, color="gray", linewidth=1.5, alpha=0.8)
        
        if data["pt_stops"] is not None:
            pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
            pt_in_buffer = pt_stops[pt_stops.intersects(buffer_geom)]
            if len(pt_in_buffer) > 0:
                pt_in_buffer.plot(ax=ax, color="red", markersize=40, alpha=0.8)
        
        if data["amenities"] is not None:
            amenities = data["amenities"].to_crs(PLOT_CRS)
            amen_in_buffer = amenities[amenities.intersects(buffer_geom)]
            if len(amen_in_buffer) > 0:
                amen_in_buffer.plot(ax=ax, color="blue", markersize=25, alpha=0.7)
        
        # Set extent
        ax.set_xlim(extent[0], extent[2])
        ax.set_ylim(extent[1], extent[3])
        
        # Add title
        title = f"Stuttgart-Mitte — {buffer_dist}m Buffer Analysis"
        ax.set_title(title, fontsize=16, fontweight="bold")
        
        # Add scale bar only
        _add_scale_bar(ax, extent)
        
        # Save
        filename = f"16_mitte_closeup_{buffer_dist}m.png"
        _save(fig, filename)

# ---------- Plot Helpers ----------
def _add_basemap(ax, extent):
    """Add basemap"""
    try:
        cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, alpha=0.30, crs=PLOT_CRS)
    except Exception:
        pass

def _add_scale_bar(ax, extent):
    """Add scale bar with multiple distances - properly spaced"""
    scale_x = extent[0] + (extent[2] - extent[0]) * 0.1
    scale_y = extent[1] + (extent[3] - extent[1]) * 0.1
    
    # Only 3 scale bars: 1km, 5km, 10km - properly spaced
    scales = [
        (1000, "1 km"), 
        (5000, "5 km"),
        (10000, "10 km")
    ]
    
    for i, (length, label) in enumerate(scales):
        # MUCH MORE SPACING between scale bars to avoid overlap
        y_offset = scale_y - (i * 400)  # Increased from 200 to 400 for better separation
        ax.plot([scale_x, scale_x + length], [y_offset, y_offset], 'k-', linewidth=2)
        # Position text below the bar with more space
        ax.text(scale_x + length/2, y_offset - 120, label, ha='center', va='top', 
                fontsize=9, fontweight='bold')

def _save(fig, name):
    """Save figure with interactive display"""
    # Show the plot in an interactive window
    plt.show()
    
    # Save the figure
    out = MAPS_DIR / name
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"  💾 Saved: {name}")
    
    # Keep the figure open for inspection (don't close immediately)
    # plt.close(fig)  # Commented out to keep window open

# ---------- HTML Dashboard Generation ----------
def generate_html_dashboard(districts_with_kpis):
    """Generate HTML dashboard with KPIs and maps"""
    print("🌐 Generating HTML dashboard...")
    
    # Prepare KPI data for HTML table
    kpi_columns = ["district_norm", "pop", "area_km2", "population_density", 
                   "pt_stops_count", "pt_stop_density", "amenities_count", 
                   "service_density", "green_landuse_pct", "cycle_length_km", 
                   "cycle_infra_density"]
    
    kpi_table = districts_with_kpis[kpi_columns].copy()
    kpi_table.columns = ["District", "Population", "Area (km²)", "Pop. Density (res/km²)",
                        "PT Stops", "PT Density (stops/km²)", "Amenities", 
                        "Service Density (per 1k res)", "Green Land (%)", "Cycle Length (km)",
                        "Cycle Density (km/km²)"]
    
    # Round numeric columns
    numeric_cols = ["Area (km²)", "Pop. Density (res/km²)", "PT Density (stops/km²)",
                   "Service Density (per 1k res)", "Green Land (%)", "Cycle Length (km)",
                   "Cycle Density (km/km²)"]
    for col in numeric_cols:
        kpi_table[col] = kpi_table[col].round(2)
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stuttgart – Urban Analysis Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            line-height: 1.6;
            color: #333;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white; 
            padding: 40px; 
            text-align: center;
        }}
        .header h1 {{ 
            font-size: 2.5em; 
            margin-bottom: 15px; 
            font-weight: 300;
        }}
        .header p {{ 
            font-size: 1.2em; 
            opacity: 0.9; 
            font-weight: 300;
        }}
        .content {{ padding: 40px; }}
        .section {{ 
            margin-bottom: 50px; 
            background: #f8f9fa; 
            padding: 30px; 
            border-radius: 15px;
            border-left: 5px solid #667eea;
        }}
        .section h2 {{ 
            color: #2c3e50; 
            margin-bottom: 20px; 
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section h2::before {{
            content: "📊";
            font-size: 0.8em;
        }}
        .overview-text {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            margin-bottom: 30px;
            line-height: 1.8;
        }}
        .overview-text h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.4em;
        }}
        .overview-text p {{
            margin-bottom: 15px;
            color: #555;
        }}
        .styled-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: 'Courier New', monospace;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        .styled-table thead tr {{
            background-color: #667eea;
            color: white;
            text-align: left;
            font-weight: bold;
        }}
        .styled-table th,
        .styled-table td {{
            padding: 12px 15px;
            text-align: center;
        }}
        .styled-table tbody tr {{
            border-bottom: 1px solid #dddddd;
        }}
        .styled-table tbody tr:nth-of-type(even) {{
            background-color: #f3f3f3;
        }}
        .styled-table tbody tr:last-of-type {{
            border-bottom: 2px solid #667eea;
        }}
        .styled-table tbody tr:hover {{
            background-color: #e8f4fd;
            color: #2c3e50;
            font-weight: bold;
        }}
        .maps-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 30px;
            margin-top: 30px;
        }}
        .map-item {{
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .map-item:hover {{
            transform: translateY(-5px);
        }}
        .map-item h3 {{
            color: #34495e;
            margin-bottom: 15px;
            font-size: 1.3em;
            text-align: center;
        }}
        .map-item img {{
            width: 100%;
            height: auto;
            border-radius: 10px;
            border: 2px solid #e9ecef;
        }}
        .map-category {{
            background: #e3f2fd;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            border-left: 5px solid #2196f3;
        }}
        .map-category h3 {{
            color: #1976d2;
            margin-bottom: 10px;
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
            opacity: 0.8;
        }}
        @media (max-width: 768px) {{
            .maps-gallery {{ grid-template-columns: 1fr; }}
            .header h1 {{ font-size: 2em; }}
            .content {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Stuttgart – Urban Analysis Dashboard</h1>
            <p>Comprehensive spatial analysis of urban infrastructure and accessibility</p>
            <p><em>Umfassende räumliche Analyse der städtischen Infrastruktur und Zugänglichkeit</em></p>
        </div>
        
        <div class="content">
            <!-- Overview Section -->
            <div class="section">
                <h2>Analysis Overview</h2>
                <div class="overview-text">
                    <h3>What This Analysis Shows</h3>
                    <p>This comprehensive urban analysis examines Stuttgart's spatial characteristics across multiple dimensions:</p>
                    <ul style="margin-left: 20px; margin-bottom: 15px;">
                        <li><strong>Population Distribution:</strong> How residents are distributed across the city's 23 districts</li>
                        <li><strong>Public Transport Accessibility:</strong> PT stop density and coverage patterns</li>
                        <li><strong>Service Provision:</strong> Distribution of urban amenities relative to population</li>
                        <li><strong>Green Infrastructure:</strong> Percentage of green land use in each district</li>
                        <li><strong>Cycling Infrastructure:</strong> Cycle path density and network coverage</li>
                    </ul>
                    <p>The analysis reveals spatial patterns that can inform urban planning decisions, identify areas with service gaps, and highlight districts with strong infrastructure provision.</p>
                </div>
            </div>

            <!-- KPI Table Section -->
            <div class="section">
                <h2>District Key Performance Indicators</h2>
                <p style="margin-bottom: 20px; color: #666;">Comprehensive metrics for all 23 districts of Stuttgart</p>
                {kpi_table.to_html(classes="styled-table", index=False)}
            </div>

            <!-- Overview Maps Section -->
            <div class="section">
                <div class="map-category">
                    <h3>🌍 City Overview Maps</h3>
                    <p>High-level visualization of Stuttgart's urban fabric, infrastructure networks, and service distribution</p>
                </div>
                <div class="maps-gallery">
                    <div class="map-item">
                        <h3>Land Use + Roads + PT Stops</h3>
                        <img src="maps/01_overview_landuse_roads_pt.png" alt="Land Use, Roads, and PT Stops Overview">
                    </div>
                </div>
            </div>

            <!-- Choropleth Analysis Section -->
            <div class="section">
                <div class="map-category">
                    <h3>🎨 Choropleth Analysis Maps</h3>
                    <p>District-level KPI visualization with color-coded metrics</p>
                </div>
                <div class="maps-gallery">
                    <div class="map-item">
                        <h3>Overall Mobility Score</h3>
                        <img src="maps/03_choropleth_mobility_score.png" alt="Overall Mobility Score">
                    </div>
                    <div class="map-item">
                        <h3>Public Transport Density</h3>
                        <img src="maps/04_choropleth_pt_density.png" alt="Public Transport Density">
                    </div>
                    <div class="map-item">
                        <h3>Walkability Score</h3>
                        <img src="maps/05_choropleth_walkability.png" alt="Walkability Score">
                    </div>
                    <div class="map-item">
                        <h3>Amenity Density</h3>
                        <img src="maps/06_choropleth_amenity_density.png" alt="Amenity Density">
                    </div>
                    <div class="map-item">
                        <h3>Green Space Ratio</h3>
                        <img src="maps/07_choropleth_green_space.png" alt="Green Space Ratio">
                    </div>
                    <div class="map-item">
                        <h3>District Area</h3>
                        <img src="maps/08_choropleth_district_area.png" alt="District Area">
                    </div>
                </div>
            </div>

            <!-- Bivariate Analysis Section -->
            <div class="section">
                <div class="map-category">
                    <h3>🔀 Bivariate Analysis Maps</h3>
                    <p>Two-dimensional analysis combining different urban metrics</p>
                </div>
                <div class="maps-gallery">
                    <div class="map-item">
                        <h3>Green Access vs PT Density</h3>
                        <img src="maps/09_bivariate_green_vs_pt.png" alt="Green Access vs PT Density">
                    </div>
                    <div class="map-item">
                        <h3>Walkability vs Green Space</h3>
                        <img src="maps/10_bivariate_walkability_vs_green.png" alt="Walkability vs Green Space">
                    </div>
                </div>
            </div>

            <!-- District Atlas Section -->
            <div class="section">
                <div class="map-category">
                    <h3>🏘️ District Atlas</h3>
                    <p>Detailed analysis of selected districts: Mitte, Bad Cannstatt, Vaihingen, Zuffenhausen, and Degerloch</p>
                </div>
                <div class="maps-gallery">
                    <div class="map-item">
                        <h3>Stuttgart-Mitte District</h3>
                        <img src="maps/11_district_mitte.png" alt="Stuttgart-Mitte District Analysis">
                    </div>
                    <div class="map-item">
                        <h3>Bad Cannstatt District</h3>
                        <img src="maps/11_district_bad_cannstatt.png" alt="Bad Cannstatt District Analysis">
                    </div>
                    <div class="map-item">
                        <h3>Vaihingen District</h3>
                        <img src="maps/11_district_vaihingen.png" alt="Vaihingen District Analysis">
                    </div>
                    <div class="map-item">
                        <h3>Zuffenhausen District</h3>
                        <img src="maps/11_district_zuffenhausen.png" alt="Zuffenhausen District Analysis">
                    </div>
                    <div class="map-item">
                        <h3>Degerloch District</h3>
                        <img src="maps/11_district_degerloch.png" alt="Degerloch District Analysis">
                    </div>
                </div>
            </div>

            <!-- Close-up Analysis Section -->
            <div class="section">
                <div class="map-category">
                    <h3>🔍 Close-up Analysis: Stuttgart-Mitte</h3>
                    <p>Detailed examination of the city center with varying buffer distances for infrastructure analysis</p>
                </div>
                <div class="maps-gallery">
                    <div class="map-item">
                        <h3>500m Buffer Analysis</h3>
                        <img src="maps/16_mitte_closeup_500m.png" alt="Stuttgart-Mitte 500m Buffer">
                    </div>
                    <div class="map-item">
                        <h3>1km Buffer Analysis</h3>
                        <img src="maps/16_mitte_closeup_1000m.png" alt="Stuttgart-Mitte 1km Buffer">
                    </div>
                    <div class="map-item">
                        <h3>2km Buffer Analysis</h3>
                        <img src="maps/16_mitte_closeup_2000m.png" alt="Stuttgart-Mitte 2km Buffer">
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated with Python, GeoPandas, and Matplotlib | Data: Stuttgart Open Data + OpenStreetMap</p>
        </div>
    </div>
</body>
</html>"""
    
    # Write HTML file
    dashboard_path = OUT_DIR / "stuttgart_report.html"
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"  💾 Saved: stuttgart_report.html")

# ---------- Main Execution ----------
def main():
    """Main execution function - MODULAR: Comment/uncomment sections to generate only desired maps"""
    print("🚀 Starting Stuttgart Urban Analysis Suite...")
    print("=" * 60)
    print(f"📁 Run #{RUN_NUMBER:03d} - Output: {OUT_DIR}")
    print("=" * 60)
    
    # Create run info file
    run_info = {
        "run_number": RUN_NUMBER,
        "timestamp": pd.Timestamp.now().isoformat(),
        "output_directory": str(OUT_DIR),
        "total_maps": 18,  # Total number of maps to be generated
        "features": [
            "Area clipping to city boundaries",
            "Pastel and earthy color schemes", 
            "Legends on all maps",
            "Choropleth analysis maps",
            "Bivariate choropleth maps",
            "District atlas maps",
            "Close-up analysis maps"
        ]
    }
    
    # Save run info
    with open(OUT_DIR / "run_info.json", "w") as f:
        import json
        json.dump(run_info, f, indent=2)
    
    # 1. Load data
    data = load_data()
    if data["districts"] is None:
        print("❌ Error: Could not load districts data")
        return
    
    print(f"✅ Loaded {len(data['districts'])} districts")
    
    # ===== MAPA 1: OVERVIEW MAPS =====
    # DESCOMENTE A LINHA ABAIXO PARA GERAR APENAS O MAPA 1
    print("\n🗺️ Generating MAP 1: Overview maps...")
    generate_overview_maps(data)
    
    # ===== EXPORTAÇÃO KEPLER.GL =====
    # DESCOMENTE A LINHA ABAIXO PARA EXPORTAR DADOS PARA KEPLER.GL
    # print("📤 Exporting data for Kepler.gl...")
    # export_to_kepler(data, city_boundary_buffered, Path(f"../outputs/stuttgart_maps_{RUN_NUMBER:03d}/maps"))
    
    # ===== MAPAS 2-8: CHOROPLETH MAPS =====
    # DESCOMENTE AS LINHAS ABAIXO PARA GERAR MAPAS CHOROPLETH
    # print("\n🗺️ Generating MAPS 2-8: Choropleth maps...")
    # districts_with_kpis = calculate_district_kpis(data)
    # kpi_csv_path = OUT_DIR / "stuttgart_kpis.csv"
    # districts_with_kpis.to_csv(kpi_csv_path, index=False)
    # print(f"💾 Saved KPIs to: {kpi_csv_path}")
    # districts_with_choropleths = generate_choropleth_maps(data, districts_with_kpis)
    
    # ===== MAPAS 9-15: DISTRICT ATLAS =====
    # DESCOMENTE AS LINHAS ABAIXO PARA GERAR ATLAS DOS DISTRITOS
    # print("\n🗺️ Generating MAPS 9-15: District atlas...")
    # generate_district_atlas(data, districts_with_choropleths)
    
    # ===== MAPAS 16-18: CLOSE-UP MAPS =====
    # DESCOMENTE AS LINHAS ABAIXO PARA GERAR MAPAS DE CLOSE-UP
    # print("\n🗺️ Generating MAPS 16-18: Close-up maps...")
    # generate_closeup_maps(data, districts_with_choropleths)
    
    # ===== MAPA 19: HTML DASHBOARD =====
    # DESCOMENTE AS LINHAS ABAIXO PARA GERAR DASHBOARD HTML
    # print("\n🌐 Building HTML dashboard...")
    # generate_html_dashboard(districts_with_kpis)
    
    print("\n🎉 Selected maps generated successfully!")
    print("=" * 60)
    print(f"📁 Output directory: {OUT_DIR}")
    print(f"🗺️ Maps: {MAPS_DIR}")
    print("\n💡 To generate more maps, uncomment the desired sections above!")
    print("💡 Currently only MAP 1 (Overview) is active!")

if __name__ == "__main__":
    main()
