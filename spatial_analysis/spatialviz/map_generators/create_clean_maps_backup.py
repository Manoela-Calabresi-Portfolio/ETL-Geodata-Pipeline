#!/usr/bin/env python3
"""
[STEP 3A - MAPS] Create Clean, Readable Thematic Maps
Focus on clarity and visual hierarchy instead of showing all data at once

Usage: python pipeline/scripts/create_clean_maps.py
Note: Run AFTER process_layers.py (Step 2)
"""

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import numpy as np
from utils import load_area_config, get_area_paths, load_pipeline_config

def create_clean_pt_stops_map(gdf, area_name):
    """Create a clean PT stops map focusing on main transport types"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Define priority categories and colors (focus on main transport types)
    priority_categories = {
        'u_bahn': '#cc0066',      # Pink for U-Bahn (subway)
        'railway_station': '#0066cc',  # Blue for train stations
        'tram': '#66cc00',        # Green for tram
        'bus_station': '#ff9900', # Orange for bus stations
        'transport_hub': '#6600cc' # Purple for major hubs
    }
    
    # Secondary categories (smaller, lighter)
    secondary_categories = {
        'bus': '#ffcc99',         # Light orange for regular bus stops
        'railway_platform': '#99ccff', # Light blue for platforms
        'taxi': '#ffff99'         # Light yellow for taxi
    }
    
    # Plot secondary categories first (background)
    for category, color in secondary_categories.items():
        cat_data = gdf[gdf['category'] == category]
        if not cat_data.empty:
            cat_data.plot(ax=ax, color=color, markersize=1, alpha=0.4, label=f'{category} ({len(cat_data):,})')
    
    # Plot priority categories on top (foreground)
    for category, color in priority_categories.items():
        cat_data = gdf[gdf['category'] == category]
        if not cat_data.empty:
            cat_data.plot(ax=ax, color=color, markersize=4, alpha=0.8, label=f'{category} ({len(cat_data):,})')
    
    ax.set_title(f'{area_name} - Public Transport\nMain stations and transport hubs', 
                fontsize=16, fontweight='bold')
    ax.set_axis_off()
    
    # Create clean legend (only for categories with data)
    legend_elements = []
    all_categories = {**priority_categories, **secondary_categories}
    for category, color in all_categories.items():
        cat_data = gdf[gdf['category'] == category]
        if not cat_data.empty:
            legend_elements.append(
                mpatches.Patch(color=color, label=f'{category.replace("_", " ").title()} ({len(cat_data):,})')
            )
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', fontsize=10, 
                 framealpha=0.9, fancybox=True)
    
    # Add metadata
    ax.text(0.02, 0.02, f'Total stops: {len(gdf):,}\\nFocus: Main transport infrastructure\\nGenerated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}',
            transform=ax.transAxes, fontsize=10, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    return fig

def create_clean_overview_map(processed_data, area_name):
    """Create a clean overview map with better visual hierarchy"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Plot layers in order with appropriate styling
    
    # 1. Landuse (background - very light)
    if 'landuse' in processed_data:
        landuse = processed_data['landuse']
        landuse.plot(ax=ax, color='lightgreen', alpha=0.2, edgecolor='none')
    
    # 2. Buildings (light, small)
    if 'buildings' in processed_data:
        buildings = processed_data['buildings']
        buildings.plot(ax=ax, color='lightgray', alpha=0.3, edgecolor='none')
    
    # 3. Roads (main roads only)
    if 'roads' in processed_data:
        roads = processed_data['roads']
        # Only show main roads
        main_roads = roads[roads['category'].isin(['motorway', 'primary', 'secondary'])]
        if not main_roads.empty:
            main_roads.plot(ax=ax, color='gray', linewidth=0.8, alpha=0.7)
    
    # 4. Key amenities (only important ones)
    if 'amenities' in processed_data:
        amenities = processed_data['amenities']
        # Focus on key amenities
        key_amenities = amenities[amenities['category'].isin([
            'education', 'healthcare', 'public_services', 'transport'
        ])]
        if not key_amenities.empty:
            key_amenities.plot(ax=ax, color='red', markersize=2, alpha=0.6)
    
    # 5. PT stops (main transport only)
    if 'pt_stops' in processed_data:
        pt_stops = processed_data['pt_stops']
        # Only show major transport
        major_transport = pt_stops[pt_stops['category'].isin([
            'u_bahn', 'railway_station', 'tram', 'bus_station', 'transport_hub'
        ])]
        if not major_transport.empty:
            major_transport.plot(ax=ax, color='blue', markersize=3, alpha=0.8)
    
    ax.set_title(f'{area_name} - Urban Overview\\nMain infrastructure and services', 
                fontsize=16, fontweight='bold')
    ax.set_axis_off()
    
    # Simple legend
    legend_elements = [
        mpatches.Patch(color='lightgreen', alpha=0.2, label='Land Use'),
        mpatches.Patch(color='lightgray', alpha=0.3, label='Buildings'),
        mpatches.Patch(color='gray', label='Main Roads'),
        mpatches.Patch(color='red', label='Key Services'),
        mpatches.Patch(color='blue', label='Public Transport')
    ]
    
    ax.legend(handles=legend_elements, loc='upper right', fontsize=12, 
             framealpha=0.9, fancybox=True)
    
    # Add metadata
    total_features = sum(len(gdf) for gdf in processed_data.values())
    ax.text(0.02, 0.02, f'Total features: {total_features:,}\\nSimplified view\\nGenerated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}',
            transform=ax.transAxes, fontsize=10, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    return fig

def create_focused_amenities_map(gdf, area_name):
    """Create a focused amenities map showing key services only"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Focus on key service categories
    key_services = {
        'education': '#e377c2',      # Pink
        'healthcare': '#17becf',     # Cyan  
        'public_services': '#7f7f7f', # Gray
        'food_beverage': '#9467bd',  # Purple
        'transport': '#8c564b',      # Brown
        'financial': '#aec7e8'       # Light blue
    }
    
    # Plot key services
    for category, color in key_services.items():
        cat_data = gdf[gdf['category'] == category]
        if not cat_data.empty:
            cat_data.plot(ax=ax, color=color, markersize=3, alpha=0.7)
    
    ax.set_title(f'{area_name} - Key Services\\nEducation, healthcare, and essential services', 
                fontsize=16, fontweight='bold')
    ax.set_axis_off()
    
    # Create legend
    legend_elements = []
    for category, color in key_services.items():
        cat_data = gdf[gdf['category'] == category]
        if not cat_data.empty:
            legend_elements.append(
                mpatches.Patch(color=color, label=f'{category.replace("_", " ").title()} ({len(cat_data):,})')
            )
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', fontsize=11, 
                 framealpha=0.9, fancybox=True)
    
    # Add metadata
    total_shown = sum(len(gdf[gdf['category'] == cat]) for cat in key_services.keys())
    ax.text(0.02, 0.02, f'Key services: {total_shown:,} of {len(gdf):,} total\\nFiltered view\\nGenerated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}',
            transform=ax.transAxes, fontsize=10, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    return fig

def main():
    """Create clean, readable maps"""
    area_name = "stuttgart"
    import logging
    import pandas as pd
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    logger = logging.getLogger("clean_maps")
    
    # Load configuration
    pipeline_config = load_pipeline_config()
    area_config = load_area_config(area_name)
    paths = get_area_paths(area_name, pipeline_config)
    
    logger.info(f"Creating clean maps for {area_config['area']['full_name']}")
    
    # Load processed data
    processed_data = {}
    layers = ['landuse', 'roads', 'buildings', 'amenities', 'pt_stops']
    
    for layer in layers:
        file_path = paths['processed_template'] / f"{layer}_categorized.parquet"
        if file_path.exists():
            try:
                gdf = gpd.read_parquet(file_path)
                gdf = gdf.to_crs('EPSG:3857')  # Web Mercator for visualization
                processed_data[layer] = gdf
                logger.info(f"Loaded {layer}: {len(gdf):,} features")
            except Exception as e:
                logger.error(f"Failed to load {layer}: {e}")
    
    # Create output directory
    maps_dir = Path("data/maps/stuttgart")
    maps_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Clean PT stops map
    if 'pt_stops' in processed_data:
        logger.info("Creating clean PT stops map...")
        fig = create_clean_pt_stops_map(processed_data['pt_stops'], area_config['area']['name'])
        output_file = maps_dir / "stuttgart_clean_pt_stops.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"✓ Saved clean PT stops map: {output_file}")
    
    # 2. Clean overview map
    logger.info("Creating clean overview map...")
    fig = create_clean_overview_map(processed_data, area_config['area']['name'])
    output_file = maps_dir / "stuttgart_clean_overview.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    logger.info(f"✓ Saved clean overview map: {output_file}")
    
    # 3. Focused amenities map
    if 'amenities' in processed_data:
        logger.info("Creating focused amenities map...")
        fig = create_focused_amenities_map(processed_data['amenities'], area_config['area']['name'])
        output_file = maps_dir / "stuttgart_clean_amenities.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"✓ Saved focused amenities map: {output_file}")
    
    logger.info("🎉 Clean maps created successfully!")

if __name__ == "__main__":
    main()
