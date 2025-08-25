#!/usr/bin/env python3
"""
Test script to debug choropleth plotting issue
"""

import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

def test_choropleth_plotting():
    """Test if choropleth data can be plotted correctly"""
    
    # Load the normalized GeoParquet
    parquet_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.parquet")
    
    if not parquet_file.exists():
        print(f"❌ Parquet file not found: {parquet_file}")
        return
    
    try:
        print("🔍 Loading choropleth data...")
        kpis_gdf = gpd.read_parquet(parquet_file)
        
        print(f"✅ Loaded data: {len(kpis_gdf)} rows")
        print(f"✅ CRS: {kpis_gdf.crs}")
        print(f"✅ Columns: {list(kpis_gdf.columns)}")
        
        # Test with green space ratio specifically
        green_data = kpis_gdf[kpis_gdf["kpi_name"] == "green_landuse_pct"]
        print(f"\n🔍 Green space data:")
        print(f"  ✅ Rows: {len(green_data)}")
        print(f"  ✅ Value range: {green_data['value'].min():.2f} to {green_data['value'].max():.2f}")
        print(f"  ✅ Geometry type: {type(green_data.geometry.iloc[0])}")
        print(f"  ✅ CRS: {green_data.crs}")
        
        # Test plotting
        print(f"\n🔍 Testing plotting...")
        
        # Create a simple plot
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Try the exact same plotting call as in create_layer_png
        green_data.plot(
            column="value", 
            ax=ax, 
            cmap="Greens", 
            legend=True,
            alpha=0.8, 
            edgecolor="lightgrey", 
            linewidth=0.3,
            legend_kwds={"label": "Green Space Ratio (%)", "orientation": "vertical"}
        )
        
        ax.set_title("Test - Green Space Ratio Choropleth")
        ax.axis('off')
        
        # Save test plot
        test_file = Path("test_green_space_choropleth.png")
        plt.savefig(test_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"  ✅ Test plot created: {test_file}")
        
        # Check if the plot actually has data
        if len(ax.collections) > 0:
            print(f"  ✅ Plot collections found: {len(ax.collections)}")
            for i, collection in enumerate(ax.collections):
                print(f"    Collection {i}: {type(collection)}, visible: {collection.get_visible()}")
        else:
            print(f"  ❌ No plot collections found!")
        
        # Test with a different approach
        print(f"\n🔍 Testing alternative plotting...")
        fig2, ax2 = plt.subplots(figsize=(10, 8))
        
        # Try plotting without column specification first
        green_data.plot(ax=ax2, color="red", alpha=0.5)
        ax2.set_title("Test - Green Space (Solid Color)")
        ax2.axis('off')
        
        test_file2 = Path("test_green_space_solid.png")
        plt.savefig(test_file2, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"  ✅ Alternative test plot created: {test_file2}")
        
    except Exception as e:
        print(f"❌ Error testing choropleth plotting: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_choropleth_plotting()
