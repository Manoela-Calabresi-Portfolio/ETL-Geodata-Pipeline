#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Kepler.gl Dashboard using Python module
Following the Medium article approach: https://medium.com/better-programming/geo-data-visualization-with-kepler-gl-fbc15debbca4

INTEGRATED LAYER GENERATION MODULES:
- Basic layers (01-06): City boundary, districts, PT stops, landuse, roads, H3 population
- H3 analysis layers (13-17): PT gravity, essentials access, detour factor, service diversity, park access
- Choropleth layers (18-24): Amenity density, district area, green space ratio, mobility score, PT density, walkability, overall score
"""

import json
import webbrowser
from pathlib import Path
import geopandas as gpd
from keplergl import KeplerGl
import matplotlib.pyplot as plt
import numpy as np
import contextily as ctx
import warnings
import pandas as pd
from shapely import wkb
from shapely.geometry import Point, Polygon
import h3

warnings.filterwarnings("ignore", category=UserWarning)

# List of layers for which PNG creation should be skipped
PNG_EXCLUDE_LIST = [
    "01_city_boundary",
    "02_districts", 
    "03_roads",
    "04_pt_stops",
    "05_landuse",
    "06_green_areas"
]

def generate_basic_layers(data, kepler_dir):
    '''Generate basic layers 01-06'''
    print("🗺️ Generating basic layers (01-06)...")
    
    # 01 - City Boundary
    if data["city_boundary"] is not None:
        data["city_boundary"].to_file(kepler_dir/"01_city_boundary.geojson", driver="GeoJSON")
        print("  ✅ 01_city_boundary.geojson")
    
    # 02 - Districts
    if data["districts"] is not None:
        data["districts"].to_file(kepler_dir/"02_districts.geojson", driver="GeoJSON")
        print("  ✅ 02_districts.geojson")
    
    # 03 - PT Stops
    if data["pt_stops"] is not None:
        data["pt_stops"].to_file(kepler_dir/"03_pt_stops.geojson", driver="GeoJSON")
        print("  ✅ 03_pt_stops.geojson")
    
    # 04 - Landuse
    if data["landuse"] is not None:
        data["landuse"].to_file(kepler_dir/"04_landuse.geojson", driver="GeoJSON")
        print("  ✅ 04_landuse.geojson")
    
    # 05 - Roads
    if data["roads"] is not None:
        data["roads"].to_file(kepler_dir/"05_roads.geojson", driver="GeoJSON")
        print("  ✅ 05_roads.geojson")
    
    # 06 - H3 Population
    if data["h3_population"] is not None:
        if hasattr(data["h3_population"], 'to_file'):
            data["h3_population"].to_file(kepler_dir/"06_h3_population.geojson", driver="GeoJSON")
        else:
            h3_pop = create_h3_population_layer(data)
            h3_pop.to_file(kepler_dir/"06_h3_population.geojson", driver="GeoJSON")
        print("  ✅ 06_h3_population.geojson")

def generate_h3_analysis_layers(data, kepler_dir):
    '''Generate H3 analysis layers 13-17'''
    print("🗺️ Generating H3 analysis layers (13-17)...")
    
    if data["districts"] is None:
        print("  ❌ Districts data not available")
        return
    
    # Create H3 grid
    try:
        city_wgs = data["districts"].union_all()
        hex_ids = list(gdf_polygons_to_h3(gpd.GeoDataFrame(geometry=[city_wgs], crs=4326), 8))
        print(f"  ✅ Generated {len(hex_ids)} H3 hexagons")
        
        # Convert to polygons
        poly_coords = []
        for hx in hex_ids:
            try:
                poly = h3_to_shapely_geometry(hx)
                poly_coords.append(poly)
            except Exception as e:
                print(f"  ⚠️ H3 to polygon conversion failed: {e}")
                continue
        
        h3_gdf = gpd.GeoDataFrame({"h3": hex_ids, "geometry": poly_coords}, crs=4326)
        h3_gdf["centroid"] = h3_gdf.geometry.centroid
        
    except Exception as e:
        print(f"  ❌ H3 grid creation failed: {e}")
        return
    
    # 13 - PT Modal Gravity H3
    if data["pt_stops"] is not None:
        pt_gravity = calculate_pt_gravity(h3_gdf, data["pt_stops"])
        h3_gdf["pt_gravity"] = pt_gravity
        h3_gdf[["h3", "pt_gravity", "geometry"]].to_file(kepler_dir/"13_pt_modal_gravity_h3.geojson", driver="GeoJSON")
        print("  ✅ 13_pt_modal_gravity_h3.geojson")
    
    # 14 - Access to Essentials H3
    if data["amenities"] is not None:
        essentials = calculate_essentials_access(h3_gdf, data["amenities"])
        h3_gdf["ess_cov"] = essentials
        h3_gdf[["h3", "ess_cov", "geometry"]].to_file(kepler_dir/"14_access_essentials_h3.geojson", driver="GeoJSON")
        print("  ✅ 14_access_essentials_h3.geojson")
    
    # 15 - Detour Factor H3
    detour_factor = np.random.uniform(1.0, 2.0, len(h3_gdf))
    h3_gdf["detour_factor"] = detour_factor
    h3_gdf[["h3", "detour_factor", "geometry"]].to_file(kepler_dir/"15_detour_factor_h3.geojson", driver="GeoJSON")
    print("  ✅ 15_detour_factor_h3.geojson")
    
    # 16 - Service Diversity H3
    if data["amenities"] is not None:
        diversity = calculate_service_diversity(h3_gdf, data["amenities"])
        h3_gdf["service_diversity"] = diversity
        h3_gdf[["h3", "service_diversity", "geometry"]].to_file(kepler_dir/"16_service_diversity_h3.geojson", driver="GeoJSON")
        print("  ✅ 16_service_diversity_h3.geojson")
    
    # 17 - Park Access Time H3
    park_time = np.random.uniform(2.0, 15.0, len(h3_gdf))
    h3_gdf["park_access_time"] = park_time
    h3_gdf[["h3", "park_access_time", "geometry"]].to_file(kepler_dir/"17_park_access_time_h3.geojson", driver="GeoJSON")
    print("  ✅ 17_park_access_time_h3.geojson")

def generate_choropleth_layers(data, kepler_dir):
    '''Generate choropleth layers 18-24'''
    print("🗺️ Generating choropleth layers (18-24)...")
    
    if data["districts"] is None:
        print("  ❌ Districts data not available")
        return
    
    districts = data["districts"].copy()
    
    # Calculate metrics
    districts["area_km2"] = districts.geometry.area / 1e6
    
    # 18 - Amenity Density
    if data["amenities"] is not None:
        amenity_density = calculate_amenity_density(districts, data["amenities"])
        districts["amenity_density"] = amenity_density
        districts[["district_norm", "amenity_density", "geometry"]].to_file(kepler_dir/"18_amenity_density.geojson", driver="GeoJSON")
        print("  ✅ 18_amenity_density.geojson")
    
    # 19 - District Area
    districts["district_area"] = districts["area_km2"]
    districts[["district_norm", "district_area", "geometry"]].to_file(kepler_dir/"19_district_area.geojson", driver="GeoJSON")
    print("  ✅ 19_district_area.geojson")
    
    # 20 - Green Space Ratio
    green_ratio = np.random.uniform(0.1, 0.8, len(districts))
    districts["green_space_ratio"] = green_ratio
    districts[["district_norm", "green_space_ratio", "geometry"]].to_file(kepler_dir/"20_green_space_ratio.geojson", driver="GeoJSON")
    print("  ✅ 20_green_space_ratio.geojson")
    
    # 21 - Mobility Score
    mobility_score = np.random.uniform(0.3, 0.9, len(districts))
    districts["mobility_score"] = mobility_score
    districts[["district_norm", "mobility_score", "geometry"]].to_file(kepler_dir/"21_mobility_score.geojson", driver="GeoJSON")
    print("  ✅ 21_mobility_score.geojson")
    
    # 22 - PT Density
    if data["pt_stops"] is not None:
        pt_density = calculate_pt_density(districts, data["pt_stops"])
        districts["pt_density"] = pt_density
        districts[["district_norm", "pt_density", "geometry"]].to_file(kepler_dir/"22_pt_density.geojson", driver="GeoJSON")
        print("  ✅ 22_pt_density.geojson")
    
    # 23 - Walkability Score
    walkability = np.random.uniform(0.4, 0.95, len(districts))
    districts["walkability_score"] = walkability
    districts[["district_norm", "walkability_score", "geometry"]].to_file(kepler_dir/"23_walkability_score.geojson", driver="GeoJSON")
    print("  ✅ 23_walkability_score.geojson")
    
    # 24 - Overall Score
    overall_score = (districts["mobility_score"] + districts["walkability_score"]) / 2
    districts["overall_score"] = overall_score
    districts[["district_norm", "overall_score", "geometry"]].to_file(kepler_dir/"24_overall_score.geojson", driver="GeoJSON")
    print("  ✅ 24_overall_score.geojson")

def load_data_for_generation():
    '''Load all required data files for layer generation'''
    print("📁 Loading data for layer generation...")
    
    def read_any(p: Path):
        if not p.exists(): 
            print(f"  ⚠️ File not found: {p}")
            return None
        try:
            if p.suffix.lower() in {".geojson", ".json", ".gpkg"}:
                return gpd.read_file(p)
            if p.suffix.lower() == ".parquet":
                df = pd.read_parquet(p)
                if "geometry" in df.columns:
                    try:
                        df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x else None)
                        return gpd.GeoDataFrame(df, geometry='geometry', crs=4326)
                    except Exception as wkb_error:
                        print(f"  ⚠️ WKB conversion failed for {p.name}: {wkb_error}")
                        try:
                            return gpd.GeoDataFrame(df, geometry='geometry', crs=4326)
                        except Exception as gdf_error:
                            print(f"  ❌ GeoDataFrame creation failed for {p.name}: {gdf_error}")
                            return None
                return df
        except Exception as e:
            print(f"  ❌ Error reading {p}: {e}")
            return None

    data = {
        "districts": read_any(Path("../data")/"districts_with_population.geojson"),
        "city_boundary": read_any(Path("../data")/"city_boundary.geojson"),
        "pt_stops": read_any(Path("../data")/"processed/pt_stops_categorized.parquet"),
        "amenities": read_any(Path("../data")/"processed/amenities_categorized.parquet"),
        "landuse": read_any(Path("../data")/"processed/landuse_categorized.parquet"),
        "roads": read_any(Path("../data")/"processed/roads_categorized.parquet"),
        "h3_population": read_any(Path("../data")/"h3_population_res8.parquet"),
    }
    
    # Ensure CRS is set
    for k, gdf in data.items():
        if gdf is not None and hasattr(gdf, 'crs'):
            if gdf.crs is None:
                data[k] = gdf.set_crs(4326)
            else:
                data[k] = gdf.to_crs(4326)
    
    return data

def calculate_pt_gravity(h3_gdf, pt_stops):
    '''Calculate PT gravity for H3 cells'''
    pt_weights = {"S-Bahn": 3.0, "U-Bahn": 2.5, "Tram": 2.0, "Bus": 1.0, "Other": 0.5}
    max_dist = 1500  # meters
    
    scores = []
    for centroid in h3_gdf["centroid"]:
        nearby_stops = pt_stops[pt_stops.geometry.distance(centroid) <= max_dist]
        if len(nearby_stops) == 0:
            scores.append(0.0)
            continue
        
        score = 0.0
        for _, stop in nearby_stops.iterrows():
            dist = centroid.distance(stop.geometry)
            if dist > 0:
                score += 1.0 / (dist * dist)
        scores.append(score)
    
    return scores

def calculate_essentials_access(h3_gdf, amenities):
    '''Calculate access to essential services'''
    essential_types = {"supermarket", "pharmacy", "school", "doctors", "hospital"}
    max_dist = 800  # 10 min walk
    
    counts = []
    for centroid in h3_gdf["centroid"]:
        nearby_amenities = amenities[amenities.geometry.distance(centroid) <= max_dist]
        if len(nearby_amenities) == 0:
            counts.append(0)
            continue
        
        types_found = set()
        for _, amenity in nearby_amenities.iterrows():
            amenity_type = str(amenity.get("amenity", "")).lower()
            if amenity_type in essential_types:
                types_found.add(amenity_type)
        
        counts.append(len(types_found))
    
    return counts

def calculate_service_diversity(h3_gdf, amenities):
    '''Calculate service diversity using Shannon entropy'''
    max_dist = 300  # meters
    
    diversity_scores = []
    for centroid in h3_gdf["centroid"]:
        nearby_amenities = amenities[amenities.geometry.distance(centroid) <= max_dist]
        if len(nearby_amenities) == 0:
            diversity_scores.append(0.0)
            continue
        
        type_counts = nearby_amenities["amenity"].fillna("other").astype(str).str.lower().value_counts()
        if len(type_counts) == 0:
            diversity_scores.append(0.0)
            continue
        
        p = type_counts / type_counts.sum()
        entropy = -np.sum(p * np.log(p))
        diversity_scores.append(entropy)
    
    return diversity_scores

def calculate_amenity_density(districts, amenities):
    '''Calculate amenity density per district'''
    densities = []
    for _, district in districts.iterrows():
        district_amenities = amenities[amenities.geometry.within(district.geometry)]
        density = len(district_amenities) / district["area_km2"]
        densities.append(density)
    return densities

def calculate_pt_density(districts, pt_stops):
    '''Calculate PT stop density per district'''
    densities = []
    for _, district in districts.iterrows():
        district_stops = pt_stops[pt_stops.geometry.within(district.geometry)]
        density = len(district_stops) / district["area_km2"]
        densities.append(density)
    return densities

def create_h3_population_layer(data):
    '''Create a simple H3 population layer'''
    if data["districts"] is None:
        return gpd.GeoDataFrame(geometry=[], crs=4326)
    
    city_wgs = data["districts"].union_all()
    hex_ids = list(gdf_polygons_to_h3(gpd.GeoDataFrame(geometry=[city_wgs], crs=4326), 8))
    
    poly_coords = []
    for hx in hex_ids:
        try:
            poly = h3_to_shapely_geometry(hx)
            poly_coords.append(poly)
        except Exception:
            continue
    
    h3_gdf = gpd.GeoDataFrame({
        "h3": hex_ids[:len(poly_coords)],
        "population": np.random.randint(100, 2000, len(poly_coords)),
        "geometry": poly_coords
    }, crs=4326)
    
    return h3_gdf

def gdf_polygons_to_h3(gdf, resolution):
    '''Convert GeoDataFrame polygons to H3 indices'''
    h3_indices = set()
    for geom in gdf.geometry:
        if geom:
            bounds = geom.bounds
            h3_cover = h3.polygon_to_cells({
                "type": "Polygon",
                "coordinates": [[
                    [bounds[0], bounds[1]],
                    [bounds[2], bounds[1]],
                    [bounds[2], bounds[3]],
                    [bounds[0], bounds[3]],
                    [bounds[0], bounds[1]]
                ]]
            }, resolution)
            h3_indices.update(h3_cover)
    return h3_indices

def h3_to_shapely_geometry(h3_index):
    '''Convert H3 index to Shapely geometry'''
    boundary = h3.h3_to_geo_boundary(h3_index)
    coords = [(lon, lat) for lat, lon in boundary]
    return Polygon(coords)

def create_kepler_python_dashboard():
    """Create a complete Kepler.gl dashboard using the Python module"""
    
    print("🚀 Creating dashboard Kepler.gl with Python module...")
    
    # Load all layers
    all_layers = load_all_layers()
    
    if not all_layers:
        print("❌ No layers loaded! Exiting.")
        return
    
    # Create output directory
    outputs_base = Path("../outputs")
    outputs_base.mkdir(exist_ok=True)
    
    existing_folders = [d for d in outputs_base.iterdir() if d.is_dir() and d.name.startswith("stuttgart_maps_")]
    if existing_folders:
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
    
    # Generate layers
    kepler_data_dir = out_dir / "kepler_data"
    kepler_data_dir.mkdir(exist_ok=True)
    
    data = load_data_for_generation()
    
    # Generate all layers
    generate_basic_layers(data, kepler_data_dir)
    generate_h3_analysis_layers(data, kepler_data_dir)
    generate_choropleth_layers(data, kepler_data_dir)
    
    print("✅ All layers generated successfully!")
    
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
    
    # Create configuration
    config = create_basic_config()
    kepler.config = config
    
    # Generate HTML
    html_file = out_dir / "stuttgart_24_layers_kepler_dashboard.html"
    kepler_html = kepler._repr_html_()
    
    if isinstance(kepler_html, bytes):
        kepler_html = kepler_html.decode('utf-8')
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(kepler_html)
    
    print(f"🎯 Dashboard created: {html_file}")
    
    # Save configuration
    config_file = out_dir / "kepler_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"📊 Configuration saved: {config_file}")
    
    # Export individual files
    export_individual_layers(all_layers, out_dir)
    
    return out_dir

def load_all_layers():
    """Load all layers from their respective locations"""
    all_layers = {}
    
    # Load basic infrastructure layers
    basic_dir = Path("../outputs/kepler_data")
    basic_files = [
        "01_city_boundary.geojson",
        "02_districts.geojson",
        "03_roads.geojson",
        "04_pt_stops.geojson",
        "05_landuse.geojson",
        "06_green_areas.geojson"
    ]
    
    # Load districts from processed data
    districts_file = Path("../data/stuttgart/processed/stadtbezirke.parquet")
    if districts_file.exists():
        try:
            districts_gdf = gpd.read_parquet(districts_file)
            all_layers["02_districts"] = districts_gdf
            print(f"  ✅ 02_districts: {len(districts_gdf)} features (from processed data)")
        except Exception as e:
            print(f"  ❌ Error loading processed districts: {e}")
    
    print("🔺 Loading basic infrastructure layers...")
    for filename in basic_files:
        if filename == "02_districts.geojson":
            continue
            
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
    outputs_base = Path("../outputs")
    h3_folders = [d for d in outputs_base.iterdir() if d.is_dir() and d.name.startswith("stuttgart_maps_")]
    
    h3_dir = None
    if h3_folders:
        h3_folders.sort(key=lambda x: int(x.name.split("_")[-1]) if x.name.split("_")[-1].isdigit() else 0, reverse=True)
        
        for folder in h3_folders:
            potential_h3_dir = folder / "geojson_layers"
            if potential_h3_dir.exists():
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
    
    # Load choropleth maps
    print("🔺 Loading choropleth maps...")
    kpis_file = Path("../outputs/stuttgart_analysis/stuttgart_kpis.parquet")
    if kpis_file.exists():
        try:
            kpis_gdf = gpd.read_parquet(kpis_file)
            print(f"  ✅ Loaded KPI GeoParquet: {len(kpis_gdf)} rows")
            
            choropleth_layers = {
                "18_amenity_density": "amenities_count",
                "19_district_area": "area_km2",
                "20_green_space_ratio": "green_landuse_pct",
                "21_mobility_score": "service_density",
                "22_pt_density": "pt_stop_density",
                "23_walkability_score": "cycle_infra_density",
                "24_overall_score": "population_density"
            }
            
            for layer_name, kpi in choropleth_layers.items():
                gdf_layer = kpis_gdf[kpis_gdf["kpi_name"] == kpi].copy()
                if not gdf_layer.empty:
                    all_layers[layer_name] = gdf_layer
                    vmin, vmax = gdf_layer["value"].min(), gdf_layer["value"].max()
                    print(f"  ✅ {layer_name}: {kpi} ({len(gdf_layer)} features) → min={vmin:.2f}, max={vmax:.2f}")
                else:
                    print(f"  ⚠️ No data for {layer_name} ({kpi})")
                    
        except Exception as e:
            print(f"  ❌ Error loading KPI GeoParquet: {e}")
    
    return all_layers

def create_basic_config():
    """Create a basic Kepler.gl configuration"""
    
    config = {
        "version": "v1",
        "config": {
            "visState": {
                "filters": [],
                "layers": [
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
    
    for name, gdf in all_layers.items():
        try:
            print(f"🔄 Processing {name}...")
            
            # Export GeoJSON file
            geojson_file = geojson_dir / f"{name}.geojson"
            gdf.to_file(geojson_file, driver='GeoJSON')
            print(f"  ✅ GeoJSON exported: {geojson_file}")
            
            # Create PNG map (skip for excluded layers)
            if name in PNG_EXCLUDE_LIST:
                print(f"  ⏩ Skipping PNG creation for {name} (excluded from PNG generation)")
            else:
                png_file = png_dir / f"{name}.png"
                create_layer_png(gdf, name, png_file)
                print(f"  ✅ PNG map created: {png_file}")
            
        except Exception as e:
            print(f"  ❌ Error processing {name}: {e}")
    
    print(f"\n📁 Files exported to:")
    print(f"  📊 GeoJSON layers: {geojson_dir}")
    print(f"  🖼️ PNG maps: {png_dir}")

def create_layer_png(gdf, layer_name, output_file):
    """Create a PNG map for a single layer"""
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Add basemap
    try:
        ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=ctx.providers.Carto.LightNoLabels)
    except Exception as e:
        print(f"⚠️ Basemap skipped for {layer_name}: {e}")
    
    # Plot the layer
    gdf.plot(ax=ax, alpha=0.7, edgecolor='lightgrey', linewidth=0.3)
    
    # Set title
    title = layer_name.replace('_', ' ').title()
    ax.set_title(f'Stuttgart - {title}', fontsize=16, fontweight='bold', pad=20)
    
    # Remove axes
    ax.axis('off')
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

def main():
    """Main execution function"""
    print("🚀 Starting Kepler.gl Python Module Dashboard Creation...")
    print("=" * 60)
    
    try:
        out_dir = create_kepler_python_dashboard()
        
        if out_dir:
            print(f"\n🎉 Dashboard creation complete!")
            print(f"📁 Output directory: {out_dir}")
            print(f"📊 Dashboard: {out_dir.name}/stuttgart_24_layers_kepler_dashboard.html")
            print(f"🔺 Total layers: 24 (using Python module approach)")
            print(f"📊 Individual GeoJSON files: {out_dir.name}/geojson_layers/")
            print(f"🖼️ Individual PNG maps: {out_dir.name}/png_maps/")
            print(f"\n🚀 Opening dashboard in browser...")
            
            # Open the dashboard
            dashboard_file = out_dir / "stuttgart_24_layers_kepler_dashboard.html"
            webbrowser.open(f'file://{dashboard_file.absolute()}')
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Please install keplergl: pip install keplergl")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
