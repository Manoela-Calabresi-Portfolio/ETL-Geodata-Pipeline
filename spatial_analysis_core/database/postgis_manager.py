#!/usr/bin/env python3
"""
PostGIS Manager

This module provides PostGIS extension management and spatial functionality
for the ETL Geodata Pipeline system.
"""

import psycopg2
import sys
from pathlib import Path
import yaml
import logging
import shutil

logger = logging.getLogger(__name__)

class PostGISManager:
    """Manages PostGIS extension and spatial functionality"""
    
    def __init__(self, credentials_path=None):
        """Initialize PostGIS manager"""
        self.credentials_path = credentials_path or Path("credentials/database_credentials.yaml")
        self.credentials = None
        self.connection = None
        
    def load_credentials(self):
        """Load database credentials from file"""
        if not self.credentials_path.exists():
            logger.error("❌ Credentials file not found!")
            return False
        
        try:
            with open(self.credentials_path, 'r') as f:
                self.credentials = yaml.safe_load(f)
            
            logger.info("✅ Credentials loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load credentials: {e}")
            return False
    
    def connect(self, database_name=None):
        """Connect to PostgreSQL database"""
        if not self.credentials:
            if not self.load_credentials():
                return False
        
        postgres_config = self.credentials['database']['postgres']
        etl_config = self.credentials['database']['etl_pipeline']
        
        # Use specified database or default to ETL database
        db_name = database_name or etl_config['database']
        
        try:
            self.connection = psycopg2.connect(
                host=etl_config['host'],
                port=etl_config['port'],
                database=db_name,
                user=postgres_config['user'],
                password=postgres_config['password']
            )
            self.connection.autocommit = True
            logger.info(f"✅ Connected to database '{db_name}' successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    def check_postgis_status(self):
        """Check if PostGIS is working"""
        if not self.connection:
            logger.error("❌ No database connection")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Try to call PostGIS function
            cursor.execute("SELECT PostGIS_Version()")
            version = cursor.fetchone()[0]
            logger.info(f"✅ PostGIS is working: {version}")
            
            # Test spatial functions
            cursor.execute("SELECT ST_AsText(ST_GeomFromText('POINT(0 0)'))")
            result = cursor.fetchone()[0]
            logger.info(f"✅ Spatial functions working: {result}")
            
            cursor.close()
            return True
            
        except Exception as e:
            logger.info(f"📝 PostGIS not available: {e}")
            return False
    
    def enable_postgis(self):
        """Enable PostGIS extension"""
        if not self.connection:
            logger.error("❌ No database connection")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Check if PostGIS is already enabled
            if self.check_postgis_status():
                logger.info("✅ PostGIS is already enabled")
                return True
            
            # Try to enable PostGIS extension
            logger.info("🔧 Enabling PostGIS extension...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            
            # Verify it's working
            if self.check_postgis_status():
                logger.info("🎉 PostGIS enabled successfully!")
                return True
            else:
                logger.error("❌ PostGIS extension enabled but not working")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to enable PostGIS: {e}")
            return False
    
    def copy_postgis_files(self, source_path=None, target_path=None):
        """Copy PostGIS files to PostgreSQL extension directory"""
        if not source_path:
            # Default PostGIS source path
            source_path = Path("C:/Program Files/postgis-3.6.0rc2/postgis-3.6.0rc2")
        
        if not target_path:
            # Default PostgreSQL 17 extension path
            target_path = Path("C:/Program Files/PostgreSQL/17/share/extension")
        
        print(f"🚀 Copying PostGIS Files to PostgreSQL Extension Directory")
        print(f"📁 Source: {source_path}")
        print(f"📁 Target: {target_path}")
        
        # Check if source exists
        if not source_path.exists():
            logger.error(f"❌ PostGIS source directory not found: {source_path}")
            return False
        
        # Check if target exists
        if not target_path.exists():
            logger.error(f"❌ PostgreSQL extension directory not found: {target_path}")
            return False
        
        try:
            # Find PostGIS extension files
            extension_files = []
            for file_path in source_path.rglob("*"):
                if file_path.is_file():
                    if file_path.suffix in ['.control', '.sql', '.so', '.dll']:
                        if 'postgis' in file_path.name.lower():
                            extension_files.append(file_path)
            
            if not extension_files:
                logger.error("❌ No PostGIS extension files found")
                return False
            
            # Copy files
            copied_count = 0
            for source_file in extension_files:
                try:
                    # Determine target path
                    target_file = target_path / source_file.name
                    
                    # Copy file
                    shutil.copy2(source_file, target_file)
                    logger.info(f"✅ Copied: {source_file.name}")
                    copied_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to copy {source_file.name}: {e}")
            
            logger.info(f"📊 Successfully copied: {copied_count} files")
            return copied_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to copy PostGIS files: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("🔌 Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

def enable_postgis():
    """Main function to enable PostGIS"""
    print("🚀 Enabling PostGIS Extension")
    print("=" * 35)
    
    postgis_manager = PostGISManager()
    
    try:
        # Load credentials
        if not postgis_manager.load_credentials():
            return False
        
        # Connect to database
        if not postgis_manager.connect():
            return False
        
        # Enable PostGIS
        if not postgis_manager.enable_postgis():
            return False
        
        print("🎉 PostGIS enabled successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to enable PostGIS: {e}")
        return False
    finally:
        postgis_manager.close()

def copy_postgis_files():
    """Main function to copy PostGIS files"""
    print("🚀 Copying PostGIS Files")
    print("=" * 30)
    
    postgis_manager = PostGISManager()
    
    try:
        if postgis_manager.copy_postgis_files():
            print("🎉 PostGIS files copied successfully!")
            print("💡 You may need to restart PostgreSQL service")
            return True
        else:
            print("❌ Failed to copy PostGIS files")
            return False
            
    except Exception as e:
        print(f"❌ Error copying PostGIS files: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "copy":
        success = copy_postgis_files()
    else:
        success = enable_postgis()
    
    sys.exit(0 if success else 1)
