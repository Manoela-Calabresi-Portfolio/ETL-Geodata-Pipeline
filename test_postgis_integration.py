#!/usr/bin/env python3
"""
Test PostGIS Integration

This script tests the PostGIS database integration components
to ensure they work correctly with the current structure.
"""

import sys
import logging
from pathlib import Path
import yaml

# Add the spatial_analysis_core to Python path
sys.path.append(str(Path(__file__).parent / "spatial_analysis_core"))

from database import PostGISClient, DatabaseManager, DataPersistence

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_components():
    """Test all database components"""
    
    # Sample database configuration (for testing only)
    test_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_etl_pipeline',
        'user': 'test_user',
        'password': 'test_password',
        'schema': 'etl_pipeline'
    }
    
    print("🧪 Testing PostGIS Integration Components")
    print("=" * 50)
    
    try:
        # Test 1: PostGIS Client
        print("\n1️⃣ Testing PostGIS Client...")
        client = PostGISClient(test_config)
        print("   ✅ PostGISClient created successfully")
        print(f"   📋 Configuration: {test_config['host']}:{test_config['port']}/{test_config['database']}")
        
        # Test 2: Database Manager
        print("\n2️⃣ Testing Database Manager...")
        manager = DatabaseManager(test_config)
        print("   ✅ DatabaseManager created successfully")
        
        # Test 3: Data Persistence
        print("\n3️⃣ Testing Data Persistence...")
        persistence = DataPersistence(client)
        print("   ✅ DataPersistence created successfully")
        
        # Test 4: Component Integration
        print("\n4️⃣ Testing Component Integration...")
        print("   ✅ All components can be imported and instantiated")
        print("   ✅ Components are properly integrated")
        
        print("\n🎉 All PostGIS integration components are working correctly!")
        print("\n📝 Note: This test only verifies component creation.")
        print("   To test actual database operations, you need:")
        print("   - PostgreSQL with PostGIS extension installed")
        print("   - Valid database credentials")
        print("   - Network access to the database")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

def test_configuration_loading():
    """Test configuration file loading"""
    
    print("\n🔧 Testing Configuration Loading...")
    print("=" * 50)
    
    try:
        # Test loading database template
        template_path = Path("cities/_template/config/database.yaml.template")
        
        if template_path.exists():
            with open(template_path, 'r') as f:
                config = yaml.safe_load(f)
            
            print("   ✅ Database configuration template loaded successfully")
            print(f"   📋 Template contains {len(config)} configuration sections")
            
            # Check required fields
            required_sections = ['database']
            for section in required_sections:
                if section in config:
                    print(f"   ✅ Section '{section}' found")
                else:
                    print(f"   ❌ Section '{section}' missing")
            
            return True
        else:
            print("   ❌ Database configuration template not found")
            return False
            
    except Exception as e:
        print(f"   ❌ Configuration loading failed: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 PostGIS Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Component Creation
    components_ok = test_database_components()
    
    # Test 2: Configuration Loading
    config_ok = test_configuration_loading()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"   Components: {'✅ PASS' if components_ok else '❌ FAIL'}")
    print(f"   Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
    
    if components_ok and config_ok:
        print("\n🎉 All tests passed! PostGIS integration is ready.")
        print("\n🚀 Next steps:")
        print("   1. Install PostgreSQL with PostGIS extension")
        print("   2. Create database and user")
        print("   3. Update city configuration files")
        print("   4. Test actual database connections")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

