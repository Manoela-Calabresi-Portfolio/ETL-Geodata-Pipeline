#!/usr/bin/env python3
"""
Quick smoke test for main pipeline - uses minimal data for fast validation
Tests: OSM extraction → DuckDB → GeoJSON export in under 3 minutes
"""

import sys
import time
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, 'src')

from etl.extract_osm import extract_osm_bulk
from etl.utils import ensure_directory
import geopandas as gpd
import duckdb

def quick_smoke_test():
    """Quick smoke test with minimal data"""
    start_time = time.time()
    
    print("🚀 Quick Pipeline Smoke Test")
    print("=" * 40)
    
    results = {
        "tests": {},
        "summary": {}
    }
    
    # Test 1: Quick OSM extraction (small area, 2 layers only)
    print("\n🔍 Test 1: OSM Extraction (minimal)")
    try:
        # Very small bbox around Stuttgart center
        bbox = (9.18, 48.77, 9.20, 48.78)  # ~2km x 1km area
        layers = ["roads", "amenities"]  # Only 2 layers for speed
        
        extract_osm_bulk(
            layers=layers,
            pbf_path=None,
            pbf_url=None,
            geofabrik_region="europe/germany/baden-wuerttemberg",
            download_dir=Path("data/raw"),
            staging_dir=Path("data/staging"),
            bbox=bbox
        )
        
        # Check outputs
        features_count = 0
        for layer in layers:
            parquet_file = Path(f"data/staging/osm_{layer}.parquet")
            if parquet_file.exists():
                gdf = gpd.read_parquet(parquet_file)
                features_count += len(gdf)
                print(f"   ✅ {layer}: {len(gdf)} features")
            else:
                print(f"   ❌ {layer}: file not created")
        
        results["tests"]["osm_extraction"] = {
            "status": "passed",
            "features": features_count,
            "layers": layers
        }
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results["tests"]["osm_extraction"] = {"status": "failed", "error": str(e)}
    
    # Test 2: DuckDB integration
    print("\n🔍 Test 2: DuckDB Integration")
    try:
        db_path = Path("data/duckdb/quick_test.duckdb")
        ensure_directory(db_path.parent)
        
        # Load one layer to DuckDB
        roads_file = Path("data/staging/osm_roads.parquet")
        if roads_file.exists():
            gdf = gpd.read_parquet(roads_file)
            
            # Simple DuckDB loading
            con = duckdb.connect(str(db_path))
            con.execute("INSTALL spatial")
            con.execute("LOAD spatial")
            con.execute("CREATE SCHEMA IF NOT EXISTS stg")
            
            # Convert geometry to WKB and load
            df_for_db = gdf.copy()
            df_for_db['geom_wkb'] = gdf.geometry.apply(lambda x: x.wkb)
            df_for_db = df_for_db.drop(columns=['geometry'])
            
            con.register('temp_roads', df_for_db)
            con.execute("""
                CREATE OR REPLACE TABLE stg.osm_roads AS
                SELECT *, ST_GeomFromWKB(geom_wkb) as geom
                FROM temp_roads
            """)
            
            # Test query
            count = con.execute("SELECT COUNT(*) FROM stg.osm_roads").fetchone()[0]
            con.close()
            
            print(f"   ✅ DuckDB: {count} roads loaded")
            results["tests"]["duckdb"] = {"status": "passed", "rows": count}
        else:
            print("   ⚠️ Skipped: no roads data")
            results["tests"]["duckdb"] = {"status": "skipped"}
            
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results["tests"]["duckdb"] = {"status": "failed", "error": str(e)}
    
    # Test 3: Quick export
    print("\n🔍 Test 3: GeoJSON Export")
    try:
        db_path = Path("data/duckdb/quick_test.duckdb")
        export_dir = Path("data/exports")
        ensure_directory(export_dir)
        
        if db_path.exists():
            con = duckdb.connect(str(db_path))
            con.execute("LOAD spatial")
            
            # Export small sample
            df = con.execute("SELECT *, ST_AsWKB(geom) AS wkb FROM stg.osm_roads LIMIT 50").fetch_df()
            con.close()
            
            if not df.empty:
                # Convert to GeoDataFrame
                gdf = gpd.GeoDataFrame(
                    df.drop(columns=["wkb"]), 
                    geometry=gpd.GeoSeries.from_wkb([bytes(x) for x in df["wkb"]]), 
                    crs="EPSG:4326"
                )
                
                # Export
                output_file = export_dir / "quick_test_roads.geojson"
                gdf.to_file(output_file, driver="GeoJSON")
                
                file_size_kb = output_file.stat().st_size / 1024
                print(f"   ✅ Export: {len(gdf)} features, {file_size_kb:.1f} KB")
                results["tests"]["export"] = {
                    "status": "passed", 
                    "features": len(gdf),
                    "file_size_kb": round(file_size_kb, 1)
                }
            else:
                print("   ⚠️ No data to export")
                results["tests"]["export"] = {"status": "skipped"}
        else:
            print("   ⚠️ Skipped: no DuckDB")
            results["tests"]["export"] = {"status": "skipped"}
            
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        results["tests"]["export"] = {"status": "failed", "error": str(e)}
    
    # Summary
    total_time = time.time() - start_time
    passed_tests = sum(1 for test in results["tests"].values() if test["status"] == "passed")
    total_tests = len(results["tests"])
    
    results["summary"] = {
        "total_time_seconds": round(total_time, 1),
        "passed_tests": passed_tests,
        "total_tests": total_tests,
        "success_rate": round(passed_tests / total_tests * 100, 1),
        "overall_status": "PASSED" if passed_tests == total_tests else "PARTIAL"
    }
    
    # Save results
    results_file = Path("data/staging/quick_smoke_test_results.json")
    ensure_directory(results_file.parent)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    print("\n" + "=" * 40)
    print("🎯 QUICK SMOKE TEST SUMMARY")
    print("=" * 40)
    status_emoji = "✅" if results["summary"]["overall_status"] == "PASSED" else "⚠️"
    print(f"Status: {status_emoji} {results['summary']['overall_status']}")
    print(f"Tests: {passed_tests}/{total_tests} passed ({results['summary']['success_rate']}%)")
    print(f"Time: {results['summary']['total_time_seconds']}s")
    
    # Individual test results
    for test_name, test_result in results["tests"].items():
        status = test_result["status"]
        emoji = "✅" if status == "passed" else "⚠️" if status == "skipped" else "❌"
        print(f"  {emoji} {test_name}: {status}")
    
    print(f"\n📁 Results saved: {results_file}")
    print("=" * 40)
    
    return results["summary"]["overall_status"] == "PASSED"

if __name__ == "__main__":
    try:
        success = quick_smoke_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        sys.exit(1)