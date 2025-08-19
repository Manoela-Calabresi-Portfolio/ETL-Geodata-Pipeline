#!/usr/bin/env python3
"""
Data Collection Module - Stuttgart Mobility & Walkability Analysis
Part 1 of 3: Data collection and processing

This module handles:
- GTFS VVS data download and processing
- OSM data collection for specific features
- District geometry processing
- Data validation and staging
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.analysis_config import load_config
from utils.geometry_utils import load_geometries, validate_geometries
from utils.osm_collector import collect_osm_data
from utils.gtfs_processor import process_gtfs_data

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main data collection function"""
    parser = argparse.ArgumentParser(description='Data Collection for Stuttgart Analysis')
    parser.add_argument('--gtfs-only', action='store_true', help='Process only GTFS data')
    parser.add_argument('--osm-only', action='store_true', help='Process only OSM data')
    parser.add_argument('--config', default='config/analysis_config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    logger.info("Configuration loaded successfully")
    
    # Create output directories
    output_dirs = ['data/raw', 'data/processed', 'data/staging']
    for dir_path in output_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    if args.gtfs_only or not args.osm_only:
        logger.info("Processing GTFS data...")
        process_gtfs_data(config)
    
    if args.osm_only or not args.gtfs_only:
        logger.info("Collecting OSM data...")
        collect_osm_data(config)
    
    logger.info("Data collection completed successfully")

if __name__ == "__main__":
    main()
