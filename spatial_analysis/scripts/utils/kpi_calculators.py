#!/usr/bin/env python3
"""
KPI Calculators - Utility module for calculating mobility and walkability indicators
"""

import logging
import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
from shapely.geometry import Point
from shapely.ops import nearest_points

logger = logging.getLogger(__name__)

def calculate_transport_indicators(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Calculate transport public indicators for each district
    
    Args:
        config: Configuration dictionary
        
    Returns:
        DataFrame with transport KPIs per district
    """
    logger.info("Calculating transport indicators...")
    
    try:
        # Load required data
        districts = load_district_data(config)
        gtfs_stops = load_gtfs_stops(config)
        population = load_population_data(config)
        
        if districts is None or gtfs_stops is None:
            logger.error("Required data not available for transport indicators")
            return pd.DataFrame()
        
        # Calculate transport KPIs
        transport_kpis = []
        
        for _, district in districts.iterrows():
            district_kpis = calculate_district_transport_kpis(
                district, gtfs_stops, population, config
            )
            transport_kpis.append(district_kpis)
        
        # Combine all district KPIs
        transport_df = pd.DataFrame(transport_kpis)
        
        # Save results
        output_path = Path("data/results/transport_kpis.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        transport_df.to_parquet(output_path)
        
        logger.info(f"Transport KPIs calculated for {len(transport_df)} districts")
        return transport_df
        
    except Exception as e:
        logger.error(f"Error calculating transport indicators: {e}")
        return pd.DataFrame()

def calculate_walkability_indicators(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Calculate walkability indicators for each district
    
    Args:
        config: Configuration dictionary
        
    Returns:
        DataFrame with walkability KPIs per district
    """
    logger.info("Calculating walkability indicators...")
    
    try:
        # Load required data
        districts = load_district_data(config)
        intersections = load_osm_intersections(config)
        pois = load_additional_pois(config)
        population = load_population_data(config)
        
        if districts is None:
            logger.error("Required data not available for walkability indicators")
            return pd.DataFrame()
        
        # Calculate walkability KPIs
        walkability_kpis = []
        
        for _, district in districts.iterrows():
            district_kpis = calculate_district_walkability_kpis(
                district, intersections, pois, population, config
            )
            walkability_kpis.append(district_kpis)
        
        # Combine all district KPIs
        walkability_df = pd.DataFrame(walkability_kpis)
        
        # Save results
        output_path = Path("data/results/walkability_kpis.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        walkability_df.to_parquet(output_path)
        
        logger.info(f"Walkability KPIs calculated for {len(walkability_df)} districts")
        return walkability_df
        
    except Exception as e:
        logger.error(f"Error calculating walkability indicators: {e}")
        return pd.DataFrame()

def calculate_green_indicators(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Calculate green area accessibility indicators for each district
    
    Args:
        config: Configuration dictionary
        
    Returns:
        DataFrame with green area KPIs per district
    """
    logger.info("Calculating green area indicators...")
    
    try:
        # Load required data
        districts = load_district_data(config)
        greenspaces = load_osm_greenspaces(config)
        population = load_population_data(config)
        
        if districts is None:
            logger.error("Required data not available for green area indicators")
            return pd.DataFrame()
        
        # Calculate green area KPIs
        green_kpis = []
        
        for _, district in districts.iterrows():
            district_kpis = calculate_district_green_kpis(
                district, greenspaces, population, config
            )
            green_kpis.append(district_kpis)
        
        # Combine all district KPIs
        green_df = pd.DataFrame(green_kpis)
        
        # Save results
        output_path = Path("data/results/green_kpis.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        green_df.to_parquet(output_path)
        
        logger.info(f"Green area KPIs calculated for {len(green_df)} districts")
        return green_df
        
    except Exception as e:
        logger.error(f"Error calculating green area indicators: {e}")
        return pd.DataFrame()

def aggregate_district_kpis(config: Dict[str, Any], kpi_weights: Dict[str, float]) -> pd.DataFrame:
    """
    Aggregate all KPIs into a comprehensive district ranking
    
    Args:
        config: Configuration dictionary
        kpi_weights: Dictionary with KPI weights
        
    Returns:
        DataFrame with aggregated KPIs and rankings
    """
    logger.info("Aggregating district KPIs...")
    
    try:
        # Load all KPI results
        transport_kpis = load_kpi_results("transport_kpis")
        walkability_kpis = load_kpi_results("walkability_kpis")
        green_kpis = load_kpi_results("green_kpis")
        
        if transport_kpis.empty and walkability_kpis.empty and green_kpis.empty:
            logger.error("No KPI data available for aggregation")
            return pd.DataFrame()
        
        # Merge all KPIs by district
        all_kpis = merge_district_kpis(transport_kpis, walkability_kpis, green_kpis)
        
        # Calculate weighted scores
        all_kpis = calculate_weighted_scores(all_kpis, kpi_weights)
        
        # Add rankings
        all_kpis = add_rankings(all_kpis)
        
        # Save aggregated results to original location
        output_path = Path("data/results/district_kpis_aggregated.parquet")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        all_kpis.to_parquet(output_path)
        
        # NEW: Export normalized KPIs for spatialviz visualization
        export_normalized_kpis_for_spatialviz(all_kpis)
        
        logger.info(f"Aggregated KPIs for {len(all_kpis)} districts")
        return all_kpis
        
    except Exception as e:
        logger.error(f"Error aggregating district KPIs: {e}")
        return pd.DataFrame()

def export_normalized_kpis_for_spatialviz(district_kpis_gdf: pd.DataFrame):
    """
    Export KPIs in normalized long format for spatialviz visualization
    
    Args:
        district_kpis_gdf: DataFrame with district KPIs
    """
    try:
        logger.info("Exporting normalized KPIs for spatialviz...")
        
        # Import required libraries
        import geopandas as gpd
        from shapely import wkt
        
        # Convert to GeoDataFrame if it's not already
        if not isinstance(district_kpis_gdf, gpd.GeoDataFrame):
            # Check if geometry column exists and convert WKT to geometry
            if 'geometry' in district_kpis_gdf.columns:
                district_kpis_gdf['geometry'] = district_kpis_gdf['geometry'].apply(wkt.loads)
                district_kpis_gdf = gpd.GeoDataFrame(district_kpis_gdf, geometry='geometry')
            else:
                logger.warning("No geometry column found, skipping spatialviz export")
                return
        
        # Ensure CRS is set (assuming EPSG:25832 based on the data)
        if district_kpis_gdf.crs is None:
            district_kpis_gdf.set_crs('EPSG:25832', inplace=True)
        
        # Convert to WGS84 (EPSG:4326) for Kepler/Contextily compatibility
        district_kpis_gdf = district_kpis_gdf.to_crs(4326)
        
        # Define KPI columns to export
        kpi_columns = [
            "amenities_count", 
            "area_km2", 
            "green_landuse_pct", 
            "service_density", 
            "pt_stop_density", 
            "cycle_infra_density", 
            "population_density"
        ]
        
        # Filter to only include districts with geometry and KPI data
        valid_districts = district_kpis_gdf[
            district_kpis_gdf['geometry'].notna() & 
            district_kpis_gdf['STADTBEZIRKNAME'].notna()
        ].copy()
        
        if valid_districts.empty:
            logger.warning("No valid districts with geometry found")
            return
        
        # Melt KPI columns into long format
        id_vars = ["STADTBEZIRKNAME", "geometry"]
        value_vars = [col for col in kpi_columns if col in valid_districts.columns]
        
        if not value_vars:
            logger.warning("No KPI columns found in data")
            return
        
        # Create long format DataFrame
        kpis_long = valid_districts.melt(
            id_vars=id_vars,
            value_vars=value_vars,
            var_name="kpi_name",
            value_name="value"
        )
        
        # Convert back to GeoDataFrame
        kpis_long_gdf = gpd.GeoDataFrame(kpis_long, geometry="geometry", crs=4326)
        
        # Create output directory
        out_dir = Path("../../spatialviz/outputs/stuttgart_analysis")
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as GeoParquet
        parquet_path = out_dir / "stuttgart_kpis.parquet"
        kpis_long_gdf.to_parquet(parquet_path, index=False)
        
        # Optional: Save as GeoJSON for debugging
        geojson_path = out_dir / "stuttgart_kpis.geojson"
        kpis_long_gdf.to_file(geojson_path, driver="GeoJSON")
        
        # Print diagnostic information
        logger.info(f"✅ Exported normalized KPIs to {parquet_path}")
        logger.info(f"✅ Exported GeoJSON for debugging to {geojson_path}")
        logger.info(f"✅ Total rows: {len(kpis_long_gdf)}")
        logger.info(f"✅ Districts: {len(valid_districts)}")
        logger.info(f"✅ KPIs per district: {len(value_vars)}")
        
        # Print value ranges for each KPI
        for kpi in value_vars:
            kpi_data = kpis_long_gdf[kpis_long_gdf["kpi_name"] == kpi]["value"]
            if not kpi_data.empty:
                vmin, vmax = kpi_data.min(), kpi_data.max()
                logger.info(f"  📊 {kpi}: min={vmin:.2f}, max={vmax:.2f}")
        
    except Exception as e:
        logger.error(f"Error exporting normalized KPIs for spatialviz: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Helper functions for data loading and calculations

def load_district_data(config: Dict[str, Any]) -> gpd.GeoDataFrame:
    """Load district boundary data"""
    try:
        districts_path = Path("data/processed/stuttgart_districts.geojson")
        if districts_path.exists():
            return gpd.read_file(districts_path)
        else:
            logger.warning("District boundaries not found")
            return None
    except Exception as e:
        logger.error(f"Error loading district data: {e}")
        return None

def load_gtfs_stops(config: Dict[str, Any]) -> pd.DataFrame:
    """Load GTFS stops data"""
    try:
        stops_path = Path("data/processed/gtfs_stops.parquet")
        if stops_path.exists():
            return pd.read_parquet(stops_path)
        else:
            logger.warning("GTFS stops not found")
            return None
    except Exception as e:
        logger.error(f"Error loading GTFS stops: {e}")
        return None

def load_population_data(config: Dict[str, Any]) -> pd.DataFrame:
    """Load population data by district"""
    try:
        pop_path = Path("data/processed/population_by_district.csv")
        if pop_path.exists():
            return pd.read_csv(pop_path)
        else:
            logger.warning("Population data not found")
            return None
    except Exception as e:
        logger.error(f"Error loading population data: {e}")
        return None

def load_osm_intersections(config: Dict[str, Any]) -> gpd.GeoDataFrame:
    """Load OSM intersections data"""
    try:
        intersections_path = Path("data/processed/osm_intersections.parquet")
        if intersections_path.exists():
            return pd.read_parquet(intersections_path)
        else:
            logger.warning("OSM intersections not found")
            return None
    except Exception as e:
        logger.error(f"Error loading OSM intersections: {e}")
        return None

def load_additional_pois(config: Dict[str, Any]) -> gpd.GeoDataFrame:
    """Load additional POI data"""
    try:
        pois_path = Path("data/processed/osm_additional_pois.parquet")
        if pois_path.exists():
            return pd.read_parquet(pois_path)
        else:
            logger.warning("Additional POIs not found")
            return None
    except Exception as e:
        logger.error(f"Error loading additional POIs: {e}")
        return None

def load_osm_greenspaces(config: Dict[str, Any]) -> gpd.GeoDataFrame:
    """Load OSM green spaces data"""
    try:
        greenspaces_path = Path("data/processed/osm_greenspaces.parquet")
        if greenspaces_path.exists():
            return pd.read_parquet(greenspaces_path)
        else:
            logger.warning("OSM green spaces not found")
            return None
    except Exception as e:
        logger.error(f"Error loading OSM green spaces: {e}")
        return None

def load_kpi_results(kpi_type: str) -> pd.DataFrame:
    """Load KPI results from data/results folder"""
    try:
        kpi_path = Path(f"data/results/{kpi_type}.parquet")
        if kpi_path.exists():
            return pd.read_parquet(kpi_path)
        else:
            return pd.DataFrame()
    except Exception as e:
        logger.warning(f"Could not load {kpi_type}: {e}")
        return pd.DataFrame()

# District-level KPI calculation functions

def calculate_district_transport_kpis(district, gtfs_stops, population, config):
    """Calculate transport KPIs for a single district"""
    district_id = district.get('district_id', district.get('name', 'unknown'))
    
    # Basic structure - implement actual calculations based on your data
    kpis = {
        'district_id': district_id,
        'pt_stops_count': 0,
        'high_freq_stops_count': 0,
        'avg_lines_per_stop': 0.0,
        'population_300m_pt': 0.0
    }
    
    # TODO: Implement actual calculations
    # This is a placeholder structure
    
    return kpis

def calculate_district_walkability_kpis(district, intersections, pois, population, config):
    """Calculate walkability KPIs for a single district"""
    district_id = district.get('district_id', district.get('name', 'unknown'))
    
    # Basic structure - implement actual calculations based on your data
    kpis = {
        'district_id': district_id,
        'intersection_density': 0.0,
        'poi_density': 0.0,
        'population_500m_poi': 0.0,
        'walkability_score': 0.0
    }
    
    # TODO: Implement actual calculations
    # This is a placeholder structure
    
    return kpis

def calculate_district_green_kpis(district, greenspaces, population, config):
    """Calculate green area KPIs for a single district"""
    district_id = district.get('district_id', district.get('name', 'unknown'))
    
    # Basic structure - implement actual calculations based on your data
    kpis = {
        'district_id': district_id,
        'greenspace_area_ha': 0.0,
        'greenspace_per_capita': 0.0,
        'population_500m_green': 0.0,
        'green_accessibility_score': 0.0
    }
    
    # TODO: Implement actual calculations
    # This is a placeholder structure
    
    return kpis

def merge_district_kpis(transport_kpis, walkability_kpis, green_kpis):
    """Merge all KPI dataframes by district"""
    # Start with transport KPIs as base
    merged = transport_kpis.copy() if not transport_kpis.empty else pd.DataFrame()
    
    # Merge walkability KPIs
    if not walkability_kpis.empty:
        if merged.empty:
            merged = walkability_kpis.copy()
        else:
            merged = merged.merge(walkability_kpis, on='district_id', how='outer')
    
    # Merge green KPIs
    if not green_kpis.empty:
        if merged.empty:
            merged = green_kpis.copy()
        else:
            merged = merged.merge(green_kpis, on='district_id', how='outer')
    
    return merged

def calculate_weighted_scores(kpis_df, kpi_weights):
    """Calculate weighted scores for each district"""
    if kpis_df.empty:
        return kpis_df
    
    # Normalize KPI values to 0-100 scale
    numeric_columns = kpis_df.select_dtypes(include=[np.number]).columns
    numeric_columns = [col for col in numeric_columns if col != 'district_id']
    
    for col in numeric_columns:
        if col in kpi_weights:
            # Normalize to 0-100 scale
            min_val = kpis_df[col].min()
            max_val = kpis_df[col].max()
            if max_val > min_val:
                kpis_df[f'{col}_normalized'] = ((kpis_df[col] - min_val) / (max_val - min_val)) * 100
            else:
                kpis_df[f'{col}_normalized'] = 50  # Default middle value
    
    # Calculate weighted total score
    normalized_cols = [col for col in kpis_df.columns if col.endswith('_normalized')]
    weighted_scores = []
    
    for _, row in kpis_df.iterrows():
        score = 0
        for col in normalized_cols:
            base_col = col.replace('_normalized', '')
            if base_col in kpi_weights:
                score += row[col] * kpi_weights[base_col]
        weighted_scores.append(score)
    
    kpis_df['weighted_total_score'] = weighted_scores
    
    return kpis_df

def add_rankings(kpis_df):
    """Add ranking columns to the KPIs dataframe"""
    if kpis_df.empty:
        return kpis_df
    
    # Add rankings for different metrics
    ranking_columns = ['weighted_total_score']
    
    for col in ranking_columns:
        if col in kpis_df.columns:
            kpis_df[f'{col}_rank'] = kpis_df[col].rank(ascending=False, method='min')
    
    return kpis_df
