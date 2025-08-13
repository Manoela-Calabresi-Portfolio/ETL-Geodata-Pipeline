from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Tuple
import sys

import geopandas as gpd
import pandas as pd
import requests
from pyrosm import OSM  # type: ignore

from .utils import ensure_directory, compute_area_m2, compute_length_m


def _human_size(num_bytes: int) -> str:
	units = ["B", "KB", "MB", "GB", "TB"]
	size = float(num_bytes)
	for unit in units:
		if size < 1024.0:
			return f"{size:.1f} {unit}"
		size /= 1024.0
	return f"{size:.1f} PB"


def download_file(url: str, dest_dir: Path, filename: Optional[str] = None) -> Path:
	ensure_directory(dest_dir)
	if filename is None:
		filename = url.split("/")[-1]
	out_path = dest_dir / filename
	if out_path.exists() and out_path.stat().st_size > 0:
		print(f"🟪 Using cached file: {out_path} ({_human_size(out_path.stat().st_size)})")
		return out_path
	print(f"🔺 Downloading: {url}")
	downloaded = 0
	with requests.get(url, stream=True, timeout=600) as r:
		r.raise_for_status()
		with open(out_path, "wb") as f:
			for chunk in r.iter_content(chunk_size=1024 * 1024):
				if not chunk:
					continue
				f.write(chunk)
				downloaded += len(chunk)
				sys.stdout.write(f"\r   downloaded {_human_size(downloaded)}")
				sys.stdout.flush()
	final_size = out_path.stat().st_size if out_path.exists() else 0
	sys.stdout.write("\n")
	print(f"🟣 Saved to: {out_path} ({_human_size(final_size)})")
	return out_path


def resolve_pbf(
	pbf_path: Optional[str],
	pbf_url: Optional[str],
	geofabrik_region: Optional[str],
	download_dir: Path,
) -> Path:
	if pbf_path:
		path = Path(pbf_path)
		print(f"🔻 Using local PBF: {path}")
		if not path.exists():
			raise FileNotFoundError(f"PBF not found: {path}")
		return path
	if pbf_url:
		print(f"🔺 Fetching PBF from URL: {pbf_url}")
		return download_file(pbf_url, download_dir)
	if geofabrik_region:
		region = geofabrik_region.strip("/")
		url = f"https://download.geofabrik.de/{region}-latest.osm.pbf"
		print(f"🔺 Fetching Geofabrik region: {region}\n   URL: {url}")
		return download_file(url, download_dir)
	raise ValueError("Provide one of pbf_path, pbf_url, or geofabrik_region")


def open_osm(pbf: Path, bbox: Optional[Tuple[float, float, float, float]]) -> OSM:
	print(f"🟣 Opening PBF: {pbf}")
	if bbox is not None:
		print(f"   with bbox: {bbox}")
		bbox_list = [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
	else:
		bbox_list = None  # type: ignore[assignment]
	return OSM(pbf.as_posix(), bounding_box=bbox_list)


def build_roads(osm: OSM) -> gpd.GeoDataFrame:
	print("🟪 Building layer: roads")
	edges = osm.get_network(network_type="driving")
	if edges is None or edges.empty:
		return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
	gdf = edges.copy()
	if gdf.crs is None:
		gdf.set_crs("EPSG:4326", inplace=True)
	gdf = gdf[gdf.geometry.notna()]
	gdf = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]
	gdf.rename(columns={"id": "osmid"}, inplace=True)
	gdf = gdf[[c for c in ["osmid", "name", "highway", "maxspeed", "lanes", "surface", "oneway", "bridge", "tunnel", "access", "geometry"] if c in gdf.columns]]
	gdf = compute_length_m(gdf)
	gdf["category"] = "roads"
	print(f"   features: {len(gdf)}")
	return gdf


def build_buildings(osm: OSM) -> gpd.GeoDataFrame:
	print("🟪 Building layer: buildings")
	b = osm.get_buildings()
	if b is None or b.empty:
		return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
	gdf = b.copy()
	if gdf.crs is None:
		gdf.set_crs("EPSG:4326", inplace=True)
	gdf = gdf[gdf.geometry.notna()]
	gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
	gdf.rename(columns={"id": "osmid"}, inplace=True)
	gdf = gdf[[c for c in ["osmid", "name", "building", "levels", "height", "geometry"] if c in gdf.columns]]
	gdf = compute_area_m2(gdf)
	gdf["category"] = "buildings"
	print(f"   features: {len(gdf)}")
	return gdf


def build_landuse(osm: OSM) -> gpd.GeoDataFrame:
	print("🟪 Building layer: landuse")
	l = osm.get_landuse()
	n = osm.get_natural()
	parts: List[gpd.GeoDataFrame] = []
	for p in [l, n]:
		if p is not None and not p.empty:
			parts.append(p)
	if not parts:
		return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
	gdf = pd.concat(parts, ignore_index=True, sort=False)
	if gdf.crs is None:
		gdf.set_crs("EPSG:4326", inplace=True)
	gdf = gdf[gdf.geometry.notna()]
	gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
	if "landuse" not in gdf.columns:
		gdf["landuse"] = pd.Series(dtype="object")
	if "natural" not in gdf.columns:
		gdf["natural"] = pd.Series(dtype="object")
	gdf.rename(columns={"id": "osmid"}, inplace=True)
	gdf = gdf[[c for c in ["osmid", "name", "landuse", "natural", "geometry"] if c in gdf.columns]]
	gdf = compute_area_m2(gdf)
	gdf["category"] = "landuse"
	print(f"   features: {len(gdf)}")
	return gdf


def build_cycle(osm: OSM) -> gpd.GeoDataFrame:
	print("🟪 Building layer: cycle")
	cycling = osm.get_network(network_type="cycling")
	parts: List[gpd.GeoDataFrame] = []
	if cycling is not None and not cycling.empty:
		parts.append(cycling)
	extra = osm.get_data_by_custom_criteria(
		custom_filter={"cycleway": True},
		filter_type="keep",
		keep_ways=True,
		keep_nodes=False,
		keep_relations=False,
	)
	if extra is not None and not extra.empty:
		parts.append(extra)
	if not parts:
		return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
	gdf = pd.concat(parts, ignore_index=True)
	if gdf.crs is None:
		gdf.set_crs("EPSG:4326", inplace=True)
	gdf = gdf[gdf.geometry.notna()]
	gdf = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]
	gdf.rename(columns={"id": "osmid"}, inplace=True)
	gdf = gdf[[c for c in ["osmid", "name", "highway", "cycleway", "bicycle", "surface", "segregated", "geometry"] if c in gdf.columns]]
	gdf = compute_length_m(gdf)
	gdf["category"] = "cycle"
	print(f"   features: {len(gdf)}")
	return gdf


def build_pt_stops(osm: OSM) -> gpd.GeoDataFrame:
	print("🟪 Building layer: pt_stops")
	pois = osm.get_pois(categories=["public_transport", "railway", "aeroway", "aerialway", "amenity"])
	bus = osm.get_data_by_custom_criteria(
		custom_filter={"highway": ["bus_stop"]},
		filter_type="keep",
		keep_nodes=True,
		keep_ways=False,
		keep_relations=True,
	)
	parts: List[gpd.GeoDataFrame] = []
	for p in [pois, bus]:
		if p is not None and not p.empty:
			parts.append(p)
	if not parts:
		return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
	gdf = pd.concat(parts, ignore_index=True, sort=False)
	if gdf.crs is None:
		gdf.set_crs("EPSG:4326", inplace=True)
	gdf = gdf[gdf.geometry.notna()]
	gdf.rename(columns={"id": "osmid"}, inplace=True)
	gdf = gdf[[c for c in ["osmid", "name", "railway", "public_transport", "highway", "amenity", "aeroway", "aerialway", "operator", "network", "ref", "geometry"] if c in gdf.columns]]
	gdf["category"] = "pt_stops"
	print(f"   features: {len(gdf)}")
	return gdf


def build_boundaries(osm: OSM) -> gpd.GeoDataFrame:
	print("🟪 Building layer: boundaries")
	try:
		b = osm.get_boundaries()
	except Exception:
		b = None
	if b is None or b.empty:
		b2 = osm.get_data_by_custom_criteria(
			custom_filter={"boundary": True},
			filter_type="keep",
			keep_ways=False,
			keep_relations=True,
			keep_nodes=False,
		)
		b = b2
	if b is None or b.empty:
		return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
	gdf = b.copy()
	if gdf.crs is None:
		gdf.set_crs("EPSG:4326", inplace=True)
	gdf = gdf[gdf.geometry.notna()]
	gdf.rename(columns={"id": "osmid"}, inplace=True)
	gdf = gdf[[c for c in ["osmid", "name", "admin_level", "boundary", "geometry"] if c in gdf.columns]]
	gdf["category"] = "boundaries"
	print(f"   features: {len(gdf)}")
	return gdf


def build_amenities(osm: OSM) -> gpd.GeoDataFrame:
	print("🟪 Building layer: amenities")
	amen = osm.get_pois(categories=["amenity"])  # generic OSM amenities
	if amen is None or amen.empty:
		return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
	gdf = amen.copy()
	if gdf.crs is None:
		gdf.set_crs("EPSG:4326", inplace=True)
	gdf = gdf[gdf.geometry.notna()]
	gdf.rename(columns={"id": "osmid"}, inplace=True)
	wanted = ["osmid", "name", "amenity", "operator", "capacity", "opening_hours", "geometry"]
	gdf = gdf[[c for c in wanted if c in gdf.columns]]
	gdf["category"] = "amenities"
	print(f"   features: {len(gdf)}")
	return gdf


LAYER_BUILDERS = {
	"roads": build_roads,
	"buildings": build_buildings,
	"landuse": build_landuse,
	"cycle": build_cycle,
	"pt_stops": build_pt_stops,
	"boundaries": build_boundaries,
	"amenities": build_amenities,
}


def write_geoparquet(gdf: gpd.GeoDataFrame, out_path: Path) -> None:
	ensure_directory(out_path.parent)
	print(f"🟣 Writing GeoParquet → {out_path}")
	gdf_4326 = gdf.to_crs("EPSG:4326") if gdf.crs else gdf.set_crs("EPSG:4326")
	gdf_4326.to_parquet(out_path)


def extract_osm_bulk(
	layers: Iterable[str],
	pbf_path: Optional[str],
	pbf_url: Optional[str],
	geofabrik_region: Optional[str],
	download_dir: Path,
	staging_dir: Path,
	bbox: Optional[Tuple[float, float, float, float]],
) -> None:
	print("🟣 Starting OSM bulk extract…")
	pbf = resolve_pbf(pbf_path, pbf_url, geofabrik_region, download_dir)
	osm = open_osm(pbf, bbox)
	for layer in layers:
		print(f"\n🟣 Processing layer: {layer}")
		builder = LAYER_BUILDERS.get(layer)
		if builder is None:
			raise ValueError(f"Unknown layer: {layer}")
		gdf = builder(osm)
		out_path = staging_dir / f"osm_{layer}.parquet"
		write_geoparquet(gdf, out_path)
	print("\n🟣 All requested layers processed.")
