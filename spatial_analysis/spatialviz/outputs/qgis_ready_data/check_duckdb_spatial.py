#!/usr/bin/env python3
"""
Check available DuckDB spatial functions
"""

import duckdb

def check_spatial_functions():
    """Check what spatial functions are available"""
    print("🔍 Checking DuckDB spatial functions...")
    
    # Connect to existing database
    con = duckdb.connect("stuttgart_analysis.duckdb")
    
    # Check spatial extension
    print("\n📦 Spatial extension status:")
    try:
        result = con.execute("SELECT * FROM duckdb_extensions() WHERE extension_name = 'spatial'").fetchall()
        print(f"  Spatial extension: {result}")
    except Exception as e:
        print(f"  Error checking extensions: {e}")
    
    # Check available functions
    print("\n🔧 Available functions:")
    try:
        functions = con.execute("SELECT function_name FROM duckdb_functions() WHERE function_name LIKE '%geom%' OR function_name LIKE '%st_%'").fetchall()
        for func in functions:
            print(f"  {func[0]}")
    except Exception as e:
        print(f"  Error checking functions: {e}")
    
    # Check tables
    print("\n📊 Available tables:")
    try:
        tables = con.execute("SHOW TABLES").fetchall()
        for table in tables:
            print(f"  {table[0]}")
    except Exception as e:
        print(f"  Error checking tables: {e}")
    
    con.close()

if __name__ == "__main__":
    check_spatial_functions()
