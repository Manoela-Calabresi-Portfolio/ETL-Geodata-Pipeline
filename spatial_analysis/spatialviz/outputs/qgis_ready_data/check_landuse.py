#!/usr/bin/env python3
"""
Check Landuse Data Script - Investigate what happened to landuse data
"""

import duckdb
import os

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

def investigate_landuse(con):
    """Investigates the landuse table"""
    print("\n🔍 Investigating landuse table...")
    print("=" * 50)
    
    try:
        # Check if table exists
        result = con.execute("SHOW TABLES")
        tables = result.fetchall()
        table_names = [table[0] for table in tables]
        
        print(f"📋 All tables: {table_names}")
        
        if 'landuse' in table_names:
            print("\n✅ landuse table exists!")
            
            # Check table structure
            print("\n📋 Table structure:")
            desc_result = con.execute("DESCRIBE landuse")
            columns = desc_result.fetchall()
            
            for col in columns:
                print(f"   - {col[0]}: {col[1]}")
            
            # Check record count
            count_result = con.execute("SELECT COUNT(*) FROM landuse")
            count = count_result.fetchone()[0]
            print(f"\n📊 Record count: {count}")
            
            if count > 0:
                # Show sample data
                print("\n📄 Sample data:")
                sample_result = con.execute("SELECT * FROM landuse LIMIT 3")
                rows = sample_result.fetchall()
                
                for i, row in enumerate(rows, 1):
                    print(f"   {i}. {row}")
            else:
                print("\n⚠️  Table exists but has 0 records!")
                
                # Check if it was truncated or what happened
                print("\n🔍 Checking for any data...")
                
                # Try to see if there are any non-NULL values
                for col in columns:
                    col_name = col[0]
                    if col_name != 'geometry':  # Skip geometry for now
                        try:
                            non_null_result = con.execute(f"SELECT COUNT(*) FROM landuse WHERE {col_name} IS NOT NULL")
                            non_null_count = non_null_result.fetchone()[0]
                            print(f"   {col_name}: {non_null_count} non-NULL values")
                        except:
                            print(f"   {col_name}: Error checking")
        else:
            print("\n❌ landuse table does not exist!")
            
            # Check for similar tables
            print("\n🔍 Looking for similar tables...")
            similar_tables = [name for name in table_names if 'land' in name.lower() or 'use' in name.lower()]
            if similar_tables:
                print(f"   Similar tables found: {similar_tables}")
            else:
                print("   No similar tables found")
        
        # Check if there are other spatial tables with data
        print("\n🗺️  Checking other spatial tables...")
        spatial_tables = ['districts', 'roads', 'pt_stops', 'city_boundary']
        
        for table in spatial_tables:
            if table in table_names:
                try:
                    count_result = con.execute(f"SELECT COUNT(*) FROM {table}")
                    count = count_result.fetchone()[0]
                    print(f"   {table}: {count} records")
                except:
                    print(f"   {table}: Error checking")
        
    except Exception as e:
        print(f"❌ Error investigating: {e}")

def main():
    """Main function"""
    print("🚀 Landuse Investigation Script")
    print("=" * 50)
    
    # Connect to DuckDB
    con = connect_duckdb()
    if not con:
        return
    
    try:
        # Investigate landuse
        investigate_landuse(con)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        con.close()
        print("\n✅ Connection closed!")

if __name__ == "__main__":
    main()

