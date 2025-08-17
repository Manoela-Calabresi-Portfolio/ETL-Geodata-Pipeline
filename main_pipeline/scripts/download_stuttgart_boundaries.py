#!/usr/bin/env python3
"""
Download real Stuttgart district boundaries using Overpass API
Much faster than processing the entire Baden-Württemberg OSM file
"""

import requests
import json
import geopandas as gpd
from pathlib import Path
import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def download_stuttgart_boundaries():
    """Download Stuttgart district boundaries from Overpass API"""
    logger = setup_logging()
    
    # Overpass query for Stuttgart administrative boundaries
    overpass_query = """
    [out:json][timeout:60];
    (
      relation["boundary"="administrative"]["admin_level"="9"][bbox:48.6,9.0,48.9,9.4];
      relation["boundary"="administrative"]["admin_level"="10"][bbox:48.6,9.0,48.9,9.4];
    );
    out geom;
    """
    
    logger.info("Querying Overpass API for Stuttgart district boundaries...")
    
    # Overpass API endpoint
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    try:
        response = requests.post(overpass_url, data=overpass_query, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Retrieved {len(data.get('elements', []))} boundary elements")
        
        if not data.get('elements'):
            logger.warning("No boundary data found. Trying broader query...")
            # Fallback: broader query for any administrative boundaries in Stuttgart area
            broader_query = """
            [out:json][timeout:60];
            (
              relation["boundary"="administrative"]["admin_level"~"^(8|9|10)$"][bbox:48.6,9.0,48.9,9.4];
            );
            out geom;
            """
            response = requests.post(overpass_url, data=broader_query, timeout=120)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Broader query retrieved {len(data.get('elements', []))} boundary elements")
        
        # Convert to GeoDataFrame
        features = []
        for element in data.get('elements', []):
            if element.get('type') == 'relation' and element.get('geometry'):
                # Extract properties
                props = element.get('tags', {})
                name = props.get('name', f"Unknown_{element.get('id')}")
                admin_level = props.get('admin_level', 'unknown')
                
                # Convert geometry
                coords = []
                for geom in element.get('geometry', []):
                    if geom.get('type') == 'way':
                        way_coords = [[pt['lon'], pt['lat']] for pt in geom.get('nd', [])]
                        if way_coords:
                            coords.extend(way_coords)
                
                if coords and len(coords) >= 3:
                    # Close polygon if not closed
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    
                    feature = {
                        'type': 'Feature',
                        'properties': {
                            'name': name,
                            'admin_level': admin_level,
                            'osm_id': element.get('id')
                        },
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [coords]
                        }
                    }
                    features.append(feature)
        
        if not features:
            logger.error("No valid polygon features found")
            return None
            
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(features, crs='EPSG:4326')
        logger.info(f"Created GeoDataFrame with {len(gdf)} districts")
        logger.info(f"District names: {list(gdf['name'])}")
        
        return gdf
        
    except Exception as e:
        logger.error(f"Error downloading boundaries: {e}")
        return None

def main():
    logger = setup_logging()
    
    # Download boundaries
    gdf = download_stuttgart_boundaries()
    
    if gdf is None:
        logger.error("Failed to download boundaries")
        return 1
    
    # Save to pipeline raw data
    output_file = Path("areas/stuttgart/data_final/raw/stuttgart_districts.geojson")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    gdf.to_file(output_file, driver='GeoJSON')
    logger.info(f"Saved Stuttgart district boundaries to: {output_file}")
    
    # Also save to spatial_analysis folder
    spatial_output = Path("../spatial_analysis/data/raw/stuttgart_districts_real.geojson")
    spatial_output.parent.mkdir(parents=True, exist_ok=True)
    
    gdf.to_file(spatial_output, driver='GeoJSON')
    logger.info(f"Also saved to spatial_analysis: {spatial_output}")
    
    return 0

if __name__ == "__main__":
    exit(main())
