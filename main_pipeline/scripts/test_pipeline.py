#!/usr/bin/env python3
"""
[STEP 0 - TEST] Test Pipeline Script
Runs a minimal test of the extraction and processing pipeline with a small bbox

Usage: python pipeline/scripts/test_pipeline.py --city stuttgart --test
Note: Optional testing step - run BEFORE full pipeline

This module provides fast testing capabilities:
- Shrinks bounding box to 10% of original size for quick testing
- Runs extraction + processing for limited layers (default: landuse only)
- Validates end-to-end pipeline functionality
- Useful for development and debugging
"""

import argparse
import sys

from utils import setup_logging
from extract_quackosm import OSMExtractor
from process_layers import LayerProcessor


def main():
    parser = argparse.ArgumentParser(description='Test the ETL pipeline with a small bounding box')
    parser.add_argument('--city', required=True, help='City/area name to test')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=level)

    try:
        extractor = OSMExtractor(args.city, test_mode=True)
        extract_results = extractor.extract_all_layers()
        extractor.print_summary(extract_results)

        processor = LayerProcessor(args.city, test_mode=True)
        process_results = processor.process_all_layers()
        processor.print_summary(process_results)

        ok = all(extract_results.values()) and process_results.get('success', False)
        return 0 if ok else 1
    except Exception as e:
        logger = setup_logging().getChild("test.main")
        logger.error(f"Fatal test error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())


