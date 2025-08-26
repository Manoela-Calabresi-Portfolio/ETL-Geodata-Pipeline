#!/usr/bin/env python3
"""
Switch to PostgreSQL 17

This script helps switch from PostgreSQL 16 to PostgreSQL 17
and updates the database connection accordingly.
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

def switch_to_postgres17():
    """Switch to PostgreSQL 17"""
    
    print("🚀 Switching to PostgreSQL 17")
    print("=" * 40)
    
    # Load credentials
    credentials = load_credentials()
    if not credentials:
        return False
    
    postgres_config = credentials['database']['postgres']
    etl_config = credentials['database']['etl_pipeline']
    
    try:
        print(f"\n1️⃣ Checking PostgreSQL services...")
        
        # Check Windows services
        try:
            result = subprocess.run(['sc', 'query', 'postgresql-x64-16'], 
                                 capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("   📋 PostgreSQL 16 service found")
                if "RUNNING" in result.stdout:
                    print("   ⚠️ PostgreSQL 16 service is RUNNING")
                else:
                    print(f"   📝 PostgreSQL 16 service status: {result.stdout}")
            else:
                print("   ❌ PostgreSQL 16 service not found")
        except Exception as e:
            print(f"   ⚠️ Could not check PostgreSQL 16 service: {e}")
        
        try:
            result = subprocess.run(['sc', 'query', 'postgresql-x64-17'], 
                                 capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("   📋 PostgreSQL 17 service found")
                if "RUNNING" in result.stdout:
                    print("   ✅ PostgreSQL 17 service is RUNNING")
                else:
                    print(f"   📝 PostgreSQL 17 service status: {result.stdout}")
            else:
                print("   ❌ PostgreSQL 17 service not found")
        except Exception as e:
            print(f"   ⚠️ Could not check PostgreSQL 17 service: {e}")
        
        print(f"\n2️⃣ Testing PostgreSQL 17 connection...")
        
        # Try to connect to PostgreSQL 17
        try:
            # Update port if needed (PostgreSQL 17 might use a different port)
            test_port = 5433  # Common alternative port for multiple PostgreSQL installations
            
            conn = psycopg2.connect(
                host='localhost',
                port=test_port,
                database='postgres',
                user=postgres_config['user'],
                password=postgres_config['password']
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"   ✅ Connected to PostgreSQL 17: {version}")
            
            cursor.close()
            conn.close()
            
            print(f"\n🎉 PostgreSQL 17 is accessible on port {test_port}!")
            print(f"💡 Update your credentials to use port {test_port}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Could not connect to PostgreSQL 17: {e}")
        
        print(f"\n3️⃣ Manual steps to switch to PostgreSQL 17:")
        print(f"   1. Open Windows Services (services.msc)")
        print(f"   2. Find 'postgresql-x64-16' service")
        print(f"   3. Right-click → Stop")
        print(f"   4. Find 'postgresql-x64-17' service")
        print(f"   5. Right-click → Start")
        print(f"   6. Update your database port in credentials file")
        
        print(f"\n4️⃣ Alternative: Use both versions on different ports")
        print(f"   PostgreSQL 16: Port 5432 (current)")
        print(f"   PostgreSQL 17: Port 5433 (recommended for PostGIS)")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Failed to switch to PostgreSQL 17: {e}")
        return False

if __name__ == "__main__":
    success = switch_to_postgres17()
    sys.exit(0 if success else 1)

