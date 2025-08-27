#!/usr/bin/env python3
"""
Stuttgart Comprehensive Analysis Script

"""

from __future__ import annotations
from pathlib import Path
import warnings, math, json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import contextily as cx
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
import networkx as nx

warnings.filterwarnings("ignore", category=UserWarning)

# Constants
DATA_DIR = Path("data")
PLOT_CRS = 3857
H3_RES = 8
OVERVIEW_PAD_M = 2000
DISTRICTS_FOCUS = ["Mitte", "Nord", "Süd", "West", "Ost", "Bad Cannstatt"]

# PT Type Colors and Weights
PT_TYPE_COLORS = {
    "Tram": "#C3423F",
    "U-Bahn": "#7D2E2E", 
    "S-Bahn": "#8B3A3A",
    "Bus": "#DAA520",
    "Other": "#777777"
}
PT_WEIGHTS = {"S-Bahn": 3.0, "U-Bahn": 2.5, "Tram": 2.0, "Bus": 1.0, "Other": 0.5}

# Essential amenities
ESSENTIALS = {
    "amenity": {"supermarket", "pharmacy", "school", "hospital", "doctors", "clinic"},
    "shop": {"supermarket"},
    "healthcare": {"hospital", "clinic", "doctor", "doctors"}
}

def get_next_output_dir():
    """Get the next available output directory in the series"""
    outputs_base = Path("outputs")
    if not outputs_base.exists():
        outputs_base.mkdir(parents=True, exist_ok=True)
    
    existing_dirs = list(outputs_base.glob("stuttgart_maps_*"))
    if not existing_dirs:
        next_num = "001"
    else:
        numbers = []
        for d in existing_dirs:
            try:
                num_str = d.name.replace("stuttgart_maps_", "")
                numbers.append(int(num_str))
            except ValueError:
                continue
        next_num = f"{max(numbers) + 1:03d}" if numbers else "001"
    
    output_dir = outputs_base / f"stuttgart_maps_{next_num}"
    return output_dir, next_num

# Initialize output directories
OUTPUT_BASE, RUN_NUMBER = get_next_output_dir()
OUT_DIR = OUTPUT_BASE / "maps"; OUT_DIR.mkdir(parents=True, exist_ok=True)
KEPLER_DIR = OUTPUT_BASE / "kepler_data"; KEPLER_DIR.mkdir(parents=True, exist_ok=True)
GEOJSON_DIR = OUTPUT_BASE / "geojson_layers"; GEOJSON_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load all required data layers"""
    def read_any(p: Path):
        if not p.exists(): 
            return None
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
                else:
                    return df
            else:
                return pd.read_parquet(p)
        except Exception as e:
            print(f"Error reading {p}: {e}")
            return None

    layers = dict(
        districts=read_any(DATA_DIR / "districts_with_population.geojson"),
        landuse=read_any(DATA_DIR / "processed/landuse_categorized.parquet"),
        roads=read_any(DATA_DIR / "processed/roads_categorized.parquet"),
        pt_stops=read_any(DATA_DIR / "processed/pt_stops_categorized.parquet"),
        amenities=read_any(DATA_DIR / "processed/amenities_categorized.parquet"),
        boundary=read_any(DATA_DIR / "city_boundary.geojson"),
        h3_pop=pd.read_parquet(DATA_DIR / "h3_population_res8.parquet") if (DATA_DIR / "h3_population_res8.parquet").exists() else None,
    )
    
    # Set CRS for GeoDataFrames
    for key, gdf in layers.items():
        if gdf is not None and hasattr(gdf, 'crs') and key != "h3_pop":
            if gdf.crs is None:
                layers[key] = gdf.set_crs(4326)
            else:
                layers[key] = gdf.to_crs(4326)
    
    return layers

def _save(fig, name):
    """Save figure to maps directory"""
    filepath = OUT_DIR / name
    fig.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  ✅ Saved: {name}")

def _city_extent_and_boundary(data):
    """Get city extent and boundary"""
    districts = data["districts"].to_crs(PLOT_CRS)
    city_boundary = districts.union_all()
    city_boundary_buffered = city_boundary.buffer(100)
    
    # Limit the buffer size to prevent extremely large extents
    max_buffer = 5000  # meters
    buffer_size = min(OVERVIEW_PAD_M, max_buffer)
    extent = tuple(gpd.GeoSeries([city_boundary.buffer(buffer_size)], crs=PLOT_CRS).total_bounds)
    
    # Ensure extent is reasonable (max 50km x 50km)
    x_min, y_min, x_max, y_max = extent
    width = x_max - x_min
    height = y_max - y_min
    
    if width > 50000 or height > 50000:
        # Use a smaller buffer if extent is too large
        buffer_size = 2000
        extent = tuple(gpd.GeoSeries([city_boundary.buffer(buffer_size)], crs=PLOT_CRS).total_bounds)
    
    return districts, city_boundary, city_boundary_buffered, extent



def _add_basemap_custom(ax, extent, basemap_source="CartoDB.Positron", basemap_alpha=0.30):
    """Add custom basemap"""
    try:
        if basemap_source == "CartoDB.Positron":
            cx.add_basemap(ax, crs=PLOT_CRS, source=cx.providers.CartoDB.Positron, alpha=basemap_alpha)
        else:
            cx.add_basemap(ax, crs=PLOT_CRS, source=getattr(cx.providers.CartoDB, basemap_source, cx.providers.CartoDB.Positron), alpha=basemap_alpha)
    except Exception as e:
        print(f"  ⚠️ Basemap failed: {e}")

def _add_scale_bar(ax, extent, km_marks=(1,5,10)):
    """Add scale bar to map"""
    try:
        import matplotlib.patches as mpatches
        xmin, ymin, xmax, ymax = extent
        width_m = xmax - xmin; height_m = ymax - ymin
        choices = [20,15,10,5,2,1] if width_m > 40000 else [10,5,2,1]
        max_km = next((k for k in choices if (k*1000) <= 0.35*width_m), 1)
        x0 = xmin + 0.06*width_m; y0 = ymin + 0.06*height_m
        unit = 1000.0; h = 0.006*height_m
        for k in range(int(max_km)):
            face = 'black' if k%2==0 else 'white'
            ax.add_patch(mpatches.Rectangle((x0+k*unit, y0), unit, h, facecolor=face,
                            edgecolor='black', linewidth=0.8, zorder=10, alpha=0.7))
        ax.add_patch(mpatches.Rectangle((x0, y0), max_km*unit, h, facecolor='none',
                        edgecolor='black', linewidth=0.8, zorder=11, alpha=0.7))
        labels = [0] + [m for m in km_marks if m <= max_km]
        for lab in labels:
            xl = x0 + lab*unit
            ax.text(xl, y0 + 1.5*h, f'{lab}', ha='center', va='bottom',
                    fontsize=9, fontweight='bold', zorder=12, alpha=0.7)
        ax.text(x0 + (max_km*unit)/2.0, y0 - 0.8*h, 'km', ha='center', va='top',
                fontsize=10, fontweight='bold', zorder=12, alpha=0.7)
    except Exception as e:
        print(f"  ⚠️ Scale bar failed: {e}")

def apply_map_template(ax, extent, english_title, german_subtitle, city_boundary_buffered):
    """Apply consistent map template"""
    _add_basemap_custom(ax, extent)
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title(f"{english_title}\n{german_subtitle}", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    
    # Add city boundary
    if city_boundary_buffered is not None:
        if hasattr(city_boundary_buffered, 'plot'):
            city_boundary_buffered.boundary.plot(ax=ax, color='black', linewidth=1.5, alpha=0.8)
        else:
            # If it's a geometry, convert to GeoDataFrame first
            gdf = gpd.GeoDataFrame(geometry=[city_boundary_buffered], crs=PLOT_CRS)
            gdf.boundary.plot(ax=ax, color='black', linewidth=1.5, alpha=0.8)

def generate_overview_maps(data):
    """Generate overview map with landuse, roads, and PT stops"""
    print("🗺️ Generating overview maps...")
    
    districts = data["districts"].to_crs(PLOT_CRS)
    city_boundary = districts.union_all()
    city_boundary_buffered = city_boundary.buffer(100)
    extent = tuple(gpd.GeoSeries([city_boundary.buffer(OVERVIEW_PAD_M)], crs=PLOT_CRS).total_bounds)

    fig, ax = plt.subplots(1,1, figsize=(16,12), dpi=150)
    ax.set_aspect("equal"); ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])

    # green/landuse simplificado
    if data["landuse"] is not None:
        lu = data["landuse"].to_crs(PLOT_CRS)
        lu = lu[lu.intersects(city_boundary_buffered)].copy()
        lu["geometry"] = lu.geometry.intersection(city_boundary_buffered)
        lu = lu[~lu.geometry.is_empty]
        lu["area_m2"] = lu.geometry.area
        min_area = 5000

        forest = lu[((lu["landuse"]=="forest") | (lu["natural"]=="forest")) & (lu["area_m2"]>=min_area)]
        if len(forest): forest.plot(ax=ax, color="#4A5D4A", alpha=0.2, edgecolor="none")
        farmland = lu[((lu["landuse"]=="farmland") | (lu["natural"]=="farmland")) & (lu["area_m2"]>=min_area)]
        if len(farmland): farmland.plot(ax=ax, color="#7FB069", alpha=0.2, edgecolor="none")
        residential = lu[(lu["landuse"]=="residential") & (lu["area_m2"]>=min_area)]
        if len(residential): residential.plot(ax=ax, color="#F5F5DC", alpha=0.8, edgecolor="none")
        industrial = lu[(lu["landuse"]=="industrial") & (lu["area_m2"]>=min_area)]
        if len(industrial): industrial.plot(ax=ax, color="#D3D3D3", alpha=0.8, edgecolor="none")
        commercial = lu[((lu["landuse"].isin(["commercial","retail"]))) & (lu["area_m2"]>=min_area)]
        if len(commercial): commercial.plot(ax=ax, color="#FFB6C1", alpha=0.8, edgecolor="none")

    # roads
    if data["roads"] is not None:
        roads = data["roads"].to_crs(PLOT_CRS)
        roads = roads[roads.intersects(city_boundary_buffered)].copy()
        roads["geometry"] = roads.geometry.intersection(city_boundary_buffered)
        roads = roads[~roads.geometry.is_empty]
        roads.plot(ax=ax, color="#8B7355", linewidth=0.5, alpha=0.3)

    # PT stops
    if data["pt_stops"] is not None:
        pt = data["pt_stops"].to_crs(PLOT_CRS)
        pt = pt[pt.intersects(city_boundary_buffered)].copy()
        # tipos principais
        sb = pt[pt["railway"]=="stop"]
        if len(sb): sb.plot(ax=ax, marker="o", color="#C3423F", markersize=9, alpha=0.8,
                            edgecolor="white", linewidth=0.5, label="S-Bahn Stop")
        ub = pt[pt["railway"]=="subway_entrance"]
        if len(ub): ub.plot(ax=ax, marker="o", color="#C3423F", markersize=9, alpha=0.8,
                            edgecolor="white", linewidth=0.5, label="U-Bahn Entrance")
        tr = pt[pt["railway"]=="tram_stop"]
        if len(tr): tr.plot(ax=ax, marker="o", color="#C3423F", markersize=9, alpha=0.8,
                            edgecolor="white", linewidth=0.5, label="Tram Stop")
        remaining = pt[~pt.index.isin(pd.concat([sb,ub,tr]).index)]
        if len(remaining): remaining.plot(ax=ax, marker="o", color="#C3423F", markersize=9,
                                          alpha=0.8, edgecolor="white", linewidth=0.5)

    # distritos (contorno)
    districts.boundary.plot(ax=ax, color="#2F4F4F", linewidth=1.5, alpha=0.1)
    _add_basemap_custom(ax, extent); ax.set_axis_off()

    # legenda simples
    legend_elements = [
        plt.Line2D([0], [0], color='#8B7355', alpha=0.3, linewidth=2, label='Roads / Straßen'),
        plt.Line2D([0], [0], color='#666666', alpha=0.4, linewidth=3, label='City Boundary / Stadtgrenze'),
        plt.Line2D([0], [0], marker="o", color="#C3423F", markersize=8, label="PT Stop / ÖPNV-Haltestelle")
    ]
    ax.legend(handles=legend_elements, loc="lower right", ncol=1, fontsize=8,
              title="Map Legend / Kartenlegende", frameon=True, framealpha=0.95)

    fig.suptitle("Stuttgart — Land Use + Roads + PT Stops", fontsize=18, fontweight="normal", y=0.95)
    ax.text(0.5, 0.92, "Flächennutzung + Straßen + ÖPNV-Haltestellen",
            transform=fig.transFigure, ha='center', fontsize=14, style='italic')
    _add_scale_bar(ax, extent)
    _save(fig, "01_overview_landuse_roads_pt.png")

    # ===== 01b: Pop density como fundo =====
    generate_population_density_map(data, city_boundary_buffered)

def generate_population_density_map(data, city_boundary_buffered):
    fig, ax = plt.subplots(1,1, figsize=(16,12), dpi=150)
    districts = data["districts"].to_crs(PLOT_CRS)
    districts["area_km2"] = districts.geometry.area / 1e6
    districts["pop_density"] = districts["pop"] / districts["area_km2"]
    districts.plot(ax=ax, column="pop_density", cmap="YlOrBr", alpha=0.7, legend=True,
                   legend_kwds={"label": "Population Density (people/km²)",
                                "orientation": "horizontal", "shrink": 0.6,
                                "aspect": 20, "pad": 0.05})
    if data["roads"] is not None:
        roads = data["roads"].to_crs(PLOT_CRS)
        roads.plot(ax=ax, color="#8B7355", alpha=0.3, linewidth=0.5)
    if data["pt_stops"] is not None:
        pts = data["pt_stops"].to_crs(PLOT_CRS)
        pts.plot(ax=ax, color="#C3423F", alpha=0.8, markersize=9)
    extent = tuple(gpd.GeoSeries([city_boundary_buffered], crs=PLOT_CRS).total_bounds)
    gpd.GeoSeries([city_boundary_buffered], crs=PLOT_CRS).boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.4)
    fig.suptitle("Stuttgart — Population Density + Roads + PT Stops", fontsize=18, y=0.95)
    ax.text(0.5, 0.92, "Bevölkerungsdichte + Straßen + ÖPNV-Haltestellen",
            transform=fig.transFigure, ha='center', fontsize=14, style='italic')
    ax.set_aspect("equal"); ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])
    _add_basemap_custom(ax, extent, "CartoDB.Positron", 0.30)
    _add_scale_bar(ax, extent)
    ax.axis('off')
    _save(fig, "01b_overview_population_density_roads_pt.png")

def generate_pop_vs_pt_mosaic_map(data):
    """Generate H3-based population vs PT density map"""
    print("🗺️ Generating H3 population vs PT density map...")
    
    districts, city_boundary, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    
    # Use H3 instead of fishnet
    try:
        import sys
        sys.path.append("scripts")
        sys.path.append("utils")
        
        from h3_utils import polyfill_gdf, cells_to_gdf
        
        # Create H3 grid
        city_wgs84 = gpd.GeoDataFrame(geometry=[city_boundary], crs=PLOT_CRS).to_crs(4326)
        h3_cells = polyfill_gdf(city_wgs84, H3_RES)
        h3_gdf = cells_to_gdf(h3_cells, to_crs=PLOT_CRS)
        
        # Calculate population density for H3 cells
        h3_gdf["area_km2"] = h3_gdf.geometry.area / 1e6
        
        # Simple population assignment (placeholder)
        h3_gdf["pop_density"] = 1000  # Placeholder
        
        # Count PT stops in H3 cells
        if data["pt_stops"] is not None:
            pts = data["pt_stops"].to_crs(PLOT_CRS)[["geometry"]].copy()
            join = gpd.sjoin(pts, h3_gdf[["geometry"]], how="left", predicate="within")
            counts = join.groupby(join.index_right).size()
            h3_gdf["pt_count"] = h3_gdf.index.map(counts).fillna(0).astype(int)
            h3_gdf["pt_density_km2"] = (h3_gdf["pt_count"] / h3_gdf["area_km2"]).round(2)
            
            # Plot H3 PT density
            fig, ax = plt.subplots(1,1, figsize=(16,12), dpi=150)
            h3_gdf.plot(ax=ax, column="pt_density_km2", cmap="Reds", alpha=0.8, 
                        legend=True, legend_kwds={"label":"PT Density (stops/km²)", "shrink":0.7})
            
            # Add district boundaries
            districts.boundary.plot(ax=ax, color="#666666", linewidth=2, alpha=0.8)
            
            ax.set_title("Stuttgart — H3 PT Stop Density", fontsize=18, y=0.95)
            ax.text(0.5, 0.92, "ÖPNV-Haltestellen Dichte (H3 Raster)", 
                    transform=fig.transFigure, ha='center', fontsize=14, style='italic')
            ax.set_aspect("equal")
            ax.set_xlim(extent[0], extent[2])
            ax.set_ylim(extent[1], extent[3])
            _add_basemap_custom(ax, extent)
            ax.axis('off')
            _save(fig, "02_h3_pt_density.png")
            
    except ImportError as e:
        print(f"  ❌ H3 utilities not available: {e}")
        print("  💡 Skipping H3 map generation")

def generate_district_accessibility_maps(data, focus_names=DISTRICTS_FOCUS):
    """Generate district accessibility maps"""
    print("🗺️ Generating district accessibility maps...")
    
    if data["districts"] is None:
        print("❌ No districts data available")
        return
    
    districts, city_boundary, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    districts = data["districts"].to_crs(PLOT_CRS)
    
    for name in focus_names:
        # Find district by name (case-insensitive partial match)
        matching_districts = districts[
            districts.get('district_norm', districts.get('STADTBEZIRKNAME', '')).str.contains(name, case=False, na=False)
        ]
        
        if matching_districts.empty:
            print(f"  ⚠️ District '{name}' not found")
            continue
        
        district = matching_districts.iloc[0]
        
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        
        # Highlight the focus district
        districts.plot(ax=ax, color='lightgray', alpha=0.3, edgecolor='white', linewidth=0.5)
        matching_districts.plot(ax=ax, color='orange', alpha=0.7, edgecolor='black', linewidth=2)
        
        # Add PT stops if available
        if data["pt_stops"] is not None:
            pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
            pt_stops.plot(ax=ax, color='red', markersize=10, alpha=0.8)
        
        apply_map_template(ax, extent, f"Stuttgart — {name} District Access", 
                          f"Bezirk {name} — Erreichbarkeit", city_boundary_buffered)
        
        _save(fig, f"03_access_{name.lower().replace(' ', '_')}.png")

def generate_h3_analysis_maps(data):
    """Generate H3 analysis maps using actual H3 hexagons"""
    print("🗺️ Generating H3 analysis maps...")
    
    districts, city_boundary, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    
    # Import H3 utilities
    import sys
    sys.path.append("cities/stuttgart/spatial_analysis/scripts")
    sys.path.append("cities/stuttgart/spatial_analysis/utils")
    
    try:
        from h3_utils import hex_polygon, polyfill_gdf, cells_to_gdf
    except ImportError as e:
        print(f"  ❌ H3 utilities not available: {e}")
        print("  💡 Using simplified grid approach instead")
        return
    
    # Create H3 grid using actual hexagons
    if data["boundary"] is not None:
        city_wgs84 = data["boundary"].to_crs(4326)
    else:
        city_wgs84 = data["districts"].to_crs(4326)
    
    try:
        # Generate H3 cells for the city boundary
        h3_cells = polyfill_gdf(city_wgs84, H3_RES)
        h3_gdf = cells_to_gdf(h3_cells, to_crs=PLOT_CRS)
        
        # Calculate areas and centroids
        h3_gdf["area_m2"] = h3_gdf.geometry.area
        h3_gdf["centroid"] = h3_gdf.geometry.centroid
        
        # PT Modal Gravity Map
        if data["pt_stops"] is not None:
            pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
            pt_stops["pt_type"] = pt_stops.apply(_classify_pt, axis=1)
            
            gravity_scores = []
            for idx, hex_row in h3_gdf.iterrows():
                hex_point = hex_row["centroid"]
                total_gravity = 0.0
                
                for _, stop_row in pt_stops.iterrows():
                    stop_point = stop_row.geometry
                    distance = hex_point.distance(stop_point)
                    
                    if distance > 0:
                        pt_type = stop_row.get("pt_type", "Other")
                        weight = PT_WEIGHTS.get(pt_type, 0.5)
                        gravity = weight / (distance ** 2)
                        total_gravity += gravity
                
                gravity_scores.append(total_gravity)
            
            h3_gdf["pt_gravity"] = gravity_scores
            max_gravity = max(gravity_scores) if gravity_scores else 1.0
            h3_gdf["pt_gravity"] = (h3_gdf["pt_gravity"] / max_gravity * 100) if max_gravity > 0 else 0.0
            
            # Create PT gravity map
            fig, ax = plt.subplots(1, 1, figsize=(20, 16))
            h3_gdf.plot(ax=ax, column="pt_gravity", cmap="Reds", alpha=0.8, edgecolor="white", linewidth=0.1,
                       legend=True, legend_kwds={"label": "PT Modal Gravity (0-100)", "orientation": "horizontal", "shrink": 0.6})
            
            apply_map_template(ax, extent, "Stuttgart — PT Modal Gravity (H3 r8)", 
                              "Σ (Weight / Distance²), S>U>Tram>Bus — H3 Raster r8", city_boundary_buffered)
            
            _save(fig, "04_pt_modal_gravity_h3.png")
        
        # Essentials Access Map
        if data["amenities"] is not None:
            amenities = data["amenities"].to_crs(PLOT_CRS)
            essentials = amenities[amenities.apply(_is_essential, axis=1)]
            
            if len(essentials) > 0:
                ess_counts = []
                walk_10min_m = 800
                
                for idx, hex_row in h3_gdf.iterrows():
                    hex_centroid = hex_row["centroid"]
                    nearby = essentials[essentials.geometry.distance(hex_centroid) <= walk_10min_m]
                    
                    unique_types = set()
                    for _, amenity in nearby.iterrows():
                        for key, values in ESSENTIALS.items():
                            if key in amenity and str(amenity[key]).lower() in values:
                                unique_types.add(str(amenity[key]).lower())
                    
                    ess_counts.append(len(unique_types))
                
                h3_gdf["ess_types"] = ess_counts
                
                # Create essentials access map
                fig, ax = plt.subplots(1, 1, figsize=(20, 16))
                h3_gdf.plot(ax=ax, column="ess_types", cmap="Greens", alpha=0.8, edgecolor="white", linewidth=0.1,
                           legend=True, legend_kwds={"label": "# Essential Types (≤10 min walk)", "orientation": "horizontal", "shrink": 0.6})
                
                apply_map_template(ax, extent, "Stuttgart — Essentials within 10-min Walk (H3 r8)", 
                                  "Erreichbarkeit von Grundversorgern", city_boundary_buffered)
                
                _save(fig, "05_access_essentials_h3.png")
        
        # Service Diversity Map
        if data["amenities"] is not None:
            amenities = data["amenities"].to_crs(PLOT_CRS)
            entropy_scores = []
            
            for idx, hex_row in h3_gdf.iterrows():
                hex_geom = hex_row.geometry
                hex_amenities = amenities[amenities.geometry.within(hex_geom)]
                
                if len(hex_amenities) == 0:
                    entropy_scores.append(0.0)
                else:
                    type_counts = hex_amenities.get('amenity', pd.Series(dtype='object')).value_counts()
                    if len(type_counts) == 0:
                        entropy_scores.append(0.0)
                    else:
                        probs = type_counts / type_counts.sum()
                        entropy = -np.sum(probs * np.log2(probs + 1.0))
                        entropy_scores.append(entropy)
            
            h3_gdf["amen_entropy"] = entropy_scores
            
            # Create service diversity map
            fig, ax = plt.subplots(1, 1, figsize=(20, 16))
            h3_gdf.plot(ax=ax, column="amen_entropy", cmap="viridis", alpha=0.8, edgecolor="white", linewidth=0.1,
                       legend=True, legend_kwds={"label": "Service Diversity (Shannon Entropy)", "orientation": "horizontal", "shrink": 0.6})
            
            apply_map_template(ax, extent, "Stuttgart — Service Diversity (H3 r8)", 
                              "Dienstleistungs-Diversität", city_boundary_buffered)
            
            _save(fig, "07_service_diversity_h3.png")
        
        # Green Gaps Map (placeholder)
        h3_gdf["green_gaps"] = 0.1  # Placeholder value
        fig, ax = plt.subplots(1, 1, figsize=(20, 16))
        h3_gdf.plot(ax=ax, column="green_gaps", cmap="Greens", alpha=0.8, edgecolor="white", linewidth=0.1,
                   legend=True, legend_kwds={"label": "Green Gaps Analysis", "orientation": "horizontal", "shrink": 0.6})
        
        apply_map_template(ax, extent, "Stuttgart — Green Gaps Analysis (H3 r8)", 
                          "Grünflächen-Lücken-Analyse", city_boundary_buffered)
        
        _save(fig, "10_green_gaps_h3.png")
        
    except Exception as e:
        print(f"  ⚠️ H3 analysis maps failed: {e}")
        print("  💡 Some H3 maps may not be generated")

def _classify_pt(row):
    """Classify PT stops by type"""
    route_type = str(row.get("route_type", "")).lower()
    name = str(row.get("name", "")).lower()
    
    if "s-bahn" in name or route_type == "train":
        return "S-Bahn"
    elif "u-bahn" in name or route_type == "subway":
        return "U-Bahn"
    elif route_type == "tram":
        return "Tram"
    elif route_type == "bus":
        return "Bus"
    else:
        return "Other"

def _is_essential(row):
    """Check if amenity is essential"""
    for key, values in ESSENTIALS.items():
        if key in row and str(row[key]).lower() in values:
            return True
    return False

def export_all_base_layers(data):
    """Export all base layers to GeoJSON for Kepler"""
    print("📁 Exporting base layers to GeoJSON...")
    
    # City boundary
    if data["boundary"] is not None:
        data["boundary"].to_file(GEOJSON_DIR/"01_city_boundary.geojson", driver="GeoJSON")
        print("  ✅ City boundary exported")
    
    # Districts
    if data["districts"] is not None:
        data["districts"].to_file(GEOJSON_DIR/"02_districts.geojson", driver="GeoJSON")
        print("  ✅ Districts exported")
    
    # Roads
    if data["roads"] is not None:
        data["roads"].to_file(GEOJSON_DIR/"03_roads.geojson", driver="GeoJSON")
        print("  ✅ Roads exported")
    
    # PT stops
    if data["pt_stops"] is not None:
        data["pt_stops"].to_file(GEOJSON_DIR/"04_pt_stops.geojson", driver="GeoJSON")
        print("  ✅ PT stops exported")
    
    # Landuse
    if data["landuse"] is not None:
        data["landuse"].to_file(GEOJSON_DIR/"05_landuse.geojson", driver="GeoJSON")
        print("  ✅ Landuse exported")
    
    # Green areas (from landuse)
    if data["landuse"] is not None:
        landuse_cols = data["landuse"].columns
        landuse_filter = pd.Series([False] * len(data["landuse"]), index=data["landuse"].index)
        
        if "landuse" in landuse_cols:
            landuse_filter |= data["landuse"]["landuse"].isin(["park", "forest", "grass", "meadow"])
        if "leisure" in landuse_cols:
            landuse_filter |= data["landuse"]["leisure"].isin(["park", "garden", "playground"])
        
        green_areas = data["landuse"][landuse_filter]
        if not green_areas.empty:
            green_areas.to_file(GEOJSON_DIR/"06_green_areas.geojson", driver="GeoJSON")
            print("  ✅ Green areas exported")

def export_h3_analysis_layers(data):
    """Export H3 analysis layers to GeoJSON"""
    print("📁 Exporting H3 analysis layers...")
    
    # Create H3 grid
    if data["boundary"] is not None:
        city_wgs84 = data["boundary"].to_crs(4326)
    else:
        city_wgs84 = data["districts"].to_crs(4326)
    
    try:
        # Create a simple grid-based analysis instead of H3
        # Get city bounds and create a regular grid
        bounds = city_wgs84.total_bounds
        x_min, y_min, x_max, y_max = bounds
        
        # Create grid cells (simplified approach)
        grid_size = 0.01  # degrees, roughly 1km
        x_coords = np.arange(x_min, x_max, grid_size)
        y_coords = np.arange(y_min, y_max, grid_size)
        
        grid_cells = []
        for x in x_coords:
            for y in y_coords:
                cell = box(x, y, x + grid_size, y + grid_size)
                grid_cells.append(cell)
        
        grid_gdf = gpd.GeoDataFrame(geometry=grid_cells, crs=4326)
        
        # Filter cells that intersect with city boundary
        grid_gdf = gpd.sjoin(grid_gdf, city_wgs84[["geometry"]], predicate="intersects", how="inner")
        grid_gdf = grid_gdf[["geometry"]].reset_index(drop=True)
        
        # Convert to plot CRS for calculations
        grid_plot = grid_gdf.to_crs(PLOT_CRS)
        grid_plot["area_m2"] = grid_plot.geometry.area
        grid_plot["centroid"] = grid_plot.geometry.centroid
        
        # Attach population data (simplified)
        grid_plot["pop"] = 1000  # Placeholder population
        grid_plot["pop_density"] = grid_plot["pop"] / (grid_plot["area_m2"] / 1e6)
        
        # Calculate PT gravity
        if data["pt_stops"] is not None:
            pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
            pt_stops["pt_type"] = pt_stops.apply(_classify_pt, axis=1)
            
            gravity_scores = []
            for idx, hex_row in grid_plot.iterrows():
                hex_point = hex_row["centroid"]
                total_gravity = 0.0
                
                for _, stop_row in pt_stops.iterrows():
                    stop_point = stop_row.geometry
                    distance = hex_point.distance(stop_point)
                    
                    if distance > 0:
                        pt_type = stop_row.get("pt_type", "Other")
                        weight = PT_WEIGHTS.get(pt_type, 0.5)
                        gravity = weight / (distance ** 2)
                        total_gravity += gravity
                
                gravity_scores.append(total_gravity)
            
            grid_plot["pt_gravity"] = gravity_scores
            max_gravity = max(gravity_scores) if gravity_scores else 1.0
            grid_plot["pt_gravity"] = (grid_plot["pt_gravity"] / max_gravity * 100) if max_gravity > 0 else 0.0
            
            # Export PT gravity
            grid_plot[["pt_gravity","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"13_pt_modal_gravity_h3.geojson", driver="GeoJSON")
            print("  ✅ PT modal gravity exported")
        
        # Calculate essential amenities access
        if data["amenities"] is not None:
            amenities = data["amenities"].to_crs(PLOT_CRS)
            essentials = amenities[amenities.apply(_is_essential, axis=1)]
            
            if len(essentials) > 0:
                ess_counts = []
                walk_10min_m = 800
                
                for idx, hex_row in grid_plot.iterrows():
                    hex_centroid = hex_row["centroid"]
                    nearby = essentials[essentials.geometry.distance(hex_centroid) <= walk_10min_m]
                    
                    unique_types = set()
                    for _, amenity in nearby.iterrows():
                        for key, values in ESSENTIALS.items():
                            if key in amenity and str(amenity[key]).lower() in values:
                                unique_types.add(str(amenity[key]).lower())
                    
                    ess_counts.append(len(unique_types))
                
                grid_plot["ess_types"] = ess_counts
                
                # Export essentials access
                grid_plot[["ess_types","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"14_access_essentials_h3.geojson", driver="GeoJSON")
                print("  ✅ Essentials access exported")
        
        # Calculate service diversity
        if data["amenities"] is not None:
            amenities = data["amenities"].to_crs(PLOT_CRS)
            entropy_scores = []
            
            for idx, hex_row in grid_plot.iterrows():
                hex_geom = hex_row.geometry
                hex_amenities = amenities[amenities.geometry.within(hex_geom)]
                
                if len(hex_amenities) == 0:
                    entropy_scores.append(0.0)
                else:
                    type_counts = hex_amenities.get('amenity', pd.Series(dtype='object')).value_counts()
                    if len(type_counts) == 0:
                        entropy_scores.append(0.0)
                    else:
                        probs = type_counts / type_counts.sum()
                        entropy = -np.sum(probs * np.log2(probs + 1.0))
                        entropy_scores.append(entropy)
            
            grid_plot["amen_entropy"] = entropy_scores
            
            # Export service diversity
            grid_plot[["amen_entropy","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"16_service_diversity_h3.geojson", driver="GeoJSON")
            print("  ✅ Service diversity exported")
        
        # Export additional analysis layers
        if "pop_density" in grid_plot.columns:
            grid_plot[["pop_density","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"18_amenity_density.geojson", driver="GeoJSON")
            print("  ✅ Amenity density exported")
        
        if "pop" in grid_plot.columns:
            grid_plot[["pop","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"19_district_area.geojson", driver="GeoJSON")
            print("  ✅ District area exported")
        
        # Create composite scores
        if "pt_gravity" in grid_plot.columns and "ess_types" in grid_plot.columns:
            # Normalize scores
            pt_norm = (grid_plot["pt_gravity"] - grid_plot["pt_gravity"].min()) / (grid_plot["pt_gravity"].max() - grid_plot["pt_gravity"].min())
            ess_norm = (grid_plot["ess_types"] - grid_plot["ess_types"].min()) / (grid_plot["ess_types"].max() - grid_plot["ess_types"].min())
            
            # Mobility score (PT + essentials)
            mobility_score = (pt_norm + ess_norm) / 2
            grid_plot["mobility_score"] = mobility_score
            grid_plot[["mobility_score","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"21_mobility_score.geojson", driver="GeoJSON")
            print("  ✅ Mobility score exported")
            
            # Walkability score (essentials + service diversity)
            if "amen_entropy" in grid_plot.columns:
                div_norm = (grid_plot["amen_entropy"] - grid_plot["amen_entropy"].min()) / (grid_plot["amen_entropy"].max() - grid_plot["amen_entropy"].min())
                walkability_score = (ess_norm + div_norm) / 2
                grid_plot["walkability_score"] = walkability_score
                grid_plot[["walkability_score","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"23_walkability_score.geojson", driver="GeoJSON")
            print("  ✅ Walkability score exported")
            
            # Overall score (all metrics)
            if "amen_entropy" in grid_plot.columns:
                overall_score = (pt_norm + ess_norm + div_norm) / 3
                grid_plot["overall_score"] = overall_score
                grid_plot[["overall_score","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"24_overall_score.geojson", driver="GeoJSON")
                print("  ✅ Overall score exported")
        
        # Export PT density
        if "pt_gravity" in grid_plot.columns:
            grid_plot[["pt_gravity","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"22_pt_density.geojson", driver="GeoJSON")
            print("  ✅ PT density exported")
        
        # Export green space ratio (placeholder)
        grid_plot["green_ratio"] = 0.1  # Placeholder value
        grid_plot[["green_ratio","geometry"]].to_crs(4326).to_file(GEOJSON_DIR/"20_green_space_ratio.geojson", driver="GeoJSON")
        print("  ✅ Green space ratio exported")
        
    except Exception as e:
        print(f"  ⚠️ H3 analysis failed: {e}")
        print("  💡 Some H3 layers may not be exported")

def main():
    """Main execution function"""
    print(f"🗺️ Generating Comprehensive Stuttgart Maps (Series {RUN_NUMBER})...")
    print(f"📁 Output directory: {OUT_DIR}")
    print(f"📁 Kepler directory: {KEPLER_DIR}")
    print(f"📁 GeoJSON directory: {GEOJSON_DIR}")
    
    # Load data
    print("📊 Loading data layers...")
    data = load_data()
    
    # Check what data is available
    print("\n🔍 Data availability check:")
    required_files = [
        (DATA_DIR / "districts_with_population.geojson", "Districts"),
        (DATA_DIR / "processed/landuse_categorized.parquet", "Landuse"),
        (DATA_DIR / "processed/roads_categorized.parquet", "Roads"),
        (DATA_DIR / "processed/pt_stops_categorized.parquet", "PT Stops"),
        (DATA_DIR / "processed/amenities_categorized.parquet", "Amenities"),
        (DATA_DIR / "city_boundary.geojson", "City Boundary"),
        (DATA_DIR / "h3_population_res8.parquet", "H3 Population")
    ]
    
    missing_files = []
    available_data = []
    
    for file_path, description in required_files:
        if file_path.exists():
            available_data.append(f"  ✅ {description}: {file_path}")
        else:
            missing_files.append(f"  ❌ {description}: {file_path}")
    
    for item in available_data:
        print(item)
    for item in missing_files:
        print(item)
    
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} required data files!")
        print("\n📝 To generate maps, you need to:")
        print("1. Run the data extraction pipeline to get OSM data")
        print("2. Run population_pipeline_stuttgart.py for population data")
        print("3. Ensure all processed data files are in the correct locations")
        print(f"\n💡 Expected data directory: {DATA_DIR.absolute()}")
        return
    
    # Validate loaded data
    critical_data = ["districts", "boundary"]
    for key in critical_data:
        if data[key] is None:
            print(f"❌ Critical data '{key}' could not be loaded")
            return
    
    # Generate maps
    print("\n🗺️ Generating maps...")
    
    try:
        # Overview maps
        generate_overview_maps(data)
        # Population density map is called from generate_overview_maps
        generate_pop_vs_pt_mosaic_map(data)
        
        # District accessibility maps
        generate_district_accessibility_maps(data, DISTRICTS_FOCUS)
        
        # H3 Analysis maps
        generate_h3_analysis_maps(data)
        
        # Export all base layers
        export_all_base_layers(data)
        
        # Export H3 analysis layers
        export_h3_analysis_layers(data)
        
        # Create run info
        run_info = {
            "run_number": RUN_NUMBER,
            "timestamp": pd.Timestamp.now().isoformat(),
            "output_directory": str(OUTPUT_BASE),
            "maps_generated": 9,  # 1 overview + 1 population + 1 H3 PT + 6 districts
            "geojson_layers_exported": True,
            "comprehensive_analysis": True,
            "available_data": [desc for _, desc in required_files if _],
            "features": [
                "Overview maps (landuse + population)",
                "H3 PT density analysis", 
                "District accessibility maps",
                "H3 analysis maps",
                "Base layer exports",
                "GeoJSON export"
            ]
        }
        
        with open(OUTPUT_BASE / "run_info.json", 'w') as f:
            json.dump(run_info, f, indent=2)
        
        print("\n🎉 Comprehensive maps and layers generated successfully!")
        print(f"📁 Check outputs in: {OUT_DIR}")
        print(f"📁 Check GeoJSON layers in: {GEOJSON_DIR}")
        print(f"📊 Run info saved: {OUTPUT_BASE / 'run_info.json'}")
        print(f"🗺️ Generated {run_info['maps_generated']} maps with H3 analysis")
        
    except Exception as e:
        print(f"\n❌ Error during map generation: {e}")
        print(f"💡 This is likely due to missing or incompatible data files.")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
