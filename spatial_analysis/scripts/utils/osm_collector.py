#!/usr/bin/env python3
"""
OSM Data Collector - Utility module for collecting OpenStreetMap data
"""

import logging
import osmnx as ox
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def collect_osm_data(config: Dict[str, Any]) -> None:
    """
    Collect OSM data for Stuttgart analysis
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Starting OSM data collection...")
    
    # Set OSMnx settings
    ox.config(use_cache=True, log_console=False)
    
    # Get Stuttgart boundary
    stuttgart_boundary = get_stuttgart_boundary()
    
    # Collect different types of OSM data
    collect_crossings(stuttgart_boundary, config)
    collect_additional_pois(stuttgart_boundary, config)
    collect_parks_and_greenspaces(stuttgart_boundary, config)
    
    logger.info("OSM data collection completed")

def get_stuttgart_boundary():
    """Get Stuttgart administrative boundary from OSM"""
    try:
        # Get Stuttgart boundary using Nominatim
        boundary = ox.geocoder.geocode_to_gdf("Stuttgart, Germany")
        return boundary
    except Exception as e:
        logger.error(f"Error getting Stuttgart boundary: {e}")
        return None

def collect_crossings(boundary, config):
    """Collect intersection/crossing data"""
    try:
        logger.info("Collecting intersection data...")
        
        # Get all nodes that are intersections
        nodes = ox.graph_to_gdfs(
            ox.graph_from_place("Stuttgart, Germany", network_type="drive"),
            nodes=True, edges=False
        )[0]
        
        # Filter to intersections (nodes with degree > 2)
        intersections = nodes[nodes['osmid'].isin(
            [n for n, d in ox.graph_from_place("Stuttgart, Germany", network_type="drive").degree()]
            if d > 2
        )]
        
        # Save intersections
        output_path = Path("data/processed/osm_intersections.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        intersections.to_parquet(output_path)
        
        logger.info(f"Collected {len(intersections)} intersections")
        
    except Exception as e:
        logger.error(f"Error collecting intersections: {e}")

def collect_additional_pois(boundary, config):
    """Collect additional POIs for walkability analysis"""
    try:
        logger.info("Collecting additional POI data...")
        
        # Define POI types for walkability
        poi_types = {
            'market': ['shop', 'amenity'],
            'school': ['amenity'],
            'park': ['leisure'],
            'healthcare': ['amenity'],
            'culture': ['amenity', 'tourism']
        }
        
        all_pois = []
        
        for category, tags in poi_types.items():
            for tag in tags:
                try:
                    pois = ox.geometries_from_place(
                        "Stuttgart, Germany",
                        tags={tag: True}
                    )
                    if not pois.empty:
                        pois['category'] = category
                        all_pois.append(pois)
                except Exception as e:
                    logger.warning(f"Could not collect {category} POIs: {e}")
        
        if all_pois:
            combined_pois = pd.concat(all_pois, ignore_index=True)
            
            # Save POIs
            output_path = Path("data/processed/osm_additional_pois.parquet")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            combined_pois.to_parquet(output_path)
            
            logger.info(f"Collected {len(combined_pois)} additional POIs")
        
    except Exception as e:
        logger.error(f"Error collecting additional POIs: {e}")

def collect_parks_and_greenspaces(boundary, config):
    """Collect parks and green spaces data"""
    try:
        logger.info("Collecting parks and green spaces data...")
        
        # Collect green spaces
        green_tags = {
            'leisure': ['park', 'garden', 'playground'],
            'landuse': ['grass', 'forest', 'recreation_ground'],
            'natural': ['wood', 'grassland']
        }
        
        all_greenspaces = []
        
        for tag_type, values in green_tags.items():
            for value in values:
                try:
                    greenspaces = ox.geometries_from_place(
                        "Stuttgart, Germany",
                        tags={tag_type: value}
                    )
                    if not greenspaces.empty:
                        greenspaces['greenspace_type'] = f"{tag_type}_{value}"
                        all_greenspaces.append(greenspaces)
                except Exception as e:
                    logger.warning(f"Could not collect {tag_type}={value}: {e}")
        
        if all_greenspaces:
            combined_greenspaces = pd.concat(all_greenspaces, ignore_index=True)
            
            # Save green spaces
            output_path = Path("data/processed/osm_greenspaces.parquet")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            combined_greenspaces.to_parquet(output_path)
            
            logger.info(f"Collected {len(combined_greenspaces)} green spaces")
        
    except Exception as e:
        logger.error(f"Error collecting green spaces: {e}")
