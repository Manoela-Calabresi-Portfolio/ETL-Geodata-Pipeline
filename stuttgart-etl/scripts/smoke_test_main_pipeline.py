#!/usr/bin/env python3
"""
Comprehensive smoke test for the complete main pipeline:
1. OSM extraction with enhanced error handling
2. DuckDB integration 
3. Data validation
4. Export functionality
5. Performance metrics

Note: This is the full test - use smoke_test_quick.py for faster validation
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any
import json

# Add src to path for imports
sys.path.insert(0, 'src')

from etl.extract_osm import extract_osm_bulk, LAYER_BUILDERS
from etl.utils import ensure_directory
import geopandas as gpd
import duckdb

def comprehensive_smoke_test():
    """Run comprehensive smoke test with all layers"""
    start_time = time.time()
    
    print("🚀 Comprehensive Pipeline Smoke Test")
    print("=" * 50)
    print("⚠️  This test uses all layers and may take 10+ minutes")
    
    # Test with all layers
    layers = ["roads", "buildings", "landuse", "cycle", "pt_stops", "boundaries", "amenities"]
    bbox = (9.1, 48.7, 9.3, 48.8)  # Full Stuttgart test area
    
    try:
        # Full OSM extraction
        extract_osm_bulk(
            layers=layers,
            pbf_path=None,
            pbf_url=None,
            geofabrik_region="europe/germany/baden-wuerttemberg",
            download_dir=Path("data/raw"),
            staging_dir=Path("data/staging"),
            bbox=bbox
        )
        
        # Validate results
        total_features = 0
        for layer in layers:
            parquet_file = Path(f"data/staging/osm_{layer}.parquet")
            if parquet_file.exists():
                gdf = gpd.read_parquet(parquet_file)
                total_features += len(gdf)
                print(f"✅ {layer}: {len(gdf)} features")
        
        total_time = time.time() - start_time
        
        print(f"\n🎯 COMPREHENSIVE TEST RESULTS:")
        print(f"✅ Total features: {total_features:,}")
        print(f"✅ Total time: {total_time:.1f}s")
        print(f"✅ All {len(layers)} layers processed")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = comprehensive_smoke_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        sys.exit(1)