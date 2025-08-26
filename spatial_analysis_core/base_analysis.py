#!/usr/bin/env python3
"""
Base City Analysis Class - Simple Base Class with Common Utilities

This is the foundation class for all city-specific spatial analysis.
It provides common functionality while allowing cities to customize
their analysis for unique characteristics.

NO generic KPIs - each city handles their own analysis logic.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

# Import our enhanced components
from .data_loader import DataLoader
from .visualization_base import VisualizationBase

logger = logging.getLogger(__name__)

class BaseCityAnalysis(ABC):
    """
    Simple base class for all city analysis
    
    This class provides:
    - Common data loading methods
    - Standard result saving framework
    - Basic visualization capabilities
    - Error handling and logging
    - NO generic KPI calculations
    """
    
    def __init__(self, city_name: str, city_config: dict):
        """
        Initialize base city analysis
        
        Args:
            city_name: Name of the city (e.g., 'stuttgart', 'curitiba')
            city_config: City-specific configuration dictionary
        """
        self.city_name = city_name
        self.city_config = city_config
        
        # Initialize shared components
        self.data_loader = DataLoader(city_config)
        self.visualizer = VisualizationBase(city_config)
        
        # Setup logging for this city
        self._setup_logging()
        
        logger.info(f"Initialized analysis for {city_name}")
    
    def _setup_logging(self):
        """Setup city-specific logging"""
        log_dir = Path(f"cities/{self.city_name}/spatial_analysis/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure file handler for this city
        file_handler = logging.FileHandler(log_dir / f"{self.city_name}_analysis.log")
        file_handler.setLevel(logging.INFO)
        
        # Add to logger
        logger.addHandler(file_handler)
    
    def load_city_data(self) -> Dict[str, Any]:
        """
        Load all city data using shared logic
        
        Returns:
            Dictionary containing all loaded data layers
        """
        try:
            logger.info(f"Loading data for {self.city_name}")
            data = self.data_loader.load_all_layers()
            logger.info(f"Successfully loaded {len(data)} data layers for {self.city_name}")
            return data
        except Exception as e:
            logger.error(f"Failed to load data for {self.city_name}: {e}")
            raise
    
    def test_data_sources(self) -> Dict[str, bool]:
        """
        Test all configured data sources
        
        Returns:
            Dictionary with test results for each data source
        """
        try:
            logger.info(f"Testing data sources for {self.city_name}")
            results = self.data_loader.test_data_sources()
            logger.info(f"Data source test results: {results}")
            return results
        except Exception as e:
            logger.error(f"Failed to test data sources for {self.city_name}: {e}")
            raise
    
    def save_results(self, results: Dict[str, Any], output_dir: Optional[str] = None) -> str:
        """
        Save analysis results to city-specific output directory
        
        Args:
            results: Analysis results to save
            output_dir: Optional custom output directory
            
        Returns:
            Path to saved results
        """
        if output_dir is None:
            output_dir = f"cities/{self.city_name}/spatial_analysis/outputs"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving results to {output_path}")
        
        # Save results based on type
        for key, value in results.items():
            if value is None:
                continue
                
            try:
                if isinstance(value, pd.DataFrame):
                    file_path = output_path / f"{key}.parquet"
                    value.to_parquet(file_path)
                    logger.info(f"Saved {key} to {file_path}")
                    
                elif isinstance(value, gpd.GeoDataFrame):
                    file_path = output_path / f"{key}.geojson"
                    value.to_file(file_path, driver='GeoJSON')
                    logger.info(f"Saved {key} to {file_path}")
                    
                elif isinstance(value, dict):
                    file_path = output_path / f"{key}.json"
                    import json
                    with open(file_path, 'w') as f:
                        json.dump(value, f, indent=2)
                    logger.info(f"Saved {key} to {file_path}")
                    
                elif isinstance(value, (str, int, float, bool)):
                    file_path = output_path / f"{key}.txt"
                    with open(file_path, 'w') as f:
                        f.write(str(value))
                    logger.info(f"Saved {key} to {file_path}")
                    
            except Exception as e:
                logger.error(f"Failed to save {key}: {e}")
        
        return str(output_path)
    
    def generate_visualizations(self, city_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate visualizations using shared logic
        
        Args:
            city_data: Loaded city data
            
        Returns:
            Dictionary mapping visualization names to file paths
        """
        try:
            logger.info(f"Generating visualizations for {self.city_name}")
            visualizations = self.visualizer.create_base_maps(city_data)
            logger.info(f"Successfully generated {len(visualizations)} visualizations for {self.city_name}")
            return visualizations
        except Exception as e:
            logger.error(f"Failed to generate visualizations for {self.city_name}: {e}")
            raise
    
    @abstractmethod
    def run_city_analysis(self) -> Dict[str, Any]:
        """
        Abstract method that each city MUST implement
        
        This is where city-specific analysis logic goes.
        Each city handles their own data categories and analysis.
        NO generic KPIs - each city implements their own logic.
        
        Returns:
            Dictionary containing analysis results
        """
        pass
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline for the city
        
        This method orchestrates the full analysis:
        1. Load data
        2. Run city-specific analysis
        3. Generate visualizations
        4. Save results
        
        Returns:
            Complete analysis results
        """
        try:
            logger.info(f"Starting full analysis for {self.city_name}")
            
            # Step 1: Load city data
            city_data = self.load_city_data()
            
            # Step 2: Run city-specific analysis (implemented by each city)
            city_specific_results = self.run_city_analysis()
            
            # Step 3: Generate visualizations
            visualizations = self.generate_visualizations(city_data)
            
            # Step 4: Combine all results
            all_results = {
                'city_data': city_data,
                'city_specific_results': city_specific_results,
                'visualizations': visualizations,
                'metadata': {
                    'city_name': self.city_name,
                    'analysis_timestamp': pd.Timestamp.now().isoformat(),
                    'config_used': self.city_config
                }
            }
            
            # Step 5: Save results
            output_path = self.save_results(all_results)
            all_results['output_path'] = output_path
            
            logger.info(f"Successfully completed full analysis for {self.city_name}")
            return all_results
            
        except Exception as e:
            logger.error(f"Failed to complete analysis for {self.city_name}: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources and connections"""
        try:
            if hasattr(self, 'data_loader'):
                self.data_loader.close()
            logger.info(f"Cleanup completed for {self.city_name}")
        except Exception as e:
            logger.error(f"Cleanup failed for {self.city_name}: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup()

