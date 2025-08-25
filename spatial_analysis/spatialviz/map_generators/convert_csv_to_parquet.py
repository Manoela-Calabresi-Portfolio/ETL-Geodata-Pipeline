#!/usr/bin/env python3
"""
Convert existing stuttgart_kpis.csv to normalized GeoParquet format
"""

import pandas as pd
import geopandas as gpd
from shapely import wkt
from pathlib import Path

def convert_csv_to_normalized_parquet():
    """Convert CSV to normalized GeoParquet format"""
    
    # Input CSV file
    csv_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.csv")
    
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    try:
        print("🔺 Loading CSV data...")
        # Read CSV
        df = pd.read_csv(csv_file)
        print(f"  ✅ Loaded CSV: {len(df)} districts")
        
        # Convert WKT geometry to shapely objects
        print("🔺 Converting geometry...")
        df['geometry'] = df['geometry'].apply(wkt.loads)
        
        # Check the actual bounds of the data to determine the correct CRS
        print("🔺 Detecting CRS from data bounds...")
        temp_gdf = gpd.GeoDataFrame(df, geometry='geometry')
        
        # Check if data is already in WGS84 (EPSG:4326) coordinates
        bounds = temp_gdf.total_bounds
        print(f"  Data bounds: {bounds}")
        
        # If coordinates are around Stuttgart (9.0-9.4, 48.6-48.9), it's already WGS84
        # If coordinates are around (400000-450000, 5400000-5450000), it's EPSG:25832
        # If coordinates are around (1000000-1050000, 6200000-6250000), it's EPSG:3857 (Web Mercator)
        if bounds[0] >= 9.0 and bounds[0] <= 9.4 and bounds[1] >= 48.6 and bounds[1] <= 48.9:
            print("  ✅ Data appears to be already in WGS84 (EPSG:4326)")
            gdf = temp_gdf.copy()
            gdf.crs = 'EPSG:4326'
        elif bounds[0] >= 400000 and bounds[0] <= 450000 and bounds[1] >= 5400000 and bounds[1] <= 5450000:
            print("  ✅ Data appears to be in EPSG:25832, converting to WGS84...")
            gdf = temp_gdf.copy()
            gdf.crs = 'EPSG:25832'
            gdf = gdf.to_crs(4326)
        elif bounds[0] >= 1000000 and bounds[0] <= 1050000 and bounds[1] >= 6200000 and bounds[1] <= 6250000:
            print("  ✅ Data appears to be in EPSG:3857 (Web Mercator), converting to WGS84...")
            gdf = temp_gdf.copy()
            gdf.crs = 'EPSG:3857'
            gdf = gdf.to_crs(4326)
        else:
            print(f"  ⚠️ Unknown coordinate system, assuming EPSG:3857 and converting...")
            gdf = temp_gdf.copy()
            gdf.crs = 'EPSG:3857'
            gdf = gdf.to_crs(4326)
        
        print(f"  ✅ Final GeoDataFrame CRS: {gdf.crs}")
        print(f"  Final bounds: {gdf.total_bounds}")
        
        # Verify the coordinates are now in Stuttgart area
        final_bounds = gdf.total_bounds
        if final_bounds[0] >= 9.0 and final_bounds[0] <= 9.4 and final_bounds[1] >= 48.6 and final_bounds[1] <= 48.9:
            print("  ✅ Coordinates are now in Stuttgart area (WGS84)")
        else:
            print(f"  ⚠️ Warning: Coordinates still not in Stuttgart area: {final_bounds}")
        
        # No need to convert again since we already handled it above
        gdf_wgs84 = gdf
        
        # Define KPI columns to export
        kpi_columns = [
            "amenities_count", 
            "area_km2", 
            "green_landuse_pct", 
            "service_density", 
            "pt_stop_density", 
            "cycle_infra_density", 
            "population_density"
        ]
        
        # Filter to only include districts with geometry and KPI data
        valid_districts = gdf_wgs84[
            gdf_wgs84['geometry'].notna() & 
            gdf_wgs84['STADTBEZIRKNAME'].notna()
        ].copy()
        
        if valid_districts.empty:
            print("❌ No valid districts with geometry found")
            return
        
        print(f"  ✅ Valid districts: {len(valid_districts)}")
        
        # Melt KPI columns into long format
        id_vars = ["STADTBEZIRKNAME", "geometry"]
        value_vars = [col for col in kpi_columns if col in valid_districts.columns]
        
        if not value_vars:
            print("❌ No KPI columns found in data")
            return
        
        print(f"  ✅ KPI columns: {value_vars}")
        
        # Create long format DataFrame
        print("🔺 Creating long format...")
        kpis_long = valid_districts.melt(
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="kpi_name",
            value_name="value"
        )
        
        # Convert back to GeoDataFrame
        kpis_long_gdf = gpd.GeoDataFrame(kpis_long, geometry="geometry", crs=4326)
        
        # Create output directory
        out_dir = Path("../outputs/stuttgart_analysis")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as GeoParquet
        parquet_path = out_dir / "stuttgart_kpis.parquet"
        kpis_long_gdf.to_parquet(parquet_path, index=False)
        
        # Optional: Save as GeoJSON for debugging
        geojson_path = out_dir / "stuttgart_kpis.geojson"
        kpis_long_gdf.to_file(geojson_path, driver="GeoJSON")
        
        # Print diagnostic information
        print(f"✅ Exported normalized KPIs to {parquet_path}")
        print(f"✅ Exported GeoJSON for debugging to {geojson_path}")
        print(f"✅ Total rows: {len(kpis_long_gdf)}")
        print(f"✅ Districts: {len(valid_districts)}")
        print(f"✅ KPIs per district: {len(value_vars)}")
        
        # Print value ranges for each KPI
        print("\n📊 KPI Value Ranges:")
        for kpi in value_vars:
            kpi_data = kpis_long_gdf[kpis_long_gdf["kpi_name"] == kpi]["value"]
            if not kpi_data.empty:
                vmin, vmax = kpi_data.min(), kpi_data.max()
                print(f"  {kpi}: min={vmin:.2f}, max={vmax:.2f}")
        
        print(f"\n🎯 Success! You can now use the normalized GeoParquet in your Kepler dashboard.")
        
    except Exception as e:
        print(f"❌ Error converting CSV to Parquet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    convert_csv_to_normalized_parquet()
