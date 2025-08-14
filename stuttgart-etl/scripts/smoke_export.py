import duckdb, geopandas as gpd, pandas as pd, pathlib
con = duckdb.connect("data/duckdb/stuttgart.duckdb")
con.execute("LOAD spatial")
df = con.execute("SELECT *, ST_AsWKB(geom_25832_1) AS wkb FROM stg.osm_roads LIMIT 5000").fetch_df()
con.close()
gdf = gpd.GeoDataFrame(df.drop(columns=["wkb"]), geometry=gpd.GeoSeries.from_wkb([bytes(x) for x in df["wkb"]]), crs="EPSG:25832").to_crs(4326)
out = pathlib.Path("data/exports"); out.mkdir(parents=True, exist_ok=True)
gdf.to_file(out / "osm_roads_sample.geojson", driver="GeoJSON")
print("OK →", (out / "osm_roads_sample.geojson").as_posix())

