#!/usr/bin/env python3
"""
[STEP 1 - EXTRACT] OSM Data Extraction using QuackOSM
Extracts thematic layers from OSM data based on area configuration and global filters

Usage: python pipeline/scripts/extract_quackosm.py --city stuttgart

This module handles the extraction phase of the ETL pipeline:
- Downloads/reads OSM PBF files
- Applies filters from config/osm_filters.yaml
- Uses QuackOSM for efficient processing with bounding box filtering
- Saves extracted layers as GeoParquet in data/staging/{city}/
- Supports test mode with smaller bounding boxes
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any
import geopandas as gpd
import yaml

from utils import (
    load_yaml, load_area_config, load_pipeline_config,
    ensure_dir, setup_logging, get_area_paths, validate_bbox, shrink_bbox
)


class OSMExtractor:
    """OSM data extraction using QuackOSM"""

    def __init__(self, area_name: str, test_mode: bool = False):
        self.area_name = area_name
        self.test_mode = test_mode
        self.logger = setup_logging().getChild(f"extract.{area_name}")

        # Load configurations
        self.pipeline_config = load_pipeline_config()
        self.area_config = load_area_config(area_name)
        self.osm_filters = load_yaml(self.pipeline_config['config_files']['osm_filters'])

        # Setup paths
        self.paths = get_area_paths(area_name, self.pipeline_config)
        ensure_dir(self.paths['staging_template'])

        # Get processing parameters
        self.bbox = self.area_config['geography']['bbox']
        if self.test_mode:
            shrink_factor = self.pipeline_config.get('test_mode', {}).get('bbox_shrink_factor', 0.1)
            self.bbox = shrink_bbox(self.bbox, shrink_factor)
        if not validate_bbox(self.bbox):
            raise ValueError(f"Invalid bounding box: {self.bbox}")

        self.logger.info(f"Initialized OSM extractor for {area_name}")
        self.logger.info(f"Bounding box: {self.bbox}")
        self.logger.info(f"Test mode: {test_mode}")

    def get_pbf_file(self) -> Path:
        pbf_path = Path(self.area_config['data_sources']['osm']['pbf_file'])
        if pbf_path.exists():
            self.logger.info(f"Found existing PBF file: {pbf_path}")
            return pbf_path
        raise FileNotFoundError(
            f"PBF file not found: {pbf_path}\n"
            f"Please download from: {self.area_config['data_sources']['osm']['pbf_url']}"
        )

    def get_layers_to_extract(self) -> List[str]:
        if self.test_mode:
            return self.pipeline_config['test_mode']['test_layers']
        area_layers = self.area_config.get('processing', {}).get('priority_layers')
        return area_layers or self.pipeline_config['defaults']['layers']

    def create_filter_file(self, layer_name: str) -> Path:
        base_filter = self.osm_filters.get(layer_name, {})
        area_overrides = self.area_config.get('overrides', {}).get('custom_filters', {})
        if layer_name in area_overrides:
            for key, values in area_overrides[layer_name].items():
                if key in base_filter and isinstance(base_filter[key], list):
                    base_filter[key] = list({*base_filter[key], *values})
                else:
                    base_filter[key] = values
        temp_file = self.paths['staging_template'].parent / f"{layer_name}_filter.json"
        with open(temp_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(base_filter, f, indent=2)
        return temp_file

    def extract_layer(self, layer_name: str, pbf_file: Path) -> bool:
        try:
            self.logger.info(f"Extracting layer: {layer_name}")
            filter_file = self.create_filter_file(layer_name)
            output_file = self.paths['staging_template'] / f"osm_{layer_name}.parquet"
            ensure_dir(output_file.parent)

            cmd = [
                "quackosm",
                str(pbf_file),
                "--osm-tags-filter-file", str(filter_file),
                "--geom-filter-bbox", f"{self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]}",
                "--output", str(output_file),
                "--silent",
                "--ignore-cache"
            ]

            self.logger.debug(f"QuackOSM command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Remove temp filter
            try:
                filter_file.unlink(missing_ok=True)
            except Exception:
                pass

            if result.returncode != 0:
                self.logger.error(f"QuackOSM failed for {layer_name}: {result.stderr}")
                return False

            if not output_file.exists():
                self.logger.error(f"Output file not created: {output_file}")
                return False

            try:
                gdf = gpd.read_parquet(output_file)
                self.logger.info(f"✓ {layer_name}: {len(gdf)} features extracted")
                self.logger.info(f"  Geometry types: {dict(gdf.geometry.geom_type.value_counts())}")
                self.logger.info(f"  CRS: {gdf.crs}")
            except Exception as e:
                self.logger.warning(f"Could not read output file for verification: {e}")

            return True

        except Exception as e:
            self.logger.error(f"Unexpected error extracting {layer_name}: {e}")
            return False

    def extract_all_layers(self) -> Dict[str, bool]:
        pbf_file = self.get_pbf_file()
        layers = self.get_layers_to_extract()
        self.logger.info(f"Starting extraction for {len(layers)} layers: {', '.join(layers)}")
        results = {}
        for layer_name in layers:
            if layer_name not in self.osm_filters:
                self.logger.warning(f"No filter defined for layer: {layer_name}")
                results[layer_name] = False
                continue
            results[layer_name] = self.extract_layer(layer_name, pbf_file)
        return results

    def print_summary(self, results: Dict[str, bool]):
        successful = sum(results.values())
        total = len(results)
        self.logger.info("\n=== EXTRACTION SUMMARY ===")
        self.logger.info(f"Successful: {successful}/{total}")
        for layer_name, success in results.items():
            status = "✓" if success else "✗"
            self.logger.info(f"  {status} {layer_name}")


def main():
    parser = argparse.ArgumentParser(description='Extract OSM data for a city using QuackOSM')
    parser.add_argument('--city', required=True, help='City/area name (must match YAML in areas/)')
    parser.add_argument('--test', action='store_true', help='Run in test mode (smaller bbox, fewer layers)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=level)

    try:
        extractor = OSMExtractor(args.city, test_mode=args.test)
        results = extractor.extract_all_layers()
        extractor.print_summary(results)
        return 0 if all(results.values()) else 1
    except Exception as e:
        logger = setup_logging().getChild("extract.main")
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
