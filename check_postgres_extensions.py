#!/usr/bin/env python3
"""
Check PostgreSQL Extensions

This script checks what extensions are available in PostgreSQL
and looks for PostGIS-related extensions.
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

def check_extensions():
    """Check available PostgreSQL extensions"""
    
    print("🔍 Checking PostgreSQL Extensions")
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
        
        # Check available extensions
        print(f"\n2️⃣ Checking available extensions...")
        cursor.execute("SELECT * FROM pg_available_extensions ORDER BY name")
        extensions = cursor.fetchall()
        
        print(f"   📋 Found {len(extensions)} available extensions")
        
        # Show PostGIS-related extensions
        postgis_extensions = [ext for ext in extensions if 'postgis' in ext[0].lower()]
        
        if postgis_extensions:
            print(f"\n3️⃣ PostGIS-related extensions found:")
            for ext in postgis_extensions:
                print(f"   📄 {ext[0]} (version {ext[1]}) - {ext[2]}")
                print(f"      Schema: {ext[3]}, Relocatable: {ext[4]}")
        else:
            print(f"\n3️⃣ No PostGIS extensions found")
        
        # Show all extensions (first 20)
        print(f"\n4️⃣ All available extensions (first 20):")
        for i, ext in enumerate(extensions[:20]):
            print(f"   {i+1:2d}. {ext[0]} (version {ext[1]})")
        
        if len(extensions) > 20:
            print(f"   ... and {len(extensions) - 20} more")
        
        # Check installed extensions
        print(f"\n5️⃣ Currently installed extensions:")
        cursor.execute("SELECT * FROM pg_extension ORDER BY extname")
        installed = cursor.fetchall()
        
        if installed:
            for ext in installed:
                print(f"   ✅ {ext[0]} (version {ext[1]})")
        else:
            print(f"   📝 No extensions currently installed")
        
        cursor.close()
        conn.close()
        
        print(f"\n📊 Extension Summary:")
        print(f"   📋 Total available: {len(extensions)}")
        print(f"   📄 PostGIS-related: {len(postgis_extensions)}")
        print(f"   ✅ Currently installed: {len(installed)}")
        
        if postgis_extensions:
            print(f"\n💡 You can try to install PostGIS with:")
            print(f"   CREATE EXTENSION {postgis_extensions[0][0]};")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to check extensions: {e}")
        return False

if __name__ == "__main__":
    success = check_extensions()
    sys.exit(0 if success else 1)

