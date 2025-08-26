#!/usr/bin/env python3
"""
Stuttgart City Analysis - City-Specific Spatial Analysis

This module implements Stuttgart-specific spatial analysis by inheriting
from the shared BaseCityAnalysis class. It handles Stuttgart's unique
characteristics like VVS public transport, German urban planning context,
and Stuttgart-specific mobility patterns.

The class adapts existing Stuttgart analysis scripts to the new structure
while maintaining all existing functionality and adding new capabilities.
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import yaml

# Import shared analysis core
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "spatial_analysis_core"))
from spatial_analysis_core.base_analysis import BaseCityAnalysis
from spatial_analysis_core.database import PostGISClient, DataPersistence

logger = logging.getLogger(__name__)

class StuttgartAnalysis(BaseCityAnalysis):
    """
    Stuttgart-specific spatial analysis class

    This class implements Stuttgart's unique analysis requirements:
    - VVS (Verkehrs- und Tarifverbund Stuttgart) public transport analysis
    - German urban planning context and standards
    - Stuttgart district (Stadtbezirke) analysis
    - Local data categories and naming conventions
    - Integration with existing Stuttgart analysis scripts
    """

    def __init__(self, city_config: dict):
        """
        Initialize Stuttgart analysis
        
        Args:
            city_config: Stuttgart city configuration dictionary
        """
        super().__init__("stuttgart", city_config)
        
        # Load Stuttgart-specific configurations
        self.city_config = self._load_stuttgart_configs()
        
        # Initialize database components if enabled
        self.postgis_client = None
        self.data_persistence = None
        if self.city_config.get('analysis', {}).get('processing', {}).get('enable_postgis', False):
            self._initialize_database()
    
    def _load_stuttgart_configs(self) -> Dict[str, Any]:
        """Load all Stuttgart configuration files"""
        config_dir = Path(__file__).parent.parent / "config"
        
        configs = {}
        
        # Load city configuration
        city_config_path = config_dir / "city.yaml"
        if city_config_path.exists():
            with open(city_config_path, 'r') as f:
                configs['city'] = yaml.safe_load(f)
        
        # Load districts configuration
        districts_config_path = config_dir / "districts.yaml"
        if districts_config_path.exists():
            with open(districts_config_path, 'r') as f:
                configs['districts'] = yaml.safe_load(f)
        
        # Load analysis configuration
        analysis_config_path = config_dir / "analysis.yaml"
        if analysis_config_path.exists():
            with open(analysis_config_path, 'r') as f:
                configs['analysis'] = yaml.safe_load(f)
        
        # Load database configuration
        database_config_path = config_dir / "database.yaml"
        if database_config_path.exists():
            with open(database_config_path, 'r') as f:
                configs['database'] = yaml.safe_load(f)
        
        logger.info(f"Loaded {len(configs)} Stuttgart configuration files")
        return configs
    
    def _initialize_database(self):
        """Initialize PostGIS database connection"""
        try:
            if 'database' in self.city_config:
                db_config = self.city_config['database']['database']
                self.postgis_client = PostGISClient(db_config)
                
                if self.postgis_client.connect():
                    self.data_persistence = DataPersistence(self.postgis_client)
                    logger.info("PostGIS database initialized successfully")
                else:
                    logger.warning("Failed to connect to PostGIS database")
            else:
                logger.warning("Database configuration not found")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def run_city_analysis(self) -> Dict[str, Any]:
        """
        Run Stuttgart-specific city analysis
        
        This method implements the main analysis workflow, adapting
        the existing Stuttgart analysis scripts to the new structure.
        
        Returns:
            Dictionary containing analysis results
        """
        start_time = time.time()
        results = {}
        
        try:
            logger.info("Starting Stuttgart city analysis...")
            
            # Step 1: Data Collection (adapted from 1_data_collection.py)
            logger.info("Step 1: Collecting Stuttgart data...")
            data_results = self._collect_stuttgart_data()
            results['data_collection'] = data_results
            
            # Step 2: KPI Calculation (adapted from 2_kpi_calculation.py)
            logger.info("Step 2: Calculating Stuttgart KPIs...")
            kpi_results = self._calculate_stuttgart_kpis()
            results['kpi_calculation'] = kpi_results
            
            # Step 3: Visualization (adapted from 3_visualization.py)
            logger.info("Step 3: Generating Stuttgart visualizations...")
            viz_results = self._generate_stuttgart_visualizations()
            results['visualization'] = viz_results
            
            # Step 4: Database Storage (new capability)
            if self.data_persistence:
                logger.info("Step 4: Storing results in database...")
                db_results = self._store_stuttgart_results(results)
                results['database_storage'] = db_results
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            results['execution_time_ms'] = execution_time_ms
            results['status'] = 'completed'
            
            logger.info(f"Stuttgart analysis completed in {execution_time_ms}ms")
            return results
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            results['execution_time_ms'] = execution_time_ms
            results['status'] = 'failed'
            results['error'] = str(e)
            logger.error(f"Stuttgart analysis failed: {e}")
            return results
    
    def _collect_stuttgart_data(self) -> Dict[str, Any]:
        """
        Collect Stuttgart-specific data
        
        Adapted from existing 1_data_collection.py script
        """
        try:
            data_results = {}
            
            # Load city data using shared DataLoader
            city_data = self.load_city_data()
            
            # Process GTFS VVS data (Stuttgart-specific)
            if 'external' in self.city_config.get('analysis', {}).get('data_sources', {}):
                gtfs_url = self.city_config['analysis']['data_sources']['external'].get('gtfs_vvs')
                if gtfs_url:
                    data_results['gtfs_vvs'] = self._process_stuttgart_gtfs(gtfs_url)
            
            # Process OSM data (Stuttgart-specific)
            osm_config = self.city_config.get('analysis', {}).get('data_sources', {}).get('osm', {})
            if osm_config:
                data_results['osm_data'] = self._collect_stuttgart_osm_data(osm_config)
            
            # Process district boundaries (Stuttgart-specific)
            districts_config = self.city_config.get('districts', {})
            if districts_config:
                data_results['districts'] = self._process_stuttgart_districts(districts_config)
            
            logger.info(f"Collected {len(data_results)} data types for Stuttgart")
            return data_results
            
        except Exception as e:
            logger.error(f"Failed to collect Stuttgart data: {e}")
            return {'error': str(e)}
    
    def _calculate_stuttgart_kpis(self) -> Dict[str, Any]:
        """
        Calculate Stuttgart-specific KPIs
        
        Adapted from existing 2_kpi_calculation.py script
        """
        try:
            kpi_results = {}
            
            # Calculate transport indicators (Stuttgart-specific)
            transport_config = self.city_config.get('analysis', {}).get('parameters', {}).get('public_transport', {})
            if transport_config:
                kpi_results['transport'] = self._calculate_stuttgart_transport_kpis(transport_config)
            
            # Calculate walkability indicators (Stuttgart-specific)
            walkability_config = self.city_config.get('analysis', {}).get('parameters', {}).get('walkability', {})
            if walkability_config:
                kpi_results['walkability'] = self._calculate_stuttgart_walkability_kpis(walkability_config)
            
            # Calculate green space indicators (Stuttgart-specific)
            green_config = self.city_config.get('analysis', {}).get('parameters', {}).get('green_spaces', {})
            if green_config:
                kpi_results['green_spaces'] = self._calculate_stuttgart_green_kpis(green_config)
            
            # Calculate mobility accessibility (Stuttgart-specific)
            mobility_config = self.city_config.get('analysis', {}).get('parameters', {}).get('mobility_accessibility', {})
            if mobility_config:
                kpi_results['mobility_accessibility'] = self._calculate_stuttgart_mobility_kpis(mobility_config)
            
            logger.info(f"Calculated {len(kpi_results)} KPI categories for Stuttgart")
            return kpi_results
            
        except Exception as e:
            logger.error(f"Failed to calculate Stuttgart KPIs: {e}")
            return {'error': str(e)}
    
    def _generate_stuttgart_visualizations(self) -> Dict[str, Any]:
        """
        Generate Stuttgart-specific visualizations
        
        Adapted from existing 3_visualization.py script
        """
        try:
            viz_results = {}
            
            # Generate base maps using shared VisualizationBase
            city_data = self.load_city_data()
            base_maps = self.generate_visualizations(city_data)
            viz_results['base_maps'] = base_maps
            
            # Generate Stuttgart-specific maps
            stuttgart_maps = self._create_stuttgart_specific_maps()
            viz_results['stuttgart_maps'] = stuttgart_maps
            
            # Export for QGIS (Stuttgart-specific)
            qgis_export = self._export_stuttgart_for_qgis()
            viz_results['qgis_export'] = qgis_export
            
            logger.info(f"Generated {len(viz_results)} visualization types for Stuttgart")
            return viz_results
            
        except Exception as e:
            logger.error(f"Failed to generate Stuttgart visualizations: {e}")
            return {'error': str(e)}
    
    def _store_stuttgart_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Store Stuttgart analysis results in database"""
        try:
            if not self.data_persistence:
                return {'error': 'Database not initialized'}
            
            # Store analysis results
            success = self.data_persistence.store_analysis_result(
                analysis_name="stuttgart_full_analysis",
                city_name="stuttgart",
                analysis_type="comprehensive",
                results=results,
                execution_time_ms=results.get('execution_time_ms')
            )
            
            if success:
                logger.info("Stuttgart results stored in database successfully")
                return {'status': 'stored', 'database': 'postgis'}
            else:
                logger.error("Failed to store Stuttgart results in database")
                return {'status': 'failed', 'error': 'Database storage failed'}
                
        except Exception as e:
            logger.error(f"Failed to store Stuttgart results: {e}")
            return {'error': str(e)}
    
    # Placeholder methods for Stuttgart-specific analysis
    # These will be implemented to adapt existing script logic
    
    def _process_stuttgart_gtfs(self, gtfs_url: str) -> Dict[str, Any]:
        """Process Stuttgart GTFS VVS data"""
        # TODO: Adapt existing GTFS processing logic
        return {'status': 'placeholder', 'message': 'GTFS processing to be implemented'}
    
    def _collect_stuttgart_osm_data(self, osm_config: Dict) -> Dict[str, Any]:
        """Collect Stuttgart OSM data"""
        # TODO: Adapt existing OSM collection logic
        return {'status': 'placeholder', 'message': 'OSM collection to be implemented'}
    
    def _process_stuttgart_districts(self, districts_config: Dict) -> Dict[str, Any]:
        """Process Stuttgart district boundaries"""
        # TODO: Adapt existing district processing logic
        return {'status': 'placeholder', 'message': 'District processing to be implemented'}
    
    def _calculate_stuttgart_transport_kpis(self, transport_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart transport KPIs"""
        # TODO: Adapt existing transport KPI logic
        return {'status': 'placeholder', 'message': 'Transport KPIs to be implemented'}
    
    def _calculate_stuttgart_walkability_kpis(self, walkability_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart walkability KPIs"""
        # TODO: Adapt existing walkability KPI logic
        return {'status': 'placeholder', 'message': 'Walkability KPIs to be implemented'}
    
    def _calculate_stuttgart_green_kpis(self, green_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart green space KPIs"""
        # TODO: Adapt existing green space KPI logic
        return {'status': 'placeholder', 'message': 'Green space KPIs to be implemented'}
    
    def _calculate_stuttgart_mobility_kpis(self, mobility_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart mobility accessibility KPIs"""
        # TODO: Adapt existing mobility KPI logic
        return {'status': 'placeholder', 'message': 'Mobility KPIs to be implemented'}
    
    def _create_stuttgart_specific_maps(self) -> Dict[str, Any]:
        """Create Stuttgart-specific maps"""
        # TODO: Adapt existing visualization logic
        return {'status': 'placeholder', 'message': 'Stuttgart maps to be implemented'}
    
    def _export_stuttgart_for_qgis(self) -> Dict[str, Any]:
        """Export Stuttgart data for QGIS"""
        # TODO: Adapt existing QGIS export logic
        return {'status': 'placeholder', 'message': 'QGIS export to be implemented'}
    
    def cleanup(self):
        """Cleanup Stuttgart analysis resources"""
        try:
            if self.postgis_client:
                self.postgis_client.close()
                logger.info("Stuttgart database connection closed")
            
            super().cleanup()
            
        except Exception as e:
            logger.error(f"Error during Stuttgart cleanup: {e}")

