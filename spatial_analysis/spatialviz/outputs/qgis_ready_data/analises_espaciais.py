#!/usr/bin/env python3
"""
Spatial Analysis Script - Stuttgart Urban Analysis
Performs spatial analysis and saves results back to DuckDB
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
    
    # Look for DuckDB file
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

def load_data_from_duckdb(con, table_name):
    """Loads data from DuckDB table into GeoDataFrame"""
    print(f"📥 Loading {table_name} from DuckDB...")
    
    try:
        # Load data
        df = con.execute(f"SELECT * FROM {table_name}").df()
        
        # Convert WKT to geometry
        if 'geometry' in df.columns:
            df['geometry'] = df['geometry'].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
            print(f"✅ Loaded {len(gdf)} records from {table_name}")
            return gdf
        else:
            print(f"⚠️  No geometry column in {table_name}")
            return df
            
    except Exception as e:
        print(f"❌ Error loading {table_name}: {e}")
        return None

def perform_transport_analysis(gdf_districts, gdf_pt_stops, gdf_roads):
    """Performs transport accessibility analysis"""
    print("\n🚌 Performing transport accessibility analysis...")
    
    # Reproject to projected CRS for accurate calculations
    gdf_districts_proj = gdf_districts.to_crs('EPSG:25832')
    gdf_pt_stops_proj = gdf_pt_stops.to_crs('EPSG:25832')
    gdf_roads_proj = gdf_roads.to_crs('EPSG:25832')
    
    results = []
    
    for idx, district in gdf_districts_proj.iterrows():
        district_geom = district.geometry
        district_name = district.get('name', f'District_{idx}')
        
        # 1. Count PT stops within district
        pt_in_district = gdf_pt_stops_proj[gdf_pt_stops_proj.geometry.within(district_geom)]
        pt_count = len(pt_in_district)
        
        # 2. Calculate road density
        roads_in_district = gdf_roads_proj[gdf_roads_proj.geometry.intersects(district_geom)]
        road_length_km = roads_in_district.geometry.length.sum() / 1000  # Convert to km
        
        # 3. Calculate district area
        district_area_ha = district_geom.area / 10000  # Convert to hectares
        
        # 4. Calculate PT density per km²
        district_area_km2 = district_area_ha / 100  # Convert hectares to km²
        pt_density = pt_count / district_area_km2 if district_area_km2 > 0 else 0
        
        # 5. Calculate road density per km²
        road_density = road_length_km / district_area_km2 if district_area_km2 > 0 else 0
        
        result = {
            'district_name': district_name,
            'district_area_ha': round(district_area_ha, 2),
            'pt_stops_count': pt_count,
            'road_length_km': round(road_length_km, 2),
            'pt_density_per_km2': round(pt_density, 2),
            'road_density_per_km2': round(road_density, 2)
        }
        
        results.append(result)
    
    print(f"✅ Analysis completed for {len(results)} districts")
    return results

def perform_buffer_analysis(gdf_districts, gdf_pt_stops):
    """Performs buffer analysis around PT stops"""
    print("\n🎯 Performing buffer analysis...")
    
    # Reproject to projected CRS
    gdf_districts_proj = gdf_districts.to_crs('EPSG:25832')
    gdf_pt_stops_proj = gdf_pt_stops.to_crs('EPSG:25832')
    
    # Create 200m buffer around PT stops
    print("   📏 Creating 200m buffers around PT stops...")
    pt_buffers = gdf_pt_stops_proj.copy()
    pt_buffers['geometry'] = pt_buffers.geometry.buffer(200)  # 200 meters
    
    # Calculate coverage per district
    buffer_results = []
    
    for idx, district in gdf_districts_proj.iterrows():
        district_geom = district.geometry
        district_name = district.get('name', f'District_{idx}')
        
        # Count PT stops with buffers that intersect district
        intersecting_buffers = pt_buffers[pt_buffers.geometry.intersects(district_geom)]
        
        # Calculate total buffer area within district
        total_buffer_area = 0
        for _, buffer_row in intersecting_buffers.iterrows():
            intersection = district_geom.intersection(buffer_row.geometry)
            total_buffer_area += intersection.area
        
        # Convert to hectares
        buffer_area_ha = total_buffer_area / 10000
        
        # Calculate district area
        district_area_ha = district_geom.area / 10000
        
        # Calculate coverage percentage
        coverage_percent = (buffer_area_ha / district_area_ha * 100) if district_area_ha > 0 else 0
        
        result = {
            'district_name': district_name,
            'district_area_ha': round(district_area_ha, 2),
            'buffer_coverage_ha': round(buffer_area_ha, 2),
            'coverage_percent': round(coverage_percent, 2),
            'pt_stops_with_buffers': len(intersecting_buffers)
        }
        
        buffer_results.append(result)
    
    print(f"✅ Buffer analysis completed for {len(buffer_results)} districts")
    return buffer_results

def save_results_to_duckdb(con, transport_results, buffer_results):
    """Saves analysis results back to DuckDB"""
    print("\n💾 Saving results to DuckDB...")
    
    try:
        # Save transport analysis
        df_transport = pd.DataFrame(transport_results)
        con.execute("DROP TABLE IF EXISTS district_transport_analysis")
        con.execute("CREATE TABLE district_transport_analysis AS SELECT * FROM df_transport")
        print(f"✅ Saved transport analysis: {len(df_transport)} records")
        
        # Save buffer analysis
        df_buffer = pd.DataFrame(buffer_results)
        con.execute("DROP TABLE IF EXISTS district_buffer_analysis")
        con.execute("CREATE TABLE district_buffer_analysis AS SELECT * FROM df_buffer")
        print(f"✅ Saved buffer analysis: {len(df_buffer)} records")
        
        # Show summary
        print("\n📊 Analysis Summary:")
        print("=" * 50)
        
        print("\n🚌 Transport Analysis:")
        print(f"   📍 Districts analyzed: {len(df_transport)}")
        print(f"   🚏 Total PT stops: {df_transport['pt_stops_count'].sum()}")
        print(f"   🛣️  Total road length: {df_transport['road_length_km'].sum():.1f} km")
        
        print("\n🎯 Buffer Analysis:")
        print(f"   📍 Districts analyzed: {len(df_buffer)}")
        print(f"   🎯 Average coverage: {df_buffer['coverage_percent'].mean():.1f}%")
        
        # Top 5 districts by PT density
        print("\n🏆 Top 5 Districts by PT Density:")
        top_pt = df_transport.nlargest(5, 'pt_density_per_km2')
        for i, (_, row) in enumerate(top_pt.iterrows(), 1):
            print(f"   {i}. {row['district_name']}: {row['pt_density_per_km2']:.1f} stops/km²")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")

def main():
    """Main function"""
    print("🚀 Spatial Analysis Script - Stuttgart Urban Analysis")
    print("=" * 60)
    
    # Connect to DuckDB
    con = connect_duckdb()
    if not con:
        return
    
    try:
        # Load data
        print("\n📥 Loading data from DuckDB...")
        districts = load_data_from_duckdb(con, 'districts')
        pt_stops = load_data_from_duckdb(con, 'pt_stops')
        roads = load_data_from_duckdb(con, 'roads')
        
        if districts is None or pt_stops is None or roads is None:
            print("❌ Could not load required data!")
            return
        
        # Perform analyses
        transport_results = perform_transport_analysis(districts, pt_stops, roads)
        buffer_results = perform_buffer_analysis(districts, pt_stops)
        
        # Save results
        save_results_to_duckdb(con, transport_results, buffer_results)
        
        print("\n🎉 Analysis completed successfully!")
        print("💡 New tables created:")
        print("   - district_transport_analysis")
        print("   - district_buffer_analysis")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    
    finally:
        con.close()
        print("\n✅ Connection closed!")

if __name__ == "__main__":
    main()
