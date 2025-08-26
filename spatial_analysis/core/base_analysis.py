#!/usr/bin/env python3
"""
Base City Analysis Class

This is the foundation class for all city-specific spatial analysis.
It provides common functionality while allowing cities to customize
their analysis for unique characteristics.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseCityAnalysis(ABC):
    """
    Base class for all city analysis
    
    This class provides:
    - Common data loading methods
    - Standard KPI calculation framework
    - Basic visualization capabilities
    - Error handling and logging
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
        self.data_loader = DataLoader(city_config)
        self.kpi_calculator = KPICalculator(city_config)
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
    
    def calculate_basic_kpis(self) -> pd.DataFrame:
        """
        Calculate basic KPIs using shared logic
        
        Returns:
            DataFrame with basic KPIs
        """
        try:
            logger.info(f"Calculating basic KPIs for {self.city_name}")
            kpis = self.kpi_calculator.calculate_basic_indicators()
            logger.info(f"Successfully calculated {len(kpis)} basic KPIs for {self.city_name}")
            return kpis
        except Exception as e:
            logger.error(f"Failed to calculate basic KPIs for {self.city_name}: {e}")
            raise
    
    def generate_base_maps(self) -> Dict[str, str]:
        """
        Generate base maps using shared logic
        
        Returns:
            Dictionary mapping map names to file paths
        """
        try:
            logger.info(f"Generating base maps for {self.city_name}")
            maps = self.visualizer.create_base_maps()
            logger.info(f"Successfully generated {len(maps)} base maps for {self.city_name}")
            return maps
        except Exception as e:
            logger.error(f"Failed to generate base maps for {self.city_name}: {e}")
            raise
    
    @abstractmethod
    def run_city_analysis(self) -> Dict[str, Any]:
        """
        Abstract method that each city must implement
        
        This is where city-specific analysis logic goes.
        Each city can customize this method for their unique needs.
        
        Returns:
            Dictionary containing analysis results
        """
        pass
    
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
        
        # Save results based on type
        for key, value in results.items():
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
        
        return str(output_path)
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run the complete analysis pipeline for the city
        
        This method orchestrates the full analysis:
        1. Load data
        2. Calculate basic KPIs
        3. Run city-specific analysis
        4. Generate visualizations
        5. Save results
        
        Returns:
            Complete analysis results
        """
        try:
            logger.info(f"Starting full analysis for {self.city_name}")
            
            # Step 1: Load city data
            city_data = self.load_city_data()
            
            # Step 2: Calculate basic KPIs
            basic_kpis = self.calculate_basic_kpis()
            
            # Step 3: Run city-specific analysis
            city_specific_results = self.run_city_analysis()
            
            # Step 4: Generate visualizations
            visualizations = self.generate_base_maps()
            
            # Step 5: Combine all results
            all_results = {
                'city_data': city_data,
                'basic_kpis': basic_kpis,
                'city_specific_results': city_specific_results,
                'visualizations': visualizations,
                'metadata': {
                    'city_name': self.city_name,
                    'analysis_timestamp': pd.Timestamp.now().isoformat(),
                    'config_used': self.city_config
                }
            }
            
            # Step 6: Save results
            output_path = self.save_results(all_results)
            all_results['output_path'] = output_path
            
            logger.info(f"Successfully completed full analysis for {self.city_name}")
            return all_results
            
        except Exception as e:
            logger.error(f"Failed to complete analysis for {self.city_name}: {e}")
            raise

