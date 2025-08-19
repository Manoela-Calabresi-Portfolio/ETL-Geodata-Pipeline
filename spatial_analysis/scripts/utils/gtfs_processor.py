#!/usr/bin/env python3
"""
GTFS Data Processor - Utility module for processing GTFS VVS data
"""

import logging
import pandas as pd
import requests
import zipfile
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import os

logger = logging.getLogger(__name__)

def process_gtfs_data(config: Dict[str, Any]) -> None:
    """
    Process GTFS VVS data for Stuttgart analysis
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Starting GTFS data processing...")
    
    # Download GTFS data
    gtfs_data = download_gtfs_vvs(config)
    
    if gtfs_data:
        # Process different GTFS components
        process_stops(gtfs_data, config)
        process_routes(gtfs_data, config)
        process_trips_and_frequencies(gtfs_data, config)
        process_calendar(gtfs_data, config)
        
        # Calculate service frequencies
        calculate_service_frequencies(config)
    
    logger.info("GTFS data processing completed")

def download_gtfs_vvs(config: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """Download GTFS VVS data from MobiData BW"""
    try:
        logger.info("Downloading GTFS VVS data...")
        
        # GTFS VVS URL (MobiData BW)
        gtfs_url = config.get('gtfs_url', 'https://www.mobidata-bw.de/daten/gtfs/vvs.zip')
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / "vvs.zip"
            
            # Download GTFS file
            response = requests.get(gtfs_url, timeout=300)
            response.raise_for_status()
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            # Extract GTFS files
            gtfs_data = {}
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
                
                # Read key GTFS files
                gtfs_files = ['stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt', 
                            'calendar.txt', 'frequencies.txt']
                
                for file_name in gtfs_files:
                    file_path = temp_path / file_name
                    if file_path.exists():
                        try:
                            gtfs_data[file_name.replace('.txt', '')] = pd.read_csv(file_path)
                            logger.info(f"Loaded {file_name}: {len(gtfs_data[file_name.replace('.txt', '')])} records")
                        except Exception as e:
                            logger.warning(f"Could not read {file_name}: {e}")
            
            return gtfs_data
            
    except Exception as e:
        logger.error(f"Error downloading GTFS data: {e}")
        return None

def process_stops(gtfs_data: Dict[str, pd.DataFrame], config: Dict[str, Any]) -> None:
    """Process GTFS stops data"""
    try:
        if 'stops' not in gtfs_data:
            logger.warning("No stops data available")
            return
        
        stops_df = gtfs_data['stops'].copy()
        
        # Filter to Stuttgart area if coordinates available
        if 'stop_lat' in stops_df.columns and 'stop_lon' in stops_df.columns:
            # Approximate Stuttgart bounding box
            stuttgart_bbox = {
                'min_lat': 48.7, 'max_lat': 48.9,
                'min_lon': 9.1, 'max_lon': 9.3
            }
            
            stops_df = stops_df[
                (stops_df['stop_lat'] >= stuttgart_bbox['min_lat']) &
                (stops_df['stop_lat'] <= stuttgart_bbox['max_lat']) &
                (stops_df['stop_lon'] >= stuttgart_bbox['min_lon']) &
                (stops_df['stop_lon'] <= stuttgart_bbox['max_lon'])
            ]
        
        # Save processed stops
        output_path = Path("data/processed/gtfs_stops.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        stops_df.to_parquet(output_path)
        
        logger.info(f"Processed {len(stops_df)} stops")
        
    except Exception as e:
        logger.error(f"Error processing stops: {e}")

def process_routes(gtfs_data: Dict[str, pd.DataFrame], config: Dict[str, Any]) -> None:
    """Process GTFS routes data"""
    try:
        if 'routes' not in gtfs_data:
            logger.warning("No routes data available")
            return
        
        routes_df = gtfs_data['routes'].copy()
        
        # Add route type descriptions
        route_type_mapping = {
            0: 'tram',
            1: 'subway',
            2: 'rail',
            3: 'bus',
            4: 'ferry',
            5: 'cable_tram',
            6: 'aerial_lift',
            7: 'funicular',
            11: 'trolleybus',
            12: 'monorail'
        }
        
        routes_df['route_type_desc'] = routes_df['route_type'].map(route_type_mapping)
        
        # Save processed routes
        output_path = Path("data/processed/gtfs_routes.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        routes_df.to_parquet(output_path)
        
        logger.info(f"Processed {len(routes_df)} routes")
        
    except Exception as e:
        logger.error(f"Error processing routes: {e}")

def process_trips_and_frequencies(gtfs_data: Dict[str, pd.DataFrame], config: Dict[str, Any]) -> None:
    """Process GTFS trips and frequencies data"""
    try:
        if 'trips' not in gtfs_data:
            logger.warning("No trips data available")
            return
        
        trips_df = gtfs_data['trips'].copy()
        
        # Process frequencies if available
        if 'frequencies' in gtfs_data:
            frequencies_df = gtfs_data['frequencies'].copy()
            
            # Merge with trips to get route information
            trips_with_freq = trips_df.merge(
                frequencies_df, on='trip_id', how='left'
            )
            
            # Calculate headway in minutes
            trips_with_freq['headway_minutes'] = trips_with_freq['headway_secs'] / 60
            
            # Save processed trips with frequencies
            output_path = Path("data/processed/gtfs_trips_with_frequencies.parquet")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            trips_with_freq.to_parquet(output_path)
            
            logger.info(f"Processed {len(trips_with_freq)} trips with frequencies")
        else:
            # Save trips without frequencies
            output_path = Path("data/processed/gtfs_trips.parquet")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            trips_df.to_parquet(output_path)
            
            logger.info(f"Processed {len(trips_df)} trips")
        
    except Exception as e:
        logger.error(f"Error processing trips and frequencies: {e}")

def process_calendar(gtfs_data: Dict[str, pd.DataFrame], config: Dict[str, Any]) -> None:
    """Process GTFS calendar data"""
    try:
        if 'calendar' not in gtfs_data:
            logger.warning("No calendar data available")
            return
        
        calendar_df = gtfs_data['calendar'].copy()
        
        # Save calendar data
        output_path = Path("data/processed/gtfs_calendar.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        calendar_df.to_parquet(output_path)
        
        logger.info(f"Processed {len(calendar_df)} calendar entries")
        
    except Exception as e:
        logger.error(f"Error processing calendar: {e}")

def calculate_service_frequencies(config: Dict[str, Any]) -> None:
    """Calculate service frequencies for each stop"""
    try:
        logger.info("Calculating service frequencies...")
        
        # Load processed data
        stops_path = Path("data/processed/gtfs_stops.parquet")
        trips_path = Path("data/processed/gtfs_trips_with_frequencies.parquet")
        
        if not stops_path.exists() or not trips_path.exists():
            logger.warning("Required GTFS files not found for frequency calculation")
            return
        
        stops_df = pd.read_parquet(stops_path)
        trips_df = pd.read_parquet(trips_path)
        
        # Calculate average headway per stop (this would need stop_times.txt for full calculation)
        # For now, create a basic frequency summary
        frequency_summary = trips_df.groupby('route_id').agg({
            'headway_minutes': ['mean', 'min', 'max']
        }).round(2)
        
        frequency_summary.columns = ['avg_headway_min', 'min_headway_min', 'max_headway_min']
        frequency_summary.reset_index(inplace=True)
        
        # Save frequency summary
        output_path = Path("data/processed/gtfs_frequency_summary.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frequency_summary.to_parquet(output_path)
        
        logger.info(f"Calculated frequencies for {len(frequency_summary)} routes")
        
    except Exception as e:
        logger.error(f"Error calculating service frequencies: {e}")
