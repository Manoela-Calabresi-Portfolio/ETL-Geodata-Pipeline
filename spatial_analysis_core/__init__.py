"""
Spatial Analysis Core Module

This module provides shared functionality for the ETL Geodata Pipeline system,
including database management and data loading capabilities.
"""

from .database.database_manager import DatabaseManager
from .database.postgis_manager import PostGISManager
from .data_loader import DataLoader, extract_city_osm_data

__all__ = ['DatabaseManager', 'PostGISManager', 'DataLoader', 'extract_city_osm_data']
