#!/usr/bin/env python3
"""
Smoke Test for Stuttgart Mobility & Walkability Analysis Pipeline
Tests basic structure and configuration loading
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_config_loading():
    """Test configuration loading"""
    try:
        from config.analysis_config import load_config
        config = load_config()
        logger.info("✅ Configuration loading: SUCCESS")
        logger.info(f"Study area: {config.get('study_area', {}).get('name', 'Unknown')}")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration loading: FAILED - {e}")
        return False

def test_directory_structure():
    """Test directory structure"""
    try:
        # Check required directories exist
        required_dirs = [
            'config',
            'scripts',
            'data',
            'areas',
            'spatialviz'
        ]
        
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                logger.info(f"✅ Directory {dir_name}: EXISTS")
            else:
                logger.error(f"❌ Directory {dir_name}: MISSING")
                return False
        
        # Check test data exists
        test_data_path = Path("../test_data")
        if test_data_path.exists():
            logger.info("✅ Test data directory: EXISTS")
            
            # Check test data files
            test_files = [
                'raw/stuttgart_districts.geojson',
                'staging/osm_roads.parquet',
                'staging/osm_amenities.parquet',
                'staging/osm_pt_stops.parquet'
            ]
            
            for file_path in test_files:
                full_path = test_data_path / file_path
                if full_path.exists():
                    logger.info(f"✅ Test file {file_path}: EXISTS")
                else:
                    logger.warning(f"⚠️ Test file {file_path}: MISSING")
        else:
            logger.warning("⚠️ Test data directory: MISSING")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Directory structure test: FAILED - {e}")
        return False

def test_imports():
    """Test basic imports"""
    try:
        # Test basic Python packages
        import pandas as pd
        import geopandas as gpd
        import yaml
        logger.info("✅ Basic imports: SUCCESS")
        return True
    except ImportError as e:
        logger.error(f"❌ Basic imports: FAILED - {e}")
        return False

def main():
    """Main smoke test function"""
    parser = argparse.ArgumentParser(description='Smoke Test for Stuttgart Analysis Pipeline')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("🚀 Starting Smoke Test for Stuttgart Analysis Pipeline")
    logger.info("=" * 60)
    
    # Run tests
    tests = [
        ("Configuration Loading", test_config_loading),
        ("Directory Structure", test_directory_structure),
        ("Basic Imports", test_imports)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        logger.info("-" * 40)
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 SMOKE TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Pipeline structure is ready.")
        return 0
    else:
        logger.error("💥 Some tests failed. Check the pipeline structure.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
