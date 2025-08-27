#!/usr/bin/env python3
"""
Multi-Source Data Loader

This module provides city-agnostic data loading functionality for the ETL Geodata Pipeline,
including OSM data extraction via QuackOSM and support for various data formats.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import logging
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import quackosm
    from quackosm import PbfFileReader, OsmPbfReader
    QUACKOSM_AVAILABLE = True
except ImportError:
    QUACKOSM_AVAILABLE = False
    print("⚠️ QuackOSM not available. Install with: pip install quackosm")

try:
    import geopandas as gpd
    import pandas as pd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    print("⚠️ GeoPandas not available. Install with: pip install geopandas")

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Multi-source data loader for city-agnostic OSM data extraction and processing.
    
    This class provides methods to extract OSM data using QuackOSM for any city,
    supporting various output formats and data types.
    """
    
    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the DataLoader.
        
        Args:
            output_dir: Directory to save extracted data. If None, uses current directory.
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if not QUACKOSM_AVAILABLE:
            logger.warning("QuackOSM not available. OSM extraction will not work.")
        if not GEOPANDAS_AVAILABLE:
            logger.warning("GeoPandas not available. Some data processing may not work.")
    
    def extract_osm_data(
        self,
        pbf_file: Union[str, Path],
        bbox: Tuple[float, float, float, float],
        output_name: str,
        tags_filter: Optional[Dict] = None,
        output_format: str = "parquet",
        crs: str = "EPSG:4326"
    ) -> Optional[gpd.GeoDataFrame]:
        """
        Extract OSM data using QuackOSM for the specified bounding box.
        
        Args:
            pbf_file: Path to OSM PBF file
            bbox: Bounding box as (min_lon, min_lat, max_lon, max_lat)
            output_name: Name for the output file (without extension)
            tags_filter: Dictionary of OSM tags to filter by
            output_format: Output format ('parquet', 'geojson', 'gpkg')
            crs: Coordinate reference system for output
            
        Returns:
            GeoDataFrame with extracted data, or None if extraction failed
        """
        if not QUACKOSM_AVAILABLE:
            logger.error("QuackOSM not available. Cannot extract OSM data.")
            return None
        
        try:
            logger.info(f"🚀 Extracting OSM data for {output_name}")
            logger.info(f"📁 PBF file: {pbf_file}")
            logger.info(f"📍 Bounding box: {bbox}")
            
            # Create output directory
            output_path = self.output_dir / output_name
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize QuackOSM reader
            reader = PbfFileReader(pbf_file)
            
            # Extract data with bounding box filter
            if tags_filter:
                logger.info(f"🔍 Applying tags filter: {tags_filter}")
                gdf = reader.get_features_gdf(
                    tags_filter=tags_filter,
                    bbox=bbox
                )
            else:
                logger.info("🔍 No tags filter applied - extracting all features")
                gdf = reader.get_features_gdf(bbox=bbox)
            
            if gdf.empty:
                logger.warning(f"⚠️ No data found for {output_name} in the specified area")
                return None
            
            logger.info(f"✅ Extracted {len(gdf)} features for {output_name}")
            
            # Set CRS
            gdf = gdf.set_crs(crs)
            
            # Save data
            self._save_data(gdf, output_path, output_name, output_format)
            
            return gdf
            
        except Exception as e:
            logger.error(f"❌ Failed to extract OSM data for {output_name}: {e}")
            return None
    
    def extract_osm_layers(
        self,
        pbf_file: Union[str, Path],
        bbox: Tuple[float, float, float, float],
        output_name: str,
        layers: Optional[List[str]] = None,
        output_format: str = "parquet",
        crs: str = "EPSG:4326"
    ) -> Dict[str, gpd.GeoDataFrame]:
        """
        Extract multiple OSM layers at once.
        
        Args:
            pbf_file: Path to OSM PBF file
            bbox: Bounding box as (min_lon, min_lat, max_lon, max_lat)
            output_name: Base name for output files
            layers: List of layer names to extract. If None, extracts common layers
            output_format: Output format for all layers
            crs: Coordinate reference system for output
            
        Returns:
            Dictionary mapping layer names to GeoDataFrames
        """
        if layers is None:
            layers = [
                "amenities",
                "buildings", 
                "landuse",
                "roads",
                "public_transport",
                "cycle_infrastructure"
            ]
        
        results = {}
        
        for layer in layers:
            logger.info(f"🔄 Extracting layer: {layer}")
            
            # Define tags filter for each layer
            tags_filter = self._get_layer_tags(layer)
            
            if tags_filter:
                gdf = self.extract_osm_data(
                    pbf_file=pbf_file,
                    bbox=bbox,
                    output_name=f"{output_name}_{layer}",
                    tags_filter=tags_filter,
                    output_format=output_format,
                    crs=crs
                )
                
                if gdf is not None:
                    results[layer] = gdf
                    logger.info(f"✅ {layer}: {len(gdf)} features")
                else:
                    logger.warning(f"⚠️ {layer}: No data extracted")
            else:
                logger.warning(f"⚠️ {layer}: No tags filter defined")
        
        return results
    
    def _get_layer_tags(self, layer: str) -> Optional[Dict]:
        """
        Get OSM tags filter for a specific layer.
        
        Args:
            layer: Layer name
            
        Returns:
            Dictionary of OSM tags to filter by
        """
        layer_tags = {
            "amenities": {
                "amenity": ["*"],
                "shop": ["*"],
                "healthcare": ["*"],
                "leisure": ["*"],
                "tourism": ["*"]
            },
            "buildings": {
                "building": ["*"]
            },
            "landuse": {
                "landuse": ["*"],
                "natural": ["*"],
                "leisure": ["park", "garden", "playground"]
            },
            "roads": {
                "highway": ["*"]
            },
            "public_transport": {
                "public_transport": ["*"],
                "railway": ["station", "stop", "platform", "tram_stop"],
                "amenity": ["bus_station"]
            },
            "cycle_infrastructure": {
                "highway": ["cycleway", "path"],
                "cycleway": ["*"]
            }
        }
        
        return layer_tags.get(layer)
    
    def _save_data(
        self,
        gdf: gpd.GeoDataFrame,
        output_path: Path,
        output_name: str,
        output_format: str
    ) -> None:
        """
        Save GeoDataFrame to the specified format.
        
        Args:
            gdf: GeoDataFrame to save
            output_path: Output directory path
            output_name: Name for the output file
            output_format: Output format
        """
        try:
            if output_format == "parquet":
                file_path = output_path / f"{output_name}.parquet"
                gdf.to_parquet(file_path)
                logger.info(f"💾 Saved: {file_path}")
                
            elif output_format == "geojson":
                file_path = output_path / f"{output_name}.geojson"
                gdf.to_file(file_path, driver="GeoJSON")
                logger.info(f"💾 Saved: {file_path}")
                
            elif output_format == "gpkg":
                file_path = output_path / f"{output_name}.gpkg"
                gdf.to_file(file_path, driver="GPKG")
                logger.info(f"💾 Saved: {file_path}")
                
            else:
                logger.warning(f"⚠️ Unsupported format: {output_format}")
                
        except Exception as e:
            logger.error(f"❌ Failed to save {output_name}: {e}")
    
    def load_data(
        self,
        file_path: Union[str, Path],
        file_type: Optional[str] = None
    ) -> Optional[Union[gpd.GeoDataFrame, pd.DataFrame]]:
        """
        Load data from various file formats.
        
        Args:
            file_path: Path to the data file
            file_type: File type ('auto', 'parquet', 'geojson', 'gpkg', 'csv')
            
        Returns:
            Loaded data as GeoDataFrame or DataFrame
        """
        if not GEOPANDAS_AVAILABLE:
            logger.error("GeoPandas not available. Cannot load data.")
            return None
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"❌ File not found: {file_path}")
            return None
        
        try:
            # Auto-detect file type if not specified
            if file_type is None or file_type == "auto":
                if file_path.suffix.lower() in [".geojson", ".json"]:
                    file_type = "geojson"
                elif file_path.suffix.lower() == ".parquet":
                    file_type = "parquet"
                elif file_path.suffix.lower() == ".gpkg":
                    file_type = "gpkg"
                elif file_path.suffix.lower() == ".csv":
                    file_type = "csv"
                else:
                    file_type = "auto"
            
            logger.info(f"📂 Loading data from: {file_path}")
            
            if file_type == "parquet":
                df = pd.read_parquet(file_path)
                # Check if it has geometry column
                if "geometry" in df.columns:
                    return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
                return df
                
            elif file_type in ["geojson", "gpkg"]:
                return gpd.read_file(file_path)
                
            elif file_type == "csv":
                return pd.read_csv(file_path)
                
            else:
                # Try to auto-detect
                return gpd.read_file(file_path)
                
        except Exception as e:
            logger.error(f"❌ Failed to load data from {file_path}: {e}")
            return None
    
    def get_data_summary(self, gdf: gpd.GeoDataFrame) -> Dict:
        """
        Get a summary of the loaded data.
        
        Args:
            gdf: GeoDataFrame to summarize
            
        Returns:
            Dictionary with data summary
        """
        if gdf is None or gdf.empty:
            return {"error": "No data to summarize"}
        
        summary = {
            "total_features": len(gdf),
            "columns": list(gdf.columns),
            "geometry_type": str(gdf.geometry.geom_type.iloc[0]) if not gdf.empty else None,
            "crs": str(gdf.crs) if hasattr(gdf, 'crs') else None,
            "memory_usage": f"{gdf.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
        }
        
        # Add column statistics for non-geometry columns
        numeric_columns = gdf.select_dtypes(include=['number']).columns
        if len(numeric_columns) > 0:
            summary["numeric_columns"] = list(numeric_columns)
        
        return summary

def extract_city_osm_data(
    pbf_file: Union[str, Path],
    bbox: Tuple[float, float, float, float],
    city_name: str,
    output_dir: Optional[Union[str, Path]] = None,
    layers: Optional[List[str]] = None,
    output_format: str = "parquet"
) -> Dict[str, gpd.GeoDataFrame]:
    """
    Convenience function to extract OSM data for a city.
    
    Args:
        pbf_file: Path to OSM PBF file
        bbox: Bounding box as (min_lon, min_lat, max_lon, max_lat)
        city_name: Name of the city for output naming
        output_dir: Output directory (defaults to city_name)
        layers: List of layers to extract (defaults to all common layers)
        output_format: Output format for all files
        
    Returns:
        Dictionary mapping layer names to GeoDataFrames
    """
    if output_dir is None:
        output_dir = Path(city_name.lower().replace(" ", "_"))
    
    loader = DataLoader(output_dir)
    
    logger.info(f"🏙️ Extracting OSM data for {city_name}")
    logger.info(f"📁 Output directory: {output_dir}")
    
    results = loader.extract_osm_layers(
        pbf_file=pbf_file,
        bbox=bbox,
        output_name=city_name.lower().replace(" ", "_"),
        layers=layers,
        output_format=output_format
    )
    
    logger.info(f"🎉 Extraction complete for {city_name}")
    logger.info(f"📊 Extracted layers: {list(results.keys())}")
    
    return results

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Example: Extract Stuttgart data
    stuttgart_bbox = (9.0, 48.6, 9.4, 48.9)  # Stuttgart bounding box
    pbf_file = "data_final/stuttgart/raw/baden-wuerttemberg-latest.osm.pbf"
    
    if Path(pbf_file).exists():
        results = extract_city_osm_data(
            pbf_file=pbf_file,
            bbox=stuttgart_bbox,
            city_name="Stuttgart",
            output_format="parquet"
        )
        
        for layer, gdf in results.items():
            print(f"\n📊 {layer}: {len(gdf)} features")
    else:
        print(f"❌ PBF file not found: {pbf_file}")
        print("💡 Update the pbf_file path to test the data loader")
