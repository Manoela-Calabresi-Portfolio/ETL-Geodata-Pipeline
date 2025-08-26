#!/usr/bin/env python3
"""
Enable PostGIS Extension

This script manually enables PostGIS in the database
using the correct installation path.
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

def enable_postgis():
    """Enable PostGIS extension in the database"""
    
    print("🚀 Enabling PostGIS Extension")
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
        
        # Check current PostgreSQL version
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"   📋 PostgreSQL version: {version}")
        
        # Check if PostGIS is already enabled
        print(f"\n2️⃣ Checking PostGIS status...")
        try:
            cursor.execute("SELECT PostGIS_Version()")
            postgis_version = cursor.fetchone()[0]
            print(f"   ✅ PostGIS already enabled: {postgis_version}")
            return True
        except Exception:
            print("   📝 PostGIS not yet enabled")
        
        # Try to enable PostGIS
        print(f"\n3️⃣ Enabling PostGIS extension...")
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            print("   ✅ PostGIS extension enabled successfully")
        except Exception as e:
            print(f"   ❌ Failed to enable PostGIS: {e}")
            
            # Try alternative approach
            print(f"\n4️⃣ Trying alternative PostGIS installation...")
            try:
                # Check available extensions
                cursor.execute("SELECT * FROM pg_available_extensions WHERE name LIKE 'postgis%'")
                extensions = cursor.fetchall()
                
                if extensions:
                    print(f"   📋 Available PostGIS extensions:")
                    for ext in extensions:
                        print(f"      - {ext[0]} (version {ext[1]})")
                    
                    # Try to enable the first available one
                    first_ext = extensions[0][0]
                    print(f"   🔧 Trying to enable {first_ext}...")
                    cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {first_ext}")
                    print(f"   ✅ {first_ext} enabled successfully")
                    
                else:
                    print("   ❌ No PostGIS extensions found")
                    print("   💡 You may need to:")
                    print("      1. Install PostGIS extension files")
                    print("      2. Copy PostGIS files to PostgreSQL extension directory")
                    print("      3. Restart PostgreSQL service")
                    return False
                    
            except Exception as e2:
                print(f"   ❌ Alternative approach failed: {e2}")
                return False
        
        # Test PostGIS functionality
        print(f"\n5️⃣ Testing PostGIS functionality...")
        try:
            cursor.execute("SELECT PostGIS_Version()")
            postgis_version = cursor.fetchone()[0]
            print(f"   ✅ PostGIS working: {postgis_version}")
            
            # Test basic spatial functions
            cursor.execute("SELECT ST_AsText(ST_GeomFromText('POINT(0 0)'))")
            result = cursor.fetchone()[0]
            print(f"   ✅ Spatial functions working: {result}")
            
        except Exception as e:
            print(f"   ❌ PostGIS test failed: {e}")
            return False
        
        cursor.close()
        conn.close()
        
        print(f"\n🎉 PostGIS enabled successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to enable PostGIS: {e}")
        return False

if __name__ == "__main__":
    success = enable_postgis()
    sys.exit(0 if success else 1)

