#!/usr/bin/env python3
"""
Enhanced VVS Maps Generator for Stuttgart
Creates beautiful, publication-quality micro and macro-scale maps

Author: Geospatial Data Expert
Purpose: Job application at VVS (Stuttgart Public Transport)
Features: All 23 real districts, enhanced aesthetics, proper choropleth scales
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import contextily as ctx
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Enhanced configuration
DATA_DIR = Path("pipeline/areas/stuttgart/data_final/staging")
DISTRICTS_GPKG = Path("stuttgart_districts_official/OpenData_KLGL_GENERALISIERT.gpkg")
OUTPUT_DIR = Path("outputs_enhanced")
MICRO_DIR = OUTPUT_DIR / "micro"
MACRO_DIR = OUTPUT_DIR / "macro"

# Create output directories
OUTPUT_DIR.mkdir(exist_ok=True)
MICRO_DIR.mkdir(exist_ok=True)
MACRO_DIR.mkdir(exist_ok=True)

# Enhanced color schemes
COLOR_SCHEMES = {
    'mobility': 'RdYlGn',      # Red-Yellow-Green for mobility scores
    'pt_access': 'Blues',      # Blue for public transport
    'walkability': 'Oranges',  # Orange for walkability
    'poi_access': 'Purples',   # Purple for POI access
    'green_space': 'Greens',   # Green for green spaces
    'population': 'Reds'       # Red for population density
}

def load_real_districts():
    """Load real Stuttgart districts from official GeoPackage"""
    print("🗺️ Loading real Stuttgart districts...")
    
    districts = gpd.read_file(DISTRICTS_GPKG, layer="KLGL_BRUTTO_STADTBEZIRK")
    
    # Convert to WGS84 for consistency
    districts = districts.to_crs(epsg=4326)
    
    print(f"✅ Loaded {len(districts)} real districts")
    print(f"   CRS: {districts.crs}")
    print(f"   Columns: {list(districts.columns)}")
    
    return districts

def load_osm_data():
    """Load OSM data from staging directory"""
    print("📊 Loading OSM data...")
    
    data = {}
    
    # Load different OSM layers
    layers = ['amenities', 'buildings', 'cycle', 'landuse', 'pt_stops', 'roads']
    
    for layer in layers:
        file_path = DATA_DIR / f"osm_{layer}.parquet"
        if file_path.exists():
            data[layer] = gpd.read_parquet(file_path)
            print(f"   ✅ {layer}: {len(data[layer])} features")
        else:
            print(f"   ⚠️ {layer}: File not found")
    
    return data

def create_enhanced_choropleth(districts, data_column, title, color_scheme, output_path):
    """Create an enhanced choropleth map with beautiful aesthetics"""
    
    # Create figure with enhanced styling
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Set background color
    ax.set_facecolor('#f8f9fa')
    
    # Create choropleth with enhanced colors
    districts.plot(
        column=data_column,
        ax=ax,
        legend=True,
        legend_kwds={
            'label': title,
            'orientation': 'horizontal',
            'shrink': 0.8,
            'aspect': 30,
            'pad': 0.02
        },
        cmap=color_scheme,
        edgecolor='#2c3e50',
        linewidth=0.8,
        alpha=0.85
    )
    
    # Add district labels with enhanced styling
    for idx, row in districts.iterrows():
        if hasattr(row.geometry, 'centroid'):
            centroid = row.geometry.centroid
            district_name = row['STADTBEZIRKNAME']
            value = row[data_column]
            
            # Create enhanced label
            ax.annotate(
                f"{district_name}\n{value:.1f}",
                xy=(centroid.x, centroid.y),
                ha='center',
                va='center',
                fontsize=9,
                fontweight='bold',
                color='#2c3e50',
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor='white',
                    edgecolor='#34495e',
                    alpha=0.9,
                    linewidth=0.5
                )
            )
    
    # Enhanced title and styling
    ax.set_title(title, fontsize=20, fontweight='bold', pad=20, color='#2c3e50')
    
    # Enhanced axis labels
    ax.set_xlabel('Longitude', fontsize=14, fontweight='bold', color='#34495e')
    ax.set_ylabel('Latitude', fontsize=14, fontweight='bold', color='#34495e')
    
    # Enhanced grid
    ax.grid(True, alpha=0.2, color='#7f8c8d', linewidth=0.5)
    
    # Remove axis spines for cleaner look
    for spine in ax.spines.values():
        spine.set_color('#bdc3c7')
        spine.set_linewidth(0.5)
    
    # Add scale bar and north arrow
    add_map_elements(ax)
    
    # Add information box
    add_info_box(ax, f"Total Districts: {len(districts)}")
    
    # Add KPI calculation explanation
    add_kpi_explanation(ax, data_column)
    
    plt.tight_layout()
    
    # Save with high quality
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Enhanced choropleth saved: {output_path}")

def add_map_elements(ax):
    """Add scale bar and north arrow to the map"""
    
    # Scale bar (simplified)
    scale_text = "Scale: 1:100,000"
    ax.text(0.02, 0.05, scale_text,
            transform=ax.transAxes,
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # North arrow
    arrow_text = "↑ N"
    ax.text(0.95, 0.95, arrow_text,
            transform=ax.transAxes,
            fontsize=14,
            fontweight='bold',
            ha='center',
            va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

def add_info_box(ax, info_text):
    """Add information box to the map"""
    ax.text(0.02, 0.98, info_text,
            transform=ax.transAxes,
            verticalalignment='top',
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.4", facecolor='#ecf0f1', alpha=0.9, edgecolor='#bdc3c7'))

def add_kpi_explanation(ax, metric_name):
    """Add KPI calculation explanation to the map corner"""
    
    # KPI explanations for each metric
    kpi_explanations = {
        'mobility_score': 'Mobility Score = (PT Density × 0.30) + (Amenity Density × 0.25) + (Green Space Ratio × 0.20) + (Walkability Score × 0.25)',
        'pt_density': 'PT Density = Number of PT Stops ÷ District Area (km²)',
        'walkability_score': 'Walkability Score = (Walkable Roads ÷ 100) + (PT Stops × 2 ÷ 100)',
        'amenity_density': 'Amenity Density = Number of Amenities ÷ District Area (km²)',
        'green_space_ratio': 'Green Space Ratio = Number of Green Spaces ÷ District Area (km²)',
        'area_km2': 'District Area = Raw Area (degrees²) × 111² ÷ 1,000,000'
    }
    
    if metric_name in kpi_explanations:
        explanation = kpi_explanations[metric_name]
        
        # Add explanation in bottom-left corner
        ax.text(0.02, 0.02, f"📊 KPI Calculation:\n{explanation}",
                transform=ax.transAxes,
                verticalalignment='bottom',
                fontsize=8,
                fontstyle='italic',
                color='#2c3e50',
                bbox=dict(boxstyle="round,pad=0.3", 
                         facecolor='white', 
                         alpha=0.9, 
                         edgecolor='#bdc3c7',
                         linewidth=0.5))

def calculate_district_metrics(districts, osm_data):
    """Calculate comprehensive metrics for all districts"""
    print("📊 Calculating district metrics...")
    
    # Initialize metrics
    metrics = {}
    
    for idx, district in districts.iterrows():
        district_name = district['STADTBEZIRKNAME']
        district_geom = district.geometry
        
        # Initialize district metrics
        metrics[district_name] = {
            'pt_stops': 0,
            'amenities': 0,
            'green_spaces': 0,
            'walkable_roads': 0,
            'area_km2': district_geom.area * 111 * 111 / 1000000  # Approximate conversion
        }
        
        # Count features within district
        for layer_name, layer_data in osm_data.items():
            if layer_data is not None:
                # Spatial join to count features within district
                within_district = layer_data[layer_data.geometry.within(district_geom)]
                metrics[district_name][f'{layer_name}_count'] = len(within_district)
                
                # Specific counts for key metrics
                if layer_name == 'pt_stops':
                    metrics[district_name]['pt_stops'] = len(within_district)
                elif layer_name == 'amenities':
                    metrics[district_name]['amenities'] = len(within_district)
                elif layer_name == 'landuse':
                    # Count green spaces
                    green_types = ['park', 'recreation_ground', 'garden', 'forest', 'grass']
                    green_count = 0
                    for _, feature in within_district.iterrows():
                        if 'landuse' in feature and any(green in str(feature['landuse']).lower() for green in green_types):
                            green_count += 1
                    metrics[district_name]['green_spaces'] = green_count
                elif layer_name == 'roads':
                    # Count walkable roads
                    walkable_types = ['residential', 'footway', 'pedestrian', 'path', 'service']
                    walkable_count = 0
                    for _, feature in within_district.iterrows():
                        if 'highway' in feature and any(walkable in str(feature['highway']).lower() for walkable in walkable_types):
                            walkable_count += 1
                    metrics[district_name]['walkable_roads'] = walkable_count
    
    # Convert to DataFrame
    metrics_df = pd.DataFrame.from_dict(metrics, orient='index')
    
    # Calculate derived metrics
    metrics_df['pt_density'] = metrics_df['pt_stops'] / metrics_df['area_km2']
    metrics_df['amenity_density'] = metrics_df['amenities'] / metrics_df['area_km2']
    metrics_df['green_space_ratio'] = metrics_df['green_spaces'] / metrics_df['area_km2']
    metrics_df['walkability_score'] = (metrics_df['walkable_roads'] + metrics_df['pt_stops'] * 2) / 100
    
    # Normalize scores to 0-1 range
    for col in ['pt_density', 'amenity_density', 'green_space_ratio', 'walkability_score']:
        if metrics_df[col].max() > 0:
            metrics_df[col] = (metrics_df[col] - metrics_df[col].min()) / (metrics_df[col].max() - metrics_df[col].min())
    
    # Overall mobility score (weighted average)
    metrics_df['mobility_score'] = (
        metrics_df['pt_density'] * 0.3 +
        metrics_df['amenity_density'] * 0.25 +
        metrics_df['green_space_ratio'] * 0.2 +
        metrics_df['walkability_score'] * 0.25
    )
    
    print(f"✅ Calculated metrics for {len(metrics_df)} districts")
    return metrics_df

def generate_macro_maps(districts, metrics_df):
    """Generate enhanced macro-scale maps for all districts"""
    print("🗺️ Generating enhanced macro-scale maps...")
    
    # Merge metrics with districts
    districts_with_metrics = districts.copy()
    districts_with_metrics = districts_with_metrics.merge(
        metrics_df.reset_index().rename(columns={'index': 'STADTBEZIRKNAME'}),
        on='STADTBEZIRKNAME'
    )
    
    # Generate enhanced choropleth maps
    maps_to_generate = [
        ('mobility_score', 'Overall Mobility Score', 'mobility'),
        ('pt_density', 'Public Transport Density', 'pt_access'),
        ('walkability_score', 'Walkability Score', 'walkability'),
        ('amenity_density', 'Amenity Density', 'poi_access'),
        ('green_space_ratio', 'Green Space Ratio', 'green_space'),
        ('area_km2', 'District Area (km²)', 'population')
    ]
    
    for data_col, title, color_scheme in maps_to_generate:
        output_path = MACRO_DIR / f"stuttgart_{data_col}_enhanced.png"
        create_enhanced_choropleth(
            districts_with_metrics,
            data_col,
            title,
            COLOR_SCHEMES[color_scheme],
            output_path
        )
    
    # Create enhanced dashboard
    create_enhanced_dashboard(districts_with_metrics, MACRO_DIR / "stuttgart_enhanced_dashboard.png")
    
    print("✅ Enhanced macro-scale maps generated!")

def create_enhanced_dashboard(districts, output_path):
    """Create an enhanced dashboard with all metrics"""
    print("📊 Creating enhanced dashboard...")
    
    # Create subplots
    fig, axes = plt.subplots(2, 3, figsize=(20, 14))
    fig.suptitle('Stuttgart Enhanced Mobility & Infrastructure Dashboard', 
                 fontsize=24, fontweight='bold', y=0.98)
    
    # Metrics to plot
    metrics = [
        ('mobility_score', 'Overall Mobility Score', 'mobility'),
        ('pt_density', 'Public Transport Density', 'pt_access'),
        ('walkability_score', 'Walkability Score', 'walkability'),
        ('amenity_density', 'Amenity Density', 'poi_access'),
        ('green_space_ratio', 'Green Space Ratio', 'green_space'),
        ('area_km2', 'District Area (km²)', 'population')
    ]
    
    for idx, (metric, title, color_scheme) in enumerate(metrics):
        row = idx // 3
        col = idx % 3
        ax = axes[row, col]
        
        # Plot choropleth
        districts.plot(
            column=metric,
            ax=ax,
            legend=True,
            legend_kwds={'shrink': 0.8},
            cmap=COLOR_SCHEMES[color_scheme],
            edgecolor='#2c3e50',
            linewidth=0.6,
            alpha=0.8
        )
        
        # Enhanced styling
        ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        ax.set_facecolor('#f8f9fa')
        ax.grid(True, alpha=0.2)
        
        # Remove axis labels for cleaner look
        ax.set_xlabel('')
        ax.set_ylabel('')
        
        # Add district labels (smaller for dashboard)
        for _, district in districts.iterrows():
            if hasattr(district.geometry, 'centroid'):
                centroid = district.geometry.centroid
                ax.annotate(
                    district['STADTBEZIRKNAME'][:8],  # Truncate long names
                    xy=(centroid.x, centroid.y),
                    ha='center',
                    va='center',
                    fontsize=6,
                    fontweight='bold',
                    color='#2c3e50'
                )
        
        # Add KPI explanation for dashboard subplots
        kpi_text = f"📊 {title}\nFormula: See individual maps"
        ax.text(0.02, 0.02, kpi_text,
                transform=ax.transAxes,
                verticalalignment='bottom',
                fontsize=6,
                fontstyle='italic',
                color='#2c3e50',
                bbox=dict(boxstyle="round,pad=0.2", 
                         facecolor='white', 
                         alpha=0.8, 
                         edgecolor='#bdc3c7',
                         linewidth=0.3))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✅ Enhanced dashboard saved: {output_path}")

def generate_micro_maps(districts, osm_data, center_station="Stuttgart Hauptbahnhof"):
    """Generate enhanced micro-scale maps around a station"""
    print(f"📍 Generating enhanced micro-scale maps around {center_station}...")
    
    # Define center point (Stuttgart Hauptbahnhof coordinates)
    center_coords = (9.1829, 48.7836)  # Stuttgart Hbf
    center_point = Point(center_coords)
    
    # Create 1km buffer
    buffer_geom = center_point.buffer(0.01)  # Approximate 1km in degrees
    
    # Clip districts to buffer area
    buffer_gdf = gpd.GeoDataFrame(geometry=[buffer_geom], crs=districts.crs)
    clipped_districts = gpd.clip(districts, buffer_gdf)
    
    # Clip OSM data to buffer area
    clipped_osm = {}
    for layer_name, layer_data in osm_data.items():
        if layer_data is not None:
            clipped_osm[layer_name] = gpd.clip(layer_data, buffer_gdf)
    
    # Generate micro maps
    create_walkability_map(clipped_districts, clipped_osm, center_point, center_station)
    create_green_access_map(clipped_districts, clipped_osm, center_point, center_station)
    create_improvements_map(clipped_districts, clipped_osm, center_point, center_station)
    
    print("✅ Enhanced micro-scale maps generated!")

def create_walkability_map(districts, osm_data, center_point, station_name):
    """Create enhanced walkability map"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 12))
    
    # Plot districts
    districts.plot(ax=ax, facecolor='lightblue', alpha=0.3, edgecolor='#2c3e50')
    
    # Plot PT stops with 500m buffer
    if 'pt_stops' in osm_data and osm_data['pt_stops'] is not None:
        pt_stops = osm_data['pt_stops']
        pt_stops.plot(ax=ax, color='red', markersize=50, alpha=0.7, label='PT Stops')
        
        # Add 500m buffers
        for _, stop in pt_stops.iterrows():
            buffer = stop.geometry.buffer(0.005)  # Approximate 500m
            ax.add_patch(plt.matplotlib.patches.Polygon(
                buffer.exterior.coords,
                facecolor='red',
                alpha=0.1,
                edgecolor='red',
                linewidth=1
            ))
    
    # Plot walkable roads
    if 'roads' in osm_data and osm_data['roads'] is not None:
        roads = osm_data['roads']
        walkable_roads = roads[roads['highway'].isin(['residential', 'footway', 'pedestrian', 'path'])]
        walkable_roads.plot(ax=ax, color='green', linewidth=2, alpha=0.8, label='Walkable Roads')
    
    # Add center station
    ax.scatter(center_point.x, center_point.y, color='blue', s=200, marker='*', 
               label=f'{station_name}', zorder=10)
    
    # Enhanced styling
    ax.set_title(f'{station_name} - Enhanced Walkability & Transport Access', 
                 fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Add scale bar and north arrow
    add_map_elements(ax)
    
    # Add KPI explanation for walkability map
    ax.text(0.02, 0.02, "📊 KPI: 500m PT buffers + Walkable roads (residential, footway, pedestrian, path)",
            transform=ax.transAxes,
            verticalalignment='bottom',
            fontsize=8,
            fontstyle='italic',
            color='#2c3e50',
            bbox=dict(boxstyle="round,pad=0.3", 
                     facecolor='white', 
                     alpha=0.9, 
                     edgecolor='#bdc3c7',
                     linewidth=0.5))
    
    plt.tight_layout()
    output_path = MICRO_DIR / f"{station_name.replace(' ', '_')}_enhanced_walkability.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Enhanced walkability map saved: {output_path}")

def create_green_access_map(districts, osm_data, center_point, station_name):
    """Create enhanced green access map"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 12))
    
    # Plot districts
    districts.plot(ax=ax, facecolor='lightgreen', alpha=0.3, edgecolor='#2c3e50')
    
    # Plot green spaces
    if 'landuse' in osm_data and osm_data['landuse'] is not None:
        landuse = osm_data['landuse']
        green_spaces = landuse[landuse['landuse'].isin(['park', 'recreation_ground', 'garden', 'forest'])]
        green_spaces.plot(ax=ax, facecolor='green', alpha=0.6, edgecolor='darkgreen', linewidth=1)
    
    # Add 10-minute walking isochrone (approximate 800m)
    isochrone = center_point.buffer(0.008)
    ax.add_patch(plt.matplotlib.patches.Polygon(
        isochrone.exterior.coords,
        facecolor='none',
        edgecolor='blue',
        linewidth=2,
        linestyle='--',
        alpha=0.7
    ))
    
    # Add center station
    ax.scatter(center_point.x, center_point.y, color='red', s=200, marker='*', 
               label=f'{station_name}', zorder=10)
    
    # Enhanced styling
    ax.set_title(f'{station_name} - Enhanced Green Space Access', 
                 fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Add scale bar and north arrow
    add_map_elements(ax)
    
    # Add KPI explanation for green access map
    ax.text(0.02, 0.02, "📊 KPI: Green spaces (park, recreation, garden, forest) + 10-min walking isochrone (800m)",
            transform=ax.transAxes,
            verticalalignment='bottom',
            fontsize=8,
            fontstyle='italic',
            color='#2c3e50',
            bbox=dict(boxstyle="round,pad=0.3", 
                     facecolor='white', 
                     alpha=0.9, 
                     edgecolor='#bdc3c7',
                     linewidth=0.5))
    
    plt.tight_layout()
    output_path = MICRO_DIR / f"{station_name.replace(' ', '_')}_enhanced_green_access.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Enhanced green access map saved: {output_path}")

def create_improvements_map(districts, osm_data, center_point, station_name):
    """Create enhanced improvements map"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 12))
    
    # Plot districts
    districts.plot(ax=ax, facecolor='lightyellow', alpha=0.3, edgecolor='#2c3e50')
    
    # Plot existing infrastructure
    if 'roads' in osm_data and osm_data['roads'] is not None:
        roads = osm_data['roads']
        roads.plot(ax=ax, color='gray', linewidth=1, alpha=0.6)
    
    # Plot amenities
    if 'amenities' in osm_data and osm_data['amenities'] is not None:
        amenities = osm_data['amenities']
        amenities.plot(ax=ax, color='purple', markersize=100, alpha=0.7, label='Amenities')
    
    # Add center station
    ax.scatter(center_point.x, center_point.y, color='blue', s=200, marker='*', 
               label=f'{station_name}', zorder=10)
    
    # Enhanced styling
    ax.set_title(f'{station_name} - Enhanced Infrastructure & Improvement Suggestions', 
                 fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Add scale bar and north arrow
    add_map_elements(ax)
    
    # Add KPI explanation for improvements map
    ax.text(0.02, 0.02, "📊 KPI: Infrastructure analysis (roads + amenities) for improvement opportunities",
            transform=ax.transAxes,
            verticalalignment='bottom',
            fontsize=8,
            fontstyle='italic',
            color='#2c3e50',
            bbox=dict(boxstyle="round,pad=0.3", 
                     facecolor='white', 
                     alpha=0.9, 
                     edgecolor='#bdc3c7',
                     linewidth=0.5))
    
    plt.tight_layout()
    output_path = MICRO_DIR / f"{station_name.replace(' ', '_')}_enhanced_improvements.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Enhanced improvements map saved: {output_path}")

def main():
    """Main function to generate all enhanced maps"""
    print("🚀 Enhanced VVS Maps Generator for Stuttgart")
    print("=" * 50)
    
    try:
        # Load data
        districts = load_real_districts()
        osm_data = load_osm_data()
        
        # Calculate comprehensive metrics for all districts
        metrics_df = calculate_district_metrics(districts, osm_data)
        
        # Generate enhanced macro-scale maps
        generate_macro_maps(districts, metrics_df)
        
        # Generate enhanced micro-scale maps
        generate_micro_maps(districts, osm_data)
        
        print("\n🎉 All enhanced maps generated successfully!")
        print(f"📁 Output directory: {OUTPUT_DIR}")
        print(f"   • Macro maps: {MACRO_DIR}")
        print(f"   • Micro maps: {MICRO_DIR}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
