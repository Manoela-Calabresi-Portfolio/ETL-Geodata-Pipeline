"""
Stuttgart Spatial Analysis Module

This module provides city-specific spatial analysis for Stuttgart, Germany.
It inherits from the shared analysis core while implementing Stuttgart-specific
analysis logic and data handling.

Classes:
    StuttgartAnalysis: Main Stuttgart analysis class inheriting from BaseCityAnalysis
    StuttgartDataCollection: Stuttgart-specific data collection methods
    StuttgartKPICalculation: Stuttgart-specific KPI calculation methods
    StuttgartVisualization: Stuttgart-specific visualization methods

Example:
    from cities.stuttgart.spatial_analysis import StuttgartAnalysis
    
    analysis = StuttgartAnalysis(config)
    results = analysis.run_full_analysis()
"""

from .stuttgart_analysis import StuttgartAnalysis

__all__ = ['StuttgartAnalysis']
__version__ = "1.0.0"
__author__ = "ETL Geodata Pipeline Team"

