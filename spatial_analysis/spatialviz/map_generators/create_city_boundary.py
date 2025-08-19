#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import geopandas as gpd
from shapely.ops import unary_union

# Paths
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
DISTRICTS_PATH = Path("../spatial_analysis/areas/stuttgart_districts_official/OpenData_KLGL_GENERALISIERT.gpkg")

def main():
    print("Creating city boundary from districts...")
    
    # Load districts
    districts = gpd.read_file(DISTRICTS_PATH, layer="KLGL_BRUTTO_STADTBEZIRK")
    districts = districts.set_crs(4326) if districts.crs is None else districts.to_crs(4326)
    
    # Union all district geometries to create city boundary
    city_boundary = gpd.GeoDataFrame(
        {"name": ["Stuttgart"]}, 
        geometry=[unary_union(districts.geometry)], 
        crs=4326
    )
    
    # Save city boundary
    output_path = DATA_DIR / "city_boundary.geojson"
    city_boundary.to_file(output_path, driver="GeoJSON")
    print(f"✅ City boundary saved to: {output_path}")

if __name__ == "__main__":
    main()
