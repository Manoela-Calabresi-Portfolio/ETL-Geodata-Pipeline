#!/usr/bin/env python3
"""
Try PostGIS Extension Manager

This script tries to install PostGIS through PostgreSQL's
built-in extension manager, which might have it available.
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

def try_postgis_extension_manager():
    """Try to install PostGIS through extension manager"""
    
    print("🚀 Trying PostGIS Extension Manager")
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
            print("   📝 PostGIS not yet enabled")
        
        # Check available extensions
        print(f"\n3️⃣ Checking available extensions...")
        cursor.execute("SELECT * FROM pg_available_extensions WHERE name LIKE 'postgis%' ORDER BY name")
        postgis_extensions = cursor.fetchall()
        
        if postgis_extensions:
            print(f"   📋 Found {len(postgis_extensions)} PostGIS extensions:")
            for ext in postgis_extensions:
                print(f"      - {ext[0]} (version {ext[1]}) - {ext[2]}")
                print(f"        Schema: {ext[3]}, Relocatable: {ext[4]}")
            
            # Try to install the first available one
            first_ext = postgis_extensions[0][0]
            print(f"\n4️⃣ Trying to install {first_ext}...")
            
            try:
                cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {first_ext}")
                print(f"   ✅ {first_ext} installed successfully")
                
                # Test if it's working
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
                print(f"   ❌ Failed to install {first_ext}: {e}")
        else:
            print("   ❌ No PostGIS extensions found in extension manager")
        
        # Check if we can install from a different source
        print(f"\n5️⃣ Trying alternative installation methods...")
        
        # Try to install from a URL or file
        try:
            print("   🔧 Trying to install PostGIS from PostgreSQL contrib...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis FROM unpackaged")
            print("   ✅ PostGIS installed from unpackaged")
            
            # Test if it's working
            cursor.execute("SELECT PostGIS_Version()")
            postgis_version = cursor.fetchone()[0]
            print(f"   🎉 PostGIS working: {postgis_version}")
            
            cursor.close()
            conn.close()
            
            print(f"\n🎉 PostGIS installed successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Alternative installation failed: {e}")
        
        cursor.close()
        conn.close()
        
        print(f"\n❌ Could not install PostGIS through extension manager")
        print(f"\n💡 Next steps:")
        print(f"   1. Download complete PostGIS 3.6.x package for PostgreSQL 17")
        print(f"   2. Run the installer (not just copy files)")
        print(f"   3. Restart PostgreSQL service")
        print(f"   4. Try CREATE EXTENSION postgis;")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Failed to try extension manager: {e}")
        return False

if __name__ == "__main__":
    success = try_postgis_extension_manager()
    sys.exit(0 if success else 1)
