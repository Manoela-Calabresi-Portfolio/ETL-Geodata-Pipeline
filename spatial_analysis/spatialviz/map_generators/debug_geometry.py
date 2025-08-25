#!/usr/bin/env python3
"""
Quick debug script to check geometry column status
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path

def debug_geometry():
    """Check if geometry column is properly formatted"""
    
    parquet_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.parquet")
    
    if not parquet_file.exists():
        print(f"❌ Parquet file not found: {parquet_file}")
        return
    
    try:
        print("🔍 Loading GeoParquet...")
        gdf = gpd.read_parquet(parquet_file)
        
        print(f"✅ Loaded data: {len(gdf)} rows")
        print(f"✅ CRS: {gdf.crs}")
        print(f"✅ Columns: {list(gdf.columns)}")
        print(f"\n🔍 Data types:")
        print(gdf.dtypes)
        
        print(f"\n🔍 Geometry column check:")
        print(f"  Geometry column type: {type(gdf.geometry)}")
        print(f"  Geometry column dtype: {gdf.geometry.dtype}")
        print(f"  First geometry: {gdf.geometry.iloc[0]}")
        print(f"  Geometry type: {type(gdf.geometry.iloc[0])}")
        
        print(f"\n🔍 Sample data:")
        print(gdf.head())
        
        print(f"\n🔍 Geometry validation:")
        valid_count = gdf.geometry.is_valid.sum()
        total_count = len(gdf)
        print(f"  Valid geometries: {valid_count}/{total_count}")
        
        if valid_count < total_count:
            print(f"  ❌ {total_count - valid_count} invalid geometries found!")
        
        # Check if it's actually a GeoDataFrame
        print(f"\n🔍 GeoDataFrame check:")
        print(f"  Is GeoDataFrame: {isinstance(gdf, gpd.GeoDataFrame)}")
        print(f"  Has geometry accessor: {hasattr(gdf, 'geometry')}")
        
    except Exception as e:
        print(f"❌ Error debugging geometry: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_geometry()
