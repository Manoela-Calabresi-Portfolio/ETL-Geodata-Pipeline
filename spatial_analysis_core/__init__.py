"""
Spatial Analysis Core Module

This module provides shared, reusable components for city-specific spatial analysis.
All city analysis scripts inherit from these base classes to ensure consistency
while allowing customization for unique city characteristics.

Classes:
    BaseCityAnalysis: Abstract base class for all city analysis
    DataLoader: Enhanced data loader with multi-source support
    VisualizationBase: Common visualization methods
    GeoCuritibaClient: Client for Geo Curitiba ArcGIS REST services

Example:
    from spatial_analysis_core.base_analysis import BaseCityAnalysis
    
    class MyCityAnalysis(BaseCityAnalysis):
        def run_city_analysis(self):
            # Implement city-specific analysis
            return {'custom_metric': 42}
"""

# Import main classes
from .base_analysis import BaseCityAnalysis
from .data_loader import DataLoader
from .visualization_base import VisualizationBase

# Import database components
from .database import PostGISClient, DatabaseManager, DataPersistence

__all__ = [
    'BaseCityAnalysis',
    'DataLoader',
    'VisualizationBase',
    'PostGISClient',
    'DatabaseManager',
    'DataPersistence'
]

__version__ = "1.0.0"
__author__ = "ETL Geodata Pipeline Team"
