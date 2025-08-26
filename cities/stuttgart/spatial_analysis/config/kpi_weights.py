#!/usr/bin/env python3
"""
KPI Weights Configuration Loader
"""

import yaml
from pathlib import Path
from typing import Dict, Any

def load_kpi_weights(config_path: str = None) -> Dict[str, Any]:
    """
    Load KPI weights configuration from YAML file
    
    Args:
        config_path: Path to the KPI weights YAML file
        
    Returns:
        Dictionary with KPI weights configuration
    """
    if config_path is None:
        config_path = Path(__file__).parent / "kpi_weights.yaml"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            weights = yaml.safe_load(file)
        return weights
    except Exception as e:
        print(f"Error loading KPI weights: {e}")
        # Return default weights if loading fails
        return {
            "main_categories": {
                "public_transport": 0.4,
                "walkability": 0.35,
                "green_access": 0.25
            }
        }
