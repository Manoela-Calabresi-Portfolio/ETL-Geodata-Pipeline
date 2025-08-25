#!/usr/bin/env python3
"""
Debug script to check choropleth data structure
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path

def debug_choropleth_data():
    """Debug the choropleth data to see why PNG maps are empty"""
    
    # Load the normalized GeoParquet
    parquet_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.parquet")
    
    if not parquet_file.exists():
        print(f"❌ Parquet file not found: {parquet_file}")
        return
    
    try:
        print("🔍 Loading choropleth data...")
        gdf = gpd.read_parquet(parquet_file)
        
        print(f"✅ Loaded data: {len(gdf)} rows")
        print(f"✅ CRS: {gdf.crs}")
        print(f"✅ Columns: {list(gdf.columns)}")
        print(f"✅ Data types:\n{gdf.dtypes}")
        
        # Check the walkability score data specifically
        walkability_data = gdf[gdf["kpi_name"] == "cycle_infra_density"]
        print(f"\n🔍 Walkability data (cycle_infra_density):")
        print(f"  ✅ Rows: {len(walkability_data)}")
        print(f"  ✅ Value range: {walkability_data['value'].min():.2f} to {walkability_data['value'].max():.2f}")
        print(f"  ✅ Value data type: {walkability_data['value'].dtype}")
        print(f"  ✅ Has NaN values: {walkability_data['value'].isna().any()}")
        
        # Check geometry
        print(f"\n🔍 Geometry check:")
        print(f"  ✅ Geometry column exists: {'geometry' in gdf.columns}")
        print(f"  ✅ Geometry type: {type(gdf.geometry.iloc[0])}")
        print(f"  ✅ CRS matches: {gdf.crs == 'EPSG:4326'}")
        
        # Check if we can plot this data
        print(f"\n🔍 Testing plotting...")
        try:
            import matplotlib.pyplot as plt
            
            # Create a simple test plot
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Try to plot the walkability data
            walkability_data.plot(
                column="value", 
                ax=ax, 
                cmap="YlGnBu", 
                legend=True,
                alpha=0.8
            )
            
            ax.set_title("Test Plot - Walkability Score")
            ax.axis('off')
            
            # Save test plot
            test_file = Path("test_walkability_plot.png")
            plt.savefig(test_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"  ✅ Test plot created: {test_file}")
            
        except Exception as e:
            print(f"  ❌ Plotting failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Check the actual data values
        print(f"\n🔍 Sample data values:")
        for kpi in gdf["kpi_name"].unique():
            kpi_data = gdf[gdf["kpi_name"] == kpi]
            print(f"  {kpi}: {len(kpi_data)} rows, values: {kpi_data['value'].min():.2f} to {kpi_data['value'].max():.2f}")
        
    except Exception as e:
        print(f"❌ Error debugging data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_choropleth_data()
