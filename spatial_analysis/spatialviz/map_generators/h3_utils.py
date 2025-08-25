# spatialviz/h3_utils.py
from __future__ import annotations
from typing import Iterable, List
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.ops import unary_union
import sys
sys.path.append("../utils")
from h3_helpers import gdf_polygons_to_h3, h3_to_shapely_geometry

def hex_polygon(h: str) -> Polygon:
    # Use our custom helper function
    return h3_to_shapely_geometry(h)

def polyfill_gdf(gdf_wgs84: gpd.GeoDataFrame, res: int) -> List[str]:
    # Use the new helper function
    cells = gdf_polygons_to_h3(gdf_wgs84, res)
    return list(cells)

def cells_to_gdf(cells: Iterable[str], to_crs: str | None = None) -> gpd.GeoDataFrame:
    g = gpd.GeoDataFrame({"h3": list(cells)}, geometry=[hex_polygon(c) for c in cells], crs=4326)
    if to_crs: g = g.to_crs(to_crs)
    return g
