#!/usr/bin/env python3
"""
PostGIS Client - Geospatial Database Operations

This module provides a comprehensive PostGIS client for storing and querying
geospatial data from the ETL Geodata Pipeline. It handles spatial operations,
data validation, and efficient storage of large geodatasets.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class PostGISClient:
    """PostGIS client for geospatial database operations"""
    
    def __init__(self, config: dict):
        """
        Initialize PostGIS client
        
        Args:
            config: Database configuration dictionary containing:
                - host: Database host
                - port: Database port
                - database: Database name
                - user: Username
                - password: Password
                - schema: Default schema (default: 'public')
        """
        self.config = config
        self.connection = None
        self.engine = None
        self.schema = config.get('schema', 'public')
        
        # Validate required config
        required_fields = ['host', 'port', 'database', 'user', 'password']
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required database config fields: {missing_fields}")
    
    def connect(self) -> bool:
        """
        Establish database connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create SQLAlchemy engine for pandas operations
            connection_string = (
                f"postgresql://{self.config['user']}:{self.config['password']}"
                f"@{self.config['host']}:{self.config['port']}/{self.config['database']}"
            )
            
            self.engine = create_engine(connection_string)
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            # Create direct psycopg2 connection for spatial operations
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            
            # Enable PostGIS extension if not exists
            self._ensure_postgis_extension()
            
            logger.info(f"Successfully connected to PostGIS database: {self.config['database']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostGIS database: {e}")
            return False
    
    def _ensure_postgis_extension(self):
        """Ensure PostGIS extension is enabled"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                self.connection.commit()
                logger.info("PostGIS extension enabled")
        except Exception as e:
            logger.warning(f"Could not enable PostGIS extension: {e}")
    
    def create_spatial_table(self, table_name: str, gdf: gpd.GeoDataFrame, 
                           if_exists: str = 'replace') -> bool:
        """
        Create spatial table from GeoDataFrame
        
        Args:
            table_name: Name of the table to create
            gdf: GeoDataFrame to store
            if_exists: Action if table exists ('replace', 'append', 'fail')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.engine:
                raise ConnectionError("Database not connected. Call connect() first.")
            
            # Ensure geometry column is properly formatted
            if 'geometry' in gdf.columns:
                # Convert to WGS84 for storage (standard for PostGIS)
                gdf = gdf.to_crs(epsg=4326)
            
            # Store in database
            gdf.to_postgis(
                name=table_name,
                con=self.engine,
                schema=self.schema,
                if_exists=if_exists,
                index=True,
                index_label='id'
            )
            
            logger.info(f"Successfully created spatial table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create spatial table {table_name}: {e}")
            return False
    
    def store_geodata(self, gdf: gpd.GeoDataFrame, table_name: str, 
                      city_name: str, data_type: str, 
                      metadata: Optional[Dict] = None) -> bool:
        """
        Store geospatial data with metadata
        
        Args:
            gdf: GeoDataFrame to store
            table_name: Name of the table
            city_name: Name of the city
            data_type: Type of data (amenities, roads, districts, etc.)
            metadata: Additional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata columns
            gdf_copy = gdf.copy()
            gdf_copy['city_name'] = city_name
            gdf_copy['data_type'] = data_type
            gdf_copy['imported_at'] = datetime.now()
            
            if metadata:
                gdf_copy['metadata'] = json.dumps(metadata)
            
            # Create table
            return self.create_spatial_table(table_name, gdf_copy, if_exists='replace')
            
        except Exception as e:
            logger.error(f"Failed to store geodata: {e}")
            return False
    
    def query_spatial_data(self, table_name: str, city_name: Optional[str] = None,
                          bbox: Optional[List[float]] = None,
                          limit: Optional[int] = None) -> Optional[gpd.GeoDataFrame]:
        """
        Query spatial data from database
        
        Args:
            table_name: Name of the table to query
            city_name: Filter by city name
            bbox: Bounding box filter [min_lon, min_lat, max_lon, max_lat]
            limit: Maximum number of records to return
            
        Returns:
            GeoDataFrame with results or None if failed
        """
        try:
            if not self.engine:
                raise ConnectionError("Database not connected. Call connect() first.")
            
            # Build query
            query = f"SELECT * FROM {self.schema}.{table_name}"
            conditions = []
            
            if city_name:
                conditions.append(f"city_name = '{city_name}'")
            
            if bbox:
                # Spatial filter using PostGIS ST_Intersects
                bbox_geom = f"ST_GeomFromText('POLYGON(({bbox[0]} {bbox[1]}, {bbox[0]} {bbox[3]}, {bbox[2]} {bbox[3]}, {bbox[2]} {bbox[1]}, {bbox[0]} {bbox[1]}))', 4326)"
                conditions.append(f"ST_Intersects(geometry, {bbox_geom})")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            gdf = gpd.read_postgis(query, self.engine, geom_col='geometry')
            
            logger.info(f"Retrieved {len(gdf)} records from {table_name}")
            return gdf
            
        except Exception as e:
            logger.error(f"Failed to query spatial data: {e}")
            return None
    
    def execute_spatial_query(self, sql: str, params: Optional[Dict] = None) -> Optional[List[Dict]]:
        """
        Execute custom spatial SQL query
        
        Args:
            sql: SQL query string
            params: Query parameters
            
        Returns:
            List of result dictionaries or None if failed
        """
        try:
            if not self.connection:
                raise ConnectionError("Database not connected. Call connect() first.")
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                
                results = cursor.fetchall()
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Failed to execute spatial query: {e}")
            return None
    
    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """
        Get information about a spatial table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information or None if failed
        """
        try:
            if not self.connection:
                raise ConnectionError("Database not connected. Call connect() first.")
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get table structure
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s AND table_schema = %s
                    ORDER BY ordinal_position
                """, (table_name, self.schema))
                
                columns = cursor.fetchall()
                
                # Get spatial information
                cursor.execute("""
                    SELECT f_geometry_column, coord_dimension, srid
                    FROM geometry_columns 
                    WHERE f_table_name = %s AND f_table_schema = %s
                """, (table_name, self.schema))
                
                spatial_info = cursor.fetchone()
                
                # Get record count
                cursor.execute(f"SELECT COUNT(*) FROM {self.schema}.{table_name}")
                record_count = cursor.fetchone()['count']
                
                return {
                    'table_name': table_name,
                    'schema': self.schema,
                    'columns': [dict(col) for col in columns],
                    'spatial_info': dict(spatial_info) if spatial_info else None,
                    'record_count': record_count
                }
                
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return None
    
    def list_tables(self) -> List[str]:
        """
        List all spatial tables in the database
        
        Returns:
            List of table names
        """
        try:
            if not self.connection:
                raise ConnectionError("Database not connected. Call connect() first.")
            
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT f_table_name 
                    FROM geometry_columns 
                    WHERE f_table_schema = %s
                    ORDER BY f_table_name
                """, (self.schema,))
                
                tables = [row[0] for row in cursor.fetchall()]
                logger.info(f"Found {len(tables)} spatial tables")
                return tables
                
        except Exception as e:
            logger.error(f"Failed to list tables: {e}")
            return []
    
    def close(self):
        """Close database connections"""
        try:
            if self.connection:
                self.connection.close()
                logger.info("Database connection closed")
            
            if self.engine:
                self.engine.dispose()
                logger.info("Database engine disposed")
                
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

