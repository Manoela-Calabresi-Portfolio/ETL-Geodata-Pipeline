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
        logger.info("Processing Stuttgart GTFS VVS data...")
        
        try:
            # Import GTFS processing utilities
            sys.path.append(str(Path(__file__).parent.parent.parent.parent / "spatial_analysis" / "scripts" / "utils"))
            from gtfs_processor import process_gtfs_data
            
            # Process GTFS data
            gtfs_results = process_gtfs_data({'gtfs_url': gtfs_url})
            
            logger.info("GTFS VVS data processed successfully")
            return {
                'status': 'success',
                'gtfs_results': gtfs_results
            }
            
        except Exception as e:
            logger.error(f"Error processing GTFS data: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _collect_stuttgart_osm_data(self, osm_config: Dict) -> Dict[str, Any]:
        """Collect Stuttgart OSM data"""
        logger.info("Collecting Stuttgart OSM data...")
        
        try:
            # Import OSM collection utilities
            sys.path.append(str(Path(__file__).parent.parent.parent.parent / "spatial_analysis" / "scripts" / "utils"))
            from osm_collector import collect_osm_data
            
            # Collect OSM data
            osm_results = collect_osm_data(osm_config)
            
            logger.info("OSM data collected successfully")
            return {
                'status': 'success',
                'osm_results': osm_results
            }
            
        except Exception as e:
            logger.error(f"Error collecting OSM data: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _process_stuttgart_districts(self, districts_config: Dict) -> Dict[str, Any]:
        """Process Stuttgart district boundaries"""
        logger.info("Processing Stuttgart district boundaries...")
        
        try:
            # Import geometry utilities
            sys.path.append(str(Path(__file__).parent.parent.parent.parent / "spatial_analysis" / "scripts" / "utils"))
            from geometry_utils import load_geometries, validate_geometries
            
            # Process district boundaries
            districts = load_geometries(districts_config)
            validated_districts = validate_geometries(districts)
            
            # Save processed districts
            output_path = self.output_dir / "stuttgart_districts.geojson"
            validated_districts.to_file(output_path, driver='GeoJSON')
            
            logger.info("District boundaries processed successfully")
            return {
                'status': 'success',
                'districts_count': len(validated_districts),
                'output_path': str(output_path)
            }
            
        except Exception as e:
            logger.error(f"Error processing district boundaries: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_stuttgart_transport_kpis(self, transport_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart transport KPIs"""
        logger.info("Calculating Stuttgart transport KPIs...")
        
        try:
            # Load required data
            districts = self._load_district_data()
            gtfs_stops = self._load_gtfs_stops()
            population = self._load_population_data()
            
            if districts is None or gtfs_stops is None:
                logger.error("Required data not available for transport indicators")
                return {'status': 'error', 'message': 'Missing required data'}
            
            # Calculate transport KPIs for each district
            transport_kpis = []
            
            for _, district in districts.iterrows():
                district_kpis = self._calculate_district_transport_kpis(
                    district, gtfs_stops, population
                )
                transport_kpis.append(district_kpis)
            
            # Combine all district KPIs
            transport_df = pd.DataFrame(transport_kpis)
            
            # Save results
            output_path = self.output_dir / "transport_kpis.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            transport_df.to_parquet(output_path)
            
            logger.info(f"Transport KPIs calculated for {len(transport_df)} districts")
            return {
                'status': 'success',
                'districts': len(transport_df),
                'output_path': str(output_path),
                'data': transport_df
            }
            
        except Exception as e:
            logger.error(f"Error calculating transport indicators: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_stuttgart_walkability_kpis(self, walkability_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart walkability KPIs"""
        logger.info("Calculating Stuttgart walkability KPIs...")
        
        try:
            # Load required data
            districts = self._load_district_data()
            intersections = self._load_osm_intersections()
            pois = self._load_additional_pois()
            population = self._load_population_data()
            
            if districts is None:
                logger.error("Required data not available for walkability indicators")
                return {'status': 'error', 'message': 'Missing required data'}
            
            # Calculate walkability KPIs for each district
            walkability_kpis = []
            
            for _, district in districts.iterrows():
                district_kpis = self._calculate_district_walkability_kpis(
                    district, intersections, pois, population
                )
                walkability_kpis.append(district_kpis)
            
            # Combine all district KPIs
            walkability_df = pd.DataFrame(walkability_kpis)
            
            # Save results
            output_path = self.output_dir / "walkability_kpis.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            walkability_df.to_parquet(output_path)
            
            logger.info(f"Walkability KPIs calculated for {len(walkability_df)} districts")
            return {
                'status': 'success',
                'districts': len(walkability_df),
                'output_path': str(output_path),
                'data': walkability_df
            }
            
        except Exception as e:
            logger.error(f"Error calculating walkability indicators: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_stuttgart_green_kpis(self, green_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart green space KPIs"""
        logger.info("Calculating Stuttgart green space KPIs...")
        
        try:
            # Load required data
            districts = self._load_district_data()
            greenspaces = self._load_osm_greenspaces()
            population = self._load_population_data()
            
            if districts is None:
                logger.error("Required data not available for green area indicators")
                return {'status': 'error', 'message': 'Missing required data'}
            
            # Calculate green area KPIs for each district
            green_kpis = []
            
            for _, district in districts.iterrows():
                district_kpis = self._calculate_district_green_kpis(
                    district, greenspaces, population
                )
                green_kpis.append(district_kpis)
            
            # Combine all district KPIs
            green_df = pd.DataFrame(green_kpis)
            
            # Save results
            output_path = self.output_dir / "green_kpis.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            green_df.to_parquet(output_path)
            
            logger.info(f"Green space KPIs calculated for {len(green_df)} districts")
            return {
                'status': 'success',
                'districts': len(green_df),
                'output_path': str(output_path),
                'data': green_df
            }
            
        except Exception as e:
            logger.error(f"Error calculating green area indicators: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _calculate_stuttgart_mobility_kpis(self, mobility_config: Dict) -> Dict[str, Any]:
        """Calculate Stuttgart mobility accessibility KPIs"""
        logger.info("Calculating Stuttgart mobility KPIs...")
        
        try:
            # Load required data
            districts = self._load_district_data()
            cycling_infra = self._load_cycling_infrastructure()
            population = self._load_population_data()
            
            if districts is None:
                logger.error("Required data not available for mobility indicators")
                return {'status': 'error', 'message': 'Missing required data'}
            
            # Calculate mobility KPIs for each district
            mobility_kpis = []
            
            for _, district in districts.iterrows():
                district_kpis = self._calculate_district_mobility_kpis(
                    district, cycling_infra, population
                )
                mobility_kpis.append(district_kpis)
            
            # Combine all district KPIs
            mobility_df = pd.DataFrame(mobility_kpis)
            
            # Save results
            output_path = self.output_dir / "mobility_kpis.parquet"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mobility_df.to_parquet(output_path)
            
            logger.info(f"Mobility KPIs calculated for {len(mobility_df)} districts")
            return {
                'status': 'success',
                'districts': len(mobility_df),
                'output_path': str(output_path),
                'data': mobility_df
            }
            
        except Exception as e:
            logger.error(f"Error calculating mobility indicators: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _create_stuttgart_specific_maps(self) -> Dict[str, Any]:
        """Create complete Stuttgart pipeline with all 24 layers"""
        logger.info("Creating complete Stuttgart pipeline with all 24 layers...")
        
        try:
            # Use local scripts in the Stuttgart folder
            scripts_dir = Path(__file__).parent / "scripts"
            sys.path.append(str(scripts_dir))
            
            # Import and run the complete pipeline generation
            from generate_complete_pipeline import generate_complete_pipeline
            
            # Run the complete pipeline script
            pipeline_results = generate_complete_pipeline()
            
            logger.info("Complete Stuttgart pipeline created successfully with all 24 layers")
            return {
                'status': 'success',
                'pipeline_results': pipeline_results,
                'message': 'Generated all 24 layers including H3 analysis and choropleth maps'
            }
            
        except Exception as e:
            logger.error(f"Error creating complete Stuttgart pipeline: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _export_stuttgart_for_qgis(self) -> Dict[str, Any]:
        """Export Stuttgart data for QGIS"""
        logger.info("Exporting Stuttgart data for QGIS...")
        
        try:
            # Import QGIS export utilities
            sys.path.append(str(Path(__file__).parent.parent.parent.parent / "spatial_analysis" / "spatialviz" / "map_generators"))
            from prepare_qgis_data import prepare_qgis_data
            
            # Prepare QGIS data
            qgis_results = prepare_qgis_data()
            
            logger.info("QGIS data export completed successfully")
            return {
                'status': 'success',
                'qgis_results': qgis_results
            }
            
        except Exception as e:
            logger.error(f"Error exporting QGIS data: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # Map generation is handled by existing pipeline scripts
    # - make_maps.py for PNG maps
    # - create_kepler_python_dashboard.py for Kepler dashboard
    
    def create_kepler_dashboard(self) -> Dict[str, Any]:
        """Create comprehensive Kepler dashboard with all 24 layers"""
        logger.info("Creating comprehensive Kepler dashboard with all layers...")
        
        try:
            # Use local scripts in the Stuttgart folder
            scripts_dir = Path(__file__).parent / "scripts"
            sys.path.append(str(scripts_dir))
            from create_kepler_python_dashboard import create_kepler_python_dashboard
            
            # Create the comprehensive dashboard
            dashboard_results = create_kepler_python_dashboard()
            
            logger.info("Comprehensive Kepler dashboard created successfully")
            return {
                'status': 'success',
                'dashboard_results': dashboard_results,
                'message': 'Dashboard created with all 24 layers including H3 analysis'
            }
            
        except Exception as e:
            logger.error(f"Error creating comprehensive Kepler dashboard: {e}")
            return {'status': 'error', 'message': str(e)}
    
    # Custom map creation methods removed - using existing pipeline instead
    
    def cleanup(self):
        """Cleanup Stuttgart analysis resources"""
        try:
            if self.postgis_client:
                self.postgis_client.close()
                logger.info("Stuttgart database connection closed")
            
            super().cleanup()
            
        except Exception as e:
            logger.error(f"Error during Stuttgart cleanup: {e}")
    
    # Helper methods for data loading and KPI calculation
    
    def _load_district_data(self) -> Optional[gpd.GeoDataFrame]:
        """Load Stuttgart district boundaries"""
        try:
            # Try to load from existing processed data first
            district_path = Path("spatial_analysis/data/stuttgart/processed/stuttgart_districts.geojson")
            if district_path.exists():
                return gpd.read_file(district_path)
            
            # Fallback to raw data
            raw_district_path = Path("spatial_analysis/data/stuttgart/raw/stadtbezirke.geojson")
            if raw_district_path.exists():
                return gpd.read_file(raw_district_path)
            
            logger.warning("No district data found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading district data: {e}")
            return None
    
    def _load_gtfs_stops(self) -> Optional[gpd.GeoDataFrame]:
        """Load GTFS stops data"""
        try:
            # Try to load from existing processed data
            gtfs_path = Path("spatial_analysis/data/stuttgart/processed/gtfs_stops.parquet")
            if gtfs_path.exists():
                return pd.read_parquet(gtfs_path)
            
            logger.warning("No GTFS stops data found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading GTFS stops: {e}")
            return None
    
    def _load_population_data(self) -> Optional[pd.DataFrame]:
        """Load population data"""
        try:
            # Try to load from existing processed data
            pop_path = Path("spatial_analysis/data/stuttgart/processed/population_by_district.csv")
            if pop_path.exists():
                return pd.read_csv(pop_path)
            
            logger.warning("No population data found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading population data: {e}")
            return None
    
    def _load_osm_intersections(self) -> Optional[gpd.GeoDataFrame]:
        """Load OSM intersections data"""
        try:
            # Try to load from existing processed data
            intersections_path = Path("spatial_analysis/data/stuttgart/processed/osm_intersections.parquet")
            if intersections_path.exists():
                return pd.read_parquet(intersections_path)
            
            logger.warning("No OSM intersections data found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading OSM intersections: {e}")
            return None
    
    def _load_additional_pois(self) -> Optional[gpd.GeoDataFrame]:
        """Load additional POI data"""
        try:
            # Try to load from existing processed data
            pois_path = Path("spatial_analysis/data/stuttgart/processed/osm_amenities.parquet")
            if pois_path.exists():
                return pd.read_parquet(pois_path)
            
            logger.warning("No additional POI data found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading additional POIs: {e}")
            return None
    
    def _load_osm_greenspaces(self) -> Optional[gpd.GeoDataFrame]:
        """Load OSM greenspaces data"""
        try:
            # Try to load from existing processed data
            greenspaces_path = Path("spatial_analysis/data/stuttgart/processed/osm_landuse.parquet")
            if greenspaces_path.exists():
                return pd.read_parquet(greenspaces_path)
            
            logger.warning("No OSM greenspaces data found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading OSM greenspaces: {e}")
            return None
    
    def _load_cycling_infrastructure(self) -> Optional[gpd.GeoDataFrame]:
        """Load cycling infrastructure data"""
        try:
            # Try to load from existing processed data
            cycling_path = Path("spatial_analysis/data/stuttgart/processed/osm_cycle.parquet")
            if cycling_path.exists():
                return pd.read_parquet(cycling_path)
            
            logger.warning("No cycling infrastructure data found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading cycling infrastructure: {e}")
            return None
    
    def _calculate_district_transport_kpis(self, district: pd.Series, gtfs_stops: pd.DataFrame, population: pd.DataFrame) -> Dict[str, Any]:
        """Calculate transport KPIs for a single district"""
        try:
            # Basic district info
            district_kpis = {
                'district_name': district.get('STADTBEZIRKNAME', 'Unknown'),
                'district_id': district.get('STADTBEZIRKID', 0)
            }
            
            # Count GTFS stops in district
            if gtfs_stops is not None and not gtfs_stops.empty:
                # Spatial join to count stops in district
                district_geom = district.geometry
                stops_in_district = gtfs_stops[gtfs_stops.geometry.within(district_geom)]
                district_kpis['pt_stop_count'] = len(stops_in_district)
                district_kpis['pt_stop_density'] = len(stops_in_district) / district.get('area_km2', 1)
            else:
                district_kpis['pt_stop_count'] = 0
                district_kpis['pt_stop_density'] = 0
            
            # Population density
            if population is not None and not population.empty:
                district_pop = population[population['district_id'] == district_kpis['district_id']]
                if not district_pop.empty:
                    district_kpis['population'] = district_pop.iloc[0].get('population', 0)
                    district_kpis['population_density'] = district_pop.iloc[0].get('population', 0) / district.get('area_km2', 1)
                else:
                    district_kpis['population'] = 0
                    district_kpis['population_density'] = 0
            else:
                district_kpis['population'] = 0
                district_kpis['population_density'] = 0
            
            return district_kpis
            
        except Exception as e:
            logger.error(f"Error calculating transport KPIs for district {district.get('STADTBEZIRKNAME', 'Unknown')}: {e}")
            return {'district_name': district.get('STADTBEZIRKNAME', 'Unknown'), 'error': str(e)}
    
    def _calculate_district_walkability_kpis(self, district: pd.Series, intersections: pd.DataFrame, pois: pd.DataFrame, population: pd.DataFrame) -> Dict[str, Any]:
        """Calculate walkability KPIs for a single district"""
        try:
            # Basic district info
            district_kpis = {
                'district_name': district.get('STADTBEZIRKNAME', 'Unknown'),
                'district_id': district.get('STADTBEZIRKID', 0)
            }
            
            # Count intersections in district
            if intersections is not None and not intersections.empty:
                district_geom = district.geometry
                intersections_in_district = intersections[intersections.geometry.within(district_geom)]
                district_kpis['intersection_count'] = len(intersections_in_district)
                district_kpis['intersection_density'] = len(intersections_in_district) / district.get('area_km2', 1)
            else:
                district_kpis['intersection_count'] = 0
                district_kpis['intersection_density'] = 0
            
            # Count POIs in district
            if pois is not None and not pois.empty:
                district_geom = district.geometry
                pois_in_district = pois[pois.geometry.within(district_geom)]
                district_kpis['poi_count'] = len(pois_in_district)
                district_kpis['poi_density'] = len(pois_in_district) / district.get('area_km2', 1)
            else:
                district_kpis['poi_count'] = 0
                district_kpis['poi_density'] = 0
            
            # Population density
            if population is not None and not population.empty:
                district_pop = population[population['district_id'] == district_kpis['district_id']]
                if not district_pop.empty:
                    district_kpis['population'] = district_pop.iloc[0].get('population', 0)
                    district_kpis['population_density'] = district_pop.iloc[0].get('population', 0) / district.get('area_km2', 1)
                else:
                    district_kpis['population'] = 0
                    district_kpis['population_density'] = 0
            else:
                district_kpis['population'] = 0
                district_kpis['population_density'] = 0
            
            return district_kpis
            
        except Exception as e:
            logger.error(f"Error calculating walkability KPIs for district {district.get('STADTBEZIRKNAME', 'Unknown')}: {e}")
            return {'district_name': district.get('STADTBEZIRKNAME', 'Unknown'), 'error': str(e)}
    
    def _calculate_district_green_kpis(self, district: pd.Series, greenspaces: pd.DataFrame, population: pd.DataFrame) -> Dict[str, Any]:
        """Calculate green space KPIs for a single district"""
        try:
            # Basic district info
            district_kpis = {
                'district_name': district.get('STADTBEZIRKNAME', 'Unknown'),
                'district_id': district.get('STADTBEZIRKID', 0)
            }
            
            # Calculate green space area in district
            if greenspaces is not None and not greenspaces.empty:
                district_geom = district.geometry
                green_in_district = greenspaces[greenspaces.geometry.within(district_geom)]
                
                if not green_in_district.empty:
                    # Calculate total green area
                    green_area = green_in_district.geometry.area.sum()
                    district_area = district_geom.area
                    green_percentage = (green_area / district_area) * 100
                    
                    district_kpis['green_area_km2'] = green_area / 1000000  # Convert to km²
                    district_kpis['green_percentage'] = green_percentage
                else:
                    district_kpis['green_area_km2'] = 0
                    district_kpis['green_percentage'] = 0
            else:
                district_kpis['green_area_km2'] = 0
                district_kpis['green_percentage'] = 0
            
            # Population density
            if population is not None and not population.empty:
                district_pop = population[population['district_id'] == district_kpis['district_id']]
                if not district_pop.empty:
                    district_kpis['population'] = district_pop.iloc[0].get('population', 0)
                    district_kpis['population_density'] = district_pop.iloc[0].get('population', 0) / district.get('area_km2', 1)
                else:
                    district_kpis['population'] = 0
                    district_kpis['population_density'] = 0
            else:
                district_kpis['population'] = 0
                district_kpis['population_density'] = 0
            
            return district_kpis
            
        except Exception as e:
            logger.error(f"Error calculating green KPIs for district {district.get('STADTBEZIRKNAME', 'Unknown')}: {e}")
            return {'district_name': district.get('STADTBEZIRKNAME', 'Unknown'), 'error': str(e)}
    
    def _calculate_district_mobility_kpis(self, district: pd.Series, cycling_infra: pd.DataFrame, population: pd.DataFrame) -> Dict[str, Any]:
        """Calculate mobility KPIs for a single district"""
        try:
            # Basic district info
            district_kpis = {
                'district_name': district.get('STADTBEZIRKNAME', 'Unknown'),
                'district_id': district.get('STADTBEZIRKID', 0)
            }
            
            # Calculate cycling infrastructure in district
            if cycling_infra is not None and not cycling_infra.empty:
                district_geom = district.geometry
                cycling_in_district = cycling_infra[cycling_infra.geometry.within(district_geom)]
                
                if not cycling_in_district.empty:
                    # Calculate total cycling infrastructure length
                    cycling_length = cycling_in_district.geometry.length.sum()
                    district_area = district_geom.area
                    cycling_density = cycling_length / (district_area / 1000000)  # km per km²
                    
                    district_kpis['cycling_length_km'] = cycling_length / 1000  # Convert to km
                    district_kpis['cycling_density'] = cycling_density
                else:
                    district_kpis['cycling_length_km'] = 0
                    district_kpis['cycling_density'] = 0
            else:
                district_kpis['cycling_length_km'] = 0
                district_kpis['cycling_density'] = 0
            
            # Population density
            if population is not None and not population.empty:
                district_pop = population[population['district_id'] == district_kpis['district_id']]
                if not district_pop.empty:
                    district_kpis['population'] = district_pop.iloc[0].get('population', 0)
                    district_kpis['population_density'] = district_pop.iloc[0].get('population', 0) / district.get('area_km2', 1)
                else:
                    district_kpis['population'] = 0
                    district_kpis['population_density'] = 0
            else:
                district_kpis['population'] = 0
                district_kpis['population_density'] = 0
            
            return district_kpis
            
        except Exception as e:
            logger.error(f"Error calculating mobility KPIs for district {district.get('STADTBEZIRKNAME', 'Unknown')}: {e}")
            return {'district_name': district.get('STADTBEZIRKNAME', 'Unknown'), 'error': str(e)}

