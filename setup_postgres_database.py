#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script

This script sets up the PostgreSQL database for the ETL Geodata Pipeline.
It creates the database, user, and enables PostGIS extension.

Usage:
    python setup_postgres_database.py
    
Note: Make sure to fill in your credentials in credentials/database_credentials.yaml first!
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
        print("📋 Please create credentials/database_credentials.yaml from the template")
        print("   cp credentials/database_credentials.template.yaml credentials/database_credentials.yaml")
        return None
    
    try:
        with open(credentials_path, 'r') as f:
            credentials = yaml.safe_load(f)
        
        # Validate required fields
        required_fields = [
            'database.postgres.password',
            'database.etl_pipeline.password'
        ]
        
        for field in required_fields:
            keys = field.split('.')
            value = credentials
            for key in keys:
                value = value.get(key, {})
            
            if not value or value == "YOUR_POSTGRES_PASSWORD_HERE":
                print(f"❌ Please fill in {field} in credentials file")
                return None
        
        print("✅ Credentials loaded successfully")
        return credentials
        
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return None

def setup_database():
    """Set up PostgreSQL database for ETL pipeline"""
    
    print("🚀 Setting up PostgreSQL Database for ETL Pipeline")
    print("=" * 60)
    
    # Load credentials
    credentials = load_credentials()
    if not credentials:
        return False
    
    # Database configuration from credentials file
    postgres_config = credentials['database']['postgres']
    etl_config = credentials['database']['etl_pipeline']
    
    try:
        print(f"\n1️⃣ Connecting to PostgreSQL as postgres user...")
        
        # Connect to PostgreSQL using credentials from file
        conn = psycopg2.connect(
            host=postgres_config['host'],
            port=postgres_config['port'],
            database='postgres',  # Connect to default database first
            user=postgres_config['user'],
            password=postgres_config['password']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("   ✅ Connected to PostgreSQL successfully")
        
        # Check if target database exists
        target_db = etl_config['database']
        print(f"\n2️⃣ Checking if database '{target_db}' exists...")
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        
        if cursor.fetchone():
            print(f"   ✅ Database '{target_db}' already exists")
        else:
            print(f"   📝 Creating database '{target_db}'...")
            cursor.execute(f"CREATE DATABASE {target_db}")
            print(f"   ✅ Database '{target_db}' created successfully")
        
        # Check if target user exists
        target_user = etl_config['user']
        print(f"\n3️⃣ Checking if user '{target_user}' exists...")
        cursor.execute("SELECT 1 FROM pg_user WHERE usename = %s", (target_user,))
        
        if cursor.fetchone():
            print(f"   ✅ User '{target_user}' already exists")
        else:
            print(f"   📝 Creating user '{target_user}'...")
            target_password = etl_config['password']
            cursor.execute(f"CREATE USER {target_user} WITH PASSWORD '{target_password}'")
            print(f"   ✅ User '{target_user}' created successfully")
        
        # Grant privileges
        print(f"\n4️⃣ Granting privileges to user '{target_user}'...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {target_db} TO {target_user}")
        cursor.execute(f"GRANT CREATE ON SCHEMA public TO {target_user}")
        print(f"   ✅ Privileges granted successfully")
        
        # Close connection to postgres database
        cursor.close()
        conn.close()
        
        # Connect to target database to enable PostGIS
        print(f"\n5️⃣ Connecting to target database '{target_db}'...")
        target_conn = psycopg2.connect(
            host=etl_config['host'],
            port=etl_config['port'],
            database=target_db,
            user=postgres_config['user'],
            password=postgres_config['password']
        )
        target_conn.autocommit = True
        target_cursor = target_conn.cursor()
        
        print("   ✅ Connected to target database successfully")
        
        # Enable PostGIS extension
        print(f"\n6️⃣ Enabling PostGIS extension...")
        try:
            target_cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            target_cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
            print("   ✅ PostGIS extensions enabled successfully")
        except Exception as e:
            print(f"   ⚠️ Warning: Could not enable PostGIS extensions: {e}")
            print("   📝 You may need to install PostGIS extension manually")
        
        # Create schemas
        print(f"\n7️⃣ Creating database schemas...")
        schemas = ['etl_pipeline', 'stuttgart', 'curitiba']
        
        for schema in schemas:
            try:
                target_cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                target_cursor.execute(f"GRANT ALL ON SCHEMA {schema} TO {target_user}")
                print(f"   ✅ Schema '{schema}' created/verified")
            except Exception as e:
                print(f"   ❌ Failed to create schema '{schema}': {e}")
        
        # Close target database connection
        target_cursor.close()
        target_conn.close()
        
        # Test connection with new user
        print(f"\n8️⃣ Testing connection with new user '{target_user}'...")
        test_conn = psycopg2.connect(
            host=etl_config['host'],
            port=etl_config['port'],
            database=target_db,
            user=target_user,
            password=etl_config['password']
        )
        test_cursor = test_conn.cursor()
        
        # Test basic operations
        test_cursor.execute("SELECT version()")
        version = test_cursor.fetchone()[0]
        print(f"   ✅ Connection test successful")
        print(f"   📋 PostgreSQL version: {version}")
        
        # Test PostGIS if available
        try:
            test_cursor.execute("SELECT PostGIS_Version()")
            postgis_version = test_cursor.fetchone()[0]
            print(f"   ✅ PostGIS version: {postgis_version}")
        except Exception as e:
            print(f"   ⚠️ PostGIS not available: {e}")
            print(f"   📝 PostGIS extension needs to be installed")
        
        test_cursor.close()
        test_conn.close()
        
        # Update Stuttgart database configuration
        print(f"\n9️⃣ Updating Stuttgart database configuration...")
        update_stuttgart_config(etl_config)
        
        print(f"\n🎉 Database setup completed successfully!")
        print(f"\n📋 Database Information:")
        print(f"   Database: {target_db}")
        print(f"   User: {target_user}")
        print(f"   Host: {etl_config['host']}")
        print(f"   Port: {etl_config['port']}")
        print(f"   Schemas: etl_pipeline, stuttgart, curitiba")
        
        print(f"\n🔧 Next Steps:")
        print(f"   1. Test the database connection in Stuttgart analysis")
        print(f"   2. Run a sample analysis to verify database integration")
        print(f"   3. Update password in production environment")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database setup failed: {e}")
        print(f"\n🔧 Troubleshooting:")
        print(f"   1. Ensure PostgreSQL is running")
        print(f"   2. Check credentials in credentials/database_credentials.yaml")
        print(f"   3. Verify PostgreSQL installation")
        return False

def update_stuttgart_config(etl_config):
    """Update Stuttgart database configuration with real credentials"""
    try:
        config_path = Path("cities/stuttgart/config/database.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Update database credentials
            config['database']['database'] = etl_config['database']
            config['database']['user'] = etl_config['user']
            config['database']['password'] = etl_config['password']
            config['database']['host'] = etl_config['host']
            config['database']['port'] = etl_config['port']
            
            # Write updated configuration
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            print(f"   ✅ Stuttgart database configuration updated")
        else:
            print(f"   ⚠️ Stuttgart database configuration not found")
            
    except Exception as e:
        print(f"   ❌ Failed to update Stuttgart config: {e}")

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
