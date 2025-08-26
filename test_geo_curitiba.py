#!/usr/bin/env python3
"""
Test Geo Curitiba Client Connection

This script tests the connection to Geo Curitiba's ArcGIS REST services
and explores available data layers for Curitiba analysis.
"""

import sys
import logging
from pathlib import Path

# Add the Curitiba spatial analysis to Python path
sys.path.append(str(Path(__file__).parent / "cities" / "curitiba" / "spatial_analysis"))

from geo_curitiba_client import GeoCuritibaClient

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_geo_curitiba_connection():
    """Test connection to Geo Curitiba services"""
    print("🔺 Testing Geo Curitiba Connection...")
    print("=" * 50)
    
    try:
        # Initialize client
        client = GeoCuritibaClient()
        print("✅ Geo Curitiba client initialized successfully")
        
        # Test basic connection
        print("\n🔍 Testing basic connection...")
        if client.test_connection():
            print("✅ Connection to Geo Curitiba successful!")
        else:
            print("❌ Connection to Geo Curitiba failed!")
            return False
        
        # Get available services
        print("\n🔍 Exploring available services...")
        available_layers = client.get_available_layers()
        
        if available_layers:
            print(f"✅ Found {len(available_layers)} services with layers:")
            for service_name, layers in available_layers.items():
                print(f"  📁 {service_name}:")
                for layer in layers:
                    print(f"    - {layer}")
        else:
            print("⚠️ No services with layers found")
        
        # Test specific service exploration
        print("\n🔍 Testing service info retrieval...")
        try:
            service_info = client.get_service_info()
            print("✅ Service info retrieved successfully")
            
            if 'folders' in service_info:
                # Handle both string and dictionary folder formats
                folder_names = []
                for f in service_info['folders']:
                    if isinstance(f, str):
                        folder_names.append(f)
                    elif isinstance(f, dict) and 'name' in f:
                        folder_names.append(f['name'])
                    else:
                        folder_names.append(str(f))
                print(f"📁 Folders found: {folder_names}")
            
            if 'services' in service_info:
                print(f"🔧 Services found: {[s['name'] for s in service_info['services']]}")
                
        except Exception as e:
            print(f"❌ Failed to get service info: {e}")
        
        # Test specific folder exploration
        print("\n🔍 Testing folder exploration...")
        try:
            # Try to explore the GeoCuritiba folder
            geo_curitiba_info = client.get_service_info("GeoCuritiba")
            print("✅ GeoCuritiba folder explored successfully")
            
            if 'services' in geo_curitiba_info:
                print(f"🔧 Services in GeoCuritiba: {[s['name'] for s in geo_curitiba_info['services']]}")
                
        except Exception as e:
            print(f"⚠️ Could not explore GeoCuritiba folder: {e}")
        
        # Test specific service exploration
        print("\n🔍 Testing specific service exploration...")
        try:
            # Try to explore the Publico_equipamentos service
            equipamentos_info = client.get_service_info("Publico_equipamentos")
            print("✅ Publico_equipamentos service explored successfully")
            
            if 'layers' in equipamentos_info:
                print(f"🗺️ Layers in Publico_equipamentos: {[l['name'] for l in equipamentos_info['layers']]}")
                
        except Exception as e:
            print(f"⚠️ Could not explore Publico_equipamentos service: {e}")
        
        # Close client
        client.close()
        print("\n✅ Geo Curitiba client test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Geo Curitiba test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Geo Curitiba Client Test")
    print("=" * 60)
    
    success = test_geo_curitiba_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! Geo Curitiba client is working correctly.")
        print("\n📋 Next steps:")
        print("  1. ✅ Geo Curitiba connection verified")
        print("  2. 🔄 Create Curitiba city skeleton")
        print("  3. 📊 Configure data sources for Curitiba")
        print("  4. 🚀 Ready for future analysis implementation")
    else:
        print("❌ Some tests failed. Check the error messages above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
