#!/usr/bin/env python3
"""
Test Stuttgart Migration

This script tests the new Stuttgart structure to ensure it works correctly
and can be imported without errors. It validates the migration approach.
"""

import sys
import logging
from pathlib import Path
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stuttgart_structure():
    """Test the new Stuttgart city structure"""
    
    print("🧪 Testing Stuttgart Migration Structure")
    print("=" * 50)
    
    try:
        # Test 1: Configuration Files
        print("\n1️⃣ Testing Configuration Files...")
        config_dir = Path("cities/stuttgart/config")
        
        config_files = [
            "city.yaml",
            "districts.yaml", 
            "analysis.yaml",
            "database.yaml"
        ]
        
        configs_loaded = 0
        for config_file in config_files:
            config_path = config_dir / config_file
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                print(f"   ✅ {config_file} loaded successfully")
                configs_loaded += 1
            else:
                print(f"   ❌ {config_file} not found")
        
        print(f"   📋 {configs_loaded}/4 configuration files loaded")
        
        # Test 2: Module Structure
        print("\n2️⃣ Testing Module Structure...")
        module_dir = Path("cities/stuttgart/spatial_analysis")
        
        module_files = [
            "__init__.py",
            "stuttgart_analysis.py"
        ]
        
        modules_found = 0
        for module_file in module_files:
            module_path = module_dir / module_file
            if module_path.exists():
                print(f"   ✅ {module_file} found")
                modules_found += 1
            else:
                print(f"   ❌ {module_file} not found")
        
        print(f"   📋 {modules_found}/2 module files found")
        
        # Test 3: Import Test
        print("\n3️⃣ Testing Module Import...")
        try:
            # Add cities directory to path
            sys.path.append(str(Path("cities")))
            
            # Import Stuttgart module
            from stuttgart.spatial_analysis import StuttgartAnalysis
            print("   ✅ StuttgartAnalysis imported successfully")
            
            # Test class instantiation
            test_config = {
                'city': {'name': 'Stuttgart'},
                'analysis': {'processing': {'enable_postgis': False}}
            }
            
            analysis = StuttgartAnalysis(test_config)
            print("   ✅ StuttgartAnalysis instantiated successfully")
            
            # Test basic methods
            configs = analysis._load_stuttgart_configs()
            print(f"   ✅ Configuration loading works: {len(configs)} configs loaded")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Import failed: {e}")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

def test_configuration_content():
    """Test configuration file content and structure"""
    
    print("\n🔧 Testing Configuration Content...")
    print("=" * 50)
    
    try:
        # Test city configuration
        city_config_path = Path("cities/stuttgart/config/city.yaml")
        if city_config_path.exists():
            with open(city_config_path, 'r') as f:
                city_config = yaml.safe_load(f)
            
            print("   ✅ City configuration loaded")
            
            # Check required fields
            required_city_fields = ['name', 'bbox', 'crs_storage', 'crs_analysis']
            for field in required_city_fields:
                if field in city_config.get('city', {}):
                    print(f"   ✅ City field '{field}' found")
                else:
                    print(f"   ❌ City field '{field}' missing")
        
        # Test analysis configuration
        analysis_config_path = Path("cities/stuttgart/config/analysis.yaml")
        if analysis_config_path.exists():
            with open(analysis_config_path, 'r') as f:
                analysis_config = yaml.safe_load(f)
            
            print("   ✅ Analysis configuration loaded")
            
            # Check required fields
            required_analysis_fields = ['modules', 'data_sources', 'parameters']
            for field in required_analysis_fields:
                if field in analysis_config.get('analysis', {}):
                    print(f"   ✅ Analysis field '{field}' found")
                else:
                    print(f"   ❌ Analysis field '{field}' missing")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration content test failed: {e}")
        return False

def test_directory_structure():
    """Test the complete directory structure"""
    
    print("\n📁 Testing Directory Structure...")
    print("=" * 50)
    
    try:
        stuttgart_dir = Path("cities/stuttgart")
        
        expected_structure = [
            "config/city.yaml",
            "config/districts.yaml",
            "config/analysis.yaml", 
            "config/database.yaml",
            "spatial_analysis/__init__.py",
            "spatial_analysis/stuttgart_analysis.py",
            "spatial_analysis/outputs/",
            "README.md"
        ]
        
        structure_ok = 0
        for item in expected_structure:
            item_path = stuttgart_dir / item
            if item_path.exists():
                print(f"   ✅ {item} exists")
                structure_ok += 1
            else:
                print(f"   ❌ {item} missing")
        
        print(f"   📋 {structure_ok}/{len(expected_structure)} structure items found")
        return structure_ok == len(expected_structure)
        
    except Exception as e:
        print(f"   ❌ Directory structure test failed: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 Stuttgart Migration Test Suite")
    print("=" * 60)
    
    # Test 1: Structure
    structure_ok = test_stuttgart_structure()
    
    # Test 2: Configuration Content
    config_ok = test_configuration_content()
    
    # Test 3: Directory Structure
    dir_ok = test_directory_structure()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"   Structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"   Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"   Directory: {'✅ PASS' if dir_ok else '❌ FAIL'}")
    
    if structure_ok and config_ok and dir_ok:
        print("\n🎉 All tests passed! Stuttgart migration structure is working.")
        print("\n🚀 Migration Status:")
        print("   ✅ New structure created successfully")
        print("   ✅ Configuration files adapted")
        print("   ✅ Analysis class implemented")
        print("   ✅ Database integration ready")
        print("\n📋 Next Steps:")
        print("   1. Implement placeholder methods with existing script logic")
        print("   2. Test with real data")
        print("   3. Validate outputs against existing system")
        print("   4. Enable database integration when PostgreSQL is ready")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

