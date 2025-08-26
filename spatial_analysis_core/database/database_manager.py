#!/usr/bin/env python3
"""
Database Manager - Database Initialization and Schema Management

This module provides database management utilities including schema creation,
table initialization, and connection management for the PostGIS database.
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for PostGIS initialization and schema management"""
    
    def __init__(self, config: dict):
        """
        Initialize database manager
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self.connection = None
    
    def create_database(self, database_name: str) -> bool:
        """
        Create a new PostgreSQL database
        
        Args:
            database_name: Name of the database to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Connect to default postgres database
            conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database='postgres',
                user=self.config['user'],
                password=self.config['password']
            )
            
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Check if database exists
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
                exists = cursor.fetchone()
                
                if not exists:
                    cursor.execute(f"CREATE DATABASE {database_name}")
                    logger.info(f"Created database: {database_name}")
                else:
                    logger.info(f"Database {database_name} already exists")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create database {database_name}: {e}")
            return False
    
    def initialize_schema(self, schema_name: str = 'etl_pipeline') -> bool:
        """
        Initialize database schema for ETL pipeline
        
        Args:
            schema_name: Name of the schema to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Connect to the target database
            conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            
            with conn.cursor() as cursor:
                # Create schema if not exists
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                
                # Create metadata tables
                self._create_metadata_tables(cursor, schema_name)
                
                # Create spatial index tables
                self._create_spatial_index_tables(cursor, schema_name)
                
                conn.commit()
                logger.info(f"Initialized schema: {schema_name}")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize schema {schema_name}: {e}")
            return False
    
    def _create_metadata_tables(self, cursor, schema_name: str):
        """Create metadata tracking tables"""
        # Data sources table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.data_sources (
                id SERIAL PRIMARY KEY,
                source_name VARCHAR(255) NOT NULL,
                source_type VARCHAR(100) NOT NULL,
                city_name VARCHAR(100) NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB,
                UNIQUE(source_name, city_name)
            )
        """)
        
        # Data tables registry
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.data_tables (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(100) NOT NULL,
                city_name VARCHAR(100) NOT NULL,
                data_type VARCHAR(100) NOT NULL,
                record_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB,
                UNIQUE(table_name, schema_name)
            )
        """)
        
        # Analysis results table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.analysis_results (
                id SERIAL PRIMARY KEY,
                analysis_name VARCHAR(255) NOT NULL,
                city_name VARCHAR(100) NOT NULL,
                analysis_type VARCHAR(100) NOT NULL,
                parameters JSONB,
                results JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER,
                status VARCHAR(50) DEFAULT 'completed'
            )
        """)
    
    def _create_spatial_index_tables(self, cursor, schema_name: str):
        """Create spatial indexing tables"""
        # Spatial index configuration
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.spatial_indexes (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(255) NOT NULL,
                schema_name VARCHAR(100) NOT NULL,
                index_name VARCHAR(255) NOT NULL,
                index_type VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information and statistics
        
        Returns:
            Dictionary with database information
        """
        try:
            conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            
            info = {}
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size
                """)
                info['database_size'] = cursor.fetchone()['size']
                
                # Table count
                cursor.execute("""
                    SELECT COUNT(*) as table_count 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                info['table_count'] = cursor.fetchone()['table_count']
                
                # Spatial table count
                cursor.execute("""
                    SELECT COUNT(*) as spatial_table_count 
                    FROM geometry_columns
                """)
                info['spatial_table_count'] = cursor.fetchone()['spatial_table_count']
                
                # PostGIS version
                cursor.execute("SELECT PostGIS_Version() as postgis_version")
                info['postgis_version'] = cursor.fetchone()['postgis_version']
                
                # PostgreSQL version
                cursor.execute("SELECT version() as postgresql_version")
                info['postgresql_version'] = cursor.fetchone()['postgresql_version']
            
            conn.close()
            return info
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {}
    
    def backup_database(self, backup_path: Path) -> bool:
        """
        Create database backup
        
        Args:
            backup_path: Path to save the backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import subprocess
            
            # Create backup directory if not exists
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build pg_dump command
            cmd = [
                'pg_dump',
                f'--host={self.config["host"]}',
                f'--port={self.config["port"]}',
                f'--username={self.config["user"]}',
                f'--dbname={self.config["database"]}',
                '--format=custom',
                '--verbose',
                f'--file={backup_path}'
            ]
            
            # Set password environment variable
            env = {'PGPASSWORD': self.config['password']}
            
            # Execute backup
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Database backup created: {backup_path}")
                return True
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create database backup: {e}")
            return False
    
    def restore_database(self, backup_path: Path) -> bool:
        """
        Restore database from backup
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import subprocess
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Build pg_restore command
            cmd = [
                'pg_restore',
                f'--host={self.config["host"]}',
                f'--port={self.config["port"]}',
                f'--username={self.config["user"]}',
                f'--dbname={self.config["database"]}',
                '--verbose',
                '--clean',
                '--if-exists',
                str(backup_path)
            ]
            
            # Set password environment variable
            env = {'PGPASSWORD': self.config['password']}
            
            # Execute restore
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Database restored from: {backup_path}")
                return True
            else:
                logger.error(f"Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        if self.connection:
            self.connection.close()
            logger.info("Database manager connection closed")

