#!/usr/bin/env python3
"""
KPI Calculation Module - Stuttgart Mobility & Walkability Analysis
Part 2 of 3: Indicator calculations

This module handles:
- Transport public indicators calculation
- Walkability metrics computation
- Green areas accessibility analysis
- Population-based KPI aggregation
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.analysis_config import load_config
from config.kpi_weights import load_kpi_weights
from utils.kpi_calculators import (
    calculate_transport_indicators,
    calculate_walkability_indicators,
    calculate_green_indicators,
    aggregate_district_kpis
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main KPI calculation function"""
    parser = argparse.ArgumentParser(description='KPI Calculation for Stuttgart Analysis')
    parser.add_argument('--transport-only', action='store_true', help='Calculate only transport KPIs')
    parser.add_argument('--walkability-only', action='store_true', help='Calculate only walkability KPIs')
    parser.add_argument('--green-only', action='store_true', help='Calculate only green area KPIs')
    parser.add_argument('--config', default='../config/analysis_config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    kpi_weights = load_kpi_weights()
    logger.info("Configuration and KPI weights loaded successfully")
    
    # Calculate transport indicators
    if args.transport_only or not (args.walkability_only or args.green_only):
        logger.info("Calculating transport indicators...")
        transport_kpis = calculate_transport_indicators(config)
        logger.info(f"Transport KPIs calculated for {len(transport_kpis)} districts")
    
    # Calculate walkability indicators
    if args.walkability_only or not (args.transport_only or args.green_only):
        logger.info("Calculating walkability indicators...")
        walkability_kpis = calculate_walkability_indicators(config)
        logger.info(f"Walkability KPIs calculated for {len(walkability_kpis)} districts")
    
    # Calculate green area indicators
    if args.green_only or not (args.transport_only or args.walkability_only):
        logger.info("Calculating green area indicators...")
        green_kpis = calculate_green_indicators(config)
        logger.info(f"Green area KPIs calculated for {len(green_kpis)} districts")
    
    # Aggregate all KPIs
    if not any([args.transport_only, args.walkability_only, args.green_only]):
        logger.info("Aggregating all district KPIs...")
        district_kpis = aggregate_district_kpis(config, kpi_weights)
        logger.info(f"All KPIs aggregated for {len(district_kpis)} districts")
    
    logger.info("KPI calculation completed successfully")

if __name__ == "__main__":
    main()
