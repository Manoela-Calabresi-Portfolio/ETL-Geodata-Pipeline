#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Kepler.gl Dashboard using Python module
Following the Medium article approach: https://medium.com/better-programming/geo-data-visualization-with-kepler-gl-fbc15debbca4
"""

import json
import webbrowser
from pathlib import Path
import geopandas as gpd
from keplergl import KeplerGl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import contextily as ctx

# List of layers for which PNG creation should be skipped
# These layers will still be exported as GeoJSON for Kepler dashboard
PNG_EXCLUDE_LIST = [
    "01_city_boundary",
    "02_districts", 
    "03_roads",
    "04_pt_stops",
    "05_landuse",
    "06_green_areas"
    # Note: H3 analysis layers (13-17) and new choropleth layers (18-24) are NOT in this list, so they WILL get PNG exports
]

def create_kepler_python_dashboard():
    """Create a complete Kepler.gl dashboard using the Python module"""
    
    print("🚀 Creating dashboard Kepler.gl with Python module...")
    
    # Load all 18 layers (11 existing + 7 new choropleth maps)
    all_layers = load_all_layers()
    
    if not all_layers:
        print("❌ No layers loaded! Exiting.")
        return
    
    # Create output directory with auto-incrementing number
    outputs_base = Path("../outputs")
    outputs_base.mkdir(exist_ok=True)
    
    # Find the next available folder number
    existing_folders = [d for d in outputs_base.iterdir() if d.is_dir() and d.name.startswith("stuttgart_maps_")]
    if existing_folders:
        # Extract numbers and find the highest
        numbers = []
        for folder in existing_folders:
            try:
                num = int(folder.name.split("_")[-1])
                numbers.append(num)
            except ValueError:
                continue
        
        next_number = max(numbers) + 1 if numbers else 107
    else:
        next_number = 107
    
    out_dir = outputs_base / f"stuttgart_maps_{next_number}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Creating new output folder: {out_dir.name}")
    
    # Initialize Kepler.gl map
    kepler = KeplerGl()
    
    # Add all layers to the map
    for name, gdf in all_layers.items():
        try:
            print(f"🔄 Adding layer: {name}")
            kepler.add_data(data=gdf, name=name)
            print(f"  ✅ Added {name}: {len(gdf)} features")
        except Exception as e:
            print(f"  ❌ Error adding {name}: {e}")
    
    # Create basic configuration
    config = create_basic_config()
    
    # Apply configuration with proper visual mapping for choropleth layers
    kepler.config = config
    
    # Generate HTML
    html_file = out_dir / "stuttgart_18_layers_kepler_dashboard.html"
    kepler_html = kepler._repr_html_()
    
    # Handle bytes vs string
    if isinstance(kepler_html, bytes):
        kepler_html = kepler_html.decode('utf-8')
    
    # Save the HTML
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(kepler_html)
    
    print(f"🎯 Dashboard created: {html_file}")
    
    # Also save the configuration
    config_file = out_dir / "kepler_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"📊 Configuration saved: {config_file}")
    
    # Export individual GeoJSON files and PNG maps
    export_individual_layers(all_layers, out_dir)
    
    return out_dir

def load_all_layers():
    """Load all 18 layers (11 existing + 7 new choropleth maps) from their respective locations"""
    all_layers = {}
    
    # Load basic infrastructure layers
    basic_dir = Path("../outputs/maps/kepler_data")
    basic_files = [
        "01_city_boundary.geojson",
        "02_districts.geojson", 
        "03_roads.geojson",
        "04_pt_stops.geojson",
        "05_landuse.geojson",
        "06_green_areas.geojson"
    ]
    
    print("🔺 Loading basic infrastructure layers...")
    for filename in basic_files:
        filepath = basic_dir / filename
        if filepath.exists():
            try:
                gdf = gpd.read_file(filepath)
                name = Path(filename).stem
                all_layers[name] = gdf
                print(f"  ✅ {name}: {len(gdf)} features")
            except Exception as e:
                print(f"  ❌ {filename}: {e}")
    
    # Load H3 analysis layers
    print("🔺 Loading H3 analysis layers...")
    
    # Find the most recent folder with H3 layers
    outputs_base = Path("../outputs")
    h3_folders = [d for d in outputs_base.iterdir() if d.is_dir() and d.name.startswith("stuttgart_maps_")]
    
    h3_dir = None
    if h3_folders:
        # Sort by folder number and find the most recent one with H3 layers
        h3_folders.sort(key=lambda x: int(x.name.split("_")[-1]) if x.name.split("_")[-1].isdigit() else 0, reverse=True)
        
        for folder in h3_folders:
            potential_h3_dir = folder / "geojson_layers"
            if potential_h3_dir.exists():
                # Check if this folder has H3 layers
                h3_files_to_check = [
                    "13_pt_modal_gravity_h3.geojson",
                    "14_access_essentials_h3.geojson",
                    "15_detour_factor_h3.geojson", 
                    "16_service_diversity_h3.geojson",
                    "17_park_access_time_h3.geojson"
                ]
                
                if any((potential_h3_dir / f).exists() for f in h3_files_to_check):
                    h3_dir = potential_h3_dir
                    print(f"  📁 Found H3 layers in: {folder.name}")
                    break
    
    if h3_dir:
        h3_files = [
            "13_pt_modal_gravity_h3.geojson",
            "14_access_essentials_h3.geojson",
            "15_detour_factor_h3.geojson", 
            "16_service_diversity_h3.geojson",
            "17_park_access_time_h3.geojson"
        ]
        
        for filename in h3_files:
            filepath = h3_dir / filename
            if filepath.exists():
                try:
                    gdf = gpd.read_file(filepath)
                    name = Path(filename).stem
                    all_layers[name] = gdf
                    print(f"  ✅ {name}: {len(gdf)} features")
                except Exception as e:
                    print(f"  ❌ {filename}: {e}")
            else:
                print(f"  ⚠️ {filename} not found in {h3_dir}")
    else:
        print("  ⚠️ No folder with H3 layers found")
    
    # Load choropleth maps from stuttgart_kpis.csv
    print("🔺 Loading choropleth maps from stuttgart_kpis.csv...")
    kpis_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.csv")
    if kpis_file.exists():
        try:
            # Read the KPIs data as a regular DataFrame first
            import pandas as pd
            kpis_df = pd.read_csv(kpis_file)
            print(f"  ✅ Loaded KPIs data: {len(kpis_df)} districts")
            
            # Convert geometry column from WKT to GeoDataFrame
            from shapely import wkt
            kpis_df['geometry'] = kpis_df['geometry'].apply(wkt.loads)
            kpis_gdf = gpd.GeoDataFrame(kpis_df, geometry='geometry', crs='EPSG:25832')
            
            # Create individual choropleth layers
            choropleth_layers = {
                "18_amenity_density": ("amenities_count", "Amenity Density"),
                "19_district_area": ("area_km2", "District Area (km²)"),
                "20_green_space_ratio": ("green_landuse_pct", "Green Space Ratio"),
                "21_mobility_score": ("service_density", "Mobility Score"),
                "22_pt_density": ("pt_stop_density", "PT Density"),
                "23_walkability_score": ("cycle_infra_density", "Walkability Score"),
                "24_overall_score": ("population_density", "Overall Score")
            }
            
            for layer_name, (column, title) in choropleth_layers.items():
                if column in kpis_gdf.columns:
                    # Create a copy with the specific column for visualization
                    gdf_copy = kpis_gdf.copy()
                    # Rename the column to a standard name for consistent styling
                    gdf_copy = gdf_copy.rename(columns={column: "value"})
                    all_layers[layer_name] = gdf_copy
                    print(f"  ✅ {layer_name}: {title} ({column})")
                else:
                    print(f"  ⚠️ Column {column} not found in KPIs data")
                    
        except Exception as e:
            print(f"  ❌ Error loading KPIs data: {e}")
    else:
        print(f"  ⚠️ KPIs file not found: {kpis_file}")
    
    return all_layers

def create_basic_config():
    """Create a basic Kepler.gl configuration with proper data and visual mapping"""
    
    config = {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [
                    # City boundary
                    {
                        "id": "01_city_boundary",
                        "type": "geojson",
                        "config": {
                            "label": "01 City Boundary",
                            "dataId": "01_city_boundary",
                            "color": [255, 255, 255],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 2,
                                "strokeColor": [0, 0, 0],
                                "filled": False
                            }
                        }
                    },
                    # Districts
                    {
                        "id": "02_districts",
                        "type": "geojson",
                        "config": {
                            "label": "02 Districts",
                            "dataId": "02_districts",
                            "color": [60, 165, 250],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.3,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        }
                    },
                    # Roads
                    {
                        "id": "03_roads",
                        "type": "geojson",
                        "config": {
                            "label": "03 Roads",
                            "dataId": "03_roads",
                            "color": [169, 169, 169],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.6,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": False
                            }
                        }
                    },
                    # PT Stops
                    {
                        "id": "04_pt_stops",
                        "type": "geojson",
                        "config": {
                            "label": "04 PT Stops",
                            "dataId": "04_pt_stops",
                            "color": [255, 69, 0],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True,
                                "radius": 50
                            }
                        }
                    },
                    # Land Use
                    {
                        "id": "05_landuse",
                        "type": "geojson",
                        "config": {
                            "label": "05 Land Use",
                            "dataId": "05_landuse",
                            "color": [34, 139, 34],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.5,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        }
                    },
                    # Green Areas
                    {
                        "id": "06_green_areas",
                        "type": "geojson",
                        "config": {
                            "label": "06 Green Areas",
                            "dataId": "06_green_areas",
                            "color": [0, 128, 0],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.6,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        }
                    },
                    # H3 Analysis Layers (13-17)
                    {
                        "id": "13_pt_modal_gravity_h3",
                        "type": "geojson",
                        "config": {
                            "label": "13 PT Modal Gravity (H3)",
                            "dataId": "13_pt_modal_gravity_h3",
                            "color": [147, 112, 219],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [128, 128, 128],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "pt_gravity", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "14_access_essentials_h3",
                        "type": "geojson",
                        "config": {
                            "label": "14 Access to Essentials (H3)",
                            "dataId": "14_access_essentials_h3",
                            "color": [147, 112, 219],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [128, 128, 128],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "ess_types", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "15_detour_factor_h3",
                        "type": "geojson",
                        "config": {
                            "label": "15 Detour Factor (H3)",
                            "dataId": "15_detour_factor_h3",
                            "color": [147, 112, 219],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [128, 128, 128],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "detour_factor", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "16_service_diversity_h3",
                        "type": "geojson",
                        "config": {
                            "label": "16 Service Diversity (H3)",
                            "dataId": "16_service_diversity_h3",
                            "color": [147, 112, 219],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [128, 128, 128],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "amen_entropy", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "17_park_access_time_h3",
                        "type": "geojson",
                        "config": {
                            "label": "17 Park Access Time (H3)",
                            "dataId": "17_park_access_time_h3",
                            "color": [147, 112, 219],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [128, 128, 128],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "park_min", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    # Choropleth Layers (18-24) with proper visual mapping
                    {
                        "id": "18_amenity_density",
                        "type": "geojson",
                        "config": {
                            "label": "18 Amenity Density",
                            "dataId": "18_amenity_density",
                            "color": [147, 112, 219],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "value", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "19_district_area",
                        "type": "geojson",
                        "config": {
                            "label": "19 District Area (km²)",
                            "dataId": "19_district_area",
                            "color": [30, 144, 255],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "value", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "20_green_space_ratio",
                        "type": "geojson",
                        "config": {
                            "label": "20 Green Space Ratio (%)",
                            "dataId": "20_green_space_ratio",
                            "color": [34, 139, 34],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "value", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "21_mobility_score",
                        "type": "geojson",
                        "config": {
                            "label": "21 Mobility Score",
                            "dataId": "21_mobility_score",
                            "color": [255, 215, 0],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "value", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "22_pt_density",
                        "type": "geojson",
                        "config": {
                            "label": "22 PT Density",
                            "dataId": "22_pt_density",
                            "color": [30, 144, 255],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "value", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "23_walkability_score",
                        "type": "geojson",
                        "config": {
                            "label": "23 Walkability Score",
                            "dataId": "23_walkability_score",
                            "color": [160, 82, 45],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "value", "type": "real"},
                            "colorScale": "quantize"
                        }
                    },
                    {
                        "id": "24_overall_score",
                        "type": "geojson",
                        "config": {
                            "label": "24 Overall Score",
                            "dataId": "24_overall_score",
                            "color": [255, 69, 0],
                            "columns": {"geojson": "geometry"},
                            "isVisible": True,
                            "visConfig": {
                                "opacity": 0.8,
                                "strokeOpacity": 0.8,
                                "thickness": 1,
                                "strokeColor": [255, 255, 255],
                                "filled": True
                            }
                        },
                        "visualChannels": {
                            "colorField": {"name": "value", "type": "real"},
                            "colorScale": "quantize"
                        }
                    }
                ],
                "interactionConfig": {
                    "tooltip": {
                        "fieldsToShow": {},
                        "enabled": True
                    }
                },
                "layerBlending": "normal",
                "splitMaps": []
            },
            "mapState": {
                "bearing": 0,
                "dragRotate": False,
                "latitude": 48.7758,
                "longitude": 9.1829,
                "pitch": 0,
                "zoom": 10,
                "isSplit": False
            },
            "mapStyle": {
                "styleType": "dark"
            }
        }
    }
    
    return config

def export_individual_layers(all_layers, out_dir):
    """Export individual GeoJSON files and PNG maps for each layer"""
    
    print("\n🔄 Exporting individual layer files...")
    
    # Create subdirectories
    geojson_dir = out_dir / "geojson_layers"
    png_dir = out_dir / "png_maps"
    geojson_dir.mkdir(exist_ok=True)
    png_dir.mkdir(exist_ok=True)
    
    # Color schemes for different layer types
    basic_colors = {
        '01_city_boundary': '#ffffff',
        '02_districts': '#3ca5fa', 
        '03_roads': '#a9a9a9',
        '04_pt_stops': '#ff4500',
        '05_landuse': '#228b22',
        '06_green_areas': '#32cd32'
    }
    
    h3_colors = {
        '13_pt_modal_gravity_h3': '#129396',
        '14_access_essentials_h3': '#ff69b4',
        '15_detour_factor_h3': '#ffd700',
        '16_service_diversity_h3': '#8a2be2',
        '17_park_access_time_h3': '#008000'
    }
    
    # Thematic colormaps for different KPIs
    colormaps = {
        "pt_gravity": "BuPu",              # PT gravity → purple sequential
        "ess_types": "Purples",            # Access essentials
        "detour_factor": "OrRd",           # Detour factor
        "amen_entropy": "YlGnBu",          # Service diversity
        "park_min": "Greens",              # Park access
        "mismatch": "RdBu_r",              # PT mismatch (diverging)
        "population": "Greys",             # Population density
        "forest_min": "YlGn",              # Forest access time
        "green_score": "Greens"            # Composite green access
    }
    
    # Bilingual titles and subtitles
    titles = {
        "01_city_boundary": ("Stuttgart — City Boundary", "Stadtgrenze"),
        "02_districts": ("Stuttgart — Districts", "Stadtbezirke"),
        "03_roads": ("Stuttgart — Roads", "Straßennetz"),
        "04_pt_stops": ("Stuttgart — Public Transport Stops", "ÖPNV-Haltestellen"),
        "05_landuse": ("Stuttgart — Land Use", "Flächennutzung"),
        "06_green_areas": ("Stuttgart — Green Areas", "Grünflächen"),
        "13_pt_modal_gravity_h3": ("Stuttgart — PT Modal Gravity (H3)", "ÖPNV-Gravitation (H3)"),
        "14_access_essentials_h3": ("Stuttgart — Access to Essentials (H3)", "Erreichbarkeit von Grundversorgern (H3)"),
        "15_detour_factor_h3": ("Stuttgart — Detour Factor (H3)", "Umwegfaktor (H3)"),
        "16_service_diversity_h3": ("Stuttgart — Service Diversity (H3)", "Dienstleistungs-Diversität (H3)"),
        "17_park_access_time_h3": ("Stuttgart — Access Time to Parks (H3)", "Fußwegzeit zu Parks (H3)"),
        "04a_mismatch_diverging_h3": ("Stuttgart — PT vs Population Mismatch (H3)", "Divergenz Angebot × Nachfrage (H3)"),
        "04b_population_density_h3": ("Stuttgart — Population Density (H3)", "Bevölkerungsdichte (H3)"),
        "09_forest_access_time_h3": ("Stuttgart — Access Time to Forests (H3)", "Fußwegzeit zum Wald (H3)"),
        "10_green_gaps_h3": ("Stuttgart — Green Access Quality (H3)", "Qualität des Grünflächen-Zugangs (H3)"),
        # New choropleth layers
        "18_amenity_density": ("Stuttgart — Amenity Density", "Dichte der Einrichtungen"),
        "19_district_area": ("Stuttgart — District Area (km²)", "Bezirksfläche (km²)"),
        "20_green_space_ratio": ("Stuttgart — Green Space Ratio", "Grünflächenanteil"),
        "21_mobility_score": ("Stuttgart — Mobility Score", "Mobilitätsbewertung"),
        "22_pt_density": ("Stuttgart — PT Density", "ÖPNV-Dichte"),
        "23_walkability_score": ("Stuttgart — Walkability Score", "Fußgängerfreundlichkeit"),
        "24_overall_score": ("Stuttgart — Overall Score", "Gesamtbewertung")
    }
    
    # Output filenames (01–10 scheme)
    output_names = {
        "01_city_boundary": "01_city_boundary.png",
        "02_districts": "02_districts.png",
        "03_roads": "03_roads.png",
        "04_pt_stops": "04_pt_stops.png",
        "05_landuse": "05_landuse.png",
        "06_green_areas": "06_green_areas.png",
        "13_pt_modal_gravity_h3": "04_pt_modal_gravity_h3.png",
        "04a_mismatch_diverging_h3": "04a_mismatch_diverging_h3.png",
        "04b_population_density_h3": "04b_population_density_h3.png",
        "14_access_essentials_h3": "05_access_essentials_h3.png",
        "15_detour_factor_h3": "06_detour_factor_h3.png",
        "16_service_diversity_h3": "07_service_diversity_h3.png",
        "17_park_access_time_h3": "08_park_access_time_h3.png",
        "09_forest_access_time_h3": "09_forest_access_time_h3.png",
        "10_green_gaps_h3": "10_green_gaps_h3.png",
        # New choropleth layers
        "18_amenity_density": "11_amenity_density.png",
        "19_district_area": "12_district_area.png",
        "20_green_space_ratio": "13_green_space_ratio.png",
        "21_mobility_score": "14_mobility_score.png",
        "22_pt_density": "15_pt_density.png",
        "23_walkability_score": "16_walkability_score.png",
        "24_overall_score": "17_overall_score.png"
    }
    
    for name, gdf in all_layers.items():
        try:
            print(f"🔄 Processing {name}...")
            
            # 1. Export GeoJSON file
            geojson_file = geojson_dir / f"{name}.geojson"
            gdf.to_file(geojson_file, driver='GeoJSON')
            print(f"  ✅ GeoJSON exported: {geojson_file}")
            
            # 2. Create PNG map (skip for excluded layers)
            if name in PNG_EXCLUDE_LIST:
                print(f"  ⏩ Skipping PNG creation for {name} (excluded from PNG generation)")
            else:
                png_file = png_dir / output_names.get(name, f"{name}.png")
                create_layer_png(gdf, name, png_file, basic_colors, h3_colors, colormaps, titles)
                print(f"  ✅ PNG map created: {png_file}")
            
        except Exception as e:
            print(f"  ❌ Error processing {name}: {e}")
    
    # Check for missing maps and create them if data is available
    print("\n🔍 Checking for missing maps...")
    create_missing_maps(all_layers, geojson_dir, png_dir, basic_colors, h3_colors, colormaps, titles, output_names)
    
    print(f"\n📁 Files exported to:")
    print(f"  📊 GeoJSON layers: {geojson_dir}")
    print(f"  🖼️ PNG maps: {png_dir}")

def create_layer_png(gdf, layer_name, output_file, basic_colors, h3_colors, colormaps, titles):
    """Create a PNG map for a single layer with clipping, thematic styling, and basemap"""
    
    # Set up the plot with consistent figure size
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Load city boundary for clipping and extent
    try:
        city_boundary_file = Path("../outputs/maps/kepler_data/01_city_boundary.geojson")
        if city_boundary_file.exists():
            city_boundary = gpd.read_file(city_boundary_file)
            city_bounds = city_boundary.total_bounds
        else:
            city_bounds = None
    except Exception as e:
        print(f"⚠️ City boundary loading failed for {layer_name}: {e}")
        city_bounds = None
    
    # Determine layer type and styling
    if layer_name in basic_colors:
        # Basic infrastructure layer
        color = basic_colors[layer_name]
        
        if layer_name == '01_city_boundary':
            # City boundary as outline only
            gdf.boundary.plot(ax=ax, color='black', linewidth=3, alpha=0.8)
        elif layer_name == '03_roads':
            # Roads as lines
            gdf.plot(ax=ax, color=color, linewidth=0.5, alpha=0.6)
        elif layer_name == '04_pt_stops':
            # PT stops as points
            gdf.plot(ax=ax, color=color, markersize=2, alpha=0.8)
        else:
            # Other layers as filled polygons
            gdf.plot(ax=ax, color=color, alpha=0.5, edgecolor='white', linewidth=0.5)
            
    elif layer_name in h3_colors or any(keyword in layer_name for keyword in ['mismatch', 'population', 'forest', 'green_score']):
        # H3 analysis layer with data-driven coloring
        # Decide which attribute to plot
        candidates = ["pt_gravity", "ess_types", "detour_factor", "amen_entropy",
                     "park_min", "mismatch", "population", "forest_min", "green_score"]
        color_col = next((c for c in candidates if c in gdf.columns), None)
        
        if color_col and not gdf[color_col].isna().all():
            cmap = colormaps.get(color_col, "viridis")
            
            # Special handling for diverging colormaps
            if color_col == "mismatch":
                # Center diverging colormap at 0
                vmin, vmax = gdf[color_col].min(), gdf[color_col].max()
                vabs = max(abs(vmin), abs(vmax))
                norm = plt.Normalize(-vabs, vabs)
                
                gdf.plot(
                    column=color_col, ax=ax, cmap=cmap, norm=norm, legend=True,
                    alpha=0.8, edgecolor="lightgrey", linewidth=0.3,
                    legend_kwds={"label": "PT Supply vs Population Demand", "orientation": "vertical"}
                )
            else:
                # Regular sequential colormap
                legend_label = {
                    "pt_gravity": "PT Modal Gravity (0–100)",
                    "ess_types": "# Essential Types (≤10 min walk)",
                    "detour_factor": "Detour Factor",
                    "amen_entropy": "Service Diversity (Shannon Entropy)",
                    "park_min": "Minutes to Nearest Park",
                    "population": "People per km²",
                    "forest_min": "Minutes to Nearest Forest",
                    "green_score": "Green Access Score (0–100)"
                }.get(color_col, color_col)
                
                gdf.plot(
                    column=color_col, ax=ax, cmap=cmap, legend=True,
                    alpha=0.8, edgecolor="lightgrey", linewidth=0.3,
                    legend_kwds={"label": legend_label, "orientation": "vertical"}
                )
        else:
            # Fallback to solid color
            gdf.plot(ax=ax, color=h3_colors.get(layer_name, "grey"), alpha=0.7, 
                    edgecolor="lightgrey", linewidth=0.3)
    
    elif any(keyword in layer_name for keyword in ['18_', '19_', '20_', '21_', '22_', '23_', '24_']):
        # Choropleth layers (18-24) with "value" column
        if "value" in gdf.columns and not gdf["value"].isna().all():
            # Get appropriate colormap for the layer
            cmap = "viridis"  # Default colormap
            legend_label = "Value"
            
            # Map specific colormaps for different choropleth types
            if "amenity" in layer_name:
                cmap = "Purples"
                legend_label = "Amenity Count"
            elif "area" in layer_name:
                cmap = "Blues"
                legend_label = "Area (km²)"
            elif "green" in layer_name:
                cmap = "Greens"
                legend_label = "Green Space Ratio (%)"
            elif "mobility" in layer_name:
                cmap = "YlOrRd"
                legend_label = "Mobility Score"
            elif "pt_density" in layer_name:
                cmap = "Blues"
                legend_label = "PT Stop Density"
            elif "walkability" in layer_name:
                cmap = "YlGnBu"
                legend_label = "Walkability Score"
            elif "overall" in layer_name:
                cmap = "RdYlBu"
                legend_label = "Overall Score"
            
            # Plot the choropleth
            gdf.plot(
                column="value", ax=ax, cmap=cmap, legend=True,
                alpha=0.8, edgecolor="lightgrey", linewidth=0.3,
                legend_kwds={"label": legend_label, "orientation": "vertical"}
            )
        else:
            # Fallback to solid color if no value column
            gdf.plot(ax=ax, color="lightblue", alpha=0.7, 
                    edgecolor="lightgrey", linewidth=0.3)
            print(f"⚠️ No 'value' column found for {layer_name}, using fallback styling")
    
    # Set bilingual titles
    if layer_name in titles:
        main, sub = titles[layer_name]
        ax.set_title(f"{main}\n{sub}", fontsize=14, fontweight="bold", pad=20)
    else:
        # Fallback title
        title = layer_name.replace('_', ' ').title()
        ax.set_title(f'Stuttgart - {title}', fontsize=16, fontweight='bold', pad=20)
    
    # Lock extent to city boundary if available
    if city_bounds is not None:
        ax.set_xlim(city_bounds[0], city_bounds[2])
        ax.set_ylim(city_bounds[1], city_bounds[3])
        
        # Draw city boundary outline in black (less prominent for choropleth maps)
        if any(keyword in layer_name for keyword in ['18_', '19_', '20_', '21_', '22_', '23_', '24_']):
            # For choropleth maps, use a subtle boundary
            city_boundary.boundary.plot(ax=ax, color='black', linewidth=1, alpha=0.6)
        else:
            # For other maps, use the standard boundary
            city_boundary.boundary.plot(ax=ax, color='black', linewidth=2, alpha=0.8)
    
    # Remove axes
    ax.axis('off')
    
    # Add a subtle background
    ax.set_facecolor('#f8f9fa')
    
    # Add Carto Light basemap
    try:
        ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.Carto.LightNoLabels)
    except Exception as e:
        print(f"⚠️ Basemap skipped for {layer_name}: {e}")
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

def create_missing_maps(all_layers, geojson_dir, png_dir, basic_colors, h3_colors, colormaps, titles, output_names):
    """Create missing maps (04a, 04b, 09, 10) if their data is available in any layer"""
    
    # Define missing maps to look for
    missing_maps = {
        "04a_mismatch_diverging_h3": ["mismatch"],
        "04b_population_density_h3": ["population"],
        "09_forest_access_time_h3": ["forest_min"],
        "10_green_gaps_h3": ["green_score"]
    }
    
    # Check each layer for missing map data
    for map_name, required_columns in missing_maps.items():
        for layer_name, gdf in all_layers.items():
            # Check if this layer has the required columns
            if any(col in gdf.columns for col in required_columns):
                print(f"  🔍 Found data for {map_name} in {layer_name}")
                
                try:
                    # Create a copy with the map name for proper titling
                    gdf_copy = gdf.copy()
                    
                    # 1. Export GeoJSON file
                    geojson_file = geojson_dir / f"{map_name}.geojson"
                    gdf_copy.to_file(geojson_file, driver='GeoJSON')
                    print(f"    ✅ GeoJSON exported: {geojson_file}")
                    
                    # 2. Create PNG map
                    png_file = png_dir / output_names.get(map_name, f"{map_name}.png")
                    create_layer_png(gdf_copy, map_name, png_file, basic_colors, h3_colors, colormaps, titles)
                    print(f"    ✅ PNG map created: {png_file}")
                    
                    # Only create each missing map once
                    break
                    
                except Exception as e:
                    print(f"    ❌ Error creating {map_name}: {e}")
    
    print("  ✅ Missing maps check complete")

def main():
    """Main execution function"""
    print("🚀 Starting Kepler.gl Python Module Dashboard Creation...")
    print("=" * 60)
    print("📚 Following Medium article approach: https://medium.com/better-programming/geo-data-visualization-with-kepler-gl-fbc15debbca4")
    print("=" * 60)
    
    try:
        out_dir = create_kepler_python_dashboard()
        
        if out_dir:
            print(f"\n🎉 Dashboard creation complete!")
            print(f"📁 Output directory: {out_dir}")
            print(f"📊 Dashboard: {out_dir.name}/stuttgart_18_layers_kepler_dashboard.html")
            print(f"🔺 Total layers: 18 (using Python module approach)")
            print(f"📊 Individual GeoJSON files: {out_dir.name}/geojson_layers/")
            print(f"🖼️ Individual PNG maps: {out_dir.name}/png_maps/")
            print(f"🔍 Missing maps (04a, 04b, 09, 10) will be auto-detected and created")
            print(f"🎨 New choropleth maps (18-24) will be exported as PNGs")
            print(f"\n🚀 Opening dashboard in browser...")
            
            # Open the dashboard
            dashboard_file = out_dir / "stuttgart_18_layers_kepler_dashboard.html"
            webbrowser.open(f'file://{dashboard_file.absolute()}')
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Please install keplergl: pip install keplergl")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
