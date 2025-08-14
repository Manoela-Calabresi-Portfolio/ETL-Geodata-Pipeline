#!/usr/bin/env python3
"""
Create simple maps of Stuttgart green areas (forests, meadows, grasslands, etc.)
derived from the landuse/natural layer in staging.

Inputs:
  - data/staging/osm_landuse.parquet (EPSG:4326)
Outputs (data/maps/):
  - stuttgart_green_areas_overview.png
  - stuttgart_green_areas_by_category.png
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple

# Add src to path for utils
sys.path.insert(0, 'src')

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
import numpy as np

from etl.utils import ensure_directory


PLOT_CRS: str = "EPSG:25832"  # ETRS89 / UTM 32N

# Heuristics for green-ish classes
GREEN_LANDUSE = {
    "forest",
    "meadow",
    "grass",
    "recreation_ground",
    "allotments",
    "orchard",
    "vineyard",
    "cemetery",
    "village_green",
    "greenfield",
}
GREEN_NATURAL = {
    "wood",
    "grassland",
    "scrub",
    "heath",
    "wetland",
}

PALETTE: Dict[str, str] = {
    "forest": "#1b5e20",
    "wood": "#2e7d32",
    "meadow": "#66bb6a",
    "grass": "#81c784",
    "grassland": "#9ccc65",
    "scrub": "#a5d6a7",
    "heath": "#b2dfdb",
    "recreation_ground": "#4caf50",
    "allotments": "#7cb342",
    "orchard": "#43a047",
    "vineyard": "#558b2f",
    "cemetery": "#8bc34a",
    "village_green": "#9ccc65",
    "wetland": "#a7ffeb",
}


def load_green_polygons(staging: Path) -> gpd.GeoDataFrame:
    landuse_path = staging / "osm_landuse.parquet"
    if not landuse_path.exists():
        raise FileNotFoundError(f"Missing {landuse_path}. Run extraction first.")

    gdf = gpd.read_parquet(landuse_path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    # Keep only polygons
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf[gdf.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()

    # Build a unified 'green_class' column from landuse/natural (vectorized, NA-safe)
    # Normalize to lowercase strings; fill missing with empty string to avoid NA truthiness
    gdf["landuse_norm"] = gdf["landuse"].astype("string").str.lower().fillna("")
    gdf["natural_norm"] = gdf["natural"].astype("string").str.lower().fillna("")

    gdf["green_class"] = np.where(
        gdf["landuse_norm"].isin(list(GREEN_LANDUSE)),
        gdf["landuse_norm"],
        None,
    )
    gdf["green_class"] = np.where(
        gdf["green_class"].isna() & gdf["natural_norm"].isin(list(GREEN_NATURAL)),
        gdf["natural_norm"],
        gdf["green_class"],
    )

    gdf = gdf[gdf["green_class"].notna()].copy()
    gdf = gdf.drop(columns=["landuse_norm", "natural_norm"], errors="ignore")
    return gdf


def _project_and_extent(gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Tuple[float, float, float, float]]:
    gdfp = gdf.to_crs(PLOT_CRS)
    extent = tuple(gdfp.total_bounds)
    return gdfp, extent  # type: ignore[return-value]


def plot_overview(gdf: gpd.GeoDataFrame, out: Path) -> None:
    gdfp, extent = _project_and_extent(gdf)
    fig, ax = plt.subplots(1, 1, figsize=(14, 11))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    gdfp.plot(ax=ax, facecolor="#66bb6a", edgecolor="#2e7d32", linewidth=0.2, alpha=0.7)
    ax.set_title("Stuttgart – Green Areas (Overview)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Easting (m) – EPSG:25832")
    ax.set_ylabel("Northing (m)")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()


def plot_by_category(gdf: gpd.GeoDataFrame, out: Path) -> None:
    gdfp, extent = _project_and_extent(gdf)
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])

    # Plot heavier classes last
    for cls in sorted(gdfp["green_class"].unique()):
        color = PALETTE.get(cls, "#66bb6a")
        gdfp[gdfp["green_class"] == cls].plot(
            ax=ax, facecolor=color, edgecolor="#2e7d32", linewidth=0.15, alpha=0.8, label=cls
        )

    ax.set_title("Stuttgart – Green Areas by Category", fontsize=16, fontweight="bold")
    ax.set_xlabel("Easting (m) – EPSG:25832")
    ax.set_ylabel("Northing (m)")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=9)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()


def main() -> None:
    staging = Path("data/staging")
    maps_dir = Path("data/maps")
    ensure_directory(maps_dir)

    green = load_green_polygons(staging)
    if green.empty:
        print("No green polygons found in landuse/natural.")
        return

    plot_overview(green, maps_dir / "stuttgart_green_areas_overview.png")
    plot_by_category(green, maps_dir / "stuttgart_green_areas_by_category.png")
    print("Saved maps:")
    print(" -", maps_dir / "stuttgart_green_areas_overview.png")
    print(" -", maps_dir / "stuttgart_green_areas_by_category.png")


if __name__ == "__main__":
    main()


