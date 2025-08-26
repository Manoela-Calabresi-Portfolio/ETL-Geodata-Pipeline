#!/usr/bin/env python3
"""
Simple PostGIS Installation

This script tries to install PostGIS through PostgreSQL's
extension system without manual file copying.
"""

import psycopg2
import sys
from pathlib import Path
import yaml

def load_credentials():
    """Load database credentials from file"""
    credentials_path = Path("credentials/database_credentials.yaml")
    
    if not credentials_path.exists():
        print("❌ Credentials file not found!")
        return None
    
    try:
        with open(credentials_path, 'r') as f:
            credentials = yaml.safe_load(f)
        
        print("✅ Credentials loaded successfully")
        return credentials
        
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return None

def install_postgis_simple():
    """Try to install PostGIS through PostgreSQL extensions"""
    
    print("🚀 Simple PostGIS Installation")
    print("=" * 40)
    
    # Load credentials
    credentials = load_credentials()
    if not credentials:
        return False
    
    postgres_config = credentials['database']['postgres']
    etl_config = credentials['database']['etl_pipeline']
    
    try:
        print(f"\n1️⃣ Connecting to database '{etl_config['database']}'...")
        
        # Connect to target database
        conn = psycopg2.connect(
            host=etl_config['host'],
            port=etl_config['port'],
            database=etl_config['database'],
            user=postgres_config['user'],
            password=postgres_config['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("   ✅ Connected to database successfully")
        
        # Check PostgreSQL version
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"   📋 PostgreSQL version: {version}")
        
        # Check if PostGIS is already working
        print(f"\n2️⃣ Testing PostGIS functions...")
        try:
            cursor.execute("SELECT PostGIS_Version()")
            postgis_version = cursor.fetchone()[0]
            print(f"   ✅ PostGIS already working: {postgis_version}")
            return True
        except Exception:
            print("   📝 PostGIS not available")
        
        # Try to install PostGIS extension
        print(f"\n3️⃣ Trying to install PostGIS extension...")
        
        # List of possible PostGIS extension names to try
        postgis_extensions = [
            'postgis',
            'postgis_3_4',
            'postgis_3_3',
            'postgis_3_2',
            'postgis_3_1',
            'postgis_3_0'
        ]
        
        for ext_name in postgis_extensions:
            try:
                print(f"   🔧 Trying to install '{ext_name}'...")
                cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {ext_name}")
                print(f"   ✅ Successfully installed '{ext_name}'")
                
                # Test if it's working
                try:
                    cursor.execute("SELECT PostGIS_Version()")
                    postgis_version = cursor.fetchone()[0]
                    print(f"   🎉 PostGIS working: {postgis_version}")
                    
                    # Test spatial functions
                    cursor.execute("SELECT ST_AsText(ST_GeomFromText('POINT(0 0)'))")
                    result = cursor.fetchone()[0]
                    print(f"   ✅ Spatial functions working: {result}")
                    
                    cursor.close()
                    conn.close()
                    
                    print(f"\n🎉 PostGIS installed and working successfully!")
                    return True
                    
                except Exception as e:
                    print(f"   ⚠️ Extension installed but not fully functional: {e}")
                    continue
                    
            except Exception as e:
                print(f"   ❌ Failed to install '{ext_name}': {e}")
                continue
        
        # If we get here, no extension worked
        print(f"\n❌ Could not install any PostGIS extension")
        print(f"\n💡 Solutions:")
        print(f"   1. Download PostGIS 3.4.x for PostgreSQL 16 from:")
        print(f"      https://postgis.net/windows_downloads/")
        print(f"   2. Use Stack Builder (if available)")
        print(f"   3. Continue without PostGIS (current system works fine)")
        
        cursor.close()
        conn.close()
        return False
        
    except Exception as e:
        print(f"\n❌ Failed to install PostGIS: {e}")
        return False

if __name__ == "__main__":
    success = install_postgis_simple()
    sys.exit(0 if success else 1)

