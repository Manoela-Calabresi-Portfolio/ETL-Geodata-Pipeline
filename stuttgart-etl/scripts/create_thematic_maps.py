#!/usr/bin/env python3
"""
Create comprehensive thematic maps for Stuttgart layers with proper north orientation.
Generates individual thematic maps for each layer with basemaps, consistent styling, and correct CRS.

Inputs:
  - data/staging/osm_*.parquet (EPSG:4326)
Outputs (data/maps/):
  - stuttgart_roads_thematic.png
  - stuttgart_buildings_thematic.png
  - stuttgart_landuse_thematic.png
  - stuttgart_cycle_thematic.png
  - stuttgart_pt_stops_thematic.png
  - stuttgart_boundaries_thematic.png
  - stuttgart_amenities_thematic.png
  - stuttgart_overview_thematic.png
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Add src to path for utils
sys.path.insert(0, 'src')

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import box

try:
    import contextily as cx  # for basemaps
    HAS_CONTEXTILY = True
except Exception:  # pragma: no cover
    cx = None  # type: ignore
    HAS_CONTEXTILY = False

try:
    import pyproj
    HAS_PYPROJ = True
except Exception:  # pragma: no cover
    pyproj = None  # type: ignore
    HAS_PYPROJ = False

from etl.utils import ensure_directory

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Simple progress logger for terminal output
def log(message: str) -> None:
    """Print a timestamped progress message to the terminal and flush immediately."""
    try:
        ts = datetime.now().strftime("%H:%M:%S")
    except Exception:
        ts = "--:--:--"
    print(f"[{ts}] {message}", flush=True)


def estimate_zoom_for_extent(extent: Tuple[float, float, float, float]) -> int:
    """Heuristic zoom level for contextily given a projected extent in meters."""
    try:
        width_m = max(1.0, float(extent[2] - extent[0]))
    except Exception:
        return 12
    if width_m > 200_000:
        return 9
    if width_m > 120_000:
        return 10
    if width_m > 70_000:
        return 11
    if width_m > 35_000:
        return 12
    return 13

def _nice_km_step(dx_m: float) -> int:
    """Pick a nice scalebar length (km) for the given map width in meters."""
    try:
        target = float(dx_m) / 4.5  # ~1/4–1/5 of map width
    except Exception:
        return 10
    for km in [1, 2, 5, 10, 20, 25, 50, 100]:
        if km * 1000 >= target:
            return km
    return 100

# Stuttgart bounding box (from config/areas.yaml) in EPSG:4326
STUTTGART_BBOX: Tuple[float, float, float, float] = (9.0, 48.6, 9.4, 48.9)

# Use Web Mercator for strict north-up rendering
PLOT_CRS: str = "EPSG:3857"

# Presentation options
SHOW_AXIS_LABELS: bool = False  # hide Easting/Northing labels to avoid confusion; scalebar provides scale

# Enhanced layer styling configuration
LAYER_STYLES: Dict[str, Dict[str, Any]] = {
    "roads": {
        "color": "#2C3E50", 
        "linewidth": 0.8, 
        "alpha": 0.8,
        "title": "Road Network",
        "description": "Primary, secondary, and local roads"
    },
    "buildings": {
        "facecolor": "#E74C3C", 
        "edgecolor": "#C0392B", 
        "linewidth": 0.1, 
        "alpha": 0.7,
        "title": "Buildings",
        "description": "Residential, commercial, and industrial buildings"
    },
    "landuse": {
        "facecolor": "#27AE60", 
        "edgecolor": "#229954", 
        "linewidth": 0.2, 
        "alpha": 0.6,
        "title": "Land Use",
        "description": "Forests, parks, agricultural areas, and urban zones"
    },
    "cycle": {
        "color": "#F39C12", 
        "linewidth": 1.2, 
        "alpha": 0.9,
        "title": "Cycling Infrastructure",
        "description": "Bike lanes, cycle paths, and cycling routes"
    },
    "pt_stops": {
        "color": "#9B59B6", 
        "markersize": 2.5, 
        "alpha": 0.8,
        "title": "Public Transport",
        "description": "Bus stops, tram stations, and transport hubs"
    },
    "boundaries": {
        "facecolor": "none", 
        "edgecolor": "#34495E", 
        "linewidth": 2.0, 
        "alpha": 0.9,
        "title": "Administrative Boundaries",
        "description": "Municipal and district boundaries"
    },
    "amenities": {
        "color": "#E67E22", 
        "markersize": 3.0, 
        "alpha": 0.8,
        "title": "Amenities & Services",
        "description": "Schools, hospitals, shops, and public facilities"
    },
}


def load_layer_safely(staging_dir: Path, layer_name: str) -> Optional[gpd.GeoDataFrame]:
    """Load layer data safely with error handling."""
    # Prefer refined commuter infrastructure for cycle layer
    if layer_name == "cycle":
        candidates = [
            staging_dir / "osm_cycling_infrastructure_commuter.parquet",
            staging_dir / "osm_cycling_infrastructure.parquet",
            staging_dir / "osm_cycle.parquet",
        ]
        file_path = next((p for p in candidates if p.exists()), candidates[-1])
    else:
        file_path = staging_dir / f"osm_{layer_name}.parquet"
    
    if not file_path.exists():
        log(f"{layer_name}: file not found at {file_path}")
        return None
    
    try:
        gdf = gpd.read_parquet(file_path)
        
        if gdf.empty:
            log(f"{layer_name}: dataset is empty")
            return None
        
        # Ensure CRS is set
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif str(gdf.crs) != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        log(f"{layer_name}: loaded {len(gdf):,} features (CRS={gdf.crs})")
        return gdf
        
    except Exception as e:
        log(f"{layer_name}: error loading layer - {str(e)}")
        return None


def project_and_clip_to_stuttgart(gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Tuple[float, float, float, float]]:
    """Project data to EPSG:25832 and clip to Stuttgart bbox for clean rendering."""
    try:
        log(f"Projecting data to {PLOT_CRS} and clipping to Stuttgart bbox …")
        # Create Stuttgart bbox in EPSG:4326, then project to EPSG:25832
        minx, miny, maxx, maxy = STUTTGART_BBOX
        bbox_poly = box(minx, miny, maxx, maxy)
        bbox_gdf = gpd.GeoDataFrame({"geometry": [bbox_poly]}, crs="EPSG:4326")
        
        # Project both data and bbox to plotting CRS
        gdf_proj = gdf.to_crs(PLOT_CRS)
        bbox_proj = bbox_gdf.to_crs(PLOT_CRS)

        # Coarse pre-filter using a bbox query for speed
        try:
            bminx, bminy, bmaxx, bmaxy = bbox_proj.total_bounds
            cand_idx = list(gdf_proj.sindex.query(box(bminx, bminy, bmaxx, bmaxy)))  # type: ignore[attr-defined]
            if cand_idx:
                gdf_proj = gdf_proj.iloc[cand_idx]
        except Exception:
            pass

        # Precise clip to bbox polygon to avoid artifacts outside the area
        gdf_clipped = gpd.clip(gdf_proj, bbox_proj.geometry.iloc[0])
        
        # Get extent from bbox (not clipped data to ensure consistent extents)
        extent = tuple(bbox_proj.total_bounds)
        
        log("Projection and clipping completed")
        return gdf_clipped, extent  # type: ignore[return-value]
        
    except Exception as e:
        log(f"Projection failed, falling back to original data: {e}")
        return gdf, STUTTGART_BBOX


def calculate_true_north_direction(extent: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Calculate true north direction using geodetic approach."""
    # Force north to be straight up regardless of CRS
    log("Using forced north-up orientation")
    return 0.0, 1.0  # Fallback: north = up


def add_basemap_and_north_arrow(ax: plt.Axes, extent: Tuple[float, float, float, float]) -> None:
    """Add contextily basemap and properly oriented north arrow."""
    
    # Add basemap if contextily is available
    if HAS_CONTEXTILY:
        try:
            cx.add_basemap(
                ax,
                source=cx.providers.CartoDB.Positron,  # Clean, light basemap
                crs=PLOT_CRS,
                zoom=estimate_zoom_for_extent(extent),
                attribution="© CARTO, © OpenStreetMap contributors",
                alpha=0.7
            )
            # Reset extent after basemap
            ax.set_xlim(extent[0], extent[2])
            ax.set_ylim(extent[1], extent[3])
            # Ensure north is up after basemap
            if ax.yaxis_inverted():
                ax.invert_yaxis()
        except Exception as e:
            log(f"Basemap rendering failed: {e}")
    
    # Add north arrow with calculated true north direction (drawn in DATA coordinates)
    try:
        dx_norm, dy_norm = calculate_true_north_direction(extent)
        # Start in lower-right corner in data space
        width = extent[2] - extent[0]
        height = extent[3] - extent[1]
        # lower-right corner, well inside the margin
        start_x = extent[0] + width * 0.88
        start_y = extent[1] + height * 0.08
        arrow_length_m = max(width, height) * 0.06

        ax.annotate(
            "N",
            xy=(start_x, start_y),
            xytext=(start_x + dx_norm * arrow_length_m, start_y + dy_norm * arrow_length_m),
            xycoords="data",
            textcoords="data",
            arrowprops=dict(
                arrowstyle="-|>", 
                color="black", 
                lw=2,
                shrinkA=0,
                shrinkB=0
            ),
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color="black",
            bbox=dict(boxstyle="circle,pad=0.3", facecolor="white", edgecolor="black", alpha=0.9)
        )
        
    except Exception as e:
        log(f"North arrow draw failed: {e}")


def add_scale_bar(ax: plt.Axes, extent: Tuple[float, float, float, float]) -> None:
    """Add a two-segment scale bar at bottom-left with auto length (0–½–1×)."""
    try:
        dx = extent[2] - extent[0]
        dy = extent[3] - extent[1]
        km = _nice_km_step(dx)
        length = km * 1000.0

        # Position: bottom-left, away from edges
        x0 = extent[0] + dx * 0.05
        y0 = extent[1] + dy * 0.08

        # Visual height of the bar
        bar_h = max(2.0, length * 0.015)

        # Draw two segments (black then white)
        half = length / 2.0
        rect1 = patches.Rectangle((x0, y0 - bar_h / 2.0), half, bar_h, facecolor="black", edgecolor="black")
        rect2 = patches.Rectangle((x0 + half, y0 - bar_h / 2.0), half, bar_h, facecolor="white", edgecolor="black")
        ax.add_patch(rect1); ax.add_patch(rect2)

        # Labels 0 | half | full
        ax.text(x0, y0 + bar_h * 0.9, "0", ha="center", va="bottom", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.7))
        ax.text(x0 + half, y0 + bar_h * 0.9, f"{km//2} km", ha="center", va="bottom", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.7))
        ax.text(x0 + length, y0 + bar_h * 0.9, f"{km} km", ha="center", va="bottom", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.7))

    except Exception as e:
        log(f"Scale bar draw failed: {e}")


def create_thematic_map(
    layer_name: str, 
    gdf: gpd.GeoDataFrame, 
    output_dir: Path,
    add_basemap: bool = True
) -> Optional[Path]:
    """Create a thematic map for a single layer."""
    
    style = LAYER_STYLES.get(layer_name, {"color": "blue", "alpha": 0.7})
    log(f"Rendering thematic map for layer '{layer_name}' …")
    
    # Project and clip data
    gdf_plot, extent = project_and_clip_to_stuttgart(gdf)
    
    if gdf_plot.empty:
        log(f"{layer_name}: no data after clipping – skipping")
        return None
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    
    # Set extent with explicit north-up orientation
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    # Ensure north is up (Y-axis NOT inverted, so higher Y values appear at top)
    if ax.yaxis_inverted():
        ax.invert_yaxis()
    
    # Add basemap first (background)
    if add_basemap:
        add_basemap_and_north_arrow(ax, extent)
    
    # Categorize and plot with legend
    def build_category_series(layer: str, gdf_in: gpd.GeoDataFrame) -> pd.Series:
        """Return a clean categorical Series per layer with sane buckets."""
        def _norm(col: str) -> pd.Series:
            if col in gdf_in.columns:
                return gdf_in[col].astype("string").str.lower()
            return pd.Series("", index=gdf_in.index, dtype="string")

        if layer == "roads":
            hw = _norm("highway")
            buckets = {
                "motorway": ["motorway", "motorway_link"],
                "primary": ["primary", "primary_link"],
                "secondary": ["secondary", "secondary_link"],
                "tertiary": ["tertiary", "tertiary_link"],
                "residential": ["residential", "living_street", "unclassified"],
                "service": ["service", "track"],
                "path": ["path", "footway", "bridleway", "steps", "pedestrian", "cycleway"],
            }
            out = pd.Series("other", index=hw.index, dtype="string")
            for k, vals in buckets.items():
                out = out.mask(hw.isin(vals), k)
            return out

        if layer == "buildings":
            b = _norm("building")
            buckets = {
                "residential": ["house", "residential", "apartments", "terrace", "detached", "semidetached_house"],
                "commercial": ["retail", "commercial", "supermarket", "office"],
                "industrial": ["industrial", "warehouse", "factory"],
                "public": ["school", "hospital", "university", "public", "civic", "government"],
                "transport": ["train_station", "transportation", "station"],
            }
            out = pd.Series("other", index=b.index, dtype="string")
            for k, vals in buckets.items():
                out = out.mask(b.isin(vals), k)
            return out

        if layer == "landuse":
            land = _norm("landuse")
            nat = _norm("natural")
            out = pd.Series("other", index=gdf_in.index, dtype="string")
            green = ["forest", "meadow", "grass", "orchard", "vineyard", "recreation_ground", "park", "cemetery"]
            urban = ["residential", "commercial", "retail", "industrial"]
            agri = ["farmland", "farm", "allotments"]
            water = ["water", "wetland"]
            out = out.mask(land.isin(urban), "urban")
            out = out.mask(land.isin(agri), "agricultural")
            out = out.mask(land.isin(green) | nat.isin(["wood", "scrub", "grassland"]), "green")
            out = out.mask(nat.isin(water) | land.isin(water), "water")
            return out

        if layer == "cycle":
            hw = _norm("highway")
            cw = _norm("cycleway")
            rte = _norm("route")
            out = pd.Series("other", index=gdf_in.index, dtype="string")
            out = out.mask(hw.eq("cycleway"), "separated_cycleway")
            out = out.mask(hw.eq("path") & (_norm("bicycle").eq("designated")), "designated_path")
            out = out.mask(cw.isin(["track", "separate", "segregated"]), "protected_track")
            out = out.mask(cw.isin(["lane", "opposite", "opposite_lane"]), "painted_lane")
            out = out.mask(rte.eq("bicycle"), "signed_route")
            out = out.mask(cw.eq("no"), "other")
            return out

        if layer == "pt_stops":
            for c in ["railway", "public_transport", "highway", "amenity"]:
                if c in gdf_in.columns:
                    s = _norm(c)
                    groups = {
                        "rail_station": ["station", "halt", "tram_stop", "subway_entrance"],
                        "bus_stop": ["bus_stop"],
                        "platform": ["platform"],
                    }
                    out = pd.Series("other", index=s.index, dtype="string")
                    for k, vals in groups.items():
                        out = out.mask(s.isin(vals), k)
                    return out
            return pd.Series("other", index=gdf_in.index, dtype="string")

        if layer == "amenities":
            a = _norm("amenity")
            groups = {
                "education": ["school", "university", "college", "kindergarten"],
                "health": ["hospital", "clinic", "doctors"],
                "worship": ["place_of_worship"],
                "retail": ["marketplace"],
            }
            out = pd.Series("other", index=a.index, dtype="string")
            for k, vals in groups.items():
                out = out.mask(a.isin(vals), k)
            return out

        if layer == "boundaries":
            lvl = _norm("admin_level")
            out = pd.Series("admin", index=lvl.index, dtype="string")
            return out

        return pd.Series("other", index=gdf_in.index, dtype="string")

    cats = build_category_series(layer_name, gdf_plot)
    # Limit to top N categories + Other
    value_counts = cats.value_counts(dropna=False)
    top_cats = list(value_counts.head(8).index)
    cats = cats.where(cats.isin(top_cats), other="other")
    # Draw 'other' first so specific categories are visible on top
    ordered_cats = ([] if "other" not in top_cats else ["other"]) + [c for c in top_cats if c != "other"]

    # Prepare color palette
    cmap = plt.get_cmap("tab20")
    color_map: Dict[str, str] = {cat: cmap(i / max(1, len(ordered_cats)-1)) for i, cat in enumerate(ordered_cats)}

    # For boundaries, draw outlines only to avoid diagonal fills
    if layer_name == "boundaries":
        gdf_plot = gdf_plot.copy()
        gdf_plot["geometry"] = gdf_plot.geometry.boundary

    # Plot each category
    handles = []
    geom_types = list(gdf_plot.geometry.geom_type.unique())
    for cat in ordered_cats:
        mask = cats == cat
        if not bool(mask.any()):
            continue
        color = color_map.get(cat, "#777777")
        # De-emphasize 'other'
        line_alpha = 0.35 if cat == "other" else style.get("alpha", 0.8)
        line_width = 0.6 if cat == "other" else style.get("linewidth", 1.0)
        z = 4 if cat == "other" else 6
        if any(gt in geom_types for gt in ["Point", "MultiPoint"]):
            gdf_plot[mask].plot(ax=ax, color=color, markersize=style.get("markersize", 2.0), alpha=line_alpha, zorder=z)
            handles.append(plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, markersize=8, label=f"{cat} ({int(mask.sum()):,})"))
        elif any(gt in geom_types for gt in ["LineString", "MultiLineString"]):
            gdf_plot[mask].plot(ax=ax, color=color, linewidth=line_width, alpha=line_alpha, zorder=z)
            handles.append(plt.Line2D([0], [0], color=color, linewidth=3, label=f"{cat} ({int(mask.sum()):,})"))
        else:
            gdf_plot[mask].plot(ax=ax, facecolor=color, edgecolor=style.get("edgecolor", "#333333"), linewidth=style.get("linewidth", 0.2), alpha=line_alpha, zorder=z)
            handles.append(patches.Patch(facecolor=color, edgecolor=style.get("edgecolor", "#333333"), label=f"{cat} ({int(mask.sum()):,})"))

    if handles:
        ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9, title="Categories", title_fontsize=10)
    
    # Styling
    title = style.get("title", layer_name.title())
    description = style.get("description", "")
    
    ax.set_title(
        f"Stuttgart - {title}\n{description}", 
        fontsize=16, 
        fontweight="bold", 
        pad=20
    )
    if SHOW_AXIS_LABELS:
        ax.set_xlabel(f"Easting (m) — {PLOT_CRS}", fontsize=12)
        ax.set_ylabel("Northing (m)", fontsize=12)
    else:
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.set_aspect("equal")
    
    # Add grid (subtle)
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    
    # Add scale bar
    add_scale_bar(ax, extent)
    
    # Add feature count and timestamp
    info_text = f"Features: {len(gdf_plot):,}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ax.text(
        0.02, 0.98, 
        info_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor="gray")
    )
    
    # Save map
    output_file = output_dir / f"stuttgart_thematic_{layer_name}.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    log(f"Saved thematic map: {output_file}")
    return output_file


def create_overview_thematic_map(layers: Dict[str, gpd.GeoDataFrame], output_dir: Path) -> Optional[Path]:
    """Create overview map with all layers."""
    log("Creating overview thematic map …")
    
    fig, ax = plt.subplots(1, 1, figsize=(18, 14))
    
    # Get extent from Stuttgart bbox
    minx, miny, maxx, maxy = STUTTGART_BBOX
    bbox_poly = box(minx, miny, maxx, maxy)
    bbox_gdf = gpd.GeoDataFrame({"geometry": [bbox_poly]}, crs="EPSG:4326").to_crs(PLOT_CRS)
    extent = tuple(bbox_gdf.total_bounds)
    
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    # Ensure north is up (Y-axis NOT inverted, so higher Y values appear at top)
    if ax.yaxis_inverted():
        ax.invert_yaxis()
    
    # Add basemap
    add_basemap_and_north_arrow(ax, extent)
    
    # Layer drawing order (background to foreground)
    layer_order = ["boundaries", "landuse", "buildings", "roads", "cycle", "amenities", "pt_stops"]
    
    legend_elements = []
    
    for layer_name in layer_order:
        if layer_name not in layers or layers[layer_name] is None:
            continue
            
        gdf = layers[layer_name]
        if gdf.empty:
            continue
        
        # Project and clip
        gdf_plot, _ = project_and_clip_to_stuttgart(gdf)
        if gdf_plot.empty:
            continue
        
        style = LAYER_STYLES.get(layer_name, {"color": "blue", "alpha": 0.7})
        geom_types = list(gdf_plot.geometry.geom_type.unique())
        
        # Plot layer
        if any(gt in geom_types for gt in ["Point", "MultiPoint"]):
            gdf_plot.plot(
                ax=ax,
                color=style.get("color", "blue"),
                markersize=style.get("markersize", 1.5),
                alpha=style.get("alpha", 0.8),
                zorder=5 + layer_order.index(layer_name)
            )
            legend_elements.append(
                plt.Line2D(
                    [0], [0], marker="o", color="w",
                    markerfacecolor=style.get("color", "blue"),
                    markersize=8,
                    label=f"{style.get('title', layer_name.title())} ({len(gdf_plot):,})"
                )
            )
        elif any(gt in geom_types for gt in ["LineString", "MultiLineString"]):
            gdf_plot.plot(
                ax=ax,
                color=style.get("color", "blue"),
                linewidth=style.get("linewidth", 0.8),
                alpha=style.get("alpha", 0.8),
                zorder=5 + layer_order.index(layer_name)
            )
            legend_elements.append(
                plt.Line2D(
                    [0], [0], color=style.get("color", "blue"),
                    linewidth=3,
                    label=f"{style.get('title', layer_name.title())} ({len(gdf_plot):,})"
                )
            )
        else:
            gdf_plot.plot(
                ax=ax,
                facecolor=style.get("facecolor", "lightblue"),
                edgecolor=style.get("edgecolor", "blue"),
                linewidth=style.get("linewidth", 0.2),
                alpha=style.get("alpha", 0.7),
                zorder=5 + layer_order.index(layer_name)
            )
            legend_elements.append(
                patches.Patch(
                    facecolor=style.get("facecolor", "lightblue"),
                    edgecolor=style.get("edgecolor", "blue"),
                    label=f"{style.get('title', layer_name.title())} ({len(gdf_plot):,})"
                )
            )
    
    # Styling
    ax.set_title("Stuttgart - Comprehensive Overview Map", fontsize=18, fontweight="bold", pad=25)
    if SHOW_AXIS_LABELS:
        ax.set_xlabel(f"Easting (m) — {PLOT_CRS}", fontsize=12)
        ax.set_ylabel("Northing (m)", fontsize=12)
    else:
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
    
    # Add legend
    if legend_elements:
        ax.legend(
            handles=legend_elements, 
            loc="upper left", 
            bbox_to_anchor=(1.02, 1), 
            fontsize=10,
            title="Layers",
            title_fontsize=12,
            frameon=True,
            fancybox=True,
            shadow=True
        )
    
    # Add scale bar
    add_scale_bar(ax, extent)
    
    # Add summary info
    total_features = sum(len(gdf) for gdf in layers.values() if gdf is not None and not gdf.empty)
    summary_text = f"Total Features: {total_features:,}\nLayers: {len([l for l in layers.values() if l is not None and not l.empty])}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ax.text(
        0.02, 0.02,
        summary_text,
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.95, edgecolor="gray")
    )
    
    # Save overview map
    output_file = output_dir / "stuttgart_thematic_overview.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    log(f"Saved overview map: {output_file}")
    return output_file


def main() -> None:
    """Main function to generate all thematic maps."""
    log("STUTTGART THEMATIC MAPS GENERATOR")
    log("=" * 50)
    log(f"CRS: {PLOT_CRS}")
    log(f"North orientation: {'calculated via geodetic bearings' if HAS_PYPROJ else 'simple north=up'}")
    log(f"Basemaps: {'enabled' if HAS_CONTEXTILY else 'disabled (install contextily)'}")
    
    staging_dir = Path("data/staging")
    output_dir = Path("data/maps")
    ensure_directory(output_dir)
    
    # Available layers
    layer_names = ["roads", "buildings", "landuse", "cycle", "pt_stops", "boundaries", "amenities"]
    
    log(f"Loading layers from: {staging_dir}")
    log(f"Saving maps to: {output_dir}")
    
    # Load all layers
    layers: Dict[str, Optional[gpd.GeoDataFrame]] = {}
    
    for layer_name in layer_names:
        log(f"Loading layer: {layer_name} …")
        layers[layer_name] = load_layer_safely(staging_dir, layer_name)
    
    # Filter valid layers
    valid_layers = {name: gdf for name, gdf in layers.items() if gdf is not None and not gdf.empty}
    
    if not valid_layers:
        log("No valid layers found – aborting")
        return
    
    log(f"Found {len(valid_layers)} valid layers")
    
    # Create individual thematic maps
    log("Creating individual thematic maps …")
    created_maps = []
    
    for layer_name, gdf in valid_layers.items():
        log(f"Creating thematic map for: {layer_name}")
        output_file = create_thematic_map(layer_name, gdf, output_dir, add_basemap=True)
        if output_file:
            created_maps.append(output_file)
            log(f"Saved: {output_file}")
    
    # Create overview map
    overview_file = create_overview_thematic_map(valid_layers, output_dir)
    if overview_file:
        created_maps.append(overview_file)
        log(f"Saved: {overview_file}")
    
    # Summary
    log("SUMMARY")
    log(f"Created {len(created_maps)} thematic maps")
    log(f"Output directory: {output_dir}")
    log("All maps use proper north orientation (north-up)")
    
    if created_maps:
        log("Generated files:")
        for map_file in created_maps:
            log(f" - {map_file.name}")


if __name__ == "__main__":
    main()