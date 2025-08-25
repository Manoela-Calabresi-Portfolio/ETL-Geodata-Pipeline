#!/usr/bin/env python3
"""
Test choropleth plotting in the exact context of create_layer_png
"""

import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

def test_plotting_in_context():
    """Test choropleth plotting in the exact context of create_layer_png"""
    
    try:
        print("🔍 Testing choropleth plotting in context...")
        
        # 1. Load the data exactly as in create_layer_png
        kpis_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.parquet")
        kpis_gdf = gpd.read_parquet(kpis_file)
        
        # 2. Filter to green space ratio exactly as in load_all_layers
        green_data = kpis_gdf[kpis_gdf["kpi_name"] == "green_landuse_pct"].copy()
        print(f"✅ Green data loaded: {len(green_data)} features")
        
        # 3. Load city boundary exactly as in create_layer_png
        city_boundary_file = Path("../../data/stuttgart/processed/stadtbezirke.parquet")
        if city_boundary_file.exists():
            city_boundary = gpd.read_parquet(city_boundary_file)
            city_boundary = city_boundary.dissolve()
            city_bounds = city_boundary.total_bounds
            print(f"✅ City boundary loaded: {city_bounds}")
        else:
            print("❌ City boundary not found")
            return
        
        # 4. Create the exact same plot setup as create_layer_png
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 5. Add basemap first (as in the fixed version)
        try:
            import contextily as ctx
            ctx.add_basemap(ax, crs=green_data.crs.to_string(), source=ctx.providers.Carto.LightNoLabels)
            print("✅ Basemap added")
        except Exception as e:
            print(f"⚠️ Basemap skipped: {e}")
        
        # 6. Plot the choropleth data (exact same call as create_layer_png)
        print("🔍 Plotting choropleth data...")
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
        
        # 7. Check what was actually plotted
        print(f"🔍 Plot collections after choropleth: {len(ax.collections)}")
        for i, collection in enumerate(ax.collections):
            print(f"  Collection {i}: {type(collection)}, visible: {collection.get_visible()}")
        
        # 8. Set extent exactly as in create_layer_png
        ax.set_xlim(city_bounds[0], city_bounds[2])
        ax.set_ylim(city_bounds[1], city_bounds[3])
        print(f"✅ Extent set to: x({city_bounds[0]:.4f}, {city_bounds[2]:.4f}), y({city_bounds[1]:.4f}, {city_bounds[3]:.4f})")
        
        # 9. Check collections after setting extent
        print(f"🔍 Plot collections after setting extent: {len(ax.collections)}")
        
        # 10. Add city boundary outline
        city_boundary.boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.6)
        print("✅ City boundary outline added")
        
        # 11. Final collection check
        print(f"🔍 Final plot collections: {len(ax.collections)}")
        
        # 12. Set title and save
        ax.set_title("Test - Green Space Ratio (Full Context)")
        ax.axis('off')
        
        test_file = Path("test_green_space_full_context.png")
        plt.savefig(test_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Test plot saved: {test_file}")
        
        # 13. Check CRS compatibility
        print(f"\n🔍 CRS Check:")
        print(f"  Green data CRS: {green_data.crs}")
        print(f"  City boundary CRS: {city_boundary.crs}")
        print(f"  CRS match: {green_data.crs == city_boundary.crs}")
        
        # 14. Check data bounds vs city bounds
        green_bounds = green_data.total_bounds
        print(f"\n🔍 Bounds Check:")
        print(f"  Green data bounds: {green_bounds}")
        print(f"  City boundary bounds: {city_bounds}")
        print(f"  Green data within city bounds: {green_bounds[0] >= city_bounds[0] and green_bounds[2] <= city_bounds[2] and green_bounds[1] >= city_bounds[1] and green_bounds[3] <= city_bounds[3]}")
        
    except Exception as e:
        print(f"❌ Error in context test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_plotting_in_context()
