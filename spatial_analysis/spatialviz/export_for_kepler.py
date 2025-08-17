# spatialviz/export_for_kepler.py
#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import geopandas as gpd
import pandas as pd

# Updated paths to match current project structure
IN  = Path("../main_pipeline/areas/stuttgart/data_final")
OUT = Path("outputs/kepler"); OUT.mkdir(parents=True, exist_ok=True)

def read_any(p: Path):
    if not p.exists(): return None
    try:
        if p.suffix.lower() in {".geojson",".json",".gpkg"}:
            return gpd.read_file(p)
        elif p.suffix.lower() == ".parquet":
            # Read parquet and check if it has geometry column
            df = pd.read_parquet(p)
            if "geometry" in df.columns:
                # Check if geometry column contains bytes (WKB format)
                if df['geometry'].dtype == 'object' and isinstance(df['geometry'].iloc[0], bytes):
                    # Convert WKB bytes to Shapely geometries
                    from shapely import wkb
                    df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
                
                # Convert to GeoDataFrame
                return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)
            else:
                return df
        else:
            return pd.read_parquet(p)
    except Exception as e:
        print(f"Error reading {p}: {e}")
        return None

def main():
    print("🗺️ Exporting data for Kepler.gl...")
    
    # Prefer "districts_with_population"; fallback to "districts"
    districts = read_any(IN/"districts_with_population.geojson")
    if districts is None:
        districts = read_any(IN/"districts.geojson")
    
    landuse   = read_any(IN/"processed/landuse_categorized.parquet")
    cycle     = read_any(IN/"processed/cycle_categorized.parquet")
    pt_stops  = read_any(IN/"processed/pt_stops_categorized.parquet")
    boundary  = read_any(IN/"city_boundary.geojson")
    if boundary is None:
        boundary = districts

    if districts is None:
        raise SystemExit("❌ districts(.geojson) missing — needed for Kepler.")

    print(f"✅ Found {len(districts)} districts")

    # Keep in WGS84 for Kepler
    def to_wgs(g):
        if g is None: return None
        return g.set_crs(4326) if g.crs is None else g.to_crs(4326)

    districts = to_wgs(districts)
    landuse   = to_wgs(landuse)
    cycle     = to_wgs(cycle)
    pt_stops  = to_wgs(pt_stops)
    boundary  = to_wgs(boundary)

    # Trim landuse to "greens" so Kepler stays fast & pretty
    if landuse is not None:
        lu = landuse.copy()
        def is_green(r):
            lu=str(r.get("landuse","")).lower(); nat=str(r.get("natural","")).lower()
            return lu in {"forest","meadow","grass","recreation_ground","park","cemetery","orchard","vineyard","allotments"} \
                or nat in {"wood","scrub","grassland","park"}
        landuse = lu[lu.apply(is_green, axis=1)]
        if len(landuse)==0: 
            landuse=None
        else:
            print(f"✅ Found {len(landuse)} green areas")

    # Write
    districts.to_file(OUT/"districts.geojson", driver="GeoJSON")
    print(f"💾 Saved: {OUT/'districts.geojson'}")
    
    if landuse is not None: 
        landuse.to_file(OUT/"greens.geojson", driver="GeoJSON")
        print(f"💾 Saved: {OUT/'greens.geojson'}")
    
    if cycle is not None: 
        cycle.to_file(OUT/"cycle.geojson", driver="GeoJSON")
        print(f"💾 Saved: {OUT/'cycle.geojson'}")
    
    if pt_stops is not None: 
        pt_stops.to_file(OUT/"pt_stops.geojson", driver="GeoJSON")
        print(f"💾 Saved: {OUT/'pt_stops.geojson'}")
    
    if boundary is not None: 
        boundary.to_file(OUT/"city_boundary.geojson", driver="GeoJSON")
        print(f"💾 Saved: {OUT/'city_boundary.geojson'}")

    print(f"\n🎉 Kepler exports saved in {OUT}/")
    print("📁 Next: Open outputs/kepler/stuttgart_kepler.html in your browser")

if __name__ == "__main__":
    main()
