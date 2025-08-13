Stuttgart ETL

This repository provides a reproducible ETL pipeline for Stuttgart geodata.

Features (incrementally implemented):
- Sources: OSM (Geofabrik PBF) and DE public datasets
- Core DB: DuckDB with Spatial extension (local file)
- CRS discipline: native in raw, EPSG:4326 for exports, EPSG:25832 for analytics
- Layers: roads, buildings, landuse, amenities, cycle infra, PT stops, boundaries
- Transform: standardization, validation, spatial joins, dissolves/clips
- Exports: GeoParquet, GeoPackage, GeoJSON, CSV
- CLI (Typer): extract, load, transform, export

Quickstart
1) Create environment and install
```bash
pip install -e .
```

2) Extract OSM (bulk, Geofabrik PBF)
```bash
cd stuttgart-etl
python -m etl.cli extract-osm --area stuttgart --layers roads buildings landuse cycle pt_stops boundaries amenities
```
Outputs:
- data/raw/*.osm.pbf (downloaded)
- data/staging/osm_*.parquet (GeoParquet per layer)

Notes
- Windows recommended: use pyogrio + pyarrow wheels to avoid GDAL issues.
- BBOX and Geofabrik region are configurable in `config/areas.yaml`.
