#!/usr/bin/env python3
"""
Debug script to examine the original CSV data and determine its coordinate system
"""

import pandas as pd
import geopandas as gpd
from shapely import wkt
from pathlib import Path

def debug_original_csv():
    """Examine the original CSV to understand its coordinate system"""
    
    csv_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.csv")
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    try:
        print("🔍 Examining original CSV data...")
        
        # Read CSV
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded CSV: {len(df)} districts")
        print(f"✅ Columns: {list(df.columns)}")
        
        # Look at the first few geometry strings
        print(f"\n🔍 First few geometry strings:")
        for i in range(min(3, len(df))):
            geom_str = df['geometry'].iloc[i]
            print(f"  District {i}: {geom_str[:100]}...")
        
        # Convert to shapely and check bounds
        print(f"\n🔍 Converting to shapely objects...")
        df['geometry'] = df['geometry'].apply(wkt.loads)
        
        # Create temporary GeoDataFrame without CRS
        temp_gdf = gpd.GeoDataFrame(df, geometry='geometry')
        bounds = temp_gdf.total_bounds
        print(f"✅ Raw bounds: {bounds}")
        
        # Check what coordinate system this might be
        print(f"\n🔍 Coordinate system analysis:")
        
        # Stuttgart area in different coordinate systems:
        # WGS84 (EPSG:4326): [9.0, 48.6, 9.4, 48.9]
        # EPSG:25832: [400000, 5400000, 450000, 5450000]
        # EPSG:3857 (Web Mercator): [1000000, 6200000, 1050000, 6250000]
        
        if bounds[0] >= 9.0 and bounds[0] <= 9.4 and bounds[1] >= 48.6 and bounds[1] <= 48.9:
            print("  ✅ Appears to be WGS84 (EPSG:4326)")
            crs_guess = "EPSG:4326"
        elif bounds[0] >= 400000 and bounds[0] <= 450000 and bounds[1] >= 5400000 and bounds[1] <= 5450000:
            print("  ✅ Appears to be EPSG:25832")
            crs_guess = "EPSG:25832"
        elif bounds[0] >= 1000000 and bounds[0] <= 1050000 and bounds[1] >= 6200000 and bounds[1] <= 6250000:
            print("  ✅ Appears to be Web Mercator (EPSG:3857)")
            crs_guess = "EPSG:3857"
        else:
            print(f"  ❓ Unknown coordinate system")
            crs_guess = None
        
        # Test conversion to WGS84
        if crs_guess and crs_guess != "EPSG:4326":
            print(f"\n🔍 Testing conversion to WGS84...")
            temp_gdf.crs = crs_guess
            converted = temp_gdf.to_crs(4326)
            converted_bounds = converted.total_bounds
            print(f"  Converted bounds: {converted_bounds}")
            
            # Check if converted coordinates are in Stuttgart area
            if converted_bounds[0] >= 9.0 and converted_bounds[0] <= 9.4 and converted_bounds[1] >= 48.6 and converted_bounds[1] <= 48.9:
                print("  ✅ Conversion successful - coordinates now in Stuttgart area!")
            else:
                print(f"  ❌ Conversion failed - coordinates still not in Stuttgart area")
        
        # Also check if there might be a scale factor issue
        print(f"\n🔍 Scale analysis:")
        x_range = bounds[2] - bounds[0]
        y_range = bounds[3] - bounds[1]
        print(f"  X range: {x_range:.2f}")
        print(f"  Y range: {y_range:.2f}")
        
        # Stuttgart should be roughly 0.4 degrees wide and 0.3 degrees tall
        if x_range > 1000 and y_range > 1000:
            print("  ⚠️ Very large ranges - might need to divide by a scale factor")
        elif x_range < 1 and y_range < 1:
            print("  ⚠️ Very small ranges - might need to multiply by a scale factor")
        
    except Exception as e:
        print(f"❌ Error debugging CSV: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_original_csv()
