#!/usr/bin/env python3
"""
Refined cycle data filtering with separate infrastructure and route layers.

Creates two distinct layers from existing staged data (fast, no re-download):
  1) Cycling Infrastructure (physical facilities only)
  2) Cycling Routes (network routes: icn/ncn/rcn/lcn)

Also generates a north-up map overlaying routes and infrastructure.

Inputs  (relative to repo root 'stuttgart-etl'):
  - data/staging/osm_cycle.parquet (EPSG:4326)

Outputs:
  - data/staging/osm_cycling_infrastructure.parquet
  - data/staging/osm_cycling_routes.parquet
  - data/maps/stuttgart_cycling_infrastructure_and_routes.png
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Tuple

import matplotlib

# Non-interactive backend for headless runs
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import box, LineString
import requests

# Add src to PYTHONPATH for utils
sys.path.insert(0, "src")
from etl.utils import ensure_directory  # type: ignore
import osmnx as ox

# Quiet noisy warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


# Global map settings
STUTTGART_BBOX: Tuple[float, float, float, float] = (9.0, 48.6, 9.4, 48.9)
PLOT_CRS: str = "EPSG:25832"  # North-up metric CRS for Baden-Württemberg


def analyze_current_data(gdf: gpd.GeoDataFrame) -> None:
    """Print a compact overview of relevant attributes before filtering."""
    print(f"\nOriginal cycle data: {len(gdf):,} features")
    for col in ["highway", "cycleway", "bicycle", "route", "network", "surface"]:
        if col in gdf.columns:
            vc = gdf[col].value_counts(dropna=True).head(10)
            if not vc.empty:
                print(f"  - {col}: {', '.join([f'{k}={int(v)}' for k, v in vc.items()])}")


def filter_cycling_infrastructure(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only physical cycling facilities.

    Rules:
      - Include dedicated cycleways: highway=cycleway
      - Include real on-road facilities: cycleway in {lane, track, opposite, opposite_track, separate}
      - Include designated paths/footways for bikes
      - Exclude explicit non-infrastructure: cycleway=no
      - Exclude ambiguous shared lanes: cycleway=shared_lane
    """
    mask = pd.Series(False, index=gdf.index)

    # Dedicated cycleways
    if "highway" in gdf.columns:
        mask |= gdf["highway"] == "cycleway"

    # Proper on-road cycling infrastructure
    if "cycleway" in gdf.columns:
        good_infra = gdf["cycleway"].isin(
            ["lane", "track", "opposite", "opposite_track", "separate"]
        )
        mask |= good_infra

    # Designated paths / footways
    if "highway" in gdf.columns and "bicycle" in gdf.columns:
        designated = gdf["highway"].isin(["path", "footway"]) & (
            gdf["bicycle"] == "designated"
        )
        mask |= designated

    # Exclusions
    if "cycleway" in gdf.columns:
        mask &= ~(gdf["cycleway"] == "no")
        mask &= ~(gdf["cycleway"] == "shared_lane")

    filtered = gdf[mask].copy()
    # Drop duplicates by OSM id where present
    if "osmid" in filtered.columns:
        filtered = filtered.drop_duplicates(subset=["osmid"], keep="first")
    return filtered


def filter_cycling_routes(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only official bicycle route networks (icn/ncn/rcn/lcn)."""
    if "route" not in gdf.columns or "network" not in gdf.columns:
        return gpd.GeoDataFrame(geometry=[], crs=gdf.crs)
    mask = (gdf["route"] == "bicycle") & gdf["network"].isin(
        ["icn", "ncn", "rcn", "lcn"]
    )
    routes = gdf[mask].copy()
    if "osmid" in routes.columns:
        routes = routes.drop_duplicates(subset=["osmid"], keep="first")
    return routes


def categorize_surface_quality(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add a 'surface_category' column for commuter suitability analysis."""
    if "surface" not in gdf.columns:
        gdf["surface_category"] = "unknown"
        return gdf

    high_quality = ["asphalt", "concrete", "paved", "paving_stones"]
    medium_quality = ["compacted", "fine_gravel", "paving_stones:30"]
    low_quality = ["gravel", "unpaved", "dirt", "grass", "sand", "mud"]

    conditions = [
        gdf["surface"].isin(high_quality),
        gdf["surface"].isin(medium_quality),
        gdf["surface"].isin(low_quality),
    ]
    choices = ["high_quality", "medium_quality", "low_quality"]
    gdf["surface_category"] = np.select(conditions, choices, default="unknown")
    return gdf


def create_dual_layer_map(
    infra_gdf: gpd.GeoDataFrame,
    routes_gdf: gpd.GeoDataFrame,
    output_dir: Path,
    *,
    filename: str = "stuttgart_cycling_infrastructure_and_routes.png",
    title_suffix: str = "Infrastructure & Routes",
) -> None:
    """Render a north-up map with infrastructure (foreground) and routes (background)."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))

    # Project bbox and set extent (guarantees north-up in projected CRS)
    bbox_geom = gpd.GeoSeries([box(*STUTTGART_BBOX)], crs="EPSG:4326")
    bbox_gdf = gpd.GeoDataFrame(geometry=bbox_geom).to_crs(PLOT_CRS)
    extent = bbox_gdf.total_bounds
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])

    # Plot routes first (background)
    if routes_gdf is not None and not routes_gdf.empty:
        routes_proj = routes_gdf.to_crs(PLOT_CRS)
        routes_proj = gpd.clip(routes_proj, bbox_gdf.geometry.iloc[0])
        routes_proj.plot(
            ax=ax,
            color="lightblue",
            linewidth=1.5,
            alpha=0.6,
            label=f"Routes ({len(routes_gdf):,})",
        )

    # Plot infrastructure on top (foreground)
    if infra_gdf is not None and not infra_gdf.empty:
        infra_proj = infra_gdf.to_crs(PLOT_CRS)
        infra_proj = gpd.clip(infra_proj, bbox_gdf.geometry.iloc[0])
        # If surface_category exists, color by it
        if "surface_category" in infra_proj.columns:
            color_map = {
                "high_quality": "#2E8B57",   # sea green
                "medium_quality": "#DAA520", # goldenrod
                "low_quality": "#A0522D",    # sienna
                "unknown": "#808080",        # gray
            }
            for cat, color in color_map.items():
                sub = infra_proj[infra_proj["surface_category"] == cat]
                if not sub.empty:
                    sub.plot(
                        ax=ax,
                        color=color,
                        linewidth=1.2,
                        alpha=0.9,
                        label=f"Infra {cat.replace('_',' ')} ({len(sub):,})",
                    )
        else:
            infra_proj.plot(
                ax=ax,
                color="#FF6B35",
                linewidth=1.2,
                alpha=0.9,
                label=f"Infrastructure ({len(infra_gdf):,})",
            )

    # Styling and north-up cues
    ax.set_title(
        (
            f"Stuttgart - Cycling {title_suffix}\n"
            f"Infrastructure: {len(infra_gdf):,} | Routes: {len(routes_gdf):,}"
        ),
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Easting (m) — EPSG:25832", fontsize=12)
    ax.set_ylabel("Northing (m)", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal")
    ax.legend(loc="upper right")

    # North arrow
    ax.annotate(
        "N",
        xy=(0.95, 0.95),
        xytext=(0.95, 0.90),
        xycoords="axes fraction",
        ha="center",
        va="center",
        arrowprops=dict(arrowstyle="->", lw=2, color="black"),
        fontsize=14,
        fontweight="bold",
    )

    ensure_directory(output_dir)
    out_path = output_dir / filename
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"   Saved map -> {out_path}")


def fetch_bicycle_routes_overpass() -> gpd.GeoDataFrame:
    """Fetch official bicycle route networks via Overpass for the Stuttgart bbox.

    Returns GeoDataFrame with EPSG:4326.
    """
    # Build Overpass query for relations route=bicycle with network in icn/ncn/rcn/lcn
    minx, miny, maxx, maxy = STUTTGART_BBOX
    bbox_str = f"{miny},{minx},{maxy},{maxx}"  # south,west,north,east

    query = (
        "[out:json][timeout:120];\n"
        "(\n"
        f"  relation[\"type\"=\"route\"][\"route\"=\"bicycle\"][\"network\"~\"^(icn|ncn|rcn|lcn)$\"]({bbox_str});\n"
        ");\n"
        "(._;>;);\n"
        "out body;\n"
    )

    try:
        resp = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, timeout=180)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"Overpass fetch failed: {exc}")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # Convert Overpass JSON to GeoDataFrame (ways only)
    elements = data.get("elements", [])
    nodes = {el["id"]: (el.get("lon"), el.get("lat")) for el in elements if el.get("type") == "node"}
    ways = [el for el in elements if el.get("type") == "way"]

    records = []
    for way in ways:
        nds = way.get("nodes", [])
        coords = [nodes[nid] for nid in nds if nid in nodes]
        if len(coords) >= 2:
            geom = LineString(coords)
            tags = way.get("tags", {})
            records.append({
                "osmid": way.get("id"),
                "name": tags.get("name"),
                "route": tags.get("route"),
                "network": tags.get("network"),
                "ref": tags.get("ref"),
                "operator": tags.get("operator"),
                "geometry": geom,
            })

    if not records:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
    return gdf


def filter_commuter_infrastructure(gdf: gpd.GeoDataFrame, min_width_m: float = 1.5) -> gpd.GeoDataFrame:
    """Return commuter-suitable infrastructure (high-quality surfaces, width >= threshold when available)."""
    # Surface filter: keep only high-quality surfaces (unknown allowed)
    if "surface" in gdf.columns:
        commuter_surfaces = ["asphalt", "concrete", "paved", "paving_stones"]
        surface_mask = gdf["surface"].isin(commuter_surfaces) | gdf["surface"].isna()
    else:
        surface_mask = pd.Series(True, index=gdf.index)

    # Width filter when present
    if "width" in gdf.columns:
        width_num = pd.to_numeric(gdf["width"], errors="coerce")
        width_mask = (width_num >= float(min_width_m)) | width_num.isna()
    else:
        width_mask = pd.Series(True, index=gdf.index)

    commuter = gdf[surface_mask & width_mask].copy()
    return commuter


def main() -> bool:
    print("Refining cycle layers (infrastructure vs routes)...")
    staging_dir = Path("data/staging")
    maps_dir = Path("data/maps")
    ensure_directory(staging_dir)
    ensure_directory(maps_dir)

    src_file = staging_dir / "osm_cycle.parquet"
    if not src_file.exists():
        print(f"❌ Source not found: {src_file}")
        return False

    # Load (expect EPSG:4326)
    gdf = gpd.read_parquet(src_file)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    analyze_current_data(gdf)

    # Split into two layers (infrastructure from existing data)
    infra = filter_cycling_infrastructure(gdf)
    # Fetch official bicycle routes (Overpass) as requested
    print("\nFetching official bicycle route networks (icn/ncn/rcn/lcn) via Overpass...")
    routes_overpass = fetch_bicycle_routes_overpass()
    # If staged data already had routes, union them (prefer Overpass result)
    staged_routes = filter_cycling_routes(gdf)
    if routes_overpass is not None and not routes_overpass.empty:
        routes = routes_overpass
    else:
        routes = staged_routes

    # Add surface quality categories for infrastructure
    infra = categorize_surface_quality(infra)

    # Build commuter-friendly subset (high-quality surfaces, width >= 1.5m)
    commuter_infra = filter_commuter_infrastructure(infra, min_width_m=1.5)
    commuter_infra = categorize_surface_quality(commuter_infra)

    # Save outputs
    infra_out = staging_dir / "osm_cycling_infrastructure.parquet"
    routes_out = staging_dir / "osm_cycling_routes.parquet"
    commuter_out = staging_dir / "osm_cycling_infrastructure_commuter.parquet"
    infra.to_parquet(infra_out)
    routes.to_parquet(routes_out)
    commuter_infra.to_parquet(commuter_out)
    print(
        f"\nSaved:\n  - {infra_out}  ({len(infra):,} features)\n  - {routes_out} ({len(routes):,} features)\n  - {commuter_out} ({len(commuter_infra):,} features)"
    )

    # Render maps (north-up)
    print("\nRendering north-up map (combined)...")
    create_dual_layer_map(
        commuter_infra,
        routes,
        maps_dir,
        filename="stuttgart_cycling_infrastructure_and_routes.png",
        title_suffix="Infrastructure (commuter) & Routes",
    )

    print("Rendering north-up map (commuter-only)...")
    create_dual_layer_map(
        commuter_infra,
        gpd.GeoDataFrame(geometry=[], crs=commuter_infra.crs),
        maps_dir,
        filename="stuttgart_cycling_commuter_only.png",
        title_suffix="Infrastructure (commuter only)",
    )

    # Short summary
    print(
        f"\nSummary: Infra {len(infra):,} | Commuter {len(commuter_infra):,} | Routes {len(routes):,} | Source {len(gdf):,}"
    )
    return True


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except Exception as exc:  # pragma: no cover
        print(f"\nCritical error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


