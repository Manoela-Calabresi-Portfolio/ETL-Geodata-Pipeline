from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import yaml
import geopandas as gpd
import pandas as pd
from shapely.geometry.base import BaseGeometry
try:
	from shapely.validation import make_valid  # Shapely 2.x
except Exception:  # pragma: no cover
	make_valid = None  # type: ignore


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
AQQQ

def _make_geometries_valid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
	"""Return a copy with valid geometries (attempt repair if invalid)."""
	if gdf.empty:
		return gdf
	if make_valid is not None:
		gdf = gdf.copy()
		gdf["geometry"] = gdf.geometry.apply(lambda geom: make_valid(geom) if isinstance(geom, BaseGeometry) else geom)
		return gdf
	# Fallback: buffer(0) trick
	gdf = gdf.copy()
	gdf["geometry"] = gdf.geometry.buffer(0)
	return gdf


def _drop_duplicate_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
	"""Drop exact duplicate geometries using WKB fingerprint, prefer keeping first occurrence."""
	if gdf.empty:
		return gdf
	gdf = gdf.copy()
	# Use WKB bytes as stable fingerprint
	geom_wkb = gdf.geometry.apply(lambda geom: geom.wkb if isinstance(geom, BaseGeometry) else None)
	gdf["_geom_wkb"] = geom_wkb
	gdf = gdf.drop_duplicates(subset=["_geom_wkb"]).drop(columns=["_geom_wkb"])  # type: ignore[arg-type]
	# If osmid exists, also drop duplicate osmids
	if "osmid" in gdf.columns:
		gdf = gdf.drop_duplicates(subset=["osmid"])  # type: ignore[arg-type]
	return gdf


def clean_geometries(
	gdf: gpd.GeoDataFrame,
	*,
	min_area_m2: Optional[float] = None,
	min_length_m: Optional[float] = None,
	metrics_crs: str = "EPSG:25832",
) -> gpd.GeoDataFrame:
	"""Clean geometries: repair invalid, drop duplicates, filter tiny features.

	Args:
		gdf: Input GeoDataFrame
		min_area_m2: If provided, drop polygons smaller than this area
		min_length_m: If provided, drop lines shorter than this length
		metrics_crs: CRS for metric computations (meters)

	Returns:
		Cleaned GeoDataFrame
	"""
	if gdf.empty:
		return gdf

	# Ensure CRS is set (default to EPSG:4326 like extraction does)
	if gdf.crs is None:
		gdf = gdf.set_crs("EPSG:4326")

	# 1) Repair invalid geometries
	gdf = _make_geometries_valid(gdf)
	# Remove null/empty geometries
	gdf = gdf[gdf.geometry.notna()]
	if gdf.empty:
		return gdf

	# 2) Drop exact duplicates
	gdf = _drop_duplicate_geometries(gdf)
	if gdf.empty:
		return gdf

	# 3) Filter tiny features if thresholds provided
	if min_area_m2 is not None or min_length_m is not None:
		gdf_metric = gdf.to_crs(metrics_crs)
		mask = pd.Series([True] * len(gdf_metric), index=gdf_metric.index)
		if min_area_m2 is not None:
			poly_mask = gdf_metric.geometry.geom_type.isin(["Polygon", "MultiPolygon"])  # type: ignore[attr-defined]
			areas = gdf_metric.loc[poly_mask].geometry.area
			mask.loc[poly_mask] = areas >= float(min_area_m2)
		if min_length_m is not None:
			line_mask = gdf_metric.geometry.geom_type.isin(["LineString", "MultiLineString"])  # type: ignore[attr-defined]
			lengths = gdf_metric.loc[line_mask].geometry.length
			mask.loc[line_mask] = lengths >= float(min_length_m)
		gdf = gdf.loc[mask]

	return gdf
