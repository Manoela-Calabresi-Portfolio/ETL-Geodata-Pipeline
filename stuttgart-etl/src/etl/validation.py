"""
Spatial data validation module for ETL pipeline.

Provides comprehensive quality checks for geospatial data including:
- Geometry validity and topology
- CRS consistency 
- Attribute completeness
- Spatial extent validation
- Feature count anomalies
- Duplicate detection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import json

import geopandas as gpd
import pandas as pd
import numpy as np
from pyproj import CRS
from shapely.geometry import Point, LineString, Polygon
from shapely.validation import explain_validity

from .utils import ensure_directory

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Container for validation results."""
    layer_name: str
    total_features: int
    passed_checks: int
    failed_checks: int
    warnings: int
    errors: List[str]
    warnings_list: List[str]
    details: Dict[str, Any]
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total_checks = self.passed_checks + self.failed_checks
        return (self.passed_checks / total_checks * 100) if total_checks > 0 else 0.0
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "layer_name": self.layer_name,
            "total_features": self.total_features,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warnings": self.warnings,
            "success_rate": round(self.success_rate, 2),
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings_list,
            "details": self.details
        }


class SpatialValidator:
    """Comprehensive spatial data validator."""
    
    def __init__(self, 
                 expected_crs: str = "EPSG:4326",
                 analytics_crs: str = "EPSG:25832",
                 min_area_m2: float = 1.0,
                 min_length_m: float = 1.0):
        """
        Initialize validator with configuration.
        
        Args:
            expected_crs: Expected CRS for input data
            analytics_crs: CRS for metric calculations  
            min_area_m2: Minimum area threshold in square meters
            min_length_m: Minimum length threshold in meters
        """
        self.expected_crs = expected_crs
        self.analytics_crs = analytics_crs
        self.min_area_m2 = min_area_m2
        self.min_length_m = min_length_m
    
    def validate_layer(self, 
                      gdf: gpd.GeoDataFrame, 
                      layer_name: str,
                      expected_geom_types: Optional[List[str]] = None,
                      required_columns: Optional[List[str]] = None,
                      expected_bbox: Optional[Tuple[float, float, float, float]] = None) -> ValidationResult:
        """
        Perform comprehensive validation on a GeoDataFrame layer.
        
        Args:
            gdf: GeoDataFrame to validate
            layer_name: Name of the layer for reporting
            expected_geom_types: Expected geometry types (e.g., ['Point', 'LineString'])
            required_columns: Required column names
            expected_bbox: Expected bounding box (minx, miny, maxx, maxy) in EPSG:4326
            
        Returns:
            ValidationResult with detailed findings
        """
        errors = []
        warnings = []
        details = {}
        passed_checks = 0
        failed_checks = 0
        
        logger.info(f"🔍 Validating layer: {layer_name}")
        
        # Basic data checks
        if gdf.empty:
            errors.append("Layer is empty - no features found")
            return ValidationResult(
                layer_name=layer_name,
                total_features=0,
                passed_checks=0,
                failed_checks=1,
                warnings=0,
                errors=errors,
                warnings_list=warnings,
                details=details
            )
        
        total_features = len(gdf)
        details["total_features"] = total_features
        
        # 1. CRS Validation
        crs_result = self._validate_crs(gdf)
        if crs_result["valid"]:
            passed_checks += 1
        else:
            failed_checks += 1
            errors.extend(crs_result["errors"])
        details["crs"] = crs_result
        
        # 2. Geometry Validation
        geom_result = self._validate_geometries(gdf, expected_geom_types)
        passed_checks += geom_result["passed"]
        failed_checks += geom_result["failed"]
        errors.extend(geom_result["errors"])
        warnings.extend(geom_result["warnings"])
        details["geometry"] = geom_result
        
        # 3. Attribute Validation
        attr_result = self._validate_attributes(gdf, required_columns)
        passed_checks += attr_result["passed"]
        failed_checks += attr_result["failed"]
        warnings.extend(attr_result["warnings"])
        details["attributes"] = attr_result
        
        # 4. Spatial Extent Validation
        extent_result = self._validate_spatial_extent(gdf, expected_bbox)
        if extent_result["valid"]:
            passed_checks += 1
        else:
            failed_checks += 1
            warnings.extend(extent_result["warnings"])
        details["spatial_extent"] = extent_result
        
        # 5. Duplicate Detection
        dup_result = self._detect_duplicates(gdf)
        if dup_result["duplicates"] == 0:
            passed_checks += 1
        else:
            failed_checks += 1
            warnings.extend(dup_result["warnings"])
        details["duplicates"] = dup_result
        
        # 6. Size/Dimension Validation
        size_result = self._validate_feature_sizes(gdf)
        passed_checks += size_result["passed"]
        failed_checks += size_result["failed"]
        warnings.extend(size_result["warnings"])
        details["feature_sizes"] = size_result
        
        return ValidationResult(
            layer_name=layer_name,
            total_features=total_features,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=len(warnings),
            errors=errors,
            warnings_list=warnings,
            details=details
        )
    
    def _validate_crs(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Validate coordinate reference system using robust CRS comparison."""
        result = {"valid": True, "errors": [], "crs": None}

        if gdf.crs is None:
            result["valid"] = False
            result["errors"].append("No CRS defined")
            result["crs"] = None
            return result

        try:
            actual_epsg = CRS.from_user_input(gdf.crs).to_epsg()
            expected_epsg = CRS.from_user_input(self.expected_crs).to_epsg()
            if actual_epsg != expected_epsg:
                result["valid"] = False
                actual_str = gdf.crs.to_string() if hasattr(gdf.crs, "to_string") else str(gdf.crs)
                result["errors"].append(
                    f"CRS mismatch: expected {self.expected_crs}, got {actual_str}"
                )
        except Exception:
            # Fallback: string comparison
            actual_str = gdf.crs.to_string() if hasattr(gdf.crs, "to_string") else str(gdf.crs)
            expected_str = CRS.from_user_input(self.expected_crs).to_string()
            if actual_str != expected_str and actual_str != self.expected_crs:
                result["valid"] = False
                result["errors"].append(
                    f"CRS mismatch: expected {self.expected_crs}, got {actual_str}"
                )

        result["crs"] = gdf.crs.to_string() if hasattr(gdf.crs, "to_string") else str(gdf.crs)
        return result
    
    def _validate_geometries(self, gdf: gpd.GeoDataFrame, expected_types: Optional[List[str]]) -> Dict[str, Any]:
        """Validate geometry validity and types."""
        result = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
            "invalid_geometries": 0,
            "geometry_types": {},
            "topology_errors": []
        }
        
        # Check for null geometries
        null_geoms = gdf.geometry.isnull().sum()
        if null_geoms > 0:
            result["failed"] += 1
            result["errors"].append(f"Found {null_geoms} null geometries")
        else:
            result["passed"] += 1
        
        # Check geometry validity
        if not gdf.empty:
            invalid_mask = ~gdf.geometry.is_valid
            invalid_count = invalid_mask.sum()
            result["invalid_geometries"] = invalid_count
            
            if invalid_count > 0:
                result["failed"] += 1
                result["errors"].append(f"Found {invalid_count} invalid geometries")
                
                # Get details of first few invalid geometries
                invalid_geoms = gdf[invalid_mask].head(5)
                for idx, geom in invalid_geoms.geometry.items():
                    try:
                        explanation = explain_validity(geom)
                        result["topology_errors"].append(f"Feature {idx}: {explanation}")
                    except Exception as e:
                        result["topology_errors"].append(f"Feature {idx}: Error checking validity - {str(e)}")
            else:
                result["passed"] += 1
        
        # Check geometry types
        if not gdf.empty:
            geom_types = gdf.geometry.geom_type.value_counts().to_dict()
            result["geometry_types"] = geom_types
            
            if expected_types:
                unexpected_types = set(geom_types.keys()) - set(expected_types)
                if unexpected_types:
                    result["failed"] += 1
                    result["warnings"].append(f"Unexpected geometry types: {list(unexpected_types)}")
                else:
                    result["passed"] += 1
        
        return result
    
    def _validate_attributes(self, gdf: gpd.GeoDataFrame, required_columns: Optional[List[str]]) -> Dict[str, Any]:
        """Validate attribute completeness and quality."""
        result = {
            "passed": 0,
            "failed": 0,
            "warnings": [],
            "missing_columns": [],
            "null_counts": {},
            "column_types": {}
        }
        
        # Check required columns
        if required_columns:
            missing_cols = [col for col in required_columns if col not in gdf.columns]
            if missing_cols:
                result["failed"] += 1
                result["missing_columns"] = missing_cols
                result["warnings"].append(f"Missing required columns: {missing_cols}")
            else:
                result["passed"] += 1
        
        # Analyze null values
        for col in gdf.columns:
            if col != "geometry":
                null_count = gdf[col].isnull().sum()
                null_pct = (null_count / len(gdf)) * 100
                result["null_counts"][col] = {
                    "count": null_count,
                    "percentage": round(null_pct, 2)
                }
                
                if null_pct > 50:
                    result["warnings"].append(f"Column '{col}' has {null_pct:.1f}% null values")
        
        # Record column types
        result["column_types"] = {col: str(dtype) for col, dtype in gdf.dtypes.items() if col != "geometry"}
        
        return result
    
    def _validate_spatial_extent(self, gdf: gpd.GeoDataFrame, expected_bbox: Optional[Tuple[float, float, float, float]]) -> Dict[str, Any]:
        """Validate spatial extent and bounding box."""
        result = {"valid": True, "warnings": [], "actual_bbox": None, "expected_bbox": expected_bbox}
        
        if gdf.empty:
            result["valid"] = False
            result["warnings"].append("Cannot validate extent - no geometries")
            return result
        
        # Calculate actual bounding box
        bounds = gdf.total_bounds
        actual_bbox = tuple(bounds)
        result["actual_bbox"] = actual_bbox
        
        # Check against expected bbox if provided
        if expected_bbox:
            exp_minx, exp_miny, exp_maxx, exp_maxy = expected_bbox
            act_minx, act_miny, act_maxx, act_maxy = actual_bbox
            
            # Allow 10% tolerance
            tolerance = 0.1
            
            if (act_minx < exp_minx * (1 - tolerance) or act_maxx > exp_maxx * (1 + tolerance) or
                act_miny < exp_miny * (1 - tolerance) or act_maxy > exp_maxy * (1 + tolerance)):
                result["valid"] = False
                result["warnings"].append(f"Spatial extent outside expected bounds: {actual_bbox} vs {expected_bbox}")
        
        return result
    
    def _detect_duplicates(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Detect duplicate geometries and features."""
        result = {"duplicates": 0, "warnings": [], "duplicate_types": {}}
        
        if gdf.empty:
            return result
        
        # Check for duplicate geometries
        geom_duplicates = gdf.geometry.duplicated().sum()
        result["duplicate_types"]["geometry"] = geom_duplicates
        
        # Check for duplicate OSM IDs if present
        if "osmid" in gdf.columns:
            osmid_duplicates = gdf["osmid"].duplicated().sum()
            result["duplicate_types"]["osmid"] = osmid_duplicates
        
        total_duplicates = sum(result["duplicate_types"].values())
        result["duplicates"] = total_duplicates
        
        if total_duplicates > 0:
            result["warnings"].append(f"Found {total_duplicates} duplicate features")
        
        return result
    
    def _validate_feature_sizes(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Validate feature sizes (areas and lengths)."""
        result = {
            "passed": 0,
            "failed": 0,
            "warnings": [],
            "size_stats": {}
        }
        
        if gdf.empty:
            return result
        
        # Convert to analytics CRS for accurate measurements
        try:
            gdf_metric = gdf.to_crs(self.analytics_crs)
        except Exception as e:
            result["failed"] += 1
            result["warnings"].append(f"Could not convert to analytics CRS: {str(e)}")
            return result
        
        # Check areas for polygon features
        polygon_mask = gdf_metric.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])
        if polygon_mask.any():
            areas = gdf_metric[polygon_mask].geometry.area
            tiny_areas = (areas < self.min_area_m2).sum()
            
            result["size_stats"]["polygons"] = {
                "count": len(areas),
                "min_area_m2": float(areas.min()),
                "max_area_m2": float(areas.max()),
                "mean_area_m2": float(areas.mean()),
                "tiny_features": tiny_areas
            }
            
            if tiny_areas > 0:
                result["warnings"].append(f"Found {tiny_areas} polygons smaller than {self.min_area_m2} m²")
        
        # Check lengths for line features
        line_mask = gdf_metric.geometry.geom_type.isin(['LineString', 'MultiLineString'])
        if line_mask.any():
            lengths = gdf_metric[line_mask].geometry.length
            tiny_lengths = (lengths < self.min_length_m).sum()
            
            result["size_stats"]["lines"] = {
                "count": len(lengths),
                "min_length_m": float(lengths.min()),
                "max_length_m": float(lengths.max()),
                "mean_length_m": float(lengths.mean()),
                "tiny_features": tiny_lengths
            }
            
            if tiny_lengths > 0:
                result["warnings"].append(f"Found {tiny_lengths} lines shorter than {self.min_length_m} m")
        
        # Overall size validation
        total_tiny = result["size_stats"].get("polygons", {}).get("tiny_features", 0) + \
                    result["size_stats"].get("lines", {}).get("tiny_features", 0)
        
        if total_tiny == 0:
            result["passed"] += 1
        else:
            result["failed"] += 1
        
        return result


def validate_pipeline_data(staging_dir: Path, 
                          output_dir: Path,
                          config: Optional[Dict[str, Any]] = None,
                          include_tests: bool = False) -> Dict[str, ValidationResult]:
    """
    Validate all layers in the staging directory.
    
    Args:
        staging_dir: Directory containing GeoParquet files
        output_dir: Directory to save validation reports
        config: Optional validation configuration
        
    Returns:
        Dictionary mapping layer names to ValidationResults
    """
    ensure_directory(output_dir)
    
    # Default configuration
    default_config = {
        "expected_crs": "EPSG:4326",
        "analytics_crs": "EPSG:25832",
        "layer_configs": {
            "roads": {
                "expected_geom_types": ["LineString", "MultiLineString"],
                "required_columns": ["osmid", "highway"]
            },
            "buildings": {
                "expected_geom_types": ["Polygon", "MultiPolygon"], 
                "required_columns": ["osmid", "building"]
            },
            "landuse": {
                "expected_geom_types": ["Polygon", "MultiPolygon"],
                "required_columns": ["osmid"]
            },
            "amenities": {
                "expected_geom_types": ["Point", "Polygon", "MultiPolygon"],
                "required_columns": ["osmid", "amenity"]
            }
        }
    }
    
    if config:
        default_config.update(config)
    
    validator = SpatialValidator(
        expected_crs=default_config["expected_crs"],
        analytics_crs=default_config["analytics_crs"]
    )
    
    results = {}
    parquet_files = list(staging_dir.glob("osm_*.parquet"))
    if include_tests:
        parquet_files.extend(staging_dir.glob("test_*.parquet"))
    
    logger.info(f"🔍 Found {len(parquet_files)} parquet files to validate")
    
    for parquet_file in parquet_files:
        layer_name = parquet_file.stem.replace("osm_", "").replace("test_osm_", "")
        
        try:
            logger.info(f"📖 Loading {parquet_file}")
            gdf = gpd.read_parquet(parquet_file)
            
            # Get layer-specific config
            layer_config = default_config["layer_configs"].get(layer_name, {})
            
            # Validate layer
            result = validator.validate_layer(
                gdf=gdf,
                layer_name=layer_name,
                expected_geom_types=layer_config.get("expected_geom_types"),
                required_columns=layer_config.get("required_columns")
            )
            
            results[layer_name] = result
            
            # Log summary
            status = "✅ PASS" if result.is_valid else "❌ FAIL"
            logger.info(f"{status} {layer_name}: {result.success_rate:.1f}% success rate")
            
        except Exception as e:
            logger.error(f"❌ Error validating {layer_name}: {str(e)}")
            results[layer_name] = ValidationResult(
                layer_name=layer_name,
                total_features=0,
                passed_checks=0,
                failed_checks=1,
                warnings=0,
                errors=[f"Validation error: {str(e)}"],
                warnings_list=[],
                details={}
            )
    
    # Save comprehensive report
    report_path = output_dir / "spatial_validation_report.json"
    report_data = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "config": default_config,
        "summary": {
            "total_layers": len(results),
            "passed_layers": sum(1 for r in results.values() if r.is_valid),
            "failed_layers": sum(1 for r in results.values() if not r.is_valid),
            "total_features": sum(r.total_features for r in results.values())
        },
        "layers": {name: result.to_dict() for name, result in results.items()}
    }
    
    def _to_json_serializable(obj: Any) -> Any:
        """Recursively convert objects to JSON-serializable built-in types."""
        # Scalars
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (pd.Timestamp,)):
            return obj.isoformat()
        # Collections
        if isinstance(obj, dict):
            return {str(k): _to_json_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [_to_json_serializable(v) for v in obj]
        # Fallback
        return obj

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(_to_json_serializable(report_data), f, indent=2, ensure_ascii=False)
    
    logger.info(f"📊 Validation report saved to: {report_path}")
    
    return results
