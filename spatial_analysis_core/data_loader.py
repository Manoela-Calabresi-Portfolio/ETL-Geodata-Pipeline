"""
Data Loader for Spatial Analysis Core
Provides city-agnostic data loading utilities for multiple data sources.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import geopandas as gpd
import pandas as pd
import yaml
from shapely import wkb

logger = logging.getLogger(__name__)


class DataLoader:
    """
    City-agnostic data loader supporting multiple data sources.
    """
    
    def __init__(self, city_config: Dict[str, Any]):
        """
        Initialize data loader with city configuration.
        
        Args:
            city_config: City configuration dictionary
        """
        self.city_config = city_config
        self.data_sources = city_config.get('data_sources', {})
        self.required_layers = city_config.get('data_requirements', {}).get('required_layers', [])
        
    def load_layer(self, layer_name: str, source_type: str = 'auto') -> Optional[gpd.GeoDataFrame]:
        """
        Load a data layer with automatic source detection.
        
        Args:
            layer_name: Name of the layer to load
            source_type: Source type ('auto', 'osm', 'external', 'api')
            
        Returns:
            GeoDataFrame with the loaded data or None if failed
        """
        try:
            if source_type == 'auto':
                return self._load_with_priority(layer_name)
            elif source_type == 'osm':
                return self._load_from_osm(layer_name)
            elif source_type == 'external':
                return self._load_from_external(layer_name)
            elif source_type == 'api':
                return self._load_from_api(layer_name)
            else:
                logger.error(f"Unknown source type: {source_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load layer {layer_name}: {e}")
            return None
    
    def _load_with_priority(self, layer_name: str) -> Optional[gpd.GeoDataFrame]:
        """
        Load data with priority-based fallback.
        
        Priority order:
        1. External files (most reliable)
        2. OSM data (via QuackOSM)
        3. API data (least reliable)
        """
        # Try external files first
        data = self._load_from_external(layer_name)
        if data is not None:
            return data
            
        # Try OSM data
        data = self._load_from_osm(layer_name)
        if data is not None:
            return data
            
        # Try API data last
        data = self._load_from_api(layer_name)
        if data is not None:
            return data
            
        logger.warning(f"Could not load layer {layer_name} from any source")
        return None
    
    def _load_from_external(self, layer_name: str) -> Optional[gpd.GeoDataFrame]:
        """
        Load data from external files (GeoJSON, Shapefile, etc.).
        """
        external_sources = self.data_sources.get('external', {})
        layer_config = external_sources.get(layer_name, {})
        
        if not layer_config:
            return None
            
        file_path = layer_config.get('path')
        if not file_path or not os.path.exists(file_path):
            return None
            
        try:
            # Determine file type and load accordingly
            if file_path.endswith('.geojson'):
                return gpd.read_file(file_path)
            elif file_path.endswith('.shp'):
                return gpd.read_file(file_path)
            elif file_path.endswith('.parquet'):
                return self._load_parquet_with_geometry(file_path)
            else:
                logger.warning(f"Unsupported file format: {file_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load external file {file_path}: {e}")
            return None
    
    def _load_from_osm(self, layer_name: str) -> Optional[gpd.GeoDataFrame]:
        """
        Load data from OSM via QuackOSM.
        """
        osm_sources = self.data_sources.get('osm', {})
        layer_config = osm_sources.get(layer_name, {})
        
        if not layer_config:
            return None
            
        try:
            # This would integrate with QuackOSM
            # For now, return None as placeholder
            logger.info(f"OSM loading for {layer_name} not yet implemented")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load OSM data for {layer_name}: {e}")
            return None
    
    def _load_from_api(self, layer_name: str) -> Optional[gpd.GeoDataFrame]:
        """
        Load data from city-specific APIs.
        """
        api_sources = self.data_sources.get('api', {})
        layer_config = api_sources.get(layer_name, {})
        
        if not layer_config:
            return None
            
        try:
            # This would integrate with city-specific API clients
            # For now, return None as placeholder
            logger.info(f"API loading for {layer_name} not yet implemented")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load API data for {layer_name}: {e}")
            return None
    
    def _load_parquet_with_geometry(self, file_path: str) -> Optional[gpd.GeoDataFrame]:
        """
        Load Parquet file with WKB geometry handling.
        """
        try:
            # Load as regular DataFrame first
            df = pd.read_parquet(file_path)
            
            # Check if geometry column exists
            geom_col = None
            for col in df.columns:
                if 'geometry' in col.lower() or 'geom' in col.lower():
                    geom_col = col
                    break
            
            if geom_col is None:
                logger.warning(f"No geometry column found in {file_path}")
                return None
            
            # Convert WKB to Shapely geometry
            if df[geom_col].dtype == 'object':
                # Handle WKB bytes
                df[geom_col] = df[geom_col].apply(lambda x: wkb.loads(x) if x is not None else None)
            
            # Convert to GeoDataFrame
            gdf = gpd.GeoDataFrame(df, geometry=geom_col)
            
            # Set CRS if available
            if 'crs' in df.columns:
                gdf.set_crs(df['crs'].iloc[0], inplace=True)
            else:
                # Default to WGS84
                gdf.set_crs('EPSG:4326', inplace=True)
            
            return gdf
            
        except Exception as e:
            logger.error(f"Failed to load Parquet file {file_path}: {e}")
            return None
    
    def validate_crs(self, gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
        """
        Validate and convert CRS if needed.
        
        Args:
            gdf: Input GeoDataFrame
            target_crs: Target CRS string
            
        Returns:
            GeoDataFrame with correct CRS
        """
        if gdf.crs is None:
            logger.warning("Input GeoDataFrame has no CRS, assuming WGS84")
            gdf.set_crs('EPSG:4326', inplace=True)
        
        if str(gdf.crs) != target_crs:
            logger.info(f"Converting CRS from {gdf.crs} to {target_crs}")
            gdf = gdf.to_crs(target_crs)
        
        return gdf
    
    def get_available_layers(self) -> Dict[str, Any]:
        """
        Get information about available data layers.
        
        Returns:
            Dictionary with layer information
        """
        layers = {}
        
        # External layers
        external_sources = self.data_sources.get('external', {})
        for layer_name, config in external_sources.items():
            layers[layer_name] = {
                'source': 'external',
                'path': config.get('path'),
                'format': config.get('format', 'auto'),
                'available': os.path.exists(config.get('path', ''))
            }
        
        # OSM layers
        osm_sources = self.data_sources.get('osm', {})
        for layer_name, config in osm_sources.items():
            layers[layer_name] = {
                'source': 'osm',
                'filters': config.get('filters', {}),
                'available': True  # OSM is always available
            }
        
        # API layers
        api_sources = self.data_sources.get('api', {})
        for layer_name, config in api_sources.items():
            layers[layer_name] = {
                'source': 'api',
                'endpoint': config.get('endpoint'),
                'available': True  # Assume API is available
            }
        
        return layers
