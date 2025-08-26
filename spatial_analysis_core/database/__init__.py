"""
Database Module - PostGIS Integration

This module provides database connectivity and operations for the ETL Geodata Pipeline.
It includes PostGIS client, data models, and migration utilities for storing processed
geospatial data and analysis results.

Classes:
    PostGISClient: Main database client for PostGIS operations
    DatabaseManager: Database connection and schema management
    DataPersistence: Data storage and retrieval operations

Example:
    from spatial_analysis_core.database import PostGISClient
    
    client = PostGISClient(config)
    client.connect()
    client.store_geodata(gdf, 'amenities')
"""

# Import main classes
from .postgis_client import PostGISClient
from .database_manager import DatabaseManager
from .data_persistence import DataPersistence

__all__ = [
    'PostGISClient',
    'DatabaseManager', 
    'DataPersistence'
]

__version__ = "1.0.0"
__author__ = "ETL Geodata Pipeline Team"

