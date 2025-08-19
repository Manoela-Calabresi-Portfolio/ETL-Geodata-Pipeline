#!/usr/bin/env python3
"""
[STEP 3B - MAPS] Create Detailed Thematic Maps
Generates comprehensive visualizations of all categorized geodata

Usage: python pipeline/scripts/create_thematic_maps.py
Note: Run AFTER process_layers.py (Step 2) - Alternative to Step 3A
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import numpy as np
from utils import setup_logging, load_area_config, get_area_paths

def create_color_palette(categories, base_colors=None):
    """Create a consistent color palette for categories"""
    if base_colors is None:
        # Use a diverse color palette
        base_colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
        ]
    
    color_map = {}
    for i, cat in enumerate(sorted(categories)):
        color_map[cat] = base_colors[i % len(base_colors)]
    
    return color_map

def plot_layer(gdf, title, color_map, ax, show_legend=True):
    """Plot a single layer with categories"""
    if gdf.empty:
        ax.text(0.5, 0.5, 'No data available', transform=ax.transAxes, 
                ha='center', va='center', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        return
    
    # Plot by category
    for category in color_map.keys():
        cat_data = gdf[gdf['category'] == category]
        if not cat_data.empty:
            # Choose plot style based on geometry type
            geom_type = cat_data.geometry.iloc[0].geom_type
            if geom_type == 'Point':
                cat_data.plot(ax=ax, color=color_map[category], markersize=2, alpha=0.7)
            elif geom_type in ['LineString', 'MultiLineString']:
                cat_data.plot(ax=ax, color=color_map[category], linewidth=0.8, alpha=0.8)
            else:  # Polygon
                cat_data.plot(ax=ax, color=color_map[category], alpha=0.6, edgecolor='white', linewidth=0.1)
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_axis_off()
    
    # Add legend if requested
    if show_legend and color_map:
        legend_elements = []
        for category, color in color_map.items():
            count = len(gdf[gdf['category'] == category])
            if count > 0:
                legend_elements.append(
                    mpatches.Patch(color=color, label=f'{category} ({count:,})')
                )
        
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper right', fontsize=8, 
                     framealpha=0.9, fancybox=True)

def create_overview_map(processed_data, area_name):
    """Create overview map with all layers"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Plot layers in order (background to foreground)
    layer_order = ['landuse', 'buildings', 'roads', 'cycle', 'amenities', 'pt_stops']
    colors = ['lightgreen', 'lightcoral', 'gray', 'blue', 'red', 'purple']
    
    for layer, color in zip(layer_order, colors):
        if layer in processed_data and not processed_data[layer].empty:
            gdf = processed_data[layer]
            geom_type = gdf.geometry.iloc[0].geom_type
            
            if geom_type == 'Point':
                gdf.plot(ax=ax, color=color, markersize=1, alpha=0.6)
            elif geom_type in ['LineString', 'MultiLineString']:
                gdf.plot(ax=ax, color=color, linewidth=0.5, alpha=0.7)
            else:  # Polygon
                gdf.plot(ax=ax, color=color, alpha=0.4, edgecolor='white', linewidth=0.1)
    
    ax.set_title(f'{area_name} - Thematic Overview\nAll layers combined', 
                fontsize=16, fontweight='bold')
    ax.set_axis_off()
    
    # Create legend
    legend_elements = []
    for layer, color in zip(layer_order, colors):
        if layer in processed_data and not processed_data[layer].empty:
            count = len(processed_data[layer])
            legend_elements.append(
                mpatches.Patch(color=color, label=f'{layer.title()} ({count:,})')
            )
    
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10, 
             framealpha=0.9, fancybox=True)
    
    return fig

def main():
    """Create all thematic maps"""
    area_name = "stuttgart"
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    logger = logging.getLogger("maps")
    
    # Load configuration
    from utils import load_pipeline_config
    pipeline_config = load_pipeline_config()
    area_config = load_area_config(area_name)
    paths = get_area_paths(area_name, pipeline_config)
    
    logger.info(f"Creating thematic maps for {area_config['area']['full_name']}")
    
    # Load all processed data
    processed_data = {}
    layers = ['landuse', 'roads', 'buildings', 'amenities', 'cycle', 'pt_stops']
    
    for layer in layers:
        file_path = paths['processed_template'] / f"{layer}_categorized.parquet"
        if file_path.exists():
            try:
                gdf = gpd.read_parquet(file_path)
                # Convert to Web Mercator for better visualization
                gdf = gdf.to_crs('EPSG:3857')
                processed_data[layer] = gdf
                logger.info(f"Loaded {layer}: {len(gdf):,} features")
            except Exception as e:
                logger.error(f"Failed to load {layer}: {e}")
        else:
            logger.warning(f"File not found: {file_path}")
    
    if not processed_data:
        logger.error("No processed data found!")
        return
    
    # Create output directory
    maps_dir = Path("data/maps/stuttgart")
    maps_dir.mkdir(parents=True, exist_ok=True)
    
    # Define category color schemes for each layer
    layer_colors = {
        'landuse': {
            'urban': '#ff4444', 'green': '#44ff44', 'agricultural': '#ffff44', 
            'water': '#4444ff', 'other': '#888888'
        },
        'roads': {
            'motorway': '#ff0000', 'primary': '#ff6600', 'secondary': '#ffaa00',
            'tertiary': '#ffdd00', 'residential': '#aaaaaa', 'service': '#dddddd',
            'cycling': '#00ff00', 'pedestrian': '#00ffff', 'other': '#888888'
        },
        'buildings': {
            'residential': '#ffcccc', 'commercial': '#ccccff', 'industrial': '#ccffcc',
            'civic': '#ffffcc', 'religious': '#ffccff', 'transport': '#ccffff',
            'agriculture': '#ffddcc', 'utility': '#ddccff', 'other': '#cccccc'
        },
        'amenities': {
            'parking': '#1f77b4', 'street_furniture': '#ff7f0e', 'waste_management': '#2ca02c',
            'utilities': '#d62728', 'food_beverage': '#9467bd', 'transport': '#8c564b',
            'education': '#e377c2', 'public_services': '#7f7f7f', 'community': '#bcbd22',
            'healthcare': '#17becf', 'financial': '#aec7e8', 'emergency': '#ffbb78',
            'maintenance': '#98df8a', 'animal_services': '#ff9896', 'commercial': '#c5b0d5',
            'recreation': '#c49c94', 'construction_logistics': '#f7b6d3', 'funeral_services': '#c7c7c7',
            'research_education': '#dbdb8d', 'accommodation': '#9edae5', 'other': '#888888'
        },
        'cycle': {
            'dedicated_cycleway': '#00aa00', 'shared_use_path': '#66cc66',
            'lane': '#aadd00', 'track': '#ccff00', 'other': '#888888'
        },
        'pt_stops': {
            'bus': '#ff6600', 'railway_station': '#0066cc', 'railway_platform': '#3388dd',
            'u_bahn': '#cc0066', 'tram': '#66cc00', 'taxi': '#ffcc00',
            'bus_station': '#ff9900', 'transport_hub': '#6600cc', 'stop_position': '#999999',
            'platform': '#bbbbbb', 'transport_service': '#cccccc', 'other': '#888888'
        }
    }
    
    # Create individual thematic maps
    for layer_name, gdf in processed_data.items():
        if gdf.empty:
            continue
            
        logger.info(f"Creating {layer_name} thematic map...")
        
        # Get categories and create color map
        categories = gdf['category'].unique()
        if layer_name in layer_colors:
            color_map = {cat: layer_colors[layer_name].get(cat, '#888888') for cat in categories}
        else:
            color_map = create_color_palette(categories)
        
        # Create map
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        
        title = f"{area_config['area']['name']} - {layer_name.title()}\n"
        if layer_name == 'pt_stops':
            title += "Bus stops, tram stations, and transport hubs"
        elif layer_name == 'amenities':
            title += "Services, facilities, and urban amenities"
        elif layer_name == 'buildings':
            title += "Building types and functions"
        elif layer_name == 'landuse':
            title += "Land use and natural areas"
        elif layer_name == 'roads':
            title += "Road network by hierarchy"
        elif layer_name == 'cycle':
            title += "Cycling infrastructure"
        
        plot_layer(gdf, title, color_map, ax, show_legend=True)
        
        # Add metadata
        ax.text(0.02, 0.02, f'Features: {len(gdf):,}\\nGenerated: {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}',
                transform=ax.transAxes, fontsize=10, verticalalignment='bottom',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Save map
        output_file = maps_dir / f"stuttgart_thematic_{layer_name}.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"✓ Saved {layer_name} map: {output_file}")
    
    # Create overview map
    logger.info("Creating overview map...")
    fig = create_overview_map(processed_data, area_config['area']['name'])
    
    overview_file = maps_dir / "stuttgart_thematic_overview.png"
    plt.tight_layout()
    plt.savefig(overview_file, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"✓ Saved overview map: {overview_file}")
    logger.info("🎉 All thematic maps created successfully!")

if __name__ == "__main__":
    import pandas as pd
    main()
