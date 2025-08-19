#!/usr/bin/env python3
"""
Configuration loader for Stuttgart Mobility & Walkability Analysis
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config/analysis_config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        logger.info(f"Configuration loaded successfully from {config_path}")
        return config
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

def get_study_area(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get study area configuration"""
    return config.get('study_area', {})

def get_data_sources(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get data sources configuration"""
    return config.get('data_sources', {})

def get_analysis_parameters(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get analysis parameters configuration"""
    return config.get('analysis_parameters', {})

def get_poi_categories(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get POI categories configuration"""
    return config.get('poi_categories', {})
