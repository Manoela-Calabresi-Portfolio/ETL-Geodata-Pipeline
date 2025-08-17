#!/usr/bin/env python3
"""
Portfolio-Grade Map Styling System
Professional design standards for VVS job application maps

Author: Geospatial Data Expert
Purpose: Consistent, publication-quality map aesthetics
"""

import matplotlib.pyplot as plt
from matplotlib.patheffects import withStroke
import matplotlib.patches as patches
import pandas as pd

# Professional Color Palette
PALETTE = {
    # Road hierarchy
    "motorway": "#252525",
    "primary": "#4f4f4f", 
    "secondary": "#8a8a8a",
    "residential": "#c2c2c2",
    "cycle": "#0ea5e9",
    
    # Green spaces
    "green_fill": "#8bd3a3",
    "green_edge": "#3d7a57",
    
    # Public transport - differentiated by type
    "pt_stop": "#2563eb",  # Default blue for general stops
    "pt_line": "#0ea5e9",
    
    # PT infrastructure specific colors
    "railway_station": "#dc2626",      # Red for major stations
    "railway_platform": "#7c3aed",    # Purple for platforms
    "subway": "#059669",               # Green for U-Bahn
    "tram": "#ea580c",                 # Orange for tram stops
    "bus": "#2563eb",                  # Blue for bus stops
    "bus_station": "#1d4ed8",         # Darker blue for bus stations
    "transport_hub": "#be185d",        # Pink for major hubs
    "platform": "#7c3aed",             # Purple for general platforms
    "stop_position": "#2563eb",        # Blue for stop positions
    "stop_area": "#1e40af",            # Dark blue for stop areas
    
    # Sequential color ramps
    "greens": ["#e8f5e9", "#c8e6c9", "#a5d6a7", "#81c784", "#66bb6a", "#4caf50", "#1b5e20"],
    "oranges": ["#fff3e0", "#ffe0b2", "#ffcc80", "#ffb74d", "#ffa726", "#ff9800", "#e65100"]
}

def apply_style(ax, north=True, scalebar=True, extent=None, title=None, subtitle=None):
    """
    Apply portfolio-grade styling to matplotlib axes
    
    Args:
        ax: Matplotlib axes object
        north: Add north arrow (top-right)
        scalebar: Add scale bar (bottom-left) 
        extent: Map extent [xmin, ymin, xmax, ymax] for positioning
        title: Main title
        subtitle: Subtitle with metric info
    """
    # Clean, minimal appearance
    ax.set_axis_off()
    for spine in ax.spines.values(): 
        spine.set_visible(False)
    ax.margins(0.03)
    
    # Set extent if provided
    if extent is not None and len(extent) == 4:
        ax.set_xlim(extent[0], extent[2])
        ax.set_ylim(extent[1], extent[3])
    
    # Add north arrow (top-right)
    if north and extent is not None and len(extent) == 4:
        w, h = extent[2] - extent[0], extent[3] - extent[1]
        x0 = extent[0] + w * 0.93
        y0 = extent[1] + h * 0.85
        
        ax.annotate("N", (x0, y0), (x0, y0 + h * 0.08),
                    arrowprops=dict(arrowstyle="-|>", lw=2, color="black"),
                    ha="center", va="center", fontsize=12, fontweight="bold",
                    path_effects=[withStroke(linewidth=3, foreground="white")])
    
    # Add scale bar (bottom-left)
    if scalebar and extent is not None and len(extent) == 4:
        w = extent[2] - extent[0]
        # Calculate appropriate scale bar length (0.5-2 km)
        L = max(500, min(2000, int(w / 6 / 1000) * 1000))
        
        x = extent[0] + w * 0.06
        y = extent[1] + (extent[3] - extent[1]) * 0.07
        
        # Two-segment scale bar
        ax.add_patch(patches.Rectangle((x, y), L/2, 80, 
                                      fc="black", ec="black", linewidth=0.5))
        ax.add_patch(patches.Rectangle((x + L/2, y), L/2, 80, 
                                      fc="white", ec="black", linewidth=0.5))
        
        # Scale label
        ax.text(x + L/2, y + 120, f"{int(L/1000)} km", ha="center",
                path_effects=[withStroke(linewidth=3, foreground="white")], 
                fontsize=9, fontweight="bold")
    
    # Add title and subtitle
    if title:
        ax.text(0.5, 0.95, title, transform=ax.transAxes, ha="center", va="top",
                fontsize=16, fontweight="bold", 
                path_effects=[withStroke(linewidth=3, foreground="white")])
    
    if subtitle:
        ax.text(0.5, 0.90, subtitle, transform=ax.transAxes, ha="center", va="top",
                fontsize=11, style="italic", alpha=0.8,
                path_effects=[withStroke(linewidth=2, foreground="white")])

def create_legend(ax, legend_elements, position="upper right"):
    """
    Create compact, professional legend
    
    Args:
        ax: Matplotlib axes object
        legend_elements: List of legend handles
        position: Legend position
    """
    legend = ax.legend(handles=legend_elements, loc=position, 
                       frameon=True, fancybox=False, 
                       framealpha=0.9, edgecolor="#3b3b3b",
                       fontsize=9, title_fontsize=10)
    
    # Style the legend frame
    legend.get_frame().set_linewidth(0.5)
    legend.get_frame().set_facecolor("white")
    
    return legend

def get_road_style(road_type):
    """
    Get consistent road styling based on type
    
    Args:
        road_type: Road classification (motorway, primary, secondary, residential, cycle)
    
    Returns:
        dict: Color, linewidth, alpha, zorder
    """
    styles = {
        "motorway": {"color": PALETTE["motorway"], "linewidth": 1.8, "alpha": 0.9, "zorder": 4},
        "primary": {"color": PALETTE["primary"], "linewidth": 1.2, "alpha": 0.8, "zorder": 3},
        "secondary": {"color": PALETTE["secondary"], "linewidth": 0.8, "alpha": 0.7, "zorder": 2},
        "residential": {"color": PALETTE["residential"], "linewidth": 0.6, "alpha": 0.6, "zorder": 1},
        "cycle": {"color": PALETTE["cycle"], "linewidth": 1.6, "alpha": 0.8, "zorder": 3}
    }
    
    return styles.get(road_type, styles["residential"])

def plot_roads(roads_gdf, ax, road_type_col="highway", default_type="residential"):
    """
    Plot roads with consistent styling
    
    Args:
        roads_gdf: GeoDataFrame with road geometries
        ax: Matplotlib axes object
        road_type_col: Column containing road types
        default_type: Default road type for styling
    """
    for road_type in roads_gdf[road_type_col].unique():
        if pd.isna(road_type):
            road_type = default_type
            
        subset = roads_gdf[roads_gdf[road_type_col] == road_type]
        style = get_road_style(road_type)
        
        subset.plot(ax=ax, color=style["color"], linewidth=style["linewidth"], 
                   alpha=style["alpha"], zorder=style["zorder"])

def plot_pt_stops(stops_gdf, ax, size_col=None, min_size=4, max_size=8):
    """
    Plot PT stops with professional styling, differentiated by category
    
    Args:
        stops_gdf: GeoDataFrame with stop geometries and category column
        ax: Matplotlib axes object
        size_col: Column for sizing stops (e.g., ridership)
        min_size: Minimum point size
        max_size: Maximum point size
    """
    # Define category-specific styling
    category_styles = {
        'railway_station': {'color': PALETTE['railway_station'], 'marker': 's', 'size': 8},
        'railway_platform': {'color': PALETTE['railway_platform'], 'marker': '^', 'size': 6},
        'subway': {'color': PALETTE['subway'], 'marker': 'o', 'size': 7},
        'tram': {'color': PALETTE['tram'], 'marker': 'o', 'size': 6},
        'bus': {'color': PALETTE['bus'], 'marker': 'o', 'size': 5},
        'bus_station': {'color': PALETTE['bus_station'], 'marker': 's', 'size': 7},
        'transport_hub': {'color': PALETTE['transport_hub'], 'marker': '*', 'size': 12},  # Star marker, larger size
        'platform': {'color': PALETTE['platform'], 'marker': '^', 'size': 6},
        'stop_position': {'color': PALETTE['stop_position'], 'marker': 'o', 'size': 5},
        'stop_area': {'color': PALETTE['stop_area'], 'marker': 's', 'size': 6},
        'u_bahn': {'color': PALETTE['subway'], 'marker': 'o', 'size': 7},  # Alias for subway
    }
    
    # Plot each category with its specific style
    for category in stops_gdf['category'].unique():
        if pd.isna(category):
            category = 'other'
            
        subset = stops_gdf[stops_gdf['category'] == category]
        
        # Get style for this category, or use default
        style = category_styles.get(category, {
            'color': PALETTE['pt_stop'], 
            'marker': 'o', 
            'size': 6
        })
        
        # Apply size scaling if size_col is provided
        if size_col and size_col in subset.columns:
            sizes = subset[size_col].fillna(0)
            if sizes.max() > sizes.min():
                sizes = min_size + (sizes - sizes.min()) / (sizes.max() - sizes.min()) * (max_size - min_size)
            else:
                sizes = style['size']
        else:
            sizes = style['size']
        
        # Plot with category-specific styling
        subset.plot(ax=ax, 
                   color=style['color'], 
                   marker=style['marker'],
                   markersize=sizes, 
                   alpha=0.9,
                   path_effects=[withStroke(linewidth=2, foreground="white")], 
                   zorder=5,
                   label=f"{category.replace('_', ' ').title()} ({len(subset)})")

def plot_green_spaces(greens_gdf, ax, alpha=0.75):
    """
    Plot green spaces with professional styling
    
    Args:
        greens_gdf: GeoDataFrame with green space geometries
        ax: Matplotlib axes object
        alpha: Transparency level
    """
    greens_gdf.plot(ax=ax, facecolor=PALETTE["green_fill"], 
                   edgecolor=PALETTE["green_edge"], linewidth=0.4, 
                   alpha=alpha, zorder=1)

def clip_to_boundary(gdf, boundary_gdf):
    """
    Clip geometries to official city boundary
    
    Args:
        gdf: GeoDataFrame to clip
        boundary_gdf: GeoDataFrame with city boundary
    
    Returns:
        GeoDataFrame: Clipped geometries
    """
    # Ensure both are in the same CRS
    if gdf.crs != boundary_gdf.crs:
        gdf = gdf.to_crs(boundary_gdf.crs)
    
    # Clip to boundary
    clipped = gdf.clip(boundary_gdf)
    
    return clipped

def simplify_for_scale(gdf, tolerance=20):
    """
    Simplify geometries for city-scale visualization
    
    Args:
        gdf: GeoDataFrame to simplify
        tolerance: Simplification tolerance (meters in EPSG:3857)
    
    Returns:
        GeoDataFrame: Simplified geometries
    """
    # Convert to EPSG:3857 for metric simplification
    if gdf.crs.to_epsg() != 3857:
        gdf_3857 = gdf.to_crs(epsg=3857)
    else:
        gdf_3857 = gdf.copy()
    
    # Simplify geometries
    gdf_3857["geometry"] = gdf_3857.geometry.simplify(tolerance)
    
    # Convert back to original CRS
    if gdf.crs.to_epsg() != 3857:
        result = gdf_3857.to_crs(gdf.crs)
    else:
        result = gdf_3857
    
    return result
