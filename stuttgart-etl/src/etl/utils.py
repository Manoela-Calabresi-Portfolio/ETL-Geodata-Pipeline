from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import yaml
import geopandas as gpd
import pandas as pd


def ensure_directory(path: Path) -> None:
	path.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> Dict[str, Any]:
	with open(path, "r", encoding="utf-8") as f:
		return yaml.safe_load(f) or {}


def parse_bbox(bbox: Optional[str], fallback_geometry: Optional[gpd.GeoSeries] = None) -> Optional[Tuple[float, float, float, float]]:
	if bbox:
		parts = [float(x.strip()) for x in bbox.split(",")]
		if len(parts) != 4:
			raise ValueError("bbox must be 'minx,miny,maxx,maxy'")
		minx, miny, maxx, maxy = parts
		if not (minx < maxx and miny < maxy):
			raise ValueError("Invalid bbox: ensure minx < maxx and miny < maxy")
		return (minx, miny, maxx, maxy)
	if fallback_geometry is not None and not fallback_geometry.empty:
		minx, miny, maxx, maxy = fallback_geometry.iloc[0].bounds
		return (float(minx), float(miny), float(maxx), float(maxy))
	return None


def compute_length_m(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
	if gdf.empty:
		gdf["length_m"] = pd.Series(dtype=float)
		return gdf
	lines = gdf.to_crs("EPSG:25832")
	gdf["length_m"] = lines.geometry.length
	return gdf


def compute_area_m2(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
	if gdf.empty:
		gdf["area_m2"] = pd.Series(dtype=float)
		return gdf
	polys = gdf.to_crs("EPSG:25832")
	gdf["area_m2"] = polys.geometry.area
	return gdf
