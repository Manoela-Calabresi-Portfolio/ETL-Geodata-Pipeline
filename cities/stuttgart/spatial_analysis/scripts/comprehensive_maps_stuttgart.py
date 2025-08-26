#!/usr/bin/env python3
"""
Comprehensive Stuttgart Maps Generator
Generates all maps in the same style as stuttgart_maps_093
"""

from __future__ import annotations
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import contextily as cx
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

# Import our local modules
import sys
sys.path.append("../style_helpers")
sys.path.append("../utils")
from style_helpers import apply_style, palette
from h3_utils import hex_polygon

warnings.filterwarnings("ignore", category=UserWarning)

# Constants
DATA_DIR = Path("../data")
PLOT_CRS = 3857
H3_RES = 8

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

def load_layers():
    """Load all required data layers"""
    layers = dict(
        districts=gpd.read_file(DATA_DIR/"districts_with_population.geojson") if (DATA_DIR/"districts_with_population.geojson").exists() else None,
        landuse=pd.read_parquet(DATA_DIR/"processed/landuse_categorized.parquet") if (DATA_DIR/"processed/landuse_categorized.parquet").exists() else None,
        roads=pd.read_parquet(DATA_DIR/"processed/roads_categorized.parquet") if (DATA_DIR/"processed/roads_categorized.parquet").exists() else None,
        pt_stops=pd.read_parquet(DATA_DIR/"processed/pt_stops_categorized.parquet") if (DATA_DIR/"processed/pt_stops_categorized.parquet").exists() else None,
        amenities=pd.read_parquet(DATA_DIR/"processed/amenities_categorized.parquet") if (DATA_DIR/"processed/amenities_categorized.parquet").exists() else None,
        boundary=gpd.read_file(DATA_DIR/"city_boundary.geojson") if (DATA_DIR/"city_boundary.geojson").exists() else None,
        h3_pop=pd.read_parquet(DATA_DIR/"h3_population_res8.parquet") if (DATA_DIR/"h3_population_res8.parquet").exists() else None,
    )
    
    # Set CRS defaults for GeoDataFrames
    for k in ["districts", "boundary"]:
        if layers[k] is not None and hasattr(layers[k], 'crs'):
            layers[k] = layers[k].set_crs(4326) if layers[k].crs is None else layers[k].to_crs(4326)
    
    # Handle parquet data that might need geometry conversion
    for k in ["landuse", "roads", "pt_stops", "amenities"]:
        if layers[k] is not None:
            # Check if it's a DataFrame with geometry column
            if hasattr(layers[k], 'geometry') and 'geometry' in layers[k].columns:
                # Check if geometry column contains bytes (WKB format)
                if layers[k]['geometry'].dtype == 'object' and isinstance(layers[k]['geometry'].iloc[0], bytes):
                    # Convert WKB bytes to Shapely geometries
                    from shapely import wkb
                    layers[k]['geometry'] = layers[k]['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
                
                # Convert to GeoDataFrame if it has geometry
                layers[k] = gpd.GeoDataFrame(layers[k], geometry='geometry', crs=4326)
            elif hasattr(layers[k], 'crs'):
                # Already a GeoDataFrame
                layers[k] = layers[k].set_crs(4326) if layers[k].crs is None else layers[k].to_crs(4326)
    
    return layers

def _extent_from(gdf):
    """Get extent from GeoDataFrame"""
    return tuple(gdf.to_crs(PLOT_CRS).total_bounds)

def _add_basemap_custom(ax, extent, alpha=0.3):
    """Add custom basemap"""
    try:
        cx.add_basemap(ax, crs=PLOT_CRS, source=cx.providers.CartoDB.Positron, alpha=alpha)
    except:
        pass

def _add_scale_bar(ax, extent):
    """Add scale bar"""
    try:
        from matplotlib_scalebar.scalebar import ScaleBar
        scalebar = ScaleBar(1, location='lower right', box_alpha=0.7)
        ax.add_artist(scalebar)
    except:
        pass

def map_01_overview_landuse_roads_pt(layers, extent):
    """Generate overview map: landuse + roads + PT"""
    print("🗺️ Generating map 01: Overview (landuse + roads + PT)...")
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)
    
    # Plot landuse as background
    if layers["landuse"] is not None:
        landuse_plot = layers["landuse"].to_crs(PLOT_CRS)
        landuse_plot.plot(ax=ax, column='category', cmap='Set3', alpha=0.6, legend=True)
    
    # Plot roads
    if layers["roads"] is not None:
        roads_plot = layers["roads"].to_crs(PLOT_CRS)
        roads_plot.plot(ax=ax, color='gray', linewidth=0.5, alpha=0.7)
    
    # Plot PT stops
    if layers["pt_stops"] is not None:
        pt_plot = layers["pt_stops"].to_crs(PLOT_CRS)
        pt_plot.plot(ax=ax, color='red', markersize=20, alpha=0.8)
    
    # Add district boundaries
    if layers["districts"] is not None:
        layers["districts"].to_crs(PLOT_CRS).boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.8)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.3)
    
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title("Stuttgart — Overview (Landuse + Roads + PT)", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / "01_overview_landuse_roads_pt.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✅ Saved: 01_overview_landuse_roads_pt.png")

def map_02_h3_population_pt(layers, extent):
    """Generate H3 population + PT map"""
    print("🗺️ Generating map 02: H3 Population + PT...")
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)
    
    if layers["h3_pop"] is not None:
        # Convert H3 to polygons
        h3_polys = [hex_polygon(h) for h in layers["h3_pop"]["h3"]]
        h3_gdf = gpd.GeoDataFrame(layers["h3_pop"], geometry=h3_polys, crs=4326).to_crs(PLOT_CRS)
        
        # Plot H3 population
        h3_gdf.plot(ax=ax, column='pop', cmap='viridis', alpha=0.8, legend=True)
    
    # Add PT stops
    if layers["pt_stops"] is not None:
        pt_plot = layers["pt_stops"].to_crs(PLOT_CRS)
        pt_plot.plot(ax=ax, color='red', markersize=15, alpha=0.8)
    
    # Add district boundaries
    if layers["districts"] is not None:
        layers["districts"].to_crs(PLOT_CRS).boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.8)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.3)
    
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title("Stuttgart — H3 Population + PT Stops", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / "02_h3_population_pt.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✅ Saved: 02_h3_population_pt.png")

def map_03_district_accessibility(layers, extent):
    """Generate district accessibility map"""
    print("🗺️ Generating map 03: District Accessibility...")
    
    if layers["districts"] is None:
        print("  ⚠️ No districts data available")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)
    
    districts_plot = layers["districts"].to_crs(PLOT_CRS)
    
    # Calculate accessibility score (example: based on population density and PT stops)
    if layers["pt_stops"] is not None:
        pt_plot = layers["pt_stops"].to_crs(PLOT_CRS)
        # Count PT stops per district
        pt_counts = gpd.sjoin(pt_plot, districts_plot, how='left', predicate='within')
        pt_counts = pt_counts.groupby(pt_counts.index_right).size()
        districts_plot['pt_count'] = districts_plot.index.map(pt_counts).fillna(0)
        
        # Plot districts with accessibility score
        districts_plot.plot(ax=ax, column='pt_count', cmap='RdYlGn', alpha=0.8, legend=True)
    
    # Add district boundaries
    districts_plot.boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.8)
    
    # Add district labels
    for idx, row in districts_plot.iterrows():
        centroid = row.geometry.centroid
        ax.annotate(row.get('district_name', f'District {idx}'), xy=(centroid.x, centroid.y), 
                   fontsize=8, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.3)
    
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title("Stuttgart — District Accessibility Analysis", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / "03_district_accessibility.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✅ Saved: 03_district_accessibility.png")

def map_04_pt_modal_gravity_h3(layers, extent):
    """Generate H3 PT modal gravity map"""
    print("🗺️ Generating map 04: H3 PT Modal Gravity...")
    
    if layers["h3_pop"] is None or layers["pt_stops"] is None:
        print("  ⚠️ Missing H3 population or PT stops data")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)
    
    # Convert H3 to polygons
    h3_polys = [hex_polygon(h) for h in layers["h3_pop"]["h3"]]
    h3_gdf = gpd.GeoDataFrame(layers["h3_pop"], geometry=h3_polys, crs=4326).to_crs(PLOT_CRS)
    
    # Calculate PT gravity (simplified: PT stops per H3 cell)
    pt_plot = layers["pt_stops"].to_crs(PLOT_CRS)
    pt_joined = gpd.sjoin(pt_plot, h3_gdf, how='right', predicate='within')
    if 'index_right' in pt_joined.columns:
        pt_counts = pt_joined.groupby(pt_joined['index_right']).size().fillna(0)
    else:
        pt_counts = pt_joined.groupby(pt_joined.index).size().fillna(0)
    h3_gdf['pt_gravity'] = pt_counts
    
    # Plot H3 PT gravity
    h3_gdf.plot(ax=ax, column='pt_gravity', cmap='Reds', alpha=0.8, legend=True)
    
    # Add district boundaries
    if layers["districts"] is not None:
        layers["districts"].to_crs(PLOT_CRS).boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.8)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.3)
    
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title("Stuttgart — H3 PT Modal Gravity", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / "04_pt_modal_gravity_h3.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✅ Saved: 04_pt_modal_gravity_h3.png")

def map_05_access_essentials_h3(layers, extent):
    """Generate H3 access to essentials map"""
    print("🗺️ Generating map 05: H3 Access to Essentials...")
    
    if layers["h3_pop"] is None or layers["amenities"] is None:
        print("  ⚠️ Missing H3 population or amenities data")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)
    
    # Convert H3 to polygons
    h3_polys = [hex_polygon(h) for h in layers["h3_pop"]["h3"]]
    h3_gdf = gpd.GeoDataFrame(layers["h3_pop"], geometry=h3_polys, crs=4326).to_crs(PLOT_CRS)
    
    # Filter essential amenities
    amenities_plot = layers["amenities"].to_crs(PLOT_CRS)
    essential_categories = ['supermarket', 'pharmacy', 'school', 'hospital', 'doctors', 'clinic']
    essential_amenities = amenities_plot[amenities_plot['category'].isin(essential_categories)]
    
    # Calculate essential amenities per H3 cell
    if len(essential_amenities) > 0:
        amen_joined = gpd.sjoin(essential_amenities, h3_gdf, how='right', predicate='within')
        amen_counts = amen_joined.groupby(amen_joined.index_right).size().fillna(0)
        h3_gdf['essentials_count'] = amen_counts
        
        # Plot H3 essentials access
        h3_gdf.plot(ax=ax, column='essentials_count', cmap='Blues', alpha=0.8, legend=True)
    
    # Add district boundaries
    if layers["districts"] is not None:
        layers["districts"].to_crs(PLOT_CRS).boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.8)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.3)
    
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title("Stuttgart — H3 Access to Essentials", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / "05_access_essentials_h3.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✅ Saved: 05_access_essentials_h3.png")

def map_06_service_diversity_h3(layers, extent):
    """Generate H3 service diversity map"""
    print("🗺️ Generating map 06: H3 Service Diversity...")
    
    if layers["h3_pop"] is None or layers["amenities"] is None:
        print("  ⚠️ Missing H3 population or amenities data")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)
    
    # Convert H3 to polygons
    h3_polys = [hex_polygon(h) for h in layers["h3_pop"]["h3"]]
    h3_gdf = gpd.GeoDataFrame(layers["h3_pop"], geometry=h3_polys, crs=4326).to_crs(PLOT_CRS)
    
    # Calculate service diversity per H3 cell
    amenities_plot = layers["amenities"].to_crs(PLOT_CRS)
    amen_joined = gpd.sjoin(amenities_plot, h3_gdf, how='right', predicate='within')
    
    # Count unique categories per H3 cell
    # Handle different spatial join column names
    if 'index_right' in amen_joined.columns:
        diversity = amen_joined.groupby(amen_joined.index_right)['category'].nunique().fillna(0)
    else:
        diversity = amen_joined.groupby(amen_joined.index)['category'].nunique().fillna(0)
    h3_gdf['service_diversity'] = diversity
    
    # Plot H3 service diversity
    h3_gdf.plot(ax=ax, column='service_diversity', cmap='viridis', alpha=0.8, legend=True)
    
    # Add district boundaries
    if layers["districts"] is not None:
        layers["districts"].to_crs(PLOT_CRS).boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.8)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.3)
    
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title("Stuttgart — H3 Service Diversity", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    plt.tight_layout()
    plt.savefig(OUT_DIR / "06_service_diversity_h3.png", dpi=300, bbox_inches='tight')
    plt.close()
    print("  ✅ Saved: 06_service_diversity_h3.png")

def export_kepler_layers(layers):
    """Export all layers to Kepler format"""
    print("\n📊 Exporting layers to Kepler.gl format...")
    
    try:
        # Export districts
        if layers["districts"] is not None:
            layers["districts"].to_crs(4326).to_file(KEPLER_DIR / "01_districts_with_kpis.geojson", driver='GeoJSON')
            print("  ✅ Districts exported")
        
        # Export PT stops
        if layers["pt_stops"] is not None:
            layers["pt_stops"].to_crs(4326).to_file(KEPLER_DIR / "02_pt_stops.geojson", driver='GeoJSON')
            print("  ✅ PT stops exported")
        
        # Export roads
        if layers["roads"] is not None:
            layers["roads"].to_crs(4326).to_file(KEPLER_DIR / "03_roads.geojson", driver='GeoJSON')
            print("  ✅ Roads exported")
        
        # Export landuse
        if layers["landuse"] is not None:
            layers["landuse"].to_crs(4326).to_file(KEPLER_DIR / "04_landuse.geojson", driver='GeoJSON')
            print("  ✅ Landuse exported")
        
        # Export H3 population
        if layers["h3_pop"] is not None:
            h3_polys = [hex_polygon(h) for h in layers["h3_pop"]["h3"]]
            h3_kepler = gpd.GeoDataFrame(layers["h3_pop"], geometry=h3_polys, crs=4326)
            h3_kepler.to_file(KEPLER_DIR / "05_h3_population.geojson", driver='GeoJSON')
            print("  ✅ H3 population exported")
        
        # Export city boundary
        if layers["boundary"] is not None:
            layers["boundary"].to_crs(4326).to_file(KEPLER_DIR / "06_city_boundary.geojson", driver='GeoJSON')
            print("  ✅ City boundary exported")
        
        print(f"📁 Kepler data exported to: {KEPLER_DIR}")
        
    except Exception as e:
        print(f"⚠️ Kepler export failed: {e}")

def main():
    """Main execution function"""
    print(f"🗺️ Generating Comprehensive Stuttgart Maps (Series {RUN_NUMBER})...")
    print(f"📁 Output directory: {OUT_DIR}")
    print(f"📁 Kepler directory: {KEPLER_DIR}")
    
    # Load data layers
    layers = load_layers()
    
    # Get extent from districts or boundary
    if layers["districts"] is not None:
        extent = _extent_from(layers["districts"])
    elif layers["boundary"] is not None:
        extent = _extent_from(layers["boundary"])
    else:
        print("❌ No spatial data available for extent calculation")
        return
    
    # Generate all maps
    print("\n🗺️ Generating comprehensive maps...")
    
    map_01_overview_landuse_roads_pt(layers, extent)
    map_02_h3_population_pt(layers, extent)
    map_03_district_accessibility(layers, extent)
    map_04_pt_modal_gravity_h3(layers, extent)
    map_05_access_essentials_h3(layers, extent)
    map_06_service_diversity_h3(layers, extent)
    
    # Export Kepler layers
    export_kepler_layers(layers)
    
    # Create run info
    import json
    from datetime import datetime
    run_info = {
        "run_number": RUN_NUMBER,
        "timestamp": datetime.now().isoformat(),
        "output_directory": str(OUTPUT_BASE),
        "maps_generated": 6,
        "kepler_layers_exported": True,
        "comprehensive_analysis": True,
        "features": [
            "Consistent clipping/extent",
            "Basemap + escala",
            "Overview maps",
            "H3 analysis maps",
            "District accessibility maps",
            "Kepler export"
        ]
    }
    
    with open(OUTPUT_BASE / "run_info.json", 'w') as f:
        json.dump(run_info, f, indent=2)
    
    print("\n🎉 All 6 comprehensive maps generated successfully!")
    print(f"📁 Check outputs in: {OUT_DIR}")
    print(f"📁 Check Kepler data in: {KEPLER_DIR}")
    print(f"📊 Run info saved: {OUTPUT_BASE / 'run_info.json'}")

if __name__ == "__main__":
    main()
