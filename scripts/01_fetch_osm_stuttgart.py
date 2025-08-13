import argparse
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
import requests


# Configure OSMnx: cache and user agent to be polite to Nominatim/Overpass
ox.settings.use_cache = True
ox.settings.cache_folder = str(Path("cache/osmnx").resolve())
ox.settings.timeout = 180
ox.settings.default_user_agent = (
    "stuttgart-osm-fetcher/1.0 (contact: youremail@example.com)"
)


DEFAULT_PLACE_QUERY = "Stuttgart, Baden-Württemberg, Germany"


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def geocode_study_area(
    place_query: str,
    buffer_meters: int = 20000,
) -> gpd.GeoSeries:
    """
    Geocode the study area and apply an optional metric buffer to approximate "grossraum".

    - Input geometries are geocoded in EPSG:4326.
    - Buffer is applied in EPSG:25832 (meters) per user's spatial workflow.
    - Returns the final area geometry back in EPSG:4326.
    """
    area_gdf = ox.geocode_to_gdf(place_query)
    if area_gdf.empty:
        raise RuntimeError(f"Could not geocode place query: {place_query}")

    # Use the union of all returned geometries; prefer polygons
    geom = area_gdf.geometry.unary_union

    # Apply buffer in metric CRS (ETRS89 / UTM zone 32N)
    area_series = gpd.GeoSeries([geom], crs="EPSG:4326").to_crs("EPSG:25832")
    if buffer_meters and buffer_meters > 0:
        area_series = area_series.buffer(buffer_meters)
    # Back to 4326 for Overpass/OSM queries
    area_series = gpd.GeoSeries(area_series, crs="EPSG:25832").to_crs("EPSG:4326")
    return area_series


def bbox_to_polygon(bbox: str) -> BaseGeometry:
    """
    Parse bbox string "minx,miny,maxx,maxy" in EPSG:4326 (lon,lat) and return a polygon.
    """
    try:
        parts = [float(x.strip()) for x in bbox.split(",")]
    except Exception as exc:
        raise ValueError(
            "--bbox must be a comma-separated list of 4 numbers: minx,miny,maxx,maxy"
        ) from exc
    if len(parts) != 4:
        raise ValueError(
            "--bbox must contain exactly 4 numbers: minx,miny,maxx,maxy"
        )
    minx, miny, maxx, maxy = parts
    if not (minx < maxx and miny < maxy):
        raise ValueError("Invalid bbox: ensure that minx < maxx and miny < maxy")
    return box(minx, miny, maxx, maxy)


def parse_bbox_tuple(bbox: Optional[str], fallback_geom: Optional[BaseGeometry] = None) -> Optional[Tuple[float, float, float, float]]:
    """
    Return (minx, miny, maxx, maxy) from string or from fallback geometry.
    """
    if bbox:
        parts = [float(x.strip()) for x in bbox.split(",")]
        if len(parts) != 4:
            raise ValueError("--bbox must be 'minx,miny,maxx,maxy'")
        minx, miny, maxx, maxy = parts
        if not (minx < maxx and miny < maxy):
            raise ValueError("Invalid bbox: ensure that minx < maxx and miny < maxy")
        return (minx, miny, maxx, maxy)
    if fallback_geom is not None:
        minx, miny, maxx, maxy = fallback_geom.bounds
        return (float(minx), float(miny), float(maxx), float(maxy))
    return None


def download_file(url: str, dest_dir: Path, filename: Optional[str] = None) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        filename = url.split("/")[-1]
    out_path = dest_dir / filename
    if out_path.exists() and out_path.stat().st_size > 0:
        return out_path
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return out_path


def fetch_osm_geometries(
    polygon: BaseGeometry,
    tags: Dict[str, Union[List[str], bool]],
) -> gpd.GeoDataFrame:
    """Fetch OSM geometries within polygon for given tag filters."""
    gdf = ox.geometries_from_polygon(polygon, tags)
    if gdf.empty:
        return gdf
    # Normalize CRS and index
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    gdf.reset_index(inplace=True)
    # unify osmid column name
    if "osmid" not in gdf.columns:
        # For nodes/ways, osmnx stores id in 'osmid' after reset_index()
        pass
    return gdf


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


def select_columns(
    gdf: gpd.GeoDataFrame,
    keep: List[str],
) -> gpd.GeoDataFrame:
    cols = [c for c in keep if c in gdf.columns]
    cols = list(dict.fromkeys(["osmid", "name", *cols, "geometry"]))
    return gdf[cols]


def process_roads(polygon: BaseGeometry) -> gpd.GeoDataFrame:
    # Focus on motorized road classes
    road_values = [
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "unclassified",
        "residential",
        "living_street",
        "service",
    ]
    tags = {"highway": road_values}
    gdf = fetch_osm_geometries(polygon, tags)
    if gdf.empty:
        return gdf
    gdf = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]
    gdf = select_columns(
        gdf,
        [
            "highway",
            "maxspeed",
            "lanes",
            "surface",
            "oneway",
            "bridge",
            "tunnel",
            "access",
        ],
    )
    gdf = compute_length_m(gdf)
    gdf["category"] = "roads"
    return gdf


def process_roads_bulk(osm) -> gpd.GeoDataFrame:
    # pyrosm network for driving
    edges = osm.get_network(network_type="driving")
    if edges is None or edges.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    gdf = edges.copy()
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    # Keep only linear geometries
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.type.isin(["LineString", "MultiLineString"])]
    # Normalize column names
    gdf.rename(columns={"id": "osmid"}, inplace=True)
    gdf = select_columns(
        gdf,
        ["highway", "maxspeed", "lanes", "surface", "oneway", "bridge", "tunnel", "access"],
    )
    gdf = compute_length_m(gdf)
    gdf["category"] = "roads"
    return gdf


def process_cycle_paths(polygon: BaseGeometry) -> gpd.GeoDataFrame:
    # Union of dedicated cycleways and ways that have cycleway/bicycle designation
    parts: List[gpd.GeoDataFrame] = []

    # Dedicated cycleway ways
    parts.append(fetch_osm_geometries(polygon, {"highway": ["cycleway"]}))
    # Ways with any cycleway tag
    parts.append(fetch_osm_geometries(polygon, {"cycleway": True}))
    # Bicycle-designated paths/footways
    parts.append(
        fetch_osm_geometries(
            polygon, {"highway": ["path", "footway"], "bicycle": ["designated", "yes"]}
        )
    )

    gdf = pd.concat([p for p in parts if p is not None and not p.empty], ignore_index=True)
    if gdf.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # Keep linear geometries only
    gdf = gdf[gdf.geometry.type.isin(["LineString", "MultiLineString"])]
    gdf = gdf.drop_duplicates(subset=["osmid", "geometry"], keep="first")
    gdf = select_columns(
        gdf,
        [
            "highway",
            "cycleway",
            "bicycle",
            "surface",
            "segregated",
            "oneway:bicycle",
        ],
    )
    gdf = compute_length_m(gdf)
    gdf["category"] = "cycle_paths"
    return gdf


def process_cycle_paths_bulk(osm) -> gpd.GeoDataFrame:
    cycling = osm.get_network(network_type="cycling")
    parts: List[gpd.GeoDataFrame] = []
    if cycling is not None and not cycling.empty:
        parts.append(cycling)
    # Additional custom filter: ways with cycleway tag
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
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.type.isin(["LineString", "MultiLineString"])]
    gdf.rename(columns={"id": "osmid"}, inplace=True)
    gdf = select_columns(
        gdf,
        ["highway", "cycleway", "bicycle", "surface", "segregated", "oneway:bicycle"],
    )
    gdf = compute_length_m(gdf)
    gdf["category"] = "cycle_paths"
    return gdf


def process_green_areas(polygon: BaseGeometry) -> gpd.GeoDataFrame:
    tags = {
        "leisure": ["park", "garden", "golf_course", "nature_reserve", "recreation_ground"],
        "landuse": ["forest", "grass", "meadow", "orchard", "vineyard", "recreation_ground", "cemetery"],
        "natural": ["wood", "grassland", "heath", "scrub", "fell", "moor", "wetland"],
        "boundary": ["protected_area"],
    }
    gdf = fetch_osm_geometries(polygon, tags)
    if gdf.empty:
        return gdf

    # Keep polygons only
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    gdf = select_columns(
        gdf,
        ["leisure", "landuse", "natural", "boundary", "protect_class", "operator"],
    )
    gdf = compute_area_m2(gdf)
    gdf["category"] = "green_areas"
    return gdf


def process_green_areas_bulk(osm) -> gpd.GeoDataFrame:
    landuse = osm.get_landuse()
    natural = osm.get_natural()
    leisure = osm.get_pois(categories=["leisure"])  # parks, gardens, recreation
    parts: List[gpd.GeoDataFrame] = []
    for p in [landuse, natural, leisure]:
        if p is not None and not p.empty:
            parts.append(p)
    if not parts:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    gdf = pd.concat(parts, ignore_index=True, sort=False)
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
    # Standardize columns
    if "leisure" not in gdf.columns:
        gdf["leisure"] = pd.Series(dtype="object")
    if "landuse" not in gdf.columns:
        gdf["landuse"] = pd.Series(dtype="object")
    if "natural" not in gdf.columns:
        gdf["natural"] = pd.Series(dtype="object")
    gdf.rename(columns={"id": "osmid"}, inplace=True)
    gdf = select_columns(gdf, ["leisure", "landuse", "natural", "boundary", "protect_class", "operator"])
    gdf = compute_area_m2(gdf)
    gdf["category"] = "green_areas"
    return gdf


def process_transport_connections(polygon: BaseGeometry) -> gpd.GeoDataFrame:
    tags = {
        "railway": ["station", "halt", "tram_stop", "subway_entrance"],
        "public_transport": ["station", "stop_position", "platform"],
        "highway": ["bus_stop"],
        "amenity": ["bus_station", "ferry_terminal"],
        "aeroway": ["aerodrome", "terminal"],
        "aerialway": ["station"],
    }
    gdf = fetch_osm_geometries(polygon, tags)
    if gdf.empty:
        return gdf

    # Points and polygons – keep all geometries for context
    gdf = gdf[gdf.geometry.notna()]
    gdf = select_columns(
        gdf,
        [
            "railway",
            "public_transport",
            "highway",
            "amenity",
            "aeroway",
            "aerialway",
            "operator",
            "network",
            "ref",
        ],
    )
    gdf["category"] = "transport_connections"
    return gdf


def process_transport_connections_bulk(osm) -> gpd.GeoDataFrame:
    # POIs for stations, platforms, terminals
    pois = osm.get_pois(categories=["public_transport", "railway", "aeroway", "aerialway", "amenity"])
    # Add bus stops via custom filter
    bus_stops = osm.get_data_by_custom_criteria(
        custom_filter={"highway": ["bus_stop"]},
        filter_type="keep",
        keep_nodes=True,
        keep_ways=False,
        keep_relations=True,
    )
    parts: List[gpd.GeoDataFrame] = []
    for p in [pois, bus_stops]:
        if p is not None and not p.empty:
            parts.append(p)
    if not parts:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    gdf = pd.concat(parts, ignore_index=True, sort=False)
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    gdf = gdf[gdf.geometry.notna()]
    gdf.rename(columns={"id": "osmid"}, inplace=True)
    gdf = select_columns(
        gdf,
        ["railway", "public_transport", "highway", "amenity", "aeroway", "aerialway", "operator", "network", "ref"],
    )
    gdf["category"] = "transport_connections"
    return gdf


def write_outputs(
    outputs: List[Tuple[str, gpd.GeoDataFrame]],
    out_dir: Path,
    out_basename: str,
) -> List[Path]:
    """
    Save outputs with two strategies:
    - Primary: one GeoPackage with multiple layers
    - Fallback: individual GeoJSON files per layer
    Returns list of written file paths.
    """
    written: List[Path] = []

    gpkg_path = out_dir / f"{out_basename}.gpkg"

    # Prefer pyogrio engine on Windows for simpler installation; fall back if unavailable
    has_pyogrio = importlib.util.find_spec("pyogrio") is not None
    engine_kw = {"engine": "pyogrio"} if has_pyogrio else {}
    # Try to write GPKG (requires Fiona/GDAL). If it fails, fall back to GeoJSON.
    try:
        if gpkg_path.exists():
            gpkg_path.unlink()
        for idx, (layer_name, gdf) in enumerate(outputs):
            if gdf.empty:
                continue
            # Ensure storage CRS is EPSG:4326 per user's workflow
            gdf_4326 = gdf.to_crs("EPSG:4326") if gdf.crs else gdf.set_crs("EPSG:4326")
            gdf_4326.to_file(gpkg_path, layer=layer_name, driver="GPKG", **engine_kw)
        if gpkg_path.exists():
            written.append(gpkg_path)
            return written
    except Exception as exc:
        # Fall through to GeoJSON
        print(f"GeoPackage write failed ({exc}). Falling back to GeoJSON files.")

    # Fallback GeoJSON per layer
    for layer_name, gdf in outputs:
        if gdf.empty:
            continue
        out_path = out_dir / f"{out_basename}_{layer_name}.geojson"
        gdf_4326 = gdf.to_crs("EPSG:4326") if gdf.crs else gdf.set_crs("EPSG:4326")
        try:
            gdf_4326.to_file(out_path, driver="GeoJSON", **engine_kw)
        except Exception:
            # try without engine kw
            gdf_4326.to_file(out_path, driver="GeoJSON")
        written.append(out_path)
    return written


def main():
    parser = argparse.ArgumentParser(
        description="Fetch OSM data for Stuttgart grossraum (roads, green areas, cycle paths, transport connections).",
    )
    parser.add_argument(
        "--source",
        choices=["overpass", "bulk"],
        default="overpass",
        help="Data source: 'overpass' (live OSM) or 'bulk' (PBF via Geofabrik/S3) (default: %(default)s)",
    )
    parser.add_argument(
        "--place",
        default=DEFAULT_PLACE_QUERY,
        help="Place query for geocoding the core city/region (default: '%(default)s')",
    )
    parser.add_argument(
        "--buffer-m",
        type=int,
        default=20000,
        help="Metric buffer in meters to approximate 'grossraum' around the place (default: %(default)s)",
    )
    parser.add_argument(
        "--bbox",
        type=str,
        default=None,
        help=(
            "Bounding box in EPSG:4326 as 'minx,miny,maxx,maxy' (lon,lat). When provided, overrides --place and --buffer-m."
        ),
    )
    # Bulk-specific options
    parser.add_argument(
        "--pbf-path",
        type=str,
        default=None,
        help="Local path to a .osm.pbf file (e.g., Geofabrik extract)",
    )
    parser.add_argument(
        "--pbf-url",
        type=str,
        default=None,
        help="Remote URL to a .osm.pbf file (e.g., Geofabrik or S3 HTTPS)",
    )
    parser.add_argument(
        "--geofabrik-region",
        type=str,
        default=None,
        help=(
            "Geofabrik region path like 'europe/germany/baden-wuerttemberg' or 'europe/germany/baden-wuerttemberg/stuttgart-regbez'. "
            "If provided, constructs URL as 'https://download.geofabrik.de/{region}-latest.osm.pbf'"
        ),
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        default=str(Path("data/osm/raw").resolve()),
        help="Directory to store downloaded PBF files (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path("data/osm").resolve()),
        help="Output directory (will be created if missing)",
    )
    parser.add_argument(
        "--out-name",
        default=None,
        help="Base filename (without extension). Default is stuttgart_osm_YYYYMMDD",
    )

    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    ensure_directory(out_dir)

    date_str = datetime.now().strftime("%Y%m%d")
    out_basename = args.out_name or f"stuttgart_osm_{date_str}"

    if args.source == "overpass":
        # Study area polygon in EPSG:4326
        if args.bbox:
            polygon = bbox_to_polygon(args.bbox)
        else:
            area_series = geocode_study_area(args.place, buffer_meters=args.buffer_m)
            polygon = area_series.iloc[0]

        print("Fetching roads …")
        roads = process_roads(polygon)
        print(f"  Roads fetched: {len(roads)} features")

        print("Fetching cycle paths …")
        cycle_paths = process_cycle_paths(polygon)
        print(f"  Cycle paths fetched: {len(cycle_paths)} features")

        print("Fetching green areas …")
        green_areas = process_green_areas(polygon)
        print(f"  Green areas fetched: {len(green_areas)} features")

        print("Fetching transport connections …")
        transport_connections = process_transport_connections(polygon)
        print(f"  Transport connections fetched: {len(transport_connections)} features")

    else:
        # Bulk mode via pyrosm
        if importlib.util.find_spec("pyrosm") is None:
            raise RuntimeError(
                "pyrosm is required for --source bulk. Please install it (pip install pyrosm)."
            )
        from pyrosm import OSM  # type: ignore

        # Determine PBF path
        pbf_path: Optional[Path] = None
        if args.pbf_path:
            pbf_path = Path(args.pbf_path)
            if not pbf_path.exists():
                raise FileNotFoundError(f"PBF file not found: {pbf_path}")
        else:
            pbf_url: Optional[str] = None
            if args.pbf_url:
                pbf_url = args.pbf_url
            elif args.geofabrik_region:
                region = args.geofabrik_region.strip("/")
                pbf_url = f"https://download.geofabrik.de/{region}-latest.osm.pbf"
            if not pbf_url:
                raise ValueError(
                    "For --source bulk, provide either --pbf-path, --pbf-url, or --geofabrik-region."
                )
            download_dir = Path(args.download_dir)
            filename_hint = pbf_url.split("/")[-1]
            pbf_path = download_file(pbf_url, download_dir, filename_hint)

        # Determine bbox for clipping
        fallback_polygon: Optional[BaseGeometry] = None
        if not args.bbox and args.place:
            area_series = geocode_study_area(args.place, buffer_meters=args.buffer_m)
            fallback_polygon = area_series.iloc[0]
        bbox_tuple = parse_bbox_tuple(args.bbox, fallback_geom=fallback_polygon)

        osm = OSM(pbf_path.as_posix(), bounding_box=bbox_tuple)

        print("Reading roads from PBF …")
        roads = process_roads_bulk(osm)
        print(f"  Roads fetched: {len(roads)} features")

        print("Reading cycle paths from PBF …")
        cycle_paths = process_cycle_paths_bulk(osm)
        print(f"  Cycle paths fetched: {len(cycle_paths)} features")

        print("Reading green areas from PBF …")
        green_areas = process_green_areas_bulk(osm)
        print(f"  Green areas fetched: {len(green_areas)} features")

        print("Reading transport connections from PBF …")
        transport_connections = process_transport_connections_bulk(osm)
        print(f"  Transport connections fetched: {len(transport_connections)} features")

    # 3) Persist results (store in EPSG:4326, metrics are in meters already)
    outputs = [
        ("roads", roads),
        ("cycle_paths", cycle_paths),
        ("green_areas", green_areas),
        ("transport_connections", transport_connections),
    ]

    written_paths = write_outputs(outputs, out_dir, out_basename)

    if not written_paths:
        print("No files were written. Please check tag results and write permissions.")
        return

    print("\nWritten files:")
    for p in written_paths:
        print(f" - {p}")


if __name__ == "__main__":
    main()


