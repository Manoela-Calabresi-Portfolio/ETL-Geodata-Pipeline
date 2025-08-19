#!/usr/bin/env python3
"""
[UTILS] Shared utilities for ETL Geodata Pipeline
Provides common functions for YAML loading, directory management, and logging

This module contains utility functions used across the pipeline:
- YAML configuration loading and parsing
- Directory management and path handling
- Logging setup and management
- Bounding box operations and validation
- Area configuration management
"""

import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Union, List
import sys


def setup_logging(level: str = "INFO", format_str: str = None, log_file: str = None) -> logging.Logger:
    """
    Setup logging configuration
    """
    if format_str is None:
        format_str = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"

    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )

    return logging.getLogger("pipeline")


def load_yaml(path: Union[str, Path]) -> Dict[Any, Any]:
    """Load YAML configuration file"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        content = yaml.safe_load(f)
    return content if content is not None else {}


def ensure_dir(path: Union[str, Path]) -> Path:
    """Create directory if it doesn't exist"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_area_config(area_name: str, areas_dir: str = "areas") -> Dict[str, Any]:
    """Load area-specific configuration"""
    config_path = Path(areas_dir) / f"{area_name}.yaml"
    return load_yaml(config_path)


def load_pipeline_config(config_path: str = "config/pipeline.yaml") -> Dict[str, Any]:
    """Load main pipeline configuration"""
    return load_yaml(config_path)


def get_area_paths(area_name: str, pipeline_config: Dict[str, Any]) -> Dict[str, Path]:
    """Generate area-specific paths based on pipeline configuration"""
    paths = {}
    path_templates = pipeline_config.get('paths', {})

    for path_name, template in path_templates.items():
        if isinstance(template, str) and '{city}' in template:
            paths[path_name] = Path(template.format(city=area_name))
        else:
            paths[path_name] = Path(template)

    return paths


def shrink_bbox(bbox: List[float], shrink_factor: float = 0.1) -> List[float]:
    """Shrink a bounding box for testing purposes"""
    lon_min, lat_min, lon_max, lat_max = bbox
    center_lon = (lon_min + lon_max) / 2
    center_lat = (lat_min + lat_max) / 2
    width = (lon_max - lon_min) * shrink_factor
    height = (lat_max - lat_min) * shrink_factor
    return [center_lon - width / 2, center_lat - height / 2, center_lon + width / 2, center_lat + height / 2]


def validate_bbox(bbox: List[float]) -> bool:
    """Validate bounding box format and values"""
    if not isinstance(bbox, list) or len(bbox) != 4:
        return False
    lon_min, lat_min, lon_max, lat_max = bbox
    if not (-180 <= lon_min <= 180) or not (-180 <= lon_max <= 180):
        return False
    if not (-90 <= lat_min <= 90) or not (-90 <= lat_max <= 90):
        return False
    if lon_min >= lon_max or lat_min >= lat_max:
        return False
    return True


def get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()


