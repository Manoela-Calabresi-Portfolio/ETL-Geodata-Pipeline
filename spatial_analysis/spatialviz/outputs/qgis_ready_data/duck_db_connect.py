#!/usr/bin/env python3
"""
DuckDB Connection Script - Stuttgart Urban Analysis
Connects to DuckDB and shows available tables
"""

import duckdb
import os
from pathlib import Path

def find_duckdb_file():
    """Finds the DuckDB file from any directory"""
    print("🔍 Looking for DuckDB file...")
    print("=" * 50)
    
    # Get current directory
    current_dir = Path.cwd()
    print(f"📁 Current directory: {current_dir}")
    
    # Look for DuckDB file in multiple possible locations
    possible_paths = [
        # From current directory
        "stuttgart_analysis.duckdb",
        
        # From qgis_ready_data folder
        "../stuttgart_analysis.duckdb",
        "../../stuttgart_analysis.duckdb",
        "../../../stuttgart_analysis.duckdb",
        "../../../../stuttgart_analysis.duckdb",
        
        # From project root
        "spatial_analysis/spatialviz/outputs/qgis_ready_data/stuttgart_analysis.duckdb",
        "../spatial_analysis/spatialviz/outputs/qgis_ready_data/stuttgart_analysis.duckdb",
        "../../spatial_analysis/spatialviz/outputs/qgis_ready_data/stuttgart_analysis.duckdb",
        
        # Absolute paths (as fallback)
        "C:/Users/manoe.MC_ASUS/Documents/ETL-Geodata-Pipeline/stuttgart_analysis.duckdb",
    ]
    
    # Try each path
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ DuckDB file found at: {path}")
            return path
    
    # If not found, search recursively
    print("❌ DuckDB file not found in common locations!")
    print("🔍 Searching recursively...")
    
    # Search in current directory and subdirectories
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".duckdb"):
                full_path = os.path.join(root, file)
                print(f"   📋 Found: {full_path}")
                if "stuttgart" in file.lower():
                    print(f"✅ This looks like the right file!")
                    return full_path
    
    # Search in parent directories
    for root, dirs, files in os.walk(".."):
        for file in files:
            if file.endswith(".duckdb"):
                full_path = os.path.join(root, file)
                print(f"   📋 Found: {full_path}")
                if "stuttgart" in file.lower():
                    print(f"✅ This looks like the right file!")
                    return full_path
    
    print("❌ No DuckDB file found!")
    return None

def connect_duckdb():
    """Connects to DuckDB and shows available tables"""
    print("🦆 Connecting to DuckDB...")
    print("=" * 50)
    
    # Find the DuckDB file
    db_file = find_duckdb_file()
    
    if not db_file:
        print("❌ Could not find DuckDB file!")
        return None
    
    # Connect to DuckDB
    try:
        con = duckdb.connect(str(db_file))
        print("✅ Connected to DuckDB!")
        return con
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def show_tables(con):
    """Shows all available tables in DuckDB"""
    if con is None:
        return
    
    print("\n📋 Available tables in DuckDB:")
    print("=" * 50)
    
    try:
        # Execute SHOW TABLES
        result = con.execute("SHOW TABLES")
        tables = result.fetchall()
        
        if not tables:
            print("   ⚠️  No tables found!")
            print("   💡 The database might be empty or not created correctly")
            return
        
        # Show each table
        for i, table in enumerate(tables, 1):
            table_name = table[0]
            print(f"   {i:2d}. {table_name}")
            
            # Count records in each table
            try:
                count_result = con.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = count_result.fetchone()[0]
                print(f"       📊 {count} records")
            except Exception as e:
                print(f"       ❌ Error counting records: {e}")
        
        print(f"\n✅ Total: {len(tables)} tables found")
        
    except Exception as e:
        print(f"❌ Error listing tables: {e}")

def explore_table(con, table_name):
    """Explores a specific table"""
    if con is None:
        return
    
    print(f"\n🔍 Exploring table: {table_name}")
    print("=" * 50)
    
    try:
        # View table structure
        result = con.execute(f"DESCRIBE {table_name}")
        columns = result.fetchall()
        
        print("📋 Table structure:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
        
        # View first records
        print(f"\n📊 First 3 records:")
        result = con.execute(f"SELECT * FROM {table_name} LIMIT 3")
        rows = result.fetchall()
        
        for i, row in enumerate(rows, 1):
            print(f"   {i}. {row}")
            
    except Exception as e:
        print(f"❌ Error exploring table: {e}")

def main():
    """Main function"""
    print("🚀 DuckDB Connection Script - Stuttgart Urban Analysis")
    print("=" * 60)
    
    # Connect to DuckDB
    con = connect_duckdb()
    
    if con is None:
        print("\n❌ Could not connect to DuckDB!")
        return
    
    # Show available tables
    show_tables(con)
    
    # If there are tables, explore the first one
    try:
        result = con.execute("SHOW TABLES")
        tables = result.fetchall()
        
        if tables:
            first_table = tables[0][0]
            print(f"\n🎯 Exploring first table: {first_table}")
            explore_table(con, first_table)
    except Exception as e:
        print(f"❌ Error exploring table: {e}")
    
    # Close connection
    if con:
        con.close()
        print("\n✅ Connection closed!")
    
    print("\n🎉 Script completed!")

if __name__ == "__main__":
    main()