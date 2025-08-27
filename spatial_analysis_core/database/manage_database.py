#!/usr/bin/env python3
"""
Database Management CLI

Command-line interface for managing PostgreSQL database and PostGIS
for the ETL Geodata Pipeline system.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.database_manager import DatabaseManager
from database.postgis_manager import PostGISManager

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Database Management CLI for ETL Geodata Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_database.py setup                    # Setup database and schemas
  python manage_database.py enable-postgis          # Enable PostGIS extension
  python manage_database.py copy-postgis            # Copy PostGIS files
  python manage_database.py check-postgis           # Check PostGIS status
  python manage_database.py test-connection         # Test database connection
        """
    )
    
    parser.add_argument(
        'command',
        choices=['setup', 'enable-postgis', 'copy-postgis', 'check-postgis', 'test-connection'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--database', '-d',
        help='Database name (default: from credentials)'
    )
    
    parser.add_argument(
        '--credentials', '-c',
        help='Path to credentials file (default: credentials/database_credentials.yaml)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'setup':
            print("🚀 Setting up PostgreSQL Database")
            print("=" * 40)
            
            db_manager = DatabaseManager(args.credentials)
            if db_manager.load_credentials():
                etl_config = db_manager.credentials['database']['etl_pipeline']
                database_name = args.database or etl_config['database']
                
                if db_manager.create_database(database_name):
                    if db_manager.connect(database_name):
                        if db_manager.create_schemas():
                            print("🎉 Database setup completed successfully!")
                            return 0
                        else:
                            print("❌ Failed to create schemas")
                            return 1
                    else:
                        print("❌ Failed to connect to database")
                        return 1
                else:
                    print("❌ Failed to create database")
                    return 1
            else:
                print("❌ Failed to load credentials")
                return 1
        
        elif args.command == 'enable-postgis':
            print("🚀 Enabling PostGIS Extension")
            print("=" * 35)
            
            postgis_manager = PostGISManager(args.credentials)
            if postgis_manager.load_credentials():
                if postgis_manager.connect(args.database):
                    if postgis_manager.enable_postgis():
                        print("🎉 PostGIS enabled successfully!")
                        return 0
                    else:
                        print("❌ Failed to enable PostGIS")
                        return 1
                else:
                    print("❌ Failed to connect to database")
                    return 1
            else:
                print("❌ Failed to load credentials")
                return 1
        
        elif args.command == 'copy-postgis':
            print("🚀 Copying PostGIS Files")
            print("=" * 30)
            
            postgis_manager = PostGISManager(args.credentials)
            if postgis_manager.copy_postgis_files():
                print("🎉 PostGIS files copied successfully!")
                print("💡 You may need to restart PostgreSQL service")
                return 0
            else:
                print("❌ Failed to copy PostGIS files")
                return 1
        
        elif args.command == 'check-postgis':
            print("🔍 Checking PostGIS Status")
            print("=" * 30)
            
            postgis_manager = PostGISManager(args.credentials)
            if postgis_manager.load_credentials():
                if postgis_manager.connect(args.database):
                    if postgis_manager.check_postgis_status():
                        print("✅ PostGIS is working correctly!")
                        return 0
                    else:
                        print("❌ PostGIS is not working")
                        return 1
                else:
                    print("❌ Failed to connect to database")
                    return 1
            else:
                print("❌ Failed to load credentials")
                return 1
        
        elif args.command == 'test-connection':
            print("🔍 Testing Database Connection")
            print("=" * 35)
            
            db_manager = DatabaseManager(args.credentials)
            if db_manager.load_credentials():
                if db_manager.connect(args.database):
                    print("✅ Database connection successful!")
                    return 0
                else:
                    print("❌ Database connection failed")
                    return 1
            else:
                print("❌ Failed to load credentials")
                return 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
