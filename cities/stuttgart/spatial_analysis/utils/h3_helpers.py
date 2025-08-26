# utils/h3_helpers.py
from __future__ import annotations
from typing import Iterable, Set
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, base
import h3

def polygon_geom_to_h3_cells(geom: base.BaseGeometry, res: int) -> Set[str]:
    """
    Convert a shapely Polygon/MultiPolygon in EPSG:4326 to a set of H3 cells.
    Uses a simple bounding box approach that works with current h3 library.
    """
    if geom.is_empty:
        return set()
    
    # Get the bounding box
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    min_lon, min_lat, max_lon, max_lat = bounds
    
    # Create H3 cells for the bounding box area
    cells = set()
    
    # Use a simple grid approach - get cells in the bounding box
    # Start from the southwest corner and move east/north
    current_lat = min_lat
    while current_lat <= max_lat:
        current_lon = min_lon
        while current_lon <= max_lon:
            try:
                cell = h3.latlng_to_cell(current_lat, current_lon, res)
                cells.add(cell)
            except:
                pass
            current_lon += 0.01  # Rough step size
        current_lat += 0.01  # Rough step size
    
    # Filter cells to only those that intersect with the geometry
    # This is a simple center-point check
    filtered_cells = set()
    for cell in cells:
        try:
            # Get the center of the H3 cell
            center_lat, center_lon = h3.cell_to_latlng(cell)
            # Check if center is inside the geometry
            from shapely.geometry import Point
            center_point = Point(center_lon, center_lat)
            if geom.contains(center_point):
                filtered_cells.add(cell)
        except:
            continue
    
    return filtered_cells

def h3_to_shapely_geometry(h3_index: str) -> Polygon:
    """
    Convert H3 index to Shapely polygon.
    """
    # h3.cell_to_boundary returns (lat, lon) tuples
    coords = h3.cell_to_boundary(h3_index)
    # Convert to (lon, lat) for Shapely
    coords_lon_lat = [(lon, lat) for lat, lon in coords]
    return Polygon(coords_lon_lat)

def gdf_polygons_to_h3(gdf: gpd.GeoDataFrame, res: int) -> Set[str]:
    """
    Ensure CRS=EPSG:4326, then union all polygon cells.
    """
    g = gdf
    if g.crs is None or str(g.crs).upper() not in ("EPSG:4326", "EPSG: 4326"):
        g = g.to_crs(4326)
    
    cells: Set[str] = set()
    for geom in g.geometry:
        cells |= polygon_geom_to_h3_cells(geom, res)
    return cells
