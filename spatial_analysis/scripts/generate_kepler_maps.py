#!/usr/bin/env python3
"""
Kepler Maps Generator for Stuttgart
Creates interactive web-based maps using Kepler.gl

Author: Geospatial Data Expert
Purpose: VVS Job Application - Interactive Mobility Analysis
"""

from pathlib import Path
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import json
import warnings
warnings.filterwarnings('ignore')

# Configuration
ROOT = Path("..")  # Go up one level from scripts directory
OUT = ROOT / "areas" / "stuttgart_districts_official" / "outputs" / "kepler"
OUT.mkdir(parents=True, exist_ok=True)

# Data paths
DISTRICTS_GPKG = ROOT / "areas" / "stuttgart_districts_official" / "OpenData_KLGL_GENERALISIERT.gpkg"
OSM_DATA_DIR = ROOT / ".." / "main_pipeline" / "areas" / "stuttgart" / "data_final" / "staging"

def read_gdf(path: Path) -> gpd.GeoDataFrame:
    """Read and prepare GeoDataFrame with proper CRS"""
    if path.suffix == '.gpkg':
        gdf = gpd.read_file(path, layer="KLGL_BRUTTO_STADTBEZIRK")
    else:
        gdf = gpd.read_file(path)
    
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)
    
    return gdf

def compute_green_kpis(districts: gpd.GeoDataFrame, greens: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Compute green space KPIs for each district"""
    print("🌳 Computing green space KPIs...")
    
    # Convert to UTM 32N for accurate area calculations
    d_utm = districts.to_crs(25832).copy()
    g_utm = greens.to_crs(25832).copy()
    
    # Calculate district areas
    d_utm["district_area_m2"] = d_utm.geometry.area
    
    # Spatial join and intersection analysis
    joined = gpd.overlay(g_utm[["geometry"]], d_utm[["geometry", "STADTBEZIRKNAME"]], how="intersection")
    joined["green_area_m2"] = joined.geometry.area
    
    # Aggregate green areas by district
    green_by_dist = joined.groupby("STADTBEZIRKNAME", as_index=False)["green_area_m2"].sum()
    
    # Merge results
    df = d_utm.drop(columns="geometry").merge(green_by_dist, on="STADTBEZIRKNAME", how="left")
    df["green_area_m2"] = df["green_area_m2"].fillna(0)
    df["prop_green_pct"] = (df["green_area_m2"] / df["district_area_m2"] * 100).round(1)
    
    # Prepare output
    d_utm = d_utm.drop(columns=["district_area_m2"])
    out = d_utm.merge(df[["STADTBEZIRKNAME", "green_area_m2", "prop_green_pct"]], on="STADTBEZIRKNAME", how="left")
    
    # Convert back to WGS84
    result = out.to_crs(4326)
    
    # Rename columns for Kepler
    result = result.rename(columns={"STADTBEZIRKNAME": "district_name"})
    
    print(f"✅ Green KPIs computed for {len(result)} districts")
    return result

def prepare_pt_stops() -> gpd.GeoDataFrame:
    """Prepare public transport stops data"""
    print("🚇 Preparing PT stops data...")
    
    pt_file = OSM_DATA_DIR / "osm_pt_stops.parquet"
    if pt_file.exists():
        stops = gpd.read_parquet(pt_file)
        
        # Ensure proper CRS
        if stops.crs.to_epsg() != 4326:
            stops = stops.to_crs(4326)
        
        # Add mode information if not present
        if 'mode' not in stops.columns:
            # Infer mode from public_transport tag
            if 'public_transport' in stops.columns:
                stops['mode'] = stops['public_transport'].fillna('unknown')
            else:
                stops['mode'] = 'pt_stop'
        
        # Add name if not present
        if 'name' not in stops.columns:
            stops['name'] = stops.get('name', 'PT Stop')
        
        print(f"✅ PT stops prepared: {len(stops)} stops")
        return stops
    else:
        print("⚠️ PT stops file not found, creating dummy data")
        # Create dummy PT stops for testing
        dummy_stops = gpd.GeoDataFrame({
            'name': ['U-Bahn Stop', 'S-Bahn Stop', 'Tram Stop', 'Bus Stop'],
            'mode': ['u-bahn', 's-bahn', 'tram', 'bus'],
            'geometry': [
                Point(9.1829, 48.7836),  # Stuttgart Hbf
                Point(9.1900, 48.7850),  # Nearby
                Point(9.1750, 48.7820),  # Nearby
                Point(9.1950, 48.7800)   # Nearby
            ]
        }, crs=4326)
        return dummy_stops

def prepare_green_spaces() -> gpd.GeoDataFrame:
    """Prepare green spaces data"""
    print("🌿 Preparing green spaces data...")
    
    landuse_file = OSM_DATA_DIR / "osm_landuse.parquet"
    if landuse_file.exists():
        landuse = gpd.read_parquet(landuse_file)
        
        # Ensure proper CRS
        if landuse.crs.to_epsg() != 4326:
            landuse = landuse.to_crs(4326)
        
        # Filter for green spaces
        green_types = ['park', 'recreation_ground', 'garden', 'forest', 'grass', 'meadow']
        greens = landuse[landuse['landuse'].isin(green_types)].copy()
        
        # Filter out invalid geometries and ensure only polygons
        greens = greens[greens.geometry.geom_type == 'Polygon'].copy()
        
        # Add required columns
        if 'name' not in greens.columns:
            greens['name'] = greens.get('landuse', 'Green Space')
        if 'type' not in greens.columns:
            greens['type'] = greens['landuse']
        
        # Calculate area
        greens_utm = greens.to_crs(25832)
        greens_utm['area_m2'] = greens_utm.geometry.area
        greens = greens_utm.to_crs(4326)
        
        print(f"✅ Green spaces prepared: {len(greens)} areas")
        return greens
    else:
        print("⚠️ Landuse file not found, creating dummy data")
        # Create dummy green spaces for testing
        dummy_greens = gpd.GeoDataFrame({
            'name': ['Stadtpark', 'Botanical Garden', 'Forest Area'],
            'type': ['park', 'garden', 'forest'],
            'area_m2': [50000, 30000, 100000],
            'geometry': [
                Point(9.1850, 48.7850).buffer(0.002),  # Park
                Point(9.1750, 48.7800).buffer(0.001),  # Garden
                Point(9.1950, 48.7900).buffer(0.003)   # Forest
            ]
        }, crs=4326)
        return dummy_greens

def prepare_walkable_roads() -> gpd.GeoDataFrame:
    """Prepare walkable roads data"""
    print("🚶 Preparing walkable roads data...")
    
    roads_file = OSM_DATA_DIR / "osm_roads.parquet"
    if roads_file.exists():
        roads = gpd.read_parquet(roads_file)
        
        # Ensure proper CRS
        if roads.crs.to_epsg() != 4326:
            roads = roads.to_crs(4326)
        
        # Filter for walkable roads
        walkable_types = ['residential', 'footway', 'pedestrian', 'path', 'service']
        walkable_roads = roads[roads['highway'].isin(walkable_types)].copy()
        
        print(f"✅ Walkable roads prepared: {len(walkable_roads)} segments")
        return walkable_roads
    else:
        print("⚠️ Roads file not found, creating dummy data")
        # Create dummy walkable roads for testing
        dummy_roads = gpd.GeoDataFrame({
            'highway': ['residential', 'footway', 'pedestrian'],
            'geometry': [
                Point(9.1800, 48.7830).buffer(0.001),  # Residential
                Point(9.1850, 48.7850).buffer(0.0005), # Footway
                Point(9.1750, 48.7800).buffer(0.0005)  # Pedestrian
            ]
        }, crs=4326)
        return dummy_roads

def create_walk_buffers(stops: gpd.GeoDataFrame, station_point: Point) -> gpd.GeoDataFrame:
    """Create 500m walk buffers around PT stops near the station"""
    print("🚶 Creating walk buffers...")
    
    # Find stops near Stuttgart Hbf (within ~1km)
    nearby_stops = stops[stops.distance(station_point) < 0.01]
    
    if len(nearby_stops) > 0:
        # Create 500m buffers in UTM coordinates
        stops_utm = nearby_stops.to_crs(25832)
        buffers = stops_utm.buffer(500)
        buffers_gdf = gpd.GeoDataFrame(geometry=buffers, crs=25832)
        
        # Convert back to WGS84
        result = buffers_gdf.to_crs(4326)
        print(f"✅ Walk buffers created: {len(result)} buffers")
        return result
    else:
        print("⚠️ No nearby stops found, creating dummy buffer")
        # Create dummy buffer around station
        station_utm = gpd.GeoDataFrame(geometry=[station_point], crs=4326).to_crs(25832)
        dummy_buffer = station_utm.buffer(500)
        dummy_gdf = gpd.GeoDataFrame(geometry=dummy_buffer, crs=25832)
        return dummy_gdf.to_crs(4326)

def create_station_point() -> gpd.GeoDataFrame:
    """Create Stuttgart Hauptbahnhof point"""
    print("🚉 Creating station point...")
    
    station = gpd.GeoDataFrame({
        'name': ['Stuttgart Hauptbahnhof'],
        'geometry': [Point(9.1829, 48.7836)]
    }, crs=4326)
    
    print("✅ Station point created")
    return station

def generate_kepler_maps():
    """Generate interactive Kepler maps"""
    print("🗺️ Generating interactive Kepler maps...")
    
    try:
        # Load and prepare data
        districts = read_gdf(DISTRICTS_GPKG)
        greens = prepare_green_spaces()
        stops = prepare_pt_stops()
        walk_roads = prepare_walkable_roads()
        station = create_station_point()
        
        # Compute green KPIs
        districts_with_kpis = compute_green_kpis(districts, greens)
        
        # Create walk buffers
        walk_buffers = create_walk_buffers(stops, station.iloc[0].geometry)
        
        # Load Kepler configurations
        with open(ROOT / "kepler_config_stuttgart_macro.json", "r") as f:
            macro_config = json.load(f)
        
        with open(ROOT / "kepler_config_hbf_micro.json", "r") as f:
            micro_config = json.load(f)
        
        # Try to import KeplerGl
        try:
            from keplergl import KeplerGl
            
            # Generate MACRO map
            print("🌍 Creating macro map...")
            macro = KeplerGl(height=720, config=macro_config)
            macro.add_data(data=districts_with_kpis, name="districts")
            macro.add_data(data=greens, name="greenspaces")
            macro.add_data(data=stops, name="stops")
            macro.save_to_html(file_name=str(OUT / "stuttgart_macro_green_pt.html"))
            
            # Generate MICRO map
            print("📍 Creating micro map...")
            micro = KeplerGl(height=720, config=micro_config)
            micro.add_data(data=walk_buffers, name="walk_buffers")
            micro.add_data(data=walk_roads, name="walkable_roads")
            micro.add_data(data=greens, name="greenspaces")
            micro.add_data(data=stops, name="stops")
            micro.add_data(data=station, name="station")
            micro.save_to_html(file_name=str(OUT / "stuttgart_hbf_micro.html"))
            
            print("✅ Kepler maps generated successfully!")
            
        except ImportError:
            print("⚠️ KeplerGl not installed, creating data exports instead...")
            
            # Export data for manual Kepler import
            districts_with_kpis.to_file(OUT / "districts_with_kpis.geojson", driver="GeoJSON")
            greens.to_file(OUT / "green_spaces.geojson", driver="GeoJSON")
            stops.to_file(OUT / "pt_stops.geojson", driver="GeoJSON")
            walk_roads.to_file(OUT / "walkable_roads.geojson", driver="GeoJSON")
            walk_buffers.to_file(OUT / "walk_buffers.geojson", driver="GeoJSON")
            station.to_file(OUT / "stuttgart_hbf.geojson", driver="GeoJSON")
            
            print("✅ Data exported for manual Kepler import")
        
        # Save configurations
        with open(ROOT / "kepler_config_stuttgart_macro.json", "w") as f:
            json.dump(macro_config, f, indent=2)
        
        with open(ROOT / "kepler_config_hbf_micro.json", "w") as f:
            json.dump(micro_config, f, indent=2)
        
        print(f"📁 Output directory: {OUT}")
        
    except Exception as e:
        print(f"❌ Error generating Kepler maps: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Kepler Maps Generator for Stuttgart")
    print("=" * 40)
    
    generate_kepler_maps()
