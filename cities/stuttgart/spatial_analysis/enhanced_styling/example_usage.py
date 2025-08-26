#!/usr/bin/env python3
"""
Example Usage of Enhanced Style Engine
Shows how to create maps exactly like the reference images
"""

import sys
from pathlib import Path
import geopandas as gpd

# Add the enhanced styling to path
sys.path.append(str(Path(__file__).parent))

from enhanced_style_engine import (
    create_essentials_h3_map,
    create_service_diversity_h3_map,
    create_walkability_score_map,
    create_enhanced_dashboard,
    create_overview_landuse_map
)

def main():
    """Example of using the enhanced style engine"""
    
    print("🎨 Enhanced Style Engine Example Usage")
    print("=" * 50)
    
    # Example 1: Create H3 Essentials Map (like 05_access_essentials_h3.png)
    print("\n1️⃣ Creating H3 Essentials Map...")
    try:
        # Load your H3 data (this is an example - you'll need real data)
        # h3_data = gpd.read_file("../data/h3_essentials.geojson")
        # create_essentials_h3_map(
        #     h3_data, 
        #     "../outputs/enhanced_maps/05_access_essentials_h3.png"
        # )
        print("   ✅ H3 Essentials map would be created here")
    except Exception as e:
        print(f"   ⚠️ Example skipped: {e}")
    
    # Example 2: Create H3 Service Diversity Map (like 07_service_diversity_h3.png)
    print("\n2️⃣ Creating H3 Service Diversity Map...")
    try:
        # Load your H3 data (this is an example - you'll need real data)
        # h3_data = gpd.read_file("../data/h3_service_diversity.geojson")
        # create_service_diversity_h3_map(
        #     h3_data, 
        #     "../outputs/enhanced_maps/07_service_diversity_h3.png"
        # )
        print("   ✅ H3 Service Diversity map would be created here")
    except Exception as e:
        print(f"   ⚠️ Example skipped: {e}")
    
    # Example 3: Create Walkability Score Map (like stuttgart_walkability_score_enhanced.png)
    print("\n3️⃣ Creating Walkability Score Map...")
    try:
        # Load your districts data (this is an example - you'll need real data)
        # districts_data = gpd.read_file("../data/districts_with_population.geojson")
        # create_walkability_score_map(
        #     districts_data, 
        #     "../outputs/enhanced_maps/stuttgart_walkability_score_enhanced.png"
        # )
        print("   ✅ Walkability Score map would be created here")
    except Exception as e:
        print(f"   ⚠️ Example skipped: {e}")
    
    # Example 4: Create Enhanced Dashboard (like stuttgart_enhanced_dashboard.png)
    print("\n4️⃣ Creating Enhanced Dashboard...")
    try:
        # Load your districts data (this is an example - you'll need real data)
        # districts_data = gpd.read_file("../data/districts_with_population.geojson")
        # create_enhanced_dashboard(
        #     districts_data, 
        #     "../outputs/enhanced_maps/stuttgart_enhanced_dashboard.png"
        # )
        print("   ✅ Enhanced Dashboard would be created here")
    except Exception as e:
        print(f"   ⚠️ Example skipped: {e}")
    
    # Example 5: Create Overview Landuse Map (like 01_overview_landuse_roads_pt.png)
    print("\n5️⃣ Creating Overview Landuse Map...")
    try:
        # Load your data (this is an example - you'll need real data)
        # landuse_data = gpd.read_file("../data/landuse_categorized.geojson")
        # roads_data = gpd.read_file("../data/roads_categorized.geojson")
        # pt_stops_data = gpd.read_file("../data/pt_stops_categorized.geojson")
        # city_boundary_data = gpd.read_file("../data/city_boundary.geojson")
        # create_overview_landuse_map(
        #     landuse_data, roads_data, pt_stops_data, city_boundary_data,
        #     "../outputs/enhanced_maps/01_overview_landuse_roads_pt.png"
        # )
        print("   ✅ Overview Landuse map would be created here")
    except Exception as e:
        print(f"   ⚠️ Example skipped: {e}")
    
    print("\n🎯 To use with real data:")
    print("   1. Load your GeoDataFrames")
    print("   2. Call the appropriate function")
    print("   3. Maps will be created with exact reference styling!")
    
    print("\n📁 Output directory: ../outputs/enhanced_maps/")
    print("🎨 All maps will match your reference images exactly!")

if __name__ == "__main__":
    main()
