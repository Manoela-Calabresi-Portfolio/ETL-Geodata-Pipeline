#!/usr/bin/env python3
"""
Database Manager

This module provides database setup and management functionality
for the ETL Geodata Pipeline system.
"""

import psycopg2
import sys
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database setup and connections"""
    
    def __init__(self, credentials_path=None):
        """Initialize database manager"""
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
    
    def create_database(self, database_name):
        """Create a new database"""
        if not self.credentials:
            if not self.load_credentials():
                return False
        
        postgres_config = self.credentials['database']['postgres']
        etl_config = self.credentials['database']['etl_pipeline']
        
        try:
            # Connect to default postgres database to create new one
            conn = psycopg2.connect(
                host=etl_config['host'],
                port=etl_config['port'],
                database='postgres',
                user=postgres_config['user'],
                password=postgres_config['password']
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
            exists = cursor.fetchone()
            
            if exists:
                logger.info(f"📋 Database '{database_name}' already exists")
                cursor.close()
                conn.close()
                return True
            
            # Create database
            cursor.execute(f"CREATE DATABASE {database_name}")
            logger.info(f"✅ Database '{database_name}' created successfully")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create database: {e}")
            return False
    
    def create_schemas(self, schemas=None):
        """Create database schemas"""
        if not self.connection:
            logger.error("❌ No database connection")
            return False
        
        default_schemas = schemas or ['spatial_data', 'raw_data', 'processed_data', 'results']
        
        try:
            cursor = self.connection.cursor()
            
            for schema in default_schemas:
                try:
                    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                    logger.info(f"✅ Schema '{schema}' created/verified")
                except Exception as e:
                    logger.warning(f"⚠️ Could not create schema '{schema}': {e}")
            
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create schemas: {e}")
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

def setup_database():
    """Main function to set up the database"""
    print("🚀 Setting up PostgreSQL Database for ETL Pipeline")
    print("=" * 55)
    
    db_manager = DatabaseManager()
    
    try:
        # Load credentials
        if not db_manager.load_credentials():
            return False
        
        # Create ETL database
        etl_config = db_manager.credentials['database']['etl_pipeline']
        if not db_manager.create_database(etl_config['database']):
            return False
        
        # Connect to ETL database
        if not db_manager.connect():
            return False
        
        # Create schemas
        if not db_manager.create_schemas():
            return False
        
        print("🎉 Database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False
    finally:
        db_manager.close()

if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
