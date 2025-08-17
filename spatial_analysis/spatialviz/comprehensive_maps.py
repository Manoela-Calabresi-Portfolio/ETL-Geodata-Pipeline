#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import warnings, math
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import contextily as cx

# Import our local modules
from style_helpers import apply_style, palette
from h3_utils import hex_polygon

warnings.filterwarnings("ignore", category=UserWarning)

# Updated paths to match current project structure
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
OUT_DIR  = Path("outputs/comprehensive_maps"); OUT_DIR.mkdir(parents=True, exist_ok=True)
PLOT_CRS = 3857

# ---------- Loaders ----------
def _read_gdf(path: Path):
    if not path.exists(): return None
    try:
        if path.suffix.lower() in {".geojson",".json",".gpkg"}:
            return gpd.read_file(path)
        elif path.suffix.lower() == ".parquet":
            df = pd.read_parquet(path)
            if "geometry" in df.columns:
                if df['geometry'].dtype == 'object' and isinstance(df['geometry'].iloc[0], bytes):
                    from shapely import wkb
                    df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
                return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)
            else:
                return df
        else:
            return pd.read_parquet(path)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def load_layers():
    layers = dict(
        districts=_read_gdf(DATA_DIR/"districts_with_population.geojson"),
        landuse=_read_gdf(DATA_DIR/"processed/landuse_categorized.parquet"),
        cycle=_read_gdf(DATA_DIR/"processed/cycle_categorized.parquet"),
        roads=_read_gdf(DATA_DIR/"processed/roads_categorized.parquet"),
        pt_stops=_read_gdf(DATA_DIR/"processed/pt_stops_categorized.parquet"),
        buildings=_read_gdf(DATA_DIR/"processed/buildings_categorized.parquet"),
        amenities=_read_gdf(DATA_DIR/"processed/amenities_categorized.parquet"),
        boundary=_read_gdf(DATA_DIR/"city_boundary.geojson"),
        h3_pop=pd.read_parquet(DATA_DIR/"h3_population_res8.parquet") if (DATA_DIR/"h3_population_res8.parquet").exists() else None,
    )
    
    for k in ["districts","landuse","cycle","roads","pt_stops","buildings","amenities","boundary"]:
        if layers[k] is not None and hasattr(layers[k], 'crs'):
            layers[k] = layers[k].set_crs(4326) if layers[k].crs is None else layers[k].to_crs(4326)
    return layers

def _extent_from(gdf):
    return tuple(gdf.to_crs(PLOT_CRS).total_bounds)

# ---------- Plot helpers ----------
def _add_basemap(ax, extent):
    try: cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, alpha=0.30, crs=PLOT_CRS)
    except Exception: pass
    ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])

def _save(fig, name):
    out = OUT_DIR/name
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {out}")

def _add_legend_right_column(ax, extent, title, colors, values, value_range):
    legend_x0, legend_y0 = 0.78, 0.15
    legend_width, legend_height = 0.18, 0.10
    
    legend_x = extent[0] + (extent[2] - extent[0]) * legend_x0
    legend_y = extent[1] + (extent[3] - extent[1]) * legend_y0
    legend_w = (extent[2] - extent[0]) * legend_width
    legend_h = (extent[3] - extent[1]) * legend_height
    
    for i, color in enumerate(colors):
        patch_x = legend_x + (i / len(colors)) * legend_w
        patch_y = legend_y + (0.5 - 0.1 * (i - len(colors) / 2)) * legend_h
        ax.add_artist(patches.Rectangle(
            (patch_x, patch_y), legend_w / len(colors), legend_h * 0.1,
            facecolor=color, edgecolor="none", alpha=0.9
        ))
    
    ax.add_artist(patches.Rectangle(
        (legend_x, legend_y), legend_w, legend_h,
        facecolor="none", edgecolor="#333", linewidth=1.5
    ))
    
    ax.text(legend_x + legend_w/2, legend_y - legend_h*0.1, 
            title, fontsize=11, ha="center", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y + legend_h/2, 
            value_range, fontsize=11, rotation=90, va="center", weight="bold")
    
    ax.text(legend_x, legend_y + legend_h + legend_h*0.05, "Low", fontsize=9, ha="center", weight="bold")
    ax.text(legend_x + legend_w, legend_y + legend_h + legend_h*0.05, "High", fontsize=9, ha="center", weight="bold")

def _add_data_info_box(ax, extent, text):
    box_x0, box_y0 = 0.02, 0.75
    box_width, box_height = 0.25, 0.20
    
    box_x = extent[0] + (extent[2] - extent[0]) * box_x0
    box_y = extent[1] + (extent[3] - extent[1]) * box_y0
    box_w = (extent[2] - extent[0]) * box_width
    box_h = (extent[3] - extent[1]) * box_height
    
    ax.add_artist(patches.Rectangle(
        (box_x, box_y), box_w, box_h,
        facecolor="white", edgecolor="#333", linewidth=1.5, alpha=0.95
    ))
    
    explanation_lines = text.split("\n")
    for i, line in enumerate(explanation_lines):
        y_pos = box_y + box_h - (i + 1) * (box_h / (len(explanation_lines) + 1))
        fontsize = 9 if i == 0 else 8
        weight = "bold" if i == 0 else "normal"
        ax.text(box_x + box_w*0.02, y_pos, line, 
                fontsize=fontsize, weight=weight, va="top", ha="left")

def _add_north_arrow_up(ax, extent):
    arrow_x0, arrow_y0 = 0.93, 0.25
    arrow_length = max(extent[2] - extent[0], extent[3] - extent[1]) * 0.08
    
    arrow_x = extent[0] + (extent[2] - extent[0]) * arrow_x0
    arrow_y = extent[1] + (extent[3] - extent[1]) * arrow_y0
    
    ax.annotate(
        "N",
        xy=(arrow_x, arrow_y),
        xytext=(arrow_x, arrow_y + arrow_length),
        ha="center", va="center",
        arrowprops=dict(arrowstyle="-|>", color="black", lw=2),
        fontsize=11, fontweight="bold",
        bbox=dict(boxstyle="circle,pad=0.25", facecolor="white", edgecolor="black", alpha=0.9),
        color="black"
    )

# ---------- Thematic Maps ----------
def thematic_amenities(amenities, extent):
    """Thematic map: Urban amenities distribution"""
    if amenities is None: return
    
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Plot amenities by category
    if "amenity" in amenities.columns:
        categories = amenities["amenity"].value_counts()
        top_categories = categories.head(10).index
        
        colors = palette()["viridis"][:len(top_categories)]
        for i, category in enumerate(top_categories):
            cat_data = amenities[amenities["amenity"] == category]
            cat_data.to_crs(PLOT_CRS).plot(
                ax=ax, color=colors[i], markersize=8, alpha=0.7, 
                label=f"{category} ({len(cat_data)})"
            )
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Urban Amenities Distribution", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Verteilung der städtischen Einrichtungen*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend
    ax.legend(bbox_to_anchor=(0.78, 0.15), loc="upper left", fontsize=9)
    
    # Add data processing info box
    _add_data_info_box(ax, extent, f"Data Processing:\n• Amenities: OSM amenity tags\n• Total features: {len(amenities):,}\n• Top categories shown\n• Data: OpenStreetMap (OSM)")
    
    # Add north arrow
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "thematic_amenities.png")

def thematic_buildings(buildings, extent):
    """Thematic map: Building types and functions"""
    if buildings is None: return
    
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Plot buildings by type
    if "building" in buildings.columns:
        building_types = buildings["building"].value_counts()
        top_types = building_types.head(8).index
        
        colors = palette()["oranges"][:len(top_types)]
        for i, btype in enumerate(top_types):
            type_data = buildings[buildings["building"] == btype]
            type_data.to_crs(PLOT_CRS).plot(
                ax=ax, color=colors[i], alpha=0.6, 
                label=f"{btype} ({len(type_data):,})"
            )
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Building Types and Functions", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Gebäudetypen und Funktionen*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend
    ax.legend(bbox_to_anchor=(0.78, 0.15), loc="upper left", fontsize=9)
    
    # Add data processing info box
    _add_data_info_box(ax, extent, f"Data Processing:\n• Buildings: OSM building tags\n• Total features: {len(buildings):,}\n• Top building types shown\n• Data: OpenStreetMap (OSM)")
    
    # Add north arrow
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "thematic_buildings.png")

def thematic_cycle(cycle, extent):
    """Thematic map: Cycling infrastructure"""
    if cycle is None: return
    
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Plot cycle infrastructure
    if "highway" in cycle.columns:
        cycle_types = cycle["highway"].value_counts()
        colors = palette()["blues"][:len(cycle_types)]
        
        for i, ctype in enumerate(cycle_types.index):
            type_data = cycle[cycle["highway"] == ctype]
            type_data.to_crs(PLOT_CRS).plot(
                ax=ax, color=colors[i], linewidth=2, alpha=0.8,
                label=f"{ctype} ({len(type_data):,})"
            )
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Cycling Infrastructure", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Radinfrastruktur*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend
    ax.legend(bbox_to_anchor=(0.78, 0.15), loc="upper left", fontsize=9)
    
    # Add data processing info box
    _add_data_info_box(ax, extent, f"Data Processing:\n• Cycle infrastructure: OSM highway tags\n• Total features: {len(cycle):,}\n• Categorized by type\n• Data: OpenStreetMap (OSM)")
    
    # Add north arrow
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "thematic_cycle.png")

def thematic_landuse(landuse, extent):
    """Thematic map: Land use and natural areas"""
    if landuse is None: return
    
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Plot land use categories
    if "landuse" in landuse.columns:
        landuse_types = landuse["landuse"].value_counts()
        top_types = landuse_types.head(8).index
        
        colors = palette()["greens"][:len(top_types)]
        for i, ltype in enumerate(top_types):
            type_data = landuse[landuse["landuse"] == ltype]
            type_data.to_crs(PLOT_CRS).plot(
                ax=ax, color=colors[i], alpha=0.7,
                label=f"{ltype} ({len(type_data):,})"
            )
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Land Use and Natural Areas", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Flächennutzung und Naturräume*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend
    ax.legend(bbox_to_anchor=(0.78, 0.15), loc="upper left", fontsize=9)
    
    # Add data processing info box
    _add_data_info_box(ax, extent, f"Data Processing:\n• Land use: OSM landuse + natural tags\n• Total features: {len(landuse):,}\n• Top categories shown\n• Data: OpenStreetMap (OSM)")
    
    # Add north arrow
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "thematic_landuse.png")

def thematic_roads(roads, extent):
    """Thematic map: Road network by hierarchy"""
    if roads is None: return
    
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Plot roads by hierarchy
    if "highway" in roads.columns:
        road_types = roads["highway"].value_counts()
        top_types = road_types.head(8).index
        
        colors = ["#d73027", "#fc8d59", "#fee08b", "#d9ef8b", "#91cf60", "#1a9850", "#808080", "#d3d3d3"]
        
        for i, rtype in enumerate(top_types):
            type_data = roads[roads["highway"] == rtype]
            linewidth = 4 if rtype in ["motorway", "trunk"] else (2 if rtype in ["primary", "secondary"] else 1)
            type_data.to_crs(PLOT_CRS).plot(
                ax=ax, color=colors[i], linewidth=linewidth, alpha=0.8,
                label=f"{rtype} ({len(type_data):,})"
            )
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Road Network by Hierarchy", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Straßennetz nach Hierarchie*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend
    ax.legend(bbox_to_anchor=(0.78, 0.15), loc="upper left", fontsize=9)
    
    # Add data processing info box
    _add_data_info_box(ax, extent, f"Data Processing:\n• Roads: OSM highway tags\n• Total features: {len(roads):,}\n• Categorized by hierarchy\n• Data: OpenStreetMap (OSM)")
    
    # Add north arrow
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "thematic_roads.png")

def thematic_pt_stops(pt_stops, extent):
    """Thematic map: Public transport stops"""
    if pt_stops is None: return
    
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Plot PT stops by type
    if "highway" in pt_stops.columns:
        stop_types = pt_stops["highway"].value_counts()
        colors = palette()["purples"][:len(stop_types)]
        
        for i, stype in enumerate(stop_types.index):
            type_data = pt_stops[pt_stops["highway"] == stype]
            markersize = 12 if stype == "transport_hub" else 8
            marker = "*" if stype == "transport_hub" else "o"
            type_data.to_crs(PLOT_CRS).plot(
                ax=ax, color=colors[i], markersize=markersize, marker=marker, alpha=0.8,
                label=f"{stype} ({len(type_data):,})"
            )
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Public Transport Stops", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — ÖPNV-Haltestellen*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend
    ax.legend(bbox_to_anchor=(0.78, 0.15), loc="upper left", fontsize=9)
    
    # Add data processing info box
    _add_data_info_box(ax, extent, f"Data Processing:\n• PT stops: OSM highway + railway tags\n• Total features: {len(pt_stops):,}\n• Categorized by type\n• Data: OpenStreetMap (OSM)")
    
    # Add north arrow
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "thematic_pt_stops.png")

def main():
    print("🗺️ Generating comprehensive map collection for Stuttgart...")
    
    layers = load_layers()
    if layers["districts"] is None:
        print("❌ No districts_with_population.geojson found.")
        return
    
    boundary = layers["boundary"] if layers["boundary"] is not None else layers["districts"]
    extent = _extent_from(boundary)
    
    print("✅ Generating thematic maps...")
    
    # Generate thematic maps
    thematic_amenities(layers["amenities"], extent)
    thematic_buildings(layers["buildings"], extent)
    thematic_cycle(layers["cycle"], extent)
    thematic_landuse(layers["landuse"], extent)
    thematic_roads(layers["roads"], extent)
    thematic_pt_stops(layers["pt_stops"], extent)
    
    print("\n🎉 All thematic maps generated successfully!")
    print(f"📁 Check outputs in: {OUT_DIR}")

if __name__ == "__main__":
    main()
