"""
Data cleaning and repair module for spatial ETL pipeline.

Provides functions to fix common spatial data quality issues:
- Invalid geometries (self-intersections, topology errors)
- Duplicate features (geometry and attribute-based)
- Tiny features below minimum thresholds
- Null value handling for optional attributes
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import warnings

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely.validation import make_valid, explain_validity
from shapely import wkt
import shapely

from .utils import ensure_directory

logger = logging.getLogger(__name__)

# Suppress shapely warnings for cleaner output
warnings.filterwarnings("ignore", category=shapely.errors.ShapelyDeprecationWarning)


class SpatialDataCleaner:
    """Comprehensive spatial data cleaner and repair tool."""
    
    def __init__(self, 
                 min_area_m2: float = 1.0,
                 min_length_m: float = 1.0,
                 analytics_crs: str = "EPSG:25832"):
        """
        Initialize cleaner with thresholds.
        
        Args:
            min_area_m2: Minimum area threshold for polygons
            min_length_m: Minimum length threshold for lines
            analytics_crs: CRS for metric calculations
        """
        self.min_area_m2 = min_area_m2
        self.min_length_m = min_length_m
        self.analytics_crs = analytics_crs
    
    def clean_layer(self, 
                   gdf: gpd.GeoDataFrame, 
                   layer_name: str,
                   fix_geometries: bool = True,
                   remove_duplicates: bool = True,
                   remove_tiny_features: bool = True,
                   fill_nulls: bool = False) -> Tuple[gpd.GeoDataFrame, Dict[str, Any]]:
        """
        Clean a GeoDataFrame layer comprehensively.
        
        Args:
            gdf: Input GeoDataFrame
            layer_name: Name for logging
            fix_geometries: Whether to repair invalid geometries
            remove_duplicates: Whether to remove duplicate features
            remove_tiny_features: Whether to remove tiny features
            fill_nulls: Whether to fill null values with defaults
            
        Returns:
            Tuple of (cleaned_gdf, cleaning_report)
        """
        logger.info(f"🧹 Cleaning layer: {layer_name}")
        
        if gdf.empty:
            return gdf, {"layer_name": layer_name, "original_features": 0, "final_features": 0}
        
        original_count = len(gdf)
        cleaned_gdf = gdf.copy()
        
        cleaning_report = {
            "layer_name": layer_name,
            "original_features": original_count,
            "operations": [],
            "removed_features": 0,
            "repaired_features": 0
        }
        
        # 1. Fix invalid geometries
        if fix_geometries:
            cleaned_gdf, geom_report = self._fix_geometries(cleaned_gdf)
            cleaning_report["operations"].append(geom_report)
            cleaning_report["repaired_features"] += geom_report["repaired_count"]
        
        # 2. Remove duplicates
        if remove_duplicates:
            cleaned_gdf, dup_report = self._remove_duplicates(cleaned_gdf)
            cleaning_report["operations"].append(dup_report)
            cleaning_report["removed_features"] += dup_report["removed_count"]
        
        # 3. Remove tiny features
        if remove_tiny_features:
            cleaned_gdf, size_report = self._remove_tiny_features(cleaned_gdf)
            cleaning_report["operations"].append(size_report)
            cleaning_report["removed_features"] += size_report["removed_count"]
        
        # 4. Handle null values (optional)
        if fill_nulls:
            cleaned_gdf, null_report = self._handle_nulls(cleaned_gdf, layer_name)
            cleaning_report["operations"].append(null_report)
        
        cleaning_report["final_features"] = len(cleaned_gdf)
        cleaning_report["features_removed_total"] = original_count - len(cleaned_gdf)
        cleaning_report["success"] = True
        
        logger.info(f"✅ {layer_name}: {original_count} → {len(cleaned_gdf)} features "
                   f"({cleaning_report['features_removed_total']} removed, "
                   f"{cleaning_report['repaired_features']} repaired)")
        
        return cleaned_gdf, cleaning_report
    
    def _fix_geometries(self, gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict[str, Any]]:
        """Fix invalid geometries using Shapely's make_valid."""
        report = {
            "operation": "geometry_repair",
            "original_invalid": 0,
            "repaired_count": 0,
            "still_invalid": 0,
            "removed_count": 0
        }
        
        if gdf.empty:
            return gdf, report
        
        # Find invalid geometries
        invalid_mask = ~gdf.geometry.is_valid
        invalid_count = invalid_mask.sum()
        report["original_invalid"] = invalid_count
        
        if invalid_count == 0:
            logger.info("   ✅ All geometries valid")
            return gdf, report
        
        logger.info(f"   🔧 Repairing {invalid_count} invalid geometries")
        
        # Create a copy for modifications
        cleaned_gdf = gdf.copy()
        
        # Repair invalid geometries
        repaired_count = 0
        removed_indices = []
        
        for idx in gdf[invalid_mask].index:
            try:
                original_geom = gdf.loc[idx, 'geometry']
                
                # Try to repair using make_valid
                repaired_geom = make_valid(original_geom)
                
                # Check if repair was successful
                if repaired_geom.is_valid and not repaired_geom.is_empty:
                    cleaned_gdf.loc[idx, 'geometry'] = repaired_geom
                    repaired_count += 1
                else:
                    # If repair failed, mark for removal
                    removed_indices.append(idx)
                    logger.warning(f"   ⚠️ Could not repair geometry at index {idx}, marking for removal")
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Error repairing geometry at index {idx}: {str(e)}")
                removed_indices.append(idx)
        
        # Remove features that couldn't be repaired
        if removed_indices:
            cleaned_gdf = cleaned_gdf.drop(index=removed_indices)
            report["removed_count"] = len(removed_indices)
        
        report["repaired_count"] = repaired_count
        
        # Check final invalid count
        final_invalid = (~cleaned_gdf.geometry.is_valid).sum()
        report["still_invalid"] = final_invalid
        
        if final_invalid > 0:
            logger.warning(f"   ⚠️ {final_invalid} geometries still invalid after repair")
        
        return cleaned_gdf, report
    
    def _remove_duplicates(self, gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict[str, Any]]:
        """Remove duplicate features based on geometry and osmid."""
        report = {
            "operation": "duplicate_removal",
            "geometry_duplicates": 0,
            "osmid_duplicates": 0,
            "removed_count": 0
        }
        
        if gdf.empty:
            return gdf, report
        
        original_count = len(gdf)
        
        # Remove geometry duplicates
        geom_dups_before = gdf.geometry.duplicated().sum()
        if geom_dups_before > 0:
            logger.info(f"   🗑️ Removing {geom_dups_before} geometry duplicates")
            gdf = gdf[~gdf.geometry.duplicated()]
            report["geometry_duplicates"] = geom_dups_before
        
        # Remove osmid duplicates if column exists
        if 'osmid' in gdf.columns:
            osmid_dups_before = gdf['osmid'].duplicated().sum()
            if osmid_dups_before > 0:
                logger.info(f"   🗑️ Removing {osmid_dups_before} osmid duplicates")
                gdf = gdf[~gdf['osmid'].duplicated()]
                report["osmid_duplicates"] = osmid_dups_before
        
        removed_count = original_count - len(gdf)
        report["removed_count"] = removed_count
        
        if removed_count > 0:
            logger.info(f"   ✅ Removed {removed_count} duplicate features")
        
        return gdf, report
    
    def _remove_tiny_features(self, gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Dict[str, Any]]:
        """Remove features below minimum size thresholds."""
        report = {
            "operation": "tiny_feature_removal",
            "tiny_polygons": 0,
            "tiny_lines": 0,
            "removed_count": 0
        }
        
        if gdf.empty:
            return gdf, report
        
        # Convert to analytics CRS for accurate measurements
        try:
            gdf_metric = gdf.to_crs(self.analytics_crs)
        except Exception as e:
            logger.warning(f"   ⚠️ Could not convert to {self.analytics_crs}: {str(e)}")
            return gdf, report
        
        original_count = len(gdf_metric)
        to_remove = []
        
        # Check polygons
        polygon_mask = gdf_metric.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])
        if polygon_mask.any():
            polygon_gdf = gdf_metric[polygon_mask]
            areas = polygon_gdf.geometry.area
            tiny_polygon_mask = areas < self.min_area_m2
            tiny_polygons = tiny_polygon_mask.sum()
            
            if tiny_polygons > 0:
                tiny_indices = polygon_gdf[tiny_polygon_mask].index.tolist()
                to_remove.extend(tiny_indices)
                report["tiny_polygons"] = tiny_polygons
                logger.info(f"   🗑️ Removing {tiny_polygons} polygons < {self.min_area_m2} m²")
        
        # Check lines
        line_mask = gdf_metric.geometry.geom_type.isin(['LineString', 'MultiLineString'])
        if line_mask.any():
            line_gdf = gdf_metric[line_mask]
            lengths = line_gdf.geometry.length
            tiny_line_mask = lengths < self.min_length_m
            tiny_lines = tiny_line_mask.sum()
            
            if tiny_lines > 0:
                tiny_indices = line_gdf[tiny_line_mask].index.tolist()
                to_remove.extend(tiny_indices)
                report["tiny_lines"] = tiny_lines
                logger.info(f"   🗑️ Removing {tiny_lines} lines < {self.min_length_m} m")
        
        # Remove tiny features
        if to_remove:
            gdf = gdf.drop(index=to_remove)
            report["removed_count"] = len(to_remove)
        
        return gdf, report
    
    def _handle_nulls(self, gdf: gpd.GeoDataFrame, layer_name: str) -> Tuple[gpd.GeoDataFrame, Dict[str, Any]]:
        """Handle null values in optional attributes."""
        report = {
            "operation": "null_handling",
            "columns_processed": [],
            "filled_values": 0
        }
        
        if gdf.empty:
            return gdf, report
        
        # Define default values for common columns by layer type
        defaults = {
            "roads": {"name": "Unnamed Road", "surface": "unknown"},
            "amenities": {"name": "Unnamed Amenity", "operator": "unknown"},
            "buildings": {"name": "Unnamed Building", "height": "unknown"},
            "landuse": {"natural": "unknown"},
            "cycle": {"name": "Unnamed Path", "surface": "unknown"},
            "pt_stops": {"name": "Unnamed Stop", "operator": "unknown"}
        }
        
        layer_defaults = defaults.get(layer_name, {})
        
        for col, default_value in layer_defaults.items():
            if col in gdf.columns:
                null_count = gdf[col].isnull().sum()
                if null_count > 0:
                    gdf[col] = gdf[col].fillna(default_value)
                    report["columns_processed"].append(col)
                    report["filled_values"] += null_count
                    logger.info(f"   🔧 Filled {null_count} null values in '{col}' with '{default_value}'")
        
        return gdf, report


def clean_staging_data(staging_dir: Path, 
                      output_dir: Optional[Path] = None,
                      layers: Optional[List[str]] = None,
                      backup: bool = True) -> Dict[str, Any]:
    """
    Clean all staging data files.
    
    Args:
        staging_dir: Directory containing GeoParquet staging files
        output_dir: Directory to save cleaned files (defaults to staging_dir)
        layers: Specific layers to clean (defaults to all found)
        backup: Whether to backup original files
        
    Returns:
        Dictionary with cleaning results
    """
    if output_dir is None:
        output_dir = staging_dir
    
    ensure_directory(output_dir)
    
    # Find parquet files
    parquet_files = list(staging_dir.glob("*.parquet"))
    if not parquet_files:
        logger.warning(f"No parquet files found in {staging_dir}")
        return {"error": "No files found"}
    
    # Filter by layers if specified
    if layers:
        parquet_files = [f for f in parquet_files 
                        if any(layer in f.stem for layer in layers)]
    
    logger.info(f"🧹 Cleaning {len(parquet_files)} files")
    
    cleaner = SpatialDataCleaner()
    results = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "files_processed": 0,
        "total_features_before": 0,
        "total_features_after": 0,
        "layers": {}
    }
    
    for parquet_file in parquet_files:
        layer_name = parquet_file.stem.replace("osm_", "").replace("test_osm_", "test_")
        
        try:
            logger.info(f"📖 Loading {parquet_file}")
            gdf = gpd.read_parquet(parquet_file)
            
            if gdf.empty:
                logger.warning(f"⚠️ Skipping empty file: {parquet_file}")
                continue
            
            # Backup original if requested
            if backup:
                backup_file = parquet_file.with_suffix('.parquet.backup')
                if not backup_file.exists():
                    gdf.to_parquet(backup_file)
                    logger.info(f"💾 Backup saved: {backup_file}")
            
            # Clean the data
            cleaned_gdf, cleaning_report = cleaner.clean_layer(gdf, layer_name)
            
            # Save cleaned data
            output_file = output_dir / parquet_file.name
            cleaned_gdf.to_parquet(output_file)
            
            # Update results
            results["files_processed"] += 1
            results["total_features_before"] += cleaning_report["original_features"]
            results["total_features_after"] += cleaning_report["final_features"]
            results["layers"][layer_name] = cleaning_report
            
            logger.info(f"💾 Cleaned data saved: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning {layer_name}: {str(e)}")
            results["layers"][layer_name] = {
                "error": str(e),
                "success": False
            }
    
    # Summary
    total_removed = results["total_features_before"] - results["total_features_after"]
    results["summary"] = {
        "files_processed": results["files_processed"],
        "features_removed": total_removed,
        "removal_rate": round(total_removed / results["total_features_before"] * 100, 2) if results["total_features_before"] > 0 else 0
    }
    
    logger.info(f"🎯 CLEANING COMPLETE: {results['files_processed']} files, "
               f"{total_removed:,} features removed ({results['summary']['removal_rate']}%)")
    
    return results
