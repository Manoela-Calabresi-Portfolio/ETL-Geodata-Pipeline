#!/usr/bin/env python3
"""
Generate Only Overview Map for Stuttgart
Extracts just the 01_overview_landuse_roads_pt.png map
"""

import sys
from pathlib import Path
sys.path.append('..')

import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from shapely.geometry import Point, box

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

def _add_scale_bar(ax, extent):
    """Add a scale bar to the map"""
    # Calculate scale bar length (approximately 5km)
    scale_length_km = 5
    scale_length_deg = scale_length_km / 111000  # Rough conversion
    
    # Position scale bar in bottom left
    x_start = extent[0] + (extent[2] - extent[0]) * 0.1
    y_pos = extent[1] + (extent[3] - extent[1]) * 0.1
    
    # Draw scale bar
    ax.plot([x_start, x_start + scale_length_deg], [y_pos, y_pos], 
            color='black', linewidth=2, solid_capstyle='butt')
    
    # Add scale bar text
    ax.text(x_start + scale_length_deg/2, y_pos - scale_length_deg/10, 
            f'{scale_length_km} km', ha='center', va='top', 
            fontsize=10, fontweight='bold', color='black',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

def _save(fig, name):
    """Save figure with proper formatting"""
    out = MAPS_DIR / name
    # Use None to avoid any clipping and preserve our custom extent
    plt.savefig(out, dpi=300, bbox_inches=None, facecolor='white')
    plt.close()
    print(f"  💾 Saved: {name}")

def generate_overview_maps(data):
    """Generate overview maps"""
    print("🗺️ Generating overview maps...")
    
    # Get city boundary from districts
    districts = data["districts"]
    city_boundary = districts.union_all()  # Fixed deprecation warning
    city_boundary_buffered = city_boundary.buffer(1000)  # 1km buffer
    
    # Convert to plotting CRS
    districts_plot = districts.to_crs(PLOT_CRS)
    # city_boundary and city_boundary_buffered are shapely Polygons, not GeoDataFrames
    
    # Get extent for plotting with buffer to avoid clipping
    extent = tuple(districts_plot.total_bounds)
    # Add 25% buffer around the city to avoid clipping boundaries (MUCH MORE SPACE!)
    x_buffer = (extent[2] - extent[0]) * 0.25
    y_buffer = (extent[3] - extent[1]) * 0.25
    extent = (
        extent[0] - x_buffer,  # x_min
        extent[1] - y_buffer,  # y_min  
        extent[2] + x_buffer,  # x_max
        extent[3] + y_buffer   # y_max
    )
    
    # Create overview map
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Plot districts
    districts_plot.plot(ax=ax, color='lightblue', edgecolor='darkblue', linewidth=0.5, alpha=0.3)
    
    # Plot landuse
    if data["landuse"] is not None:
        landuse = data["landuse"].to_crs(PLOT_CRS)
        landuse = landuse[landuse.geometry.type.isin(["Polygon", "MultiPolygon"])]
        
        # Filter small areas
        landuse["area"] = landuse.geometry.area
        min_area = 10000  # 10,000 m² minimum
        landuse_filtered = landuse[landuse["area"] >= min_area]
        
        print(f"  - Total areas: {len(landuse)}, Plotted areas: {len(landuse_filtered)}, Filtered out: {len(landuse) - len(landuse_filtered)} small areas")
        
        # Plot forest areas
        forest_mask = landuse_filtered["landuse"].str.lower() == "forest"
        if forest_mask.any():
            forest_areas = landuse_filtered[forest_mask]
            forest_areas.plot(ax=ax, color="#4A5D4A", alpha=0.2, edgecolor='none')
            print(f"  - Plotted forest: {len(forest_areas)} areas")
        
        # Plot farmland
        farmland_mask = landuse_filtered["landuse"].str.lower() == "farmland"
        if farmland_mask.any():
            farmland_areas = landuse_filtered[farmland_mask]
            farmland_areas.plot(ax=ax, color="#7FB069", alpha=0.2, edgecolor='none')
            print(f"  - Plotted farmland: {len(farmland_areas)} areas")
        
        # Plot residential areas
        residential_mask = landuse_filtered["landuse"].str.lower() == "residential"
        if residential_mask.any():
            residential_areas = landuse_filtered[residential_mask]
            residential_areas.plot(ax=ax, color="#F5F5DC", alpha=0.8, edgecolor='none')
            print(f"  - Plotted residential: {len(residential_areas)} areas (filtered)")
        
        # Plot industrial areas
        industrial_mask = landuse_filtered["landuse"].str.lower() == "industrial"
        if industrial_mask.any():
            industrial_areas = landuse_filtered[industrial_mask]
            industrial_areas.plot(ax=ax, color="#D3D3D3", alpha=0.8, edgecolor='none')
            print(f"  - Plotted industrial: {len(industrial_areas)} areas (filtered)")
        
        # Plot commercial areas
        commercial_mask = landuse_filtered["landuse"].str.lower() == "commercial"
        if commercial_mask.any():
            commercial_areas = landuse_filtered[commercial_mask]
            commercial_areas.plot(ax=ax, color="#FFB6C1", alpha=0.8, edgecolor='none')
            print(f"  - Plotted commercial: {len(commercial_areas)} areas (filtered)")
    
    # Plot roads
    if data["roads"] is not None:
        roads = data["roads"].to_crs(PLOT_CRS)
        roads.plot(ax=ax, color='#8B7355', alpha=0.3, linewidth=0.5)
    
    # Plot PT stops
    if data["pt_stops"] is not None:
        pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
        pt_stops.plot(ax=ax, color='#C3423F', markersize=3, alpha=0.8)
        print(f"DEBUG: Found {len(pt_stops)} remaining PT stops to plot in Brick Red")
    
    # Apply style without North arrow and scale bar (we add our own scale bar)
    ax.set_aspect("equal")
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_axis_off()
    
    # Main title in English - Standard Bold 14
    ax.set_title("Stuttgart — Land Use + Roads + PT Stops", fontsize=14, fontweight="bold", 
                 pad=20)
    
    # German subtitle below - Standard Italic 12 (aligned to English title)
    ax.text(0.5, 0.92, "Stuttgart — Flächennutzung + Straßen + ÖPNV-Haltestellen", 
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
    legend_elements.append(plt.Rectangle((0,0),1,1, facecolor="#9DC183", alpha=0.2, 
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
              title="Map Legend / Kartenlegende", title_fontsize=12)
    
    _add_scale_bar(ax, extent)
    
    _save(fig, "01_overview_landuse_roads_pt.png")

def main():
    """Main function - generate only overview map"""
    print("🚀 Starting Stuttgart Overview Map Generation...")
    print("=" * 60)
    print(f"📁 Run #{RUN_NUMBER:03d} - Output: {OUT_DIR}")
    print("=" * 60)
    
    # Load data
    data = load_data()
    
    # Check if districts loaded
    if data["districts"] is None:
        print("❌ Error: Could not load districts data")
        return 1
    
    print(f"✅ Loaded {len(data['districts'])} districts")
    
    # Generate only overview map
    generate_overview_maps(data)
    
    print("\n" + "=" * 60)
    print("🎉 Overview map generated successfully!")
    print(f"📁 Check output in: {OUT_DIR}")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
