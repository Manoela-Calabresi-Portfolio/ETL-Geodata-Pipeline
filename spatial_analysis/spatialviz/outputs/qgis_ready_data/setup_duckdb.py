#!/usr/bin/env python3
"""
Setup DuckDB for Seamless QGIS Workflow - Stuttgart Urban Analysis
Converts existing GeoJSON data to DuckDB for real-time updates
"""

import duckdb
import geopandas as gpd
import pandas as pd
from pathlib import Path
import os
import json
from shapely import wkt

def setup_duckdb():
    """Setup DuckDB database with spatial data"""
    print("🦆 Setting up DuckDB for seamless QGIS workflow...")
    print("=" * 60)
    
    # Connect to DuckDB (creates file if doesn't exist)
    db_path = "stuttgart_analysis.duckdb"
    con = duckdb.connect(db_path)
    
    print(f"✅ Connected to: {db_path}")
    
    # Load spatial extension
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    print("✅ Spatial extension loaded")
    
    return con

def load_data_to_duckdb(con):
    """Load all existing data into DuckDB using native DuckDB spatial functions"""
    print("\n📊 Loading data into DuckDB...")
    
    # Load districts with population
    print("🏘️ Loading districts...")
    districts = gpd.read_file("01_districts_population.geojson")
    
    # Convert to WKT for DuckDB
    districts['geometry_wkt'] = districts.geometry.apply(lambda x: wkt.dumps(x))
    
    # Create table and insert data
    con.execute("""
        CREATE TABLE IF NOT EXISTS districts (
            id INTEGER,
            name VARCHAR,
            pop INTEGER,
            pop_density DOUBLE,
            geometry_wkt VARCHAR
        )
    """)
    
    # Insert data
    for idx, row in districts.iterrows():
        con.execute("""
            INSERT INTO districts (id, name, pop, pop_density, geometry_wkt)
            VALUES (?, ?, ?, ?, ?)
        """, [idx, row.get('name', f'District_{idx}'), row.get('pop', 0), 
              row.get('pop_density', 0), row['geometry_wkt']])
    
    print(f"  ✅ Loaded {len(districts)} districts")
    
    # Load landuse
    print("🌳 Loading landuse...")
    landuse = gpd.read_file("02_landuse_categorized.geojson")
    landuse['geometry_wkt'] = landuse.geometry.apply(lambda x: wkt.dumps(x))
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS landuse (
            id INTEGER,
            landuse VARCHAR,
            geometry_wkt VARCHAR
        )
    """)
    
    for idx, row in landuse.iterrows():
        con.execute("""
            INSERT INTO landuse (id, landuse, geometry_wkt)
            VALUES (?, ?, ?)
        """, [idx, row.get('landuse', 'unknown'), row['geometry_wkt']])
    
    print(f"  ✅ Loaded {len(landuse)} landuse areas")
    
    # Load roads
    print("🛣️ Loading roads...")
    roads = gpd.read_file("03_roads_categorized.geojson")
    roads['geometry_wkt'] = roads.geometry.apply(lambda x: wkt.dumps(x))
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS roads (
            id INTEGER,
            road_type VARCHAR,
            geometry_wkt VARCHAR
        )
    """)
    
    for idx, row in roads.iterrows():
        con.execute("""
            INSERT INTO roads (id, road_type, geometry_wkt)
            VALUES (?, ?, ?)
        """, [idx, row.get('road_type', 'unknown'), row['geometry_wkt']])
    
    print(f"  ✅ Loaded {len(roads)} road segments")
    
    # Load PT stops
    print("🚌 Loading PT stops...")
    pt_stops = gpd.read_file("04_pt_stops_categorized.geojson")
    pt_stops['geometry_wkt'] = pt_stops.geometry.apply(lambda x: wkt.dumps(x))
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS pt_stops (
            id INTEGER,
            stop_type VARCHAR,
            geometry_wkt VARCHAR
        )
    """)
    
    for idx, row in pt_stops.iterrows():
        con.execute("""
            INSERT INTO pt_stops (id, stop_type, geometry_wkt)
            VALUES (?, ?, ?)
        """, [idx, row.get('stop_type', 'unknown'), row['geometry_wkt']])
    
    print(f"  ✅ Loaded {len(pt_stops)} PT stops")
    
    # Load city boundary
    print("🏙️ Loading city boundary...")
    city_boundary = gpd.read_file("05_city_boundary.geojson")
    city_boundary['geometry_wkt'] = city_boundary.geometry.apply(lambda x: wkt.dumps(x))
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS city_boundary (
            id INTEGER,
            geometry_wkt VARCHAR
        )
    """)
    
    for idx, row in city_boundary.iterrows():
        con.execute("""
            INSERT INTO city_boundary (id, geometry_wkt)
            VALUES (?, ?)
        """, [idx, row['geometry_wkt']])
    
    print(f"  ✅ Loaded city boundary")

def demonstrate_workflow(con):
    """Demonstrate the seamless workflow using Python for spatial analysis"""
    print("\n🚀 Demonstrating Seamless Workflow...")
    print("=" * 60)
    
    # Example 1: Create buffer analysis using Python
    print("📐 Example 1: Creating 500m buffer around districts...")
    
    # Read districts from DuckDB
    districts_data = con.execute("SELECT * FROM districts").fetchall()
    districts_df = pd.DataFrame(districts_data, columns=['id', 'name', 'pop', 'pop_density', 'geometry_wkt'])
    
    # Convert WKT back to GeoDataFrame for spatial operations
    districts_gdf = gpd.GeoDataFrame(
        districts_df.drop('geometry_wkt', axis=1),
        geometry=gpd.GeoSeries.from_wkt(districts_df['geometry_wkt']),
        crs='EPSG:4326'
    )
    
    # Convert to projected CRS for accurate buffer operations
    districts_gdf_proj = districts_gdf.to_crs('EPSG:25832')  # ETRS89 / UTM zone 32N
    
    # Create buffer in projected CRS (500m = 500)
    districts_gdf_proj['buffer_500m'] = districts_gdf_proj.geometry.buffer(500)
    
    # Convert back to WGS84 for storage
    districts_gdf_proj['buffer_500m_wgs84'] = districts_gdf_proj['buffer_500m'].to_crs('EPSG:4326')
    
    # Save back to DuckDB
    districts_gdf_proj['buffer_wkt'] = districts_gdf_proj['buffer_500m_wgs84'].apply(lambda x: wkt.dumps(x))
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS districts_with_buffer (
            id INTEGER,
            name VARCHAR,
            pop INTEGER,
            pop_density DOUBLE,
            buffer_wkt VARCHAR
        )
    """)
    
    for idx, row in districts_gdf_proj.iterrows():
        con.execute("""
            INSERT INTO districts_with_buffer (id, name, pop, pop_density, buffer_wkt)
            VALUES (?, ?, ?, ?, ?)
        """, [row['id'], row['name'], row['pop'], row['pop_density'], row['buffer_wkt']])
    
    print("  ✅ Buffer created using Python and saved to DuckDB")
    print("  💡 QGIS will see this immediately!")
    
    # Example 2: Calculate accessibility using Python
    print("\n🎯 Example 2: Calculating accessibility to PT stops...")
    
    # Read PT stops from DuckDB
    pt_data = con.execute("SELECT * FROM pt_stops").fetchall()
    pt_df = pd.DataFrame(pt_data, columns=['id', 'stop_type', 'geometry_wkt'])
    
    # Convert to GeoDataFrame
    pt_gdf = gpd.GeoDataFrame(
        pt_df.drop('geometry_wkt', axis=1),
        geometry=gpd.GeoSeries.from_wkt(pt_df['geometry_wkt']),
        crs='EPSG:4326'
    )
    
    # Convert to projected CRS for accurate buffer operations
    pt_gdf_proj = pt_gdf.to_crs('EPSG:25832')
    
    # Create service areas in projected CRS (300m = 300)
    pt_gdf_proj['service_area'] = pt_gdf_proj.geometry.buffer(300)
    
    # Convert back to WGS84 for storage
    pt_gdf_proj['service_area_wgs84'] = pt_gdf_proj['service_area'].to_crs('EPSG:4326')
    
    # Save to DuckDB
    pt_gdf_proj['service_area_wkt'] = pt_gdf_proj['service_area_wgs84'].apply(lambda x: wkt.dumps(x))
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS pt_service_areas (
            id INTEGER,
            stop_type VARCHAR,
            service_area_wkt VARCHAR
        )
    """)
    
    for idx, row in pt_gdf_proj.iterrows():
        con.execute("""
            INSERT INTO pt_service_areas (id, stop_type, service_area_wkt)
            VALUES (?, ?, ?)
        """, [row['id'], row['stop_type'], row['service_area_wkt']])
    
    print("  ✅ PT service areas created using Python and saved")
    print("  💡 QGIS updates automatically!")
    
    # Example 3: Complex analysis using Python
    print("\n🧮 Example 3: Complex analysis - Population density + Green areas...")
    
    # Read all data
    landuse_data = con.execute("SELECT * FROM landuse").fetchall()
    landuse_df = pd.DataFrame(landuse_data, columns=['id', 'landuse', 'geometry_wkt'])
    
    landuse_gdf = gpd.GeoDataFrame(
        landuse_df.drop('geometry_wkt', axis=1),
        geometry=gpd.GeoSeries.from_wkt(landuse_df['geometry_wkt']),
        crs='EPSG:4326'
    )
    
    # Filter green areas
    green_areas = landuse_gdf[landuse_gdf['landuse'].isin(['forest', 'farmland'])]
    
    # Calculate green area percentage per district
    results = []
    for idx, district in districts_gdf.iterrows():
        district_geom = district.geometry
        green_in_district = green_areas[green_areas.geometry.intersects(district_geom)]
        
        if len(green_in_district) > 0:
            green_area = green_in_district.geometry.intersection(district_geom).area.sum()
            district_area = district_geom.area
            green_percentage = (green_area / district_area) * 100
        else:
            green_percentage = 0
            
        results.append({
            'district_name': district.get('name', f'District_{idx}'),
            'population': district.get('pop', 0),
            'green_percentage': green_percentage,
            'geometry_wkt': wkt.dumps(district_geom)
        })
    
    # Save results to DuckDB
    con.execute("""
        CREATE TABLE IF NOT EXISTS districts_green_analysis (
            id INTEGER,
            district_name VARCHAR,
            population INTEGER,
            green_percentage DOUBLE,
            geometry_wkt VARCHAR
        )
    """)
    
    for idx, result in enumerate(results):
        con.execute("""
            INSERT INTO districts_green_analysis (id, district_name, population, green_percentage, geometry_wkt)
            VALUES (?, ?, ?, ?, ?)
        """, [idx, result['district_name'], result['population'], result['green_percentage'], result['geometry_wkt']])
    
    print("  ✅ Complex analysis completed using Python and saved")
    print("  💡 QGIS shows results instantly!")

def show_qgis_instructions():
    """Show how to connect QGIS to DuckDB"""
    print("\n🗺️ QGIS Connection Instructions:")
    print("=" * 60)
    
    print("1. 📦 Install DuckDB Provider plugin in QGIS:")
    print("   - Plugins → Manage and Install Plugins")
    print("   - Search for 'DuckDB Provider'")
    print("   - Install and restart QGIS")
    
    print("\n2. 🔌 Connect to DuckDB:")
    print("   - Layer → Add Layer → Add DuckDB Layer")
    print("   - Browse to: stuttgart_analysis.duckdb")
    print("   - Select table and click 'Add'")
    
    print("\n3. 🎨 Apply styles:")
    print("   - Use the .qml files we created earlier")
    print("   - Right-click layer → Load Style")
    
    print("\n4. 🔄 Real-time updates:")
    print("   - Python modifies DuckDB → QGIS updates automatically!")
    print("   - No more export/import cycles! 🎉")

def show_tables_info(con):
    """Show information about created tables"""
    print("\n📊 Database Tables Created:")
    print("=" * 60)
    
    # Get list of tables
    tables = con.execute("SHOW TABLES").fetchall()
    
    for table in tables:
        table_name = table[0]
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  📋 {table_name}: {count} records")
    
    print("\n💡 All tables are ready for QGIS!")

def main():
    """Main setup function"""
    print("🚀 Setting up DuckDB for Seamless QGIS Workflow!")
    print("=" * 60)
    
    # Setup DuckDB
    con = setup_duckdb()
    
    # Load existing data
    load_data_to_duckdb(con)
    
    # Demonstrate workflow
    demonstrate_workflow(con)
    
    # Show table information
    show_tables_info(con)
    
    # Show QGIS instructions
    show_qgis_instructions()
    
    # Close connection
    con.close()
    
    print("\n🎉 Setup Complete!")
    print("💡 Now you can:")
    print("   - Python: Process data and save to DuckDB")
    print("   - QGIS: Visualize and style automatically")
    print("   - Seamless workflow: No more file exports! ✨")
    
    print(f"\n📁 Your DuckDB file: stuttgart_analysis.duckdb")
    print("🗺️ Open in QGIS and start working seamlessly!")

if __name__ == "__main__":
    main()

