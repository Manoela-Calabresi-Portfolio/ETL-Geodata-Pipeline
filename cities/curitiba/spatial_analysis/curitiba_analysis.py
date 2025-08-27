#!/usr/bin/env python3
"""
Curitiba Analysis Script

This script demonstrates how to use the spatial_analysis_core data loader
for Curitiba-specific analysis.
"""

import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from spatial_analysis_core import DataLoader, extract_city_osm_data
from cities.curitiba.spatial_analysis.geo_curitiba_client import GeoCuritibaClient

def analyze_curitiba():
    """Main analysis function for Curitiba"""
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "city.yaml"
    with open(config_path, 'r') as f:
        import yaml
        config = yaml.safe_load(f)
    
    # Get Curitiba parameters
    bbox = config['city']['bbox']
    city_name = config['city']['name']
    
    # Initialize data loader
    output_dir = Path(__file__).parent.parent / "data" / "outputs" / "analysis"
    loader = DataLoader(output_dir)
    
    # Extract OSM data (when PBF file is available)
    # results = extract_city_osm_data(
    #     pbf_file="path/to/parana-latest.osm.pbf",
    #     bbox=bbox,
    #     city_name=city_name,
    #     output_format="parquet"
    # )
    
    # Integrate with GeoCuritiba client
    client = GeoCuritibaClient()
    
    # Perform Curitiba-specific analysis
    # - BRT system analysis
    # - Green infrastructure assessment
    # - Urban planning effectiveness
    # - District performance ranking
    
    print(f"✅ Curitiba analysis pipeline ready!")
    print(f"📍 Bounding box: {bbox}")
    print(f"🏙️ City: {city_name}")

if __name__ == "__main__":
    analyze_curitiba()
