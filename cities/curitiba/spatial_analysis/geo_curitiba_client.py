#!/usr/bin/env python3
"""
Geo Curitiba Client - ArcGIS REST Services Integration

This module provides a client for accessing Geo Curitiba's ArcGIS REST services,
allowing us to fetch official municipal data for Curitiba analysis.
"""

import logging
import requests
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import json

logger = logging.getLogger(__name__)

class GeoCuritibaClient:
    """Client for Geo Curitiba ArcGIS REST services"""
    
    def __init__(self, base_url: str = "https://geocuritiba.ippuc.org.br/server/rest/services"):
        """
        Initialize Geo Curitiba client
        
        Args:
            base_url: Base URL for Geo Curitiba REST services
        """
        self.base_url = base_url
        self.session = requests.Session()
        
        # Set reasonable timeout for API calls
        self.session.timeout = 60
        
        logger.info(f"Initialized Geo Curitiba client for {base_url}")
    
    def get_service_info(self, folder: str = None) -> dict:
        """
        Get available services from Geo Curitiba
        
        Args:
            folder: Optional folder to explore
            
        Returns:
            Dictionary containing service information
        """
        url = f"{self.base_url}"
        if folder:
            url += f"/{folder}"
        
        try:
            response = self.session.get(url, params={'f': 'pjson'})
            response.raise_for_status()
            
            # Check if response is valid JSON
            try:
                service_info = response.json()
                logger.info(f"Retrieved service info from {url}")
                return service_info
            except json.JSONDecodeError as json_error:
                logger.warning(f"Invalid JSON response from {url}: {json_error}")
                logger.debug(f"Response content: {response.text[:200]}...")
                # Return empty dict for invalid JSON responses
                return {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get service info from {url}: {e}")
            raise
    
    def get_feature_data(self, service_path: str, layer_id: int = 0, 
                        where: str = None, out_fields: str = "*") -> gpd.GeoDataFrame:
        """
        Get feature data from Geo Curitiba FeatureServer services
        
        Args:
            service_path: Path to the service (e.g., "GeoCuritiba/GeoCuritiba")
            layer_id: Layer ID within the service
            where: Optional WHERE clause for filtering
            out_fields: Fields to return (default: all fields)
            
        Returns:
            GeoDataFrame containing the feature data
        """
        url = f"{self.base_url}/{service_path}/FeatureServer/{layer_id}/query"
        
        params = {
            'f': 'geojson',
            'outFields': out_fields,
            'returnGeometry': 'true',
            'returnCountOnly': 'false'
        }
        
        if where:
            params['where'] = where
        
        try:
            logger.info(f"Fetching feature data from {url}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Parse GeoJSON response
            geojson_data = response.json()
            
            # Convert to GeoDataFrame
            gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
            
            logger.info(f"Successfully loaded {len(gdf)} features from {service_path}")
            return gdf
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch feature data from {url}: {e}")
            raise
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse response from {url}: {e}")
            raise
    
    def get_map_data(self, service_path: str, bbox: List[float] = None, 
                    size: str = "1024,1024") -> gpd.GeoDataFrame:
        """
        Get map data from Geo Curitiba MapServer services
        
        Args:
            service_path: Path to the service (e.g., "Publico_equipamentos/Publico_equipamentos")
            bbox: Bounding box [min_lon, min_lat, max_lon, max_lat]
            size: Image size for export (width,height)
            
        Returns:
            GeoDataFrame containing the map data
        """
        url = f"{self.base_url}/{service_path}/MapServer/export"
        
        params = {
            'f': 'geojson',
            'size': size
        }
        
        if bbox:
            params['bbox'] = ','.join(map(str, bbox))
        
        try:
            logger.info(f"Fetching map data from {url}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Parse GeoJSON response
            geojson_data = response.json()
            
            # Convert to GeoDataFrame
            gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
            
            logger.info(f"Successfully loaded {len(gdf)} features from {service_path}")
            return gdf
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch map data from {url}: {e}")
            raise
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse response from {url}: {e}")
            raise
    
    def get_layer_info(self, service_path: str, layer_id: int = 0) -> dict:
        """
        Get information about a specific layer
        
        Args:
            service_path: Path to the service
            layer_id: Layer ID within the service
            
        Returns:
            Dictionary containing layer information
        """
        url = f"{self.base_url}/{service_path}/FeatureServer/{layer_id}"
        
        try:
            response = self.session.get(url, params={'f': 'pjson'})
            response.raise_for_status()
            
            layer_info = response.json()
            logger.info(f"Retrieved layer info from {url}")
            return layer_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get layer info from {url}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test connection to Geo Curitiba services
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            service_info = self.get_service_info()
            logger.info("Geo Curitiba connection test successful")
            return True
        except Exception as e:
            logger.error(f"Geo Curitiba connection test failed: {e}")
            return False
    
    def get_available_layers(self) -> Dict[str, List[str]]:
        """
        Get list of available layers from all services
        
        Returns:
            Dictionary mapping service names to available layer names
        """
        try:
            service_info = self.get_service_info()
            available_layers = {}
            
            # Validate service_info is a dictionary
            if not isinstance(service_info, dict):
                logger.warning(f"Service info is not a dictionary: {type(service_info)}")
                return available_layers
            
            # Debug: Log the structure of service_info
            logger.debug(f"Service info keys: {list(service_info.keys())}")
            if 'services' in service_info:
                logger.debug(f"Services count: {len(service_info['services'])}")
                logger.debug(f"First service: {service_info['services'][0] if service_info['services'] else 'None'}")
            if 'folders' in service_info:
                logger.debug(f"Folders count: {len(service_info['folders'])}")
                logger.debug(f"First folder: {service_info['folders'][0] if service_info['folders'] else 'None'}")
            
            # Parse services and folders
            if 'services' in service_info:
                for service in service_info['services']:
                    # Validate service structure
                    if not isinstance(service, dict) or 'name' not in service or 'type' not in service:
                        logger.warning(f"Invalid service structure: {service}")
                        continue
                        
                    service_name = service['name']
                    service_type = service['type']
                    
                    logger.debug(f"Processing service: {service_name} (type: {service_type})")
                    
                    if service_type in ['FeatureServer', 'MapServer']:
                        try:
                            # Get layers for this service
                            service_layers = self.get_service_info(service_name)
                            
                            # Check if response is valid JSON with layers
                            if isinstance(service_layers, dict) and 'layers' in service_layers:
                                available_layers[service_name] = [
                                    layer['name'] for layer in service_layers['layers']
                                ]
                                logger.debug(f"Added {len(available_layers[service_name])} layers for {service_name}")
                            else:
                                logger.debug(f"Service {service_name} returned no layers or invalid response")
                                
                        except Exception as e:
                            logger.warning(f"Could not get layers for {service_name}: {e}")
            
            if 'folders' in service_info:
                for folder in service_info['folders']:
                    # Handle both string and dictionary folder formats
                    if isinstance(folder, str):
                        folder_name = folder
                        logger.debug(f"Processing string folder: {folder_name}")
                    elif isinstance(folder, dict) and 'name' in folder:
                        folder_name = folder['name']
                        logger.debug(f"Processing dict folder: {folder_name}")
                    else:
                        logger.warning(f"Invalid folder structure: {folder}")
                        continue
                    
                    try:
                        folder_layers = self.get_service_info(folder_name)
                        
                        # Check if folder response is valid JSON
                        if isinstance(folder_layers, dict) and 'services' in folder_layers:
                            for service in folder_layers['services']:
                                # Validate service structure in folder
                                if not isinstance(service, dict) or 'name' not in service or 'type' not in service:
                                    logger.warning(f"Invalid service structure in folder {folder_name}: {service}")
                                    continue
                                    
                                service_name = f"{folder_name}/{service['name']}"
                                service_type = service['type']
                                
                                logger.debug(f"Processing folder service: {service_name} (type: {service_type})")
                                
                                if service_type in ['FeatureServer', 'MapServer']:
                                    try:
                                        service_layers = self.get_service_info(service_name)
                                        
                                        # Check if service response is valid JSON with layers
                                        if isinstance(service_layers, dict) and 'layers' in service_layers:
                                            available_layers[service_name] = [
                                                layer['name'] for layer in service_layers['layers']
                                            ]
                                            logger.debug(f"Added {len(available_layers[service_name])} layers for {service_name}")
                                        else:
                                            logger.debug(f"Service {service_name} returned no layers or invalid response")
                                            
                                    except Exception as e:
                                        logger.warning(f"Could not get layers for {service_name}: {e}")
                        else:
                            logger.debug(f"Folder {folder_name} returned no services or invalid response")
                            
                    except Exception as e:
                        logger.warning(f"Could not explore folder {folder_name}: {e}")
            
            logger.info(f"Found {len(available_layers)} services with layers")
            return available_layers
            
        except Exception as e:
            logger.error(f"Failed to get available layers: {e}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    def close(self):
        """Close the client session"""
        if self.session:
            self.session.close()
            logger.info("Geo Curitiba client session closed")
