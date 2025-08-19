#!/usr/bin/env python3
"""
Prepare QGIS Data Script - Stuttgart Urban Analysis
Exports available data to GeoJSON for QGIS
"""

import duckdb
import geopandas as gpd
import pandas as pd
from shapely import wkt
import os
from pathlib import Path

def connect_duckdb():
    """Connects to DuckDB"""
    print("🦆 Connecting to DuckDB...")
    
    possible_paths = [
        "stuttgart_analysis.duckdb",
        "../stuttgart_analysis.duckdb",
        "../../stuttgart_analysis.duckdb",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Found: {path}")
            return duckdb.connect(str(path))
    
    print("❌ DuckDB file not found!")
    return None

def load_and_export_table(con, table_name, output_dir):
    """Loads table from DuckDB and exports to GeoJSON"""
    print(f"\n📥 Processing {table_name}...")
    
    try:
        # Load data
        df = con.execute(f"SELECT * FROM {table_name}").df()
        print(f"   📊 Loaded {len(df)} records")
        
        # Check if it has geometry
        if 'geometry' in df.columns:
            # Convert WKT to geometry
            df['geometry'] = df['geometry'].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
            
            # Export to GeoJSON
            output_file = os.path.join(output_dir, f"{table_name}.geojson")
            gdf.to_file(output_file, driver='GeoJSON')
            print(f"   ✅ Exported to: {output_file}")
            
            # Show sample data
            print(f"   📋 Columns: {list(gdf.columns)}")
            print(f"   🎯 Sample record: {gdf.iloc[0].to_dict()}")
            
            return gdf
        else:
            print(f"   ⚠️  No geometry column - exporting as CSV")
            output_file = os.path.join(output_dir, f"{table_name}.csv")
            df.to_csv(output_file, index=False)
            print(f"   ✅ Exported to: {output_file}")
            return df
            
    except Exception as e:
        print(f"   ❌ Error processing {table_name}: {e}")
        return None

def create_sample_landuse_data():
    """Creates sample landuse data for demonstration"""
    print("\n🏗️  Creating sample landuse data...")
    
    # Create sample polygons (simplified)
    from shapely.geometry import Polygon
    
    # Sample landuse types
    landuse_types = ['residential', 'commercial', 'industrial', 'green_space', 'transport']
    
    # Create sample geometries (simplified rectangles)
    sample_geometries = []
    for i in range(50):  # Create 50 sample polygons
        # Simple rectangle geometry
        coords = [
            (9.1 + (i * 0.01), 48.7 + (i * 0.01)),
            (9.1 + (i * 0.01), 48.7 + (i * 0.01) + 0.005),
            (9.1 + (i * 0.01) + 0.005, 48.7 + (i * 0.01) + 0.005),
            (9.1 + (i * 0.01) + 0.005, 48.7 + (i * 0.01)),
            (9.1 + (i * 0.01), 48.7 + (i * 0.01))
        ]
        
        polygon = Polygon(coords)
        sample_geometries.append(polygon)
    
    # Create GeoDataFrame
    sample_data = {
        'id': range(50),
        'landuse': [landuse_types[i % len(landuse_types)] for i in range(50)],
        'area_ha': [round(poly.area * 111000 * 111000 / 10000, 2) for poly in sample_geometries],  # Rough conversion
        'geometry': sample_geometries
    }
    
    gdf = gpd.GeoDataFrame(sample_data, geometry='geometry', crs='EPSG:4326')
    
    print(f"   ✅ Created {len(gdf)} sample landuse polygons")
    return gdf

def main():
    """Main function"""
    print("🚀 Prepare QGIS Data Script - Stuttgart Urban Analysis")
    print("=" * 60)
    
    # Create output directory
    output_dir = "qgis_export"
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    
    # Connect to DuckDB
    con = connect_duckdb()
    if not con:
        return
    
    try:
        # Get list of tables
        tables_result = con.execute("SHOW TABLES").fetchall()
        tables = [table[0] for table in tables_result]
        
        print(f"\n📋 Available tables: {tables}")
        
        # Export each table
        exported_data = {}
        
        for table_name in tables:
            if table_name not in ['pt_service_areas', 'pt_buffers_200m']:  # Skip very large tables
                data = load_and_export_table(con, table_name, output_dir)
                if data is not None:
                    exported_data[table_name] = data
        
        # Create sample landuse data
        sample_landuse = create_sample_landuse_data()
        landuse_file = os.path.join(output_dir, "sample_landuse.geojson")
        sample_landuse.to_file(landuse_file, driver='GeoJSON')
        print(f"   ✅ Exported sample landuse to: {landuse_file}")
        
        # Create summary
        print(f"\n📊 Export Summary:")
        print("=" * 50)
        print(f"📁 Output directory: {output_dir}")
        print(f"📋 Tables exported: {len(exported_data)}")
        
        for table_name, data in exported_data.items():
            if hasattr(data, 'geometry'):
                print(f"   🗺️  {table_name}: {len(data)} geometries")
            else:
                print(f"   📄 {table_name}: {len(data)} records")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Open QGIS")
        print(f"   2. Add layers from: {output_dir}")
        print(f"   3. Use sample_landuse.geojson for landuse visualization")
        
    except Exception as e:
        print(f"❌ Error during export: {e}")
    
    finally:
        con.close()
        print("\n✅ Connection closed!")

if __name__ == "__main__":
    main()

