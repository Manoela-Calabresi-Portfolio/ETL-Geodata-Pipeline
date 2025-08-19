#!/usr/bin/env python3
"""
Visualization Module - Stuttgart Mobility & Walkability Analysis
Part 3 of 3: Maps, rankings and reports

This module handles:
- Thematic map generation
- District ranking tables
- Interactive visualizations
- Final report generation
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.analysis_config import load_config
from spatialviz.utils.visualization_helpers import (
    generate_thematic_maps,
    create_ranking_tables,
    build_interactive_dashboard,
    generate_final_report
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main visualization function"""
    parser = argparse.ArgumentParser(description='Visualization for Stuttgart Analysis')
    parser.add_argument('--maps-only', action='store_true', help='Generate only maps')
    parser.add_argument('--rankings-only', action='store_true', help='Generate only rankings')
    parser.add_argument('--dashboard-only', action='store_true', help='Generate only dashboard')
    parser.add_argument('--report-only', action='store_true', help='Generate only final report')
    parser.add_argument('--config', default='config/analysis_config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    logger.info("Configuration loaded successfully")
    
    # Output directories are handled by spatialviz
    # All outputs go to spatialviz/outputs/
    
    # Generate thematic maps
    if args.maps_only or not (args.rankings_only or args.dashboard_only or args.report_only):
        logger.info("Generating thematic maps...")
        generate_thematic_maps(config)
        logger.info("Thematic maps generated successfully")
    
    # Create ranking tables
    if args.rankings_only or not (args.maps_only or args.dashboard_only or args.report_only):
        logger.info("Creating ranking tables...")
        create_ranking_tables(config)
        logger.info("Ranking tables created successfully")
    
    # Build interactive dashboard
    if args.dashboard_only or not (args.maps_only or args.rankings_only or args.report_only):
        logger.info("Building interactive dashboard...")
        build_interactive_dashboard(config)
        logger.info("Interactive dashboard built successfully")
    
    # Generate final report
    if args.report_only or not (args.maps_only or args.rankings_only or args.dashboard_only):
        logger.info("Generating final report...")
        generate_final_report(config)
        logger.info("Final report generated successfully")
    
    logger.info("Visualization completed successfully")

if __name__ == "__main__":
    main()
