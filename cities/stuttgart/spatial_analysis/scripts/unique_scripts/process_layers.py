#!/usr/bin/env python3
"""
[STEP 2 - PROCESS] Layer Processing Script
Applies category mappings to extracted OSM layers and saves processed results

Usage: python pipeline/scripts/process_layers.py --city stuttgart
Note: Run AFTER extract_quackosm.py (Step 1)

This module handles the processing phase of the ETL pipeline:
- Loads staged layers from data/staging/{city}/
- Applies global category mappings from config/*_rules.yaml
- Applies city-specific overrides from areas/{city}.yaml
- Saves categorized data to data/processed/{city}/
- Supports both categorized layers (landuse, roads) and passthrough layers
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from utils import (
    load_yaml, load_area_config, load_pipeline_config,
    ensure_dir, setup_logging, get_area_paths
)
logger = setup_logging().getChild("process")


class LayerProcessor:
    """Process extracted OSM layers with category mappings"""
    
    def __init__(self, area_name: str, test_mode: bool = False):
        self.area_name = area_name
        self.test_mode = test_mode
        self.logger = setup_logging().getChild(f"process.{area_name}")
        
        # Load configurations
        self.pipeline_config = load_pipeline_config()
        self.area_config = load_area_config(area_name)
        
        # Load category mapping rules
        self.landuse_rules = load_yaml(self.pipeline_config['config_files']['landuse_rules'])
        self.roads_rules = load_yaml(self.pipeline_config['config_files']['roads_rules'])
        self.buildings_rules = load_yaml(self.pipeline_config['config_files']['buildings_rules'])
        self.amenities_rules = load_yaml(self.pipeline_config['config_files']['amenities_rules'])
        self.cycle_rules = load_yaml(self.pipeline_config['config_files']['cycle_rules'])
        self.pt_stops_rules = load_yaml(self.pipeline_config['config_files']['pt_stops_rules'])
        
        # Setup paths
        self.staging_dir = Path(f"data/staging/{area_name}")
        self.processed_dir = Path(f"data/processed/{area_name}")
        ensure_dir(self.processed_dir)
        
        self.logger.info(f"Initialized layer processor for {area_name}")
        self.logger.info(f"Staging directory: {self.staging_dir}")
        self.logger.info(f"Processed directory: {self.processed_dir}")
    
    def process_all_layers(self) -> Dict[str, Any]:
        """Process all available layers"""
        if not self.staging_dir.exists():
            self.logger.warning("No staging directory found")
            return {"success": False, "layers": {}}
        
        results = {
            "success": True,
            "layers": {},
            "processed_count": 0,
            "failed_count": 0
        }
        
        # Process layers with category mapping
        mapping_layers = {
            "landuse": (self.landuse_rules, ["landuse", "natural"]),
            "roads": (self.roads_rules, ["highway"]),
            "buildings": (self.buildings_rules, ["building"]),
            "amenities": (self.amenities_rules, ["amenity"]),
            "cycle": (self.cycle_rules, ["highway", "cycleway", "bicycle"]),
            "pt_stops": (self.pt_stops_rules, ["public_transport", "highway", "railway"])
        }
        
        for layer_name, (rules, tag_columns) in mapping_layers.items():
            # Use intelligent processing for PT stops
            if layer_name == "pt_stops":
                success = self.process_pt_stops_with_intelligent_mapping(layer_name, rules)
            else:
                success = self.process_layer_with_mapping(layer_name, rules, tag_columns)
            
            results["layers"][layer_name] = success
            if success:
                results["processed_count"] += 1
            else:
                results["failed_count"] += 1
                results["success"] = False
        
        # Copy any remaining layers that don't need category mapping
        remaining_layers = ["boundaries"]  # Add any other layers that don't need categorization
        copied_count = self.copy_remaining_layers(remaining_layers)
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print processing summary"""
        self.logger.info("=" * 50)
        self.logger.info("PROCESSING SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Area: {self.area_config['area']['full_name']}")
        self.logger.info(f"Processed: {results['processed_count']}")
        self.logger.info(f"Failed: {results['failed_count']}")
        
        for layer_name, success in results["layers"].items():
            status = "✓" if success else "✗"
            self.logger.info(f"  {status} {layer_name}")
        
        if results["success"]:
            self.logger.info("🎉 All layers processed successfully!")
        else:
            self.logger.warning(f"⚠️ {results['failed_count']} layers failed")
    
    def process_pt_stops_with_intelligent_mapping(self, layer_name: str, rules: Dict[str, List[str]]) -> bool:
        """Process PT stops with intelligent categorization based on operators, networks, and attributes"""
        try:
            input_file = self.staging_dir / f"osm_{layer_name}.parquet"
            if not input_file.exists():
                self.logger.warning(f"Layer file not found: {input_file}")
                return False

            gdf = gpd.read_parquet(input_file)
            self.logger.info(f"Processing {layer_name} layer...")
            
            def intelligent_pt_categorize(row):
                """Intelligent categorization based on multiple attributes"""
                
                # Get attributes
                pt_type = row.get('public_transport', '')
                highway = row.get('highway', '')
                railway = row.get('railway', '')
                amenity = row.get('amenity', '')
                operator = str(row.get('operator', '')).lower()
                network = str(row.get('network', '')).lower()
                name = str(row.get('name', '')).lower()
                
                # S-Bahn identification
                if any(keyword in operator for keyword in ['s-bahn', 'db regio']) or \
                   any(keyword in network for keyword in ['s-bahn', 'stuttgart s-bahn']) or \
                   any(keyword in name for keyword in ['s-bahn', 's ']):
                    return 's_bahn'
                
                # U-Bahn identification  
                if railway == 'subway_entrance' or \
                   any(keyword in operator for keyword in ['u-bahn', 'subway']) or \
                   any(keyword in network for keyword in ['u-bahn', 'subway']) or \
                   any(keyword in name for keyword in ['u-bahn', 'u ']):
                    return 'u_bahn'
                
                # Regional/DB trains
                if any(keyword in operator for keyword in ['db ', 'deutsche bahn']) and \
                   not any(keyword in operator for keyword in ['s-bahn']):
                    return 'regional_train'
                
                # Tram/Light rail (SSB operates trams in Stuttgart)
                if railway == 'tram_stop' or \
                   railway == 'light_rail' or \
                   (any(keyword in operator for keyword in ['ssb', 'stuttgarter straßenbahn']) and 
                    pt_type in ['platform', 'stop_position'] and highway != 'bus_stop'):
                    return 'tram'
                
                # Bus stops and stations
                if highway == 'bus_stop':
                    return 'bus'
                if amenity == 'bus_station':
                    return 'bus_station'
                
                # Taxi stands
                if amenity == 'taxi':
                    return 'taxi'
                
                # Railway stations (general)
                if railway in ['station', 'halt', 'stop']:
                    return 'railway_station'
                
                # Railway platforms (general)
                if railway == 'platform':
                    return 'railway_platform'
                
                # Subway entrances
                if railway == 'subway_entrance':
                    return 'subway'
                
                # General categorization by public_transport type
                if pt_type == 'platform':
                    return 'platform'
                elif pt_type == 'stop_position':
                    return 'stop_position'
                elif pt_type == 'station':
                    return 'transport_hub'
                elif pt_type == 'stop_area':
                    return 'stop_area'
                elif pt_type in ['entrance', 'info_board', 'platform_edge', 'platform_access', 'service_center']:
                    return 'transport_service'
                
                return 'other'
            
            # Apply intelligent categorization
            gdf['category'] = gdf.apply(intelligent_pt_categorize, axis=1)
            
            # Log category distribution
            category_counts = gdf['category'].value_counts().to_dict()
            category_str = ', '.join([f"'{k}': {v}" for k, v in category_counts.items()])
            self.logger.info(f"{layer_name.title()} categories: {{{category_str}}}")
            
            # Save processed data
            output_file = self.processed_dir / f"{layer_name}_categorized.parquet"
            ensure_dir(output_file.parent)
            gdf.to_parquet(output_file)
            
            self.logger.info(f"✓ {layer_name.title()} processed: {len(gdf)} features -> {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process {layer_name}: {e}")
            return False

    def process_layer_with_mapping(self, layer_name: str, mapping_rules: Dict[str, list], 
                                 tag_columns: List[str]) -> bool:
        """Process any layer with category mapping"""
        try:
            input_file = self.staging_dir / f"osm_{layer_name}.parquet"
            output_file = self.processed_dir / f"{layer_name}_categorized.parquet"
            
            if not input_file.exists():
                self.logger.warning(f"{layer_name.title()} file not found: {input_file}")
                return False
            
            self.logger.info(f"Processing {layer_name} layer...")
            gdf = gpd.read_parquet(input_file)
            
            # Determine primary tag column
            tag_column = self.determine_primary_tag_column(gdf, tag_columns, tag_columns[0])
            
            if not tag_column:
                self.logger.warning(f"No suitable tag column found in {layer_name} data")
                return False
            
            # Apply category mapping
            processed_gdf = apply_category_mapping(gdf, mapping_rules, tag_column)
            
            # Log category distribution
            category_counts = processed_gdf["category"].value_counts()
            self.logger.info(f"{layer_name.title()} categories: {dict(category_counts)}")
            
            # Save processed data
            processed_gdf.to_parquet(output_file)
            self.logger.info(f"✓ {layer_name.title()} processed: {len(processed_gdf)} features -> {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Error processing {layer_name}: {e}")
            return False
    
    def determine_primary_tag_column(self, gdf: gpd.GeoDataFrame, 
                                   candidate_columns: List[str], preferred: str) -> Optional[str]:
        """Determine which column to use for category mapping"""
        # Check if preferred column exists and has data
        if preferred in gdf.columns and gdf[preferred].notna().sum() > 0:
            return preferred
        
        # Check other candidates
        for col in candidate_columns:
            if col in gdf.columns and gdf[col].notna().sum() > 0:
                self.logger.info(f"Using {col} column for {preferred} mapping")
                return col
        
        return None
    
    def copy_remaining_layers(self, layer_names: List[str]) -> int:
        """Copy layers that don't need category mapping"""
        copied_count = 0
        
        for layer in layer_names:
            input_file = self.staging_dir / f"osm_{layer}.parquet"
            output_file = self.processed_dir / f"{layer}.parquet"
            
            if input_file.exists():
                try:
                    gdf = gpd.read_parquet(input_file)
                    
                    # Add basic metadata columns
                    gdf["processing_timestamp"] = pd.Timestamp.now()
                    gdf["source_layer"] = layer
                    
                    gdf.to_parquet(output_file)
                    self.logger.info(f"✓ Copied {layer}: {len(gdf)} features -> {output_file}")
                    copied_count += 1
                except Exception as e:
                    self.logger.error(f"✗ Error copying {layer}: {e}")
            else:
                self.logger.warning(f"Layer file not found: {input_file}")
        
        return copied_count


def apply_category_mapping(gdf: gpd.GeoDataFrame, mapping_rules: Dict[str, list], 
                          tag_column: str) -> gpd.GeoDataFrame:
    """Apply category mapping rules to a GeoDataFrame"""
    # Create a copy to avoid modifying original
    result_gdf = gdf.copy()
    
    # Initialize category column
    result_gdf["category"] = "other"
    
    # Apply mapping rules
    for category, tag_values in mapping_rules.items():
        if tag_column in result_gdf.columns:
            mask = result_gdf[tag_column].isin(tag_values)
            result_gdf.loc[mask, "category"] = category
    
    # Add raw tag column for reference
    if tag_column in result_gdf.columns:
        result_gdf["raw_tag"] = result_gdf[tag_column]
    
    return result_gdf

def process_landuse_layer(staging_dir: Path, processed_dir: Path, 
                         mapping_rules: Dict[str, list]) -> bool:
    """Process landuse layer with category mapping"""
    try:
        input_file = staging_dir / "osm_landuse.parquet"
        output_file = processed_dir / "landuse_categorized.parquet"
        
        if not input_file.exists():
            logger.warning(f"Landuse file not found: {input_file}")
            return False
        
        logger.info("Processing landuse layer...")
        gdf = gpd.read_parquet(input_file)
        
        # Determine primary tag column (landuse or natural)
        tag_column = None
        if 'landuse' in gdf.columns and gdf['landuse'].notna().sum() > 0:
            tag_column = 'landuse'
        elif 'natural' in gdf.columns and gdf['natural'].notna().sum() > 0:
            tag_column = 'natural'
        else:
            logger.warning("No suitable tag column found in landuse data")
            return False
        
        processed_gdf = apply_category_mapping(gdf, mapping_rules, tag_column)
        
        # Log category distribution
        category_counts = processed_gdf["category"].value_counts()
        logger.info(f"Landuse categories: {category_counts.to_dict()}")
        
        processed_gdf.to_parquet(output_file)
        logger.info(f"✓ Landuse processed: {len(processed_gdf)} features -> {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error processing landuse: {e}")
        return False

def process_roads_layer(staging_dir: Path, processed_dir: Path, 
                       mapping_rules: Dict[str, list]) -> bool:
    """Process roads layer with category mapping"""
    try:
        input_file = staging_dir / "osm_roads.parquet"
        output_file = processed_dir / "roads_categorized.parquet"
        
        if not input_file.exists():
            logger.warning(f"Roads file not found: {input_file}")
            return False
        
        logger.info("Processing roads layer...")
        gdf = gpd.read_parquet(input_file)
        
        # Use highway column for roads
        if 'highway' not in gdf.columns:
            logger.warning("No 'highway' column found in roads data")
            return False
        
        processed_gdf = apply_category_mapping(gdf, mapping_rules, 'highway')
        
        # Log category distribution
        category_counts = processed_gdf["category"].value_counts()
        logger.info(f"Road categories: {category_counts.to_dict()}")
        
        processed_gdf.to_parquet(output_file)
        logger.info(f"✓ Roads processed: {len(processed_gdf)} features -> {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error processing roads: {e}")
        return False

def copy_other_layers(staging_dir: Path, processed_dir: Path) -> int:
    """Copy other layers (without category mapping) to processed directory"""
    copied_count = 0
    other_layers = ["buildings", "cycle", "amenities", "pt_stops", "boundaries"]
    
    for layer in other_layers:
        input_file = staging_dir / f"osm_{layer}.parquet"
        output_file = processed_dir / f"{layer}.parquet"
        
        if input_file.exists():
            try:
                gdf = gpd.read_parquet(input_file)
                gdf.to_parquet(output_file)
                logger.info(f"✓ Copied {layer}: {len(gdf)} features -> {output_file}")
                copied_count += 1
            except Exception as e:
                logger.error(f"✗ Error copying {layer}: {e}")
        else:
            logger.warning(f"Layer file not found: {input_file}")
    
    return copied_count

def main():
    parser = argparse.ArgumentParser(description='Process extracted OSM layers with category mappings')
    parser.add_argument('--city', required=True, help='City/area name (must match YAML in areas/)')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=level)

    try:
        pipeline_config = load_pipeline_config()
        area_config = load_area_config(args.city)

        # Initialize processor and run
        processor = LayerProcessor(args.city, test_mode=args.test)
        results = processor.process_all_layers()
        processor.print_summary(results)

        return 0 if results["success"] else 1

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    import argparse, sys
    sys.exit(main())
