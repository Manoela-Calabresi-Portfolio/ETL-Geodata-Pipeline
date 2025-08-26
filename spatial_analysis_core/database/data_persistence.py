#!/usr/bin/env python3
"""
Data Persistence - Analysis Results and Metadata Storage

This module provides data persistence utilities for storing analysis results,
metadata, and data lineage information in the PostGIS database.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import json
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class DataPersistence:
    """Data persistence layer for analysis results and metadata"""
    
    def __init__(self, postgis_client):
        """
        Initialize data persistence layer
        
        Args:
            postgis_client: PostGISClient instance
        """
        self.client = postgis_client
    
    def store_analysis_result(self, analysis_name: str, city_name: str, 
                            analysis_type: str, results: Dict[str, Any],
                            parameters: Optional[Dict[str, Any]] = None,
                            execution_time_ms: Optional[int] = None) -> bool:
        """
        Store analysis results in database
        
        Args:
            analysis_name: Name of the analysis
            city_name: Name of the city
            analysis_type: Type of analysis (walkability, accessibility, etc.)
            results: Analysis results dictionary
            parameters: Analysis parameters used
            execution_time_ms: Execution time in milliseconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for storage
            data = {
                'analysis_name': analysis_name,
                'city_name': city_name,
                'analysis_type': analysis_type,
                'parameters': json.dumps(parameters) if parameters else None,
                'results': json.dumps(results),
                'execution_time_ms': execution_time_ms,
                'created_at': datetime.now(),
                'status': 'completed'
            }
            
            # Store in analysis_results table
            sql = """
                INSERT INTO etl_pipeline.analysis_results 
                (analysis_name, city_name, analysis_type, parameters, results, 
                 execution_time_ms, status, created_at)
                VALUES (%(analysis_name)s, %(city_name)s, %(analysis_type)s, 
                        %(parameters)s, %(results)s, %(execution_time_ms)s, 
                        %(status)s, %(created_at)s)
            """
            
            success = self.client.execute_spatial_query(sql, data)
            
            if success:
                logger.info(f"Stored analysis result: {analysis_name} for {city_name}")
                return True
            else:
                logger.error(f"Failed to store analysis result: {analysis_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to store analysis result: {e}")
            return False
    
    def store_data_source(self, source_name: str, source_type: str, city_name: str,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data source information
        
        Args:
            source_name: Name of the data source
            source_type: Type of source (OSM, GTFS, API, etc.)
            city_name: Name of the city
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for storage
            data = {
                'source_name': source_name,
                'source_type': source_type,
                'city_name': city_name,
                'metadata': json.dumps(metadata) if metadata else None,
                'last_updated': datetime.now()
            }
            
            # Upsert data source
            sql = """
                INSERT INTO etl_pipeline.data_sources 
                (source_name, source_type, city_name, metadata, last_updated)
                VALUES (%(source_name)s, %(source_type)s, %(city_name)s, 
                        %(metadata)s, %(last_updated)s)
                ON CONFLICT (source_name, city_name) 
                DO UPDATE SET 
                    last_updated = EXCLUDED.last_updated,
                    metadata = EXCLUDED.metadata
            """
            
            success = self.client.execute_spatial_query(sql, data)
            
            if success:
                logger.info(f"Stored data source: {source_name} for {city_name}")
                return True
            else:
                logger.error(f"Failed to store data source: {source_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to store data source: {e}")
            return False
    
    def store_data_table_info(self, table_name: str, schema_name: str, city_name: str,
                             data_type: str, record_count: int,
                             metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store data table information
        
        Args:
            table_name: Name of the table
            schema_name: Database schema name
            city_name: Name of the city
            data_type: Type of data (amenities, roads, districts, etc.)
            record_count: Number of records in the table
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for storage
            data = {
                'table_name': table_name,
                'schema_name': schema_name,
                'city_name': city_name,
                'data_type': data_type,
                'record_count': record_count,
                'metadata': json.dumps(metadata) if metadata else None,
                'last_updated': datetime.now()
            }
            
            # Upsert table info
            sql = """
                INSERT INTO etl_pipeline.data_tables 
                (table_name, schema_name, city_name, data_type, record_count, 
                 metadata, last_updated)
                VALUES (%(table_name)s, %(schema_name)s, %(city_name)s, 
                        %(data_type)s, %(record_count)s, %(metadata)s, %(last_updated)s)
                ON CONFLICT (table_name, schema_name) 
                DO UPDATE SET 
                    record_count = EXCLUDED.record_count,
                    metadata = EXCLUDED.metadata,
                    last_updated = EXCLUDED.last_updated
            """
            
            success = self.client.execute_spatial_query(sql, data)
            
            if success:
                logger.info(f"Stored table info: {table_name} in {schema_name}")
                return True
            else:
                logger.error(f"Failed to store table info: {table_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to store table info: {e}")
            return False
    
    def get_analysis_history(self, city_name: Optional[str] = None,
                           analysis_type: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get analysis execution history
        
        Args:
            city_name: Filter by city name
            analysis_type: Filter by analysis type
            limit: Maximum number of results
            
        Returns:
            List of analysis results
        """
        try:
            # Build query
            sql = """
                SELECT * FROM etl_pipeline.analysis_results 
                WHERE 1=1
            """
            params = {}
            
            if city_name:
                sql += " AND city_name = %(city_name)s"
                params['city_name'] = city_name
            
            if analysis_type:
                sql += " AND analysis_type = %(analysis_type)s"
                params['analysis_type'] = analysis_type
            
            sql += " ORDER BY created_at DESC LIMIT %(limit)s"
            params['limit'] = limit
            
            results = self.client.execute_spatial_query(sql, params)
            
            if results:
                # Parse JSON fields
                for result in results:
                    if result.get('parameters'):
                        result['parameters'] = json.loads(result['parameters'])
                    if result.get('results'):
                        result['results'] = json.loads(result['results'])
                
                logger.info(f"Retrieved {len(results)} analysis results")
                return results
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get analysis history: {e}")
            return []
    
    def get_data_sources(self, city_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get data sources information
        
        Args:
            city_name: Filter by city name
            
        Returns:
            List of data sources
        """
        try:
            sql = """
                SELECT * FROM etl_pipeline.data_sources 
                WHERE 1=1
            """
            params = {}
            
            if city_name:
                sql += " AND city_name = %(city_name)s"
                params['city_name'] = city_name
            
            sql += " ORDER BY last_updated DESC"
            
            results = self.client.execute_spatial_query(sql, params)
            
            if results:
                # Parse JSON fields
                for result in results:
                    if result.get('metadata'):
                        result['metadata'] = json.loads(result['metadata'])
                
                logger.info(f"Retrieved {len(results)} data sources")
                return results
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get data sources: {e}")
            return []
    
    def get_data_tables(self, city_name: Optional[str] = None,
                       data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get data tables information
        
        Args:
            city_name: Filter by city name
            data_type: Filter by data type
            
        Returns:
            List of data tables
        """
        try:
            sql = """
                SELECT * FROM etl_pipeline.data_tables 
                WHERE 1=1
            """
            params = {}
            
            if city_name:
                sql += " AND city_name = %(city_name)s"
                params['city_name'] = city_name
            
            if data_type:
                sql += " AND data_type = %(data_type)s"
                params['data_type'] = data_type
            
            sql += " ORDER BY last_updated DESC"
            
            results = self.client.execute_spatial_query(sql, params)
            
            if results:
                # Parse JSON fields
                for result in results:
                    if result.get('metadata'):
                        result['metadata'] = json.loads(result['metadata'])
                
                logger.info(f"Retrieved {len(results)} data tables")
                return results
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get data tables: {e}")
            return []
    
    def create_data_lineage(self, input_sources: List[str], output_tables: List[str],
                           analysis_name: str, city_name: str) -> bool:
        """
        Create data lineage tracking
        
        Args:
            input_sources: List of input data source names
            output_tables: List of output table names
            analysis_name: Name of the analysis
            city_name: Name of the city
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate lineage ID
            lineage_id = hashlib.md5(
                f"{analysis_name}_{city_name}_{datetime.now().isoformat()}".encode()
            ).hexdigest()
            
            # Store lineage information
            lineage_data = {
                'lineage_id': lineage_id,
                'analysis_name': analysis_name,
                'city_name': city_name,
                'input_sources': json.dumps(input_sources),
                'output_tables': json.dumps(output_tables),
                'created_at': datetime.now()
            }
            
            # Create lineage table if not exists
            create_sql = """
                CREATE TABLE IF NOT EXISTS etl_pipeline.data_lineage (
                    lineage_id VARCHAR(32) PRIMARY KEY,
                    analysis_name VARCHAR(255) NOT NULL,
                    city_name VARCHAR(100) NOT NULL,
                    input_sources JSONB,
                    output_tables JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            
            self.client.execute_spatial_query(create_sql)
            
            # Insert lineage record
            insert_sql = """
                INSERT INTO etl_pipeline.data_lineage 
                (lineage_id, analysis_name, city_name, input_sources, output_tables, created_at)
                VALUES (%(lineage_id)s, %(analysis_name)s, %(city_name)s, 
                        %(input_sources)s, %(output_tables)s, %(created_at)s)
            """
            
            success = self.client.execute_spatial_query(insert_sql, lineage_data)
            
            if success:
                logger.info(f"Created data lineage: {lineage_id}")
                return True
            else:
                logger.error(f"Failed to create data lineage")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create data lineage: {e}")
            return False
    
    def get_data_lineage(self, city_name: Optional[str] = None,
                        analysis_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get data lineage information
        
        Args:
            city_name: Filter by city name
            analysis_name: Filter by analysis name
            
        Returns:
            List of data lineage records
        """
        try:
            sql = """
                SELECT * FROM etl_pipeline.data_lineage 
                WHERE 1=1
            """
            params = {}
            
            if city_name:
                sql += " AND city_name = %(city_name)s"
                params['city_name'] = city_name
            
            if analysis_name:
                sql += " AND analysis_name = %(analysis_name)s"
                params['analysis_name'] = analysis_name
            
            sql += " ORDER BY created_at DESC"
            
            results = self.client.execute_spatial_query(sql, params)
            
            if results:
                # Parse JSON fields
                for result in results:
                    if result.get('input_sources'):
                        result['input_sources'] = json.loads(result['input_sources'])
                    if result.get('output_tables'):
                        result['output_tables'] = json.loads(result['output_tables'])
                
                logger.info(f"Retrieved {len(results)} data lineage records")
                return results
            else:
                return []
                
        except Exception as e:
            logger.error(f"Failed to get data lineage: {e}")
            return []

