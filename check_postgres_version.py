#!/usr/bin/env python3
"""
Check Actual PostgreSQL Version

This script checks what PostgreSQL version is actually running
and compares it with what we think we have.
"""

import psycopg2
import sys
from pathlib import Path
import yaml
import subprocess

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

def check_postgres_version():
    """Check actual PostgreSQL version"""
    
    print("🔍 Checking Actual PostgreSQL Version")
    print("=" * 45)
    
    # Load credentials
    credentials = load_credentials()
    if not credentials:
        return False
    
    postgres_config = credentials['database']['postgres']
    etl_config = credentials['database']['etl_pipeline']
    
    try:
        print(f"\n1️⃣ Checking PostgreSQL installation paths...")
        
        # Check different possible PostgreSQL paths
        postgres_paths = [
            Path("C:/Program Files/PostgreSQL/17"),
            Path("C:/Program Files/PostgreSQL/16"),
            Path("C:/Program Files/PostgreSQL/15"),
            Path("C:/Program Files/PostgreSQL/14")
        ]
        
        for path in postgres_paths:
            if path.exists():
                print(f"   📁 Found: {path}")
                
                # Check if psql exists
                psql_path = path / "bin" / "psql.exe"
                if psql_path.exists():
                    print(f"   ✅ psql found: {psql_path}")
                    
                    # Try to get version from psql
                    try:
                        result = subprocess.run([str(psql_path), "--version"], 
                                             capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            print(f"   📋 Version: {result.stdout.strip()}")
                    except Exception as e:
                        print(f"   ⚠️ Could not run psql: {e}")
                else:
                    print(f"   ❌ psql not found in {path}")
            else:
                print(f"   ❌ Not found: {path}")
        
        print(f"\n2️⃣ Checking database connection version...")
        
        # Connect to database and check version
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
        
        # Get detailed version info
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"   📋 Database version: {version}")
        
        # Parse version string
        if "PostgreSQL 17" in version:
            print("   🎉 Confirmed: PostgreSQL 17")
        elif "PostgreSQL 16" in version:
            print("   ⚠️ Confirmed: PostgreSQL 16")
        else:
            print(f"   ❓ Unknown version: {version}")
        
        # Check data directory
        cursor.execute("SHOW data_directory")
        data_dir = cursor.fetchone()[0]
        print(f"   📁 Data directory: {data_dir}")
        
        # Check config file
        cursor.execute("SHOW config_file")
        config_file = cursor.fetchone()[0]
        print(f"   📄 Config file: {config_file}")
        
        cursor.close()
        conn.close()
        
        print(f"\n3️⃣ PostGIS compatibility check...")
        
        if "PostgreSQL 17" in version:
            print("   ✅ PostgreSQL 17 detected")
            print("   ✅ PostGIS 3.6.0rc2 should be compatible")
            print("   💡 The issue might be:")
            print("      1. PostGIS files not in the right directory")
            print("      2. PostgreSQL looking in wrong extension path")
            print("      3. Need to restart PostgreSQL service")
        else:
            print("   ⚠️ PostgreSQL 16 detected")
            print("   ❌ PostGIS 3.6.0rc2 is NOT compatible")
            print("   💡 You need PostGIS 3.4.x for PostgreSQL 16")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Failed to check version: {e}")
        return False

if __name__ == "__main__":
    success = check_postgres_version()
    sys.exit(0 if success else 1)

