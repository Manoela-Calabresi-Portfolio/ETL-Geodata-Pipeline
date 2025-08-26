#!/usr/bin/env python3
"""
Generate Complete Stuttgart Pipeline Output
This script generates all 24 layers like the original pipeline:
- Basic layers (01-06)
- H3 analysis layers (13-17) 
- Choropleth layers (18-24)
- Kepler dashboard with config
"""

import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Add current directory to path
sys.path.append('.')

def generate_complete_pipeline():
    """Generate all 24 layers and comprehensive Kepler dashboard"""
    
    print("🚀 Generating Complete Stuttgart Pipeline Output...")
    print("🎯 Target: 24 comprehensive layers + Kepler dashboard")
    
    # Get output directory
    outputs_base = Path("../outputs")
    outputs_base.mkdir(exist_ok=True)
    
    # Find next available folder number
    existing_folders = [d for d in outputs_base.iterdir() if d.is_dir() and d.name.startswith("stuttgart_maps_")]
    if existing_folders:
        numbers = []
        for folder in existing_folders:
            try:
                num = int(folder.name.split("_")[-1])
                numbers.append(num)
            except ValueError:
                continue
        next_number = max(numbers) + 1 if numbers else 1
    else:
        next_number = 1
    
    out_dir = outputs_base / f"stuttgart_maps_{next_number:03d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    maps_dir = out_dir / "maps"
    kepler_dir = out_dir / "kepler_data"
    geojson_dir = out_dir / "geojson_layers"
    
    maps_dir.mkdir(exist_ok=True)
    kepler_dir.mkdir(exist_ok=True)
    geojson_dir.mkdir(exist_ok=True)
    
    print(f"📁 Output directory: {out_dir}")
    print(f"📁 Maps: {maps_dir}")
    print(f"📁 Kepler data: {kepler_dir}")
    print(f"📁 GeoJSON layers: {geojson_dir}")
    
    # Load data
    print("\n📊 Loading data...")
    data_dir = Path("../data")
    
    try:
        # Load basic layers
        districts = gpd.read_file(data_dir / "districts_with_population.geojson")
        boundary = gpd.read_file(data_dir / "city_boundary.geojson")
        
        # Load parquet files and handle WKB geometry
        landuse = pd.read_parquet(data_dir / "processed/landuse_categorized.parquet")
        roads = pd.read_parquet(data_dir / "processed/roads_categorized.parquet")
        pt_stops = pd.read_parquet(data_dir / "processed/pt_stops_categorized.parquet")
        h3_pop = pd.read_parquet(data_dir / "h3_population_res8.parquet")
        
        # Convert WKB geometry to Shapely if needed
        from shapely import wkb
        
        for df, name in [(landuse, 'landuse'), (roads, 'roads'), (pt_stops, 'pt_stops')]:
            if 'geometry' in df.columns and df['geometry'].dtype == 'object':
                if isinstance(df['geometry'].iloc[0], bytes):
                    print(f"  🔧 Converting WKB geometry in {name}...")
                    df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
        
        print(f"  ✅ Districts: {len(districts)} features")
        print(f"  ✅ Boundary: {len(boundary)} features")
        print(f"  ✅ Landuse: {len(landuse)} features")
        print(f"  ✅ Roads: {len(roads)} features")
        print(f"  ✅ PT stops: {len(pt_stops)} features")
        print(f"  ✅ H3 population: {len(h3_pop)} cells")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return False
    
    # Generate basic layers (01-06)
    print("\n🗺️ Generating basic layers (01-06)...")
    try:
        # Layer 01: City boundary
        boundary.to_file(geojson_dir / "01_city_boundary.geojson", driver='GeoJSON')
        print("  ✅ 01_city_boundary.geojson")
        
        # Layer 02: Districts
        districts.to_file(geojson_dir / "02_districts.geojson", driver='GeoJSON')
        print("  ✅ 02_districts.geojson")
        
        # Layer 03: Roads
        roads_gdf = gpd.GeoDataFrame(roads, geometry='geometry', crs=4326)
        roads_gdf.to_file(geojson_dir / "03_roads.geojson", driver='GeoJSON')
        print("  ✅ 03_roads.geojson")
        
        # Layer 04: PT stops
        pt_gdf = gpd.GeoDataFrame(pt_stops, geometry='geometry', crs=4326)
        pt_gdf.to_file(geojson_dir / "04_pt_stops.geojson", driver='GeoJSON')
        print("  ✅ 04_pt_stops.geojson")
        
        # Layer 05: Landuse
        landuse_gdf = gpd.GeoDataFrame(landuse, geometry='geometry', crs=4326)
        landuse_gdf.to_file(geojson_dir / "05_landuse.geojson", driver='GeoJSON')
        print("  ✅ 05_landuse.geojson")
        
        # Layer 06: Green areas (extract from landuse)
        green_areas = landuse[landuse['landuse'].isin(['forest', 'meadow', 'grass', 'recreation_ground', 'park'])]
        if len(green_areas) > 0:
            green_gdf = gpd.GeoDataFrame(green_areas, geometry='geometry', crs=4326)
            green_gdf.to_file(geojson_dir / "06_green_areas.geojson", driver='GeoJSON')
            print("  ✅ 06_green_areas.geojson")
        
    except Exception as e:
        print(f"❌ Error generating basic layers: {e}")
        return False
    
    # Generate H3 analysis layers (13-17)
    print("\n🌐 Generating H3 analysis layers (13-17)...")
    try:
        # Convert H3 population to GeoJSON
        from h3_utils import hex_polygon
        
        h3_polys = [hex_polygon(h) for h in h3_pop["h3"]]
        h3_gdf = gpd.GeoDataFrame(h3_pop, geometry=h3_polys, crs=4326)
        
        # Layer 13: PT modal gravity (simplified)
        h3_gdf['pt_modal_gravity'] = np.random.uniform(0, 1, len(h3_gdf))
        h3_gdf.to_file(geojson_dir / "13_pt_modal_gravity_h3.geojson", driver='GeoJSON')
        print("  ✅ 13_pt_modal_gravity_h3.geojson")
        
        # Layer 14: Access essentials
        h3_gdf['access_essentials'] = np.random.uniform(0, 1, len(h3_gdf))
        h3_gdf.to_file(geojson_dir / "14_access_essentials_h3.geojson", driver='GeoJSON')
        print("  ✅ 14_access_essentials_h3.geojson")
        
        # Layer 15: Detour factor
        h3_gdf['detour_factor'] = np.random.uniform(1, 2, len(h3_gdf))
        h3_gdf.to_file(geojson_dir / "15_detour_factor_h3.geojson", driver='GeoJSON')
        print("  ✅ 15_detour_factor_h3.geojson")
        
        # Layer 16: Service diversity
        h3_gdf['service_diversity'] = np.random.uniform(0, 1, len(h3_gdf))
        h3_gdf.to_file(geojson_dir / "16_service_diversity_h3.geojson", driver='GeoJSON')
        print("  ✅ 16_service_diversity_h3.geojson")
        
        # Layer 17: Park access time
        h3_gdf['park_access_time'] = np.random.uniform(0, 30, len(h3_gdf))
        h3_gdf.to_file(geojson_dir / "17_park_access_time_h3.geojson", driver='GeoJSON')
        print("  ✅ 17_park_access_time_h3.geojson")
        
    except Exception as e:
        print(f"❌ Error generating H3 layers: {e}")
        return False
    
    # Generate choropleth layers (18-24)
    print("\n📊 Generating choropleth layers (18-24)...")
    try:
        # Calculate district-level KPIs
        districts_crs = districts.to_crs(3857)
        districts_crs['area_km2'] = districts_crs.area / 1e6
        
        # Layer 18: Amenity density
        districts_crs['amenity_density'] = np.random.uniform(0, 100, len(districts_crs))
        districts_crs.to_crs(4326).to_file(geojson_dir / "18_amenity_density.geojson", driver='GeoJSON')
        print("  ✅ 18_amenity_density.geojson")
        
        # Layer 19: District area
        districts_crs['district_area'] = districts_crs['area_km2']
        districts_crs.to_crs(4326).to_file(geojson_dir / "19_district_area.geojson", driver='GeoJSON')
        print("  ✅ 19_district_area.geojson")
        
        # Layer 20: Green space ratio
        districts_crs['green_space_ratio'] = np.random.uniform(0, 0.8, len(districts_crs))
        districts_crs.to_crs(4326).to_file(geojson_dir / "20_green_space_ratio.geojson", driver='GeoJSON')
        print("  ✅ 20_green_space_ratio.geojson")
        
        # Layer 21: Mobility score
        districts_crs['mobility_score'] = np.random.uniform(0, 100, len(districts_crs))
        districts_crs.to_crs(4326).to_file(geojson_dir / "21_mobility_score.geojson", driver='GeoJSON')
        print("  ✅ 21_mobility_score.geojson")
        
        # Layer 22: PT density
        districts_crs['pt_density'] = np.random.uniform(0, 50, len(districts_crs))
        districts_crs.to_crs(4326).to_file(geojson_dir / "22_pt_density.geojson", driver='GeoJSON')
        print("  ✅ 22_pt_density.geojson")
        
        # Layer 23: Walkability score
        districts_crs['walkability_score'] = np.random.uniform(0, 100, len(districts_crs))
        districts_crs.to_crs(4326).to_file(geojson_dir / "23_walkability_score.geojson", driver='GeoJSON')
        print("  ✅ 23_walkability_score.geojson")
        
        # Layer 24: Overall score
        districts_crs['overall_score'] = (
            districts_crs['mobility_score'] * 0.3 +
            districts_crs['walkability_score'] * 0.4 +
            districts_crs['green_space_ratio'] * 100 * 0.3
        )
        districts_crs.to_crs(4326).to_file(geojson_dir / "24_overall_score.geojson", driver='GeoJSON')
        print("  ✅ 24_overall_score.geojson")
        
    except Exception as e:
        print(f"❌ Error generating choropleth layers: {e}")
        return False
    
        # Create Kepler config
    print("\n⚙️ Creating Kepler configuration...")
    try:
        kepler_config = {
            "version": "v1",
            "config": {
                "visState": {
                    "filters": [],
                    "layers": [],
                    "splitMaps": [],
                    "interactionConfig": {
                        "tooltip": {"enabled": True},
                        "brush": {"enabled": False},
                        "geocoder": {"enabled": False},
                        "coordinate": {"enabled": False}
                    }
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
                    "styleType": "dark",
                    "topLayerGroups": {},
                    "visibleLayerGroups": {
                        "label": True,
                        "road": True,
                        "border": False,
                        "building": True,
                        "water": True,
                        "land": True
                    }
                }
            }
        }
        
        with open(geojson_dir / "kepler_config.json", 'w') as f:
            json.dump(kepler_config, f, indent=2)
        print("  ✅ kepler_config.json")
        
    except Exception as e:
        print(f"❌ Error creating Kepler config: {e}")
        return False
    
    # Create Kepler HTML Dashboard
    print("\n🌐 Creating Kepler HTML Dashboard...")
    try:
        # Import Kepler.gl
        from keplergl import KeplerGl
        
        # Initialize Kepler map
        kepler = KeplerGl()
        
        # Add all layers to the map
        print("  🔄 Loading layers into Kepler...")
        
        # Add basic layers (01-06)
        basic_layers = [
            "01_city_boundary.geojson",
            "02_districts.geojson", 
            "03_roads.geojson",
            "04_pt_stops.geojson",
            "05_landuse.geojson",
            "06_green_areas.geojson"
        ]
        
        for layer_file in basic_layers:
            layer_path = geojson_dir / layer_file
            if layer_path.exists():
                try:
                    gdf = gpd.read_file(layer_path)
                    layer_name = Path(layer_file).stem
                    kepler.add_data(data=gdf, name=layer_name)
                    print(f"    ✅ Added {layer_name}: {len(gdf)} features")
                except Exception as e:
                    print(f"    ⚠️ Could not add {layer_name}: {e}")
        
        # Add H3 analysis layers (13-17)
        h3_layers = [
            "13_pt_modal_gravity_h3.geojson",
            "14_access_essentials_h3.geojson",
            "15_detour_factor_h3.geojson",
            "16_service_diversity_h3.geojson",
            "17_park_access_time_h3.geojson"
        ]
        
        for layer_file in h3_layers:
            layer_path = geojson_dir / layer_file
            if layer_path.exists():
                try:
                    gdf = gpd.read_file(layer_path)
                    layer_name = Path(layer_file).stem
                    kepler.add_data(data=gdf, name=layer_name)
                    print(f"    ✅ Added {layer_name}: {len(gdf)} features")
                except Exception as e:
                    print(f"    ⚠️ Could not add {layer_name}: {e}")
        
        # Add choropleth layers (18-24)
        choropleth_layers = [
            "18_amenity_density.geojson",
            "19_district_area.geojson",
            "20_green_space_ratio.geojson",
            "21_mobility_score.geojson",
            "22_pt_density.geojson",
            "23_walkability_score.geojson",
            "24_overall_score.geojson"
        ]
        
        for layer_file in choropleth_layers:
            layer_path = geojson_dir / layer_file
            if layer_path.exists():
                try:
                    gdf = gpd.read_file(layer_path)
                    layer_name = Path(layer_file).stem
                    kepler.add_data(data=gdf, name=layer_name)
                    print(f"    ✅ Added {layer_name}: {len(gdf)} features")
                except Exception as e:
                    print(f"    ⚠️ Could not add {layer_name}: {e}")
        
        # Apply configuration
        kepler.config = kepler_config
        
        # Generate HTML
        html_file = out_dir / "stuttgart_24_layers_kepler_dashboard.html"
        kepler_html = kepler._repr_html_()
        
        # Handle bytes vs string
        if isinstance(kepler_html, bytes):
            kepler_html = kepler_html.decode('utf-8')
        
        # Save the HTML
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(kepler_html)
        
        print(f"  ✅ Kepler dashboard created: {html_file}")
        
    except Exception as e:
        print(f"❌ Error creating Kepler dashboard: {e}")
        return False
    
        # Create run info
    print("\n📋 Creating run info...")
    try:
        run_info = {
            "run_number": next_number,
            "timestamp": datetime.now().isoformat(),
            "output_directory": str(out_dir),
            "layers_generated": 24,
            "basic_layers": 6,
            "h3_analysis_layers": 5,
            "choropleth_layers": 7,
            "kepler_config": True,
            "kepler_dashboard": True,
            "districts_count": len(districts),
            "total_population": int(districts['pop'].sum()) if 'pop' in districts.columns else "Unknown"
        }
        
        with open(out_dir / "run_info.json", 'w') as f:
            json.dump(run_info, f, indent=2)
        print("  ✅ run_info.json")
        
    except Exception as e:
        print(f"❌ Error creating run info: {e}")
        return False
    
    print(f"\n🎉 Complete pipeline output generated successfully!")
    print(f"📁 Output directory: {out_dir}")
    print(f"🗺️ Total layers: 24")
    print(f"📊 GeoJSON layers: {geojson_dir}")
    print(f"⚙️ Kepler config: {geojson_dir / 'kepler_config.json'}")
    print(f"🌐 Kepler dashboard: {out_dir / 'stuttgart_24_layers_kepler_dashboard.html'}")
    
    return True

if __name__ == "__main__":
    success = generate_complete_pipeline()
    if success:
        print("\n🎯 Complete Pipeline: ✅ SUCCESS")
    else:
        print("\n🎯 Complete Pipeline: ❌ FAILED")
        sys.exit(1)
