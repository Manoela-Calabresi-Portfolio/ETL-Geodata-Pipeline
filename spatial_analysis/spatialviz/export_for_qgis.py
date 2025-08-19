#!/usr/bin/env python3
"""
Export Data for QGIS - Stuttgart Urban Analysis
Exports all layers necessary to recreate the land use and population density maps
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import json
import shutil

# Configuration
DATA_DIR = Path("../../main_pipeline/areas/stuttgart/data_final")
OUTPUT_DIR = Path("outputs/qgis_ready_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def export_districts_with_population():
    """Export districts with population data for population density map"""
    print("🏘️ Exporting districts with population...")
    
    districts_file = DATA_DIR / "districts_with_population.geojson"
    if districts_file.exists():
        districts = gpd.read_file(districts_file)
        
        # Calculate population density
        districts["area_km2"] = districts.geometry.area / 1_000_000
        districts["pop_density"] = districts["pop"] / districts["area_km2"]
        
        # Export to GeoJSON
        output_path = OUTPUT_DIR / "01_districts_population.geojson"
        districts.to_file(output_path, driver="GeoJSON")
        print(f"  ✅ Exported: {output_path}")
        print(f"  📊 Population density range: {districts['pop_density'].min():.0f} - {districts['pop_density'].max():.0f} people/km²")
        
        return output_path
    else:
        print("  ❌ Districts file not found")
        return None

def export_landuse_categorized():
    """Export categorized land use data"""
    print("🌳 Exporting categorized land use...")
    
    landuse_file = DATA_DIR / "processed/landuse_categorized.parquet"
    if landuse_file.exists():
        landuse = gpd.read_parquet(landuse_file)
        
        # Filter out very small areas (< 1000 m²)
        landuse["area_m2"] = landuse.geometry.area
        landuse = landuse[landuse["area_m2"] >= 1000]
        
        # Export to GeoJSON
        output_path = OUTPUT_DIR / "02_landuse_categorized.geojson"
        landuse.to_file(output_path, driver="GeoJSON")
        print(f"  ✅ Exported: {output_path}")
        print(f"  📊 Total areas: {len(landuse)}")
        
        return output_path
    else:
        print("  ❌ Land use file not found")
        return None

def export_roads_categorized():
    """Export categorized roads data"""
    print("🛣️ Exporting categorized roads...")
    
    roads_file = DATA_DIR / "processed/roads_categorized.parquet"
    if roads_file.exists():
        roads = gpd.read_parquet(roads_file)
        
        # Export to GeoJSON
        output_path = OUTPUT_DIR / "03_roads_categorized.geojson"
        roads.to_file(output_path, driver="GeoJSON")
        print(f"  ✅ Exported: {output_path}")
        print(f"  📊 Total road segments: {len(roads)}")
        
        return output_path
    else:
        print("  ❌ Roads file not found")
        return None

def export_pt_stops_categorized():
    """Export categorized PT stops data"""
    print("🚌 Exporting categorized PT stops...")
    
    pt_stops_file = DATA_DIR / "processed/pt_stops_categorized.parquet"
    if pt_stops_file.exists():
        pt_stops = gpd.read_parquet(pt_stops_file)
        
        # Export to GeoJSON
        output_path = OUTPUT_DIR / "04_pt_stops_categorized.geojson"
        pt_stops.to_file(output_path, driver="GeoJSON")
        print(f"  📊 Total PT stops: {len(pt_stops)}")
        
        return output_path
    else:
        print("  ❌ PT stops file not found")
        return None

def export_city_boundary():
    """Export city boundary for reference"""
    print("🏙️ Exporting city boundary...")
    
    districts_file = DATA_DIR / "districts_with_population.geojson"
    if districts_file.exists():
        districts = gpd.read_file(districts_file)
        
        # Create city boundary from districts union
        city_boundary = districts.unary_union
        city_boundary_gdf = gpd.GeoDataFrame(geometry=[city_boundary])
        
        # Export to GeoJSON
        output_path = OUTPUT_DIR / "05_city_boundary.geojson"
        city_boundary_gdf.to_file(output_path, driver="GeoJSON")
        print(f"  ✅ Exported: {output_path}")
        
        return output_path
    else:
        print("  ❌ Districts file not found")
        return None

def create_qgis_project_config():
    """Create QGIS project configuration file"""
    print("🗺️ Creating QGIS project configuration...")
    
    config = {
        "project_name": "Stuttgart Urban Analysis - QGIS",
        "description": "Complete dataset to recreate land use and population density maps",
        "crs": "EPSG:4326",
        "layers": [
            {
                "name": "01 - Districts with Population",
                "file": "01_districts_population.geojson",
                "type": "polygon",
                "description": "Administrative districts with population data for density mapping",
                "style_suggestions": {
                    "population_density": {
                        "type": "graduated",
                        "column": "pop_density",
                        "colors": "YlOrRd",
                        "classes": 5,
                        "mode": "quantile"
                    }
                }
            },
            {
                "name": "02 - Land Use Categories",
                "file": "02_landuse_categorized.geojson",
                "type": "polygon",
                "description": "Categorized land use areas (forest, residential, industrial, etc.)",
                "style_suggestions": {
                    "landuse": {
                        "type": "categorized",
                        "column": "landuse",
                        "colors": {
                            "forest": "#4A5D4A",
                            "farmland": "#7FB069",
                            "residential": "#F5F5DC",
                            "industrial": "#D3D3D3",
                            "commercial": "#FFB6C1"
                        }
                    }
                }
            },
            {
                "name": "03 - Road Network",
                "file": "03_roads_categorized.geojson",
                "type": "line",
                "description": "Categorized road network",
                "style_suggestions": {
                    "color": "#8B7355",
                    "width": 0.5,
                    "alpha": 0.3
                }
            },
            {
                "name": "04 - PT Stops",
                "file": "04_pt_stops_categorized.geojson",
                "type": "point",
                "description": "Public transport stops",
                "style_suggestions": {
                    "color": "#C3423F",
                    "size": 3,
                    "alpha": 0.8
                }
            },
            {
                "name": "05 - City Boundary",
                "file": "05_city_boundary.geojson",
                "type": "polygon",
                "description": "City boundary for reference and clipping",
                "style_suggestions": {
                    "fill": "transparent",
                    "border": "#666666",
                    "width": 3,
                    "alpha": 0.4
                }
            }
        ],
        "map_templates": [
            {
                "name": "Land Use Map",
                "description": "Land use + Roads + PT stops",
                "layers_order": [
                    "01 - Districts with Population",
                    "02 - Land Use Categories", 
                    "03 - Road Network",
                    "04 - PT Stops",
                    "05 - City Boundary"
                ],
                "title": "Stuttgart — Land Use + Roads + PT Stops",
                "subtitle": "Stuttgart — Flächennutzung + Straßen + ÖPNV-Haltestellen"
            },
            {
                "name": "Population Density Map",
                "description": "Population density + Roads + PT stops",
                "layers_order": [
                    "01 - Districts with Population",
                    "03 - Road Network",
                    "04 - PT Stops",
                    "05 - City Boundary"
                ],
                "title": "Stuttgart — Population Density + Roads + PT Stops",
                "subtitle": "Stuttgart — Bevölkerungsdichte + Straßen + ÖPNV-Haltestellen"
            }
        ]
    }
    
    config_file = OUTPUT_DIR / "qgis_project_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ QGIS config saved: {config_file}")
    return config_file

def create_import_instructions():
    """Create detailed import instructions for QGIS"""
    print("📝 Creating QGIS import instructions...")
    
    instructions = """# QGIS Import Instructions - Stuttgart Urban Analysis

## 🗺️ How to Import in QGIS:

### 1. Open QGIS and Create New Project
- File → New Project
- Save project as: `stuttgart_urban_analysis.qgz`

### 2. Import Layers (in this order):
1. **01_districts_population.geojson** - Districts with population
2. **02_landuse_categorized.geojson** - Land use categories  
3. **03_roads_categorized.geojson** - Road network
4. **04_pt_stops_categorized.geojson** - PT stops
5. **05_city_boundary.geojson** - City boundary

### 3. Set CRS
- When prompted, set CRS to: **EPSG:4326 (WGS84)**

### 4. Style the Population Density Map:
- Select **01_districts_population** layer
- Right-click → Properties → Symbology
- Change to: **Graduated**
- Column: **pop_density**
- Color ramp: **YlOrRd** (Yellow-Orange-Red)
- Classes: **5**
- Mode: **Quantile**

### 5. Style the Land Use Map:
- Select **02_landuse_categorized** layer
- Right-click → Properties → Symbology
- Change to: **Categorized**
- Column: **landuse**
- Set colors manually:
  - Forest: #4A5D4A (Dark green)
  - Farmland: #7FB069 (Medium green)
  - Residential: #F5F5DC (Light beige)
  - Industrial: #D3D3D3 (Light gray)
  - Commercial: #FFB6C1 (Light pink)

### 6. Style Roads:
- Select **03_roads_categorized** layer
- Color: #8B7355 (Brown)
- Width: 0.5
- Transparency: 70%

### 7. Style PT Stops:
- Select **04_pt_stops_categorized** layer
- Color: #C3423F (Red)
- Size: 3
- Transparency: 20%

### 8. Style City Boundary:
- Select **05_city_boundary** layer
- Fill: Transparent
- Border: #666666 (Gray)
- Width: 3
- Transparency: 60%

## 🎯 Map Templates:

### Template 1: Land Use Map
- **Background:** Land use categories
- **Overlay:** Roads + PT stops
- **Title:** "Stuttgart — Land Use + Roads + PT Stops"

### Template 2: Population Density Map  
- **Background:** Population density (graduated colors)
- **Overlay:** Roads + PT stops
- **Title:** "Stuttgart — Population Density + Roads + PT Stops"

## 💡 Tips:
- Use **Layer Properties** → **Symbology** for styling
- **Save project** frequently
- **Export maps** as PNG/PDF when ready
- Use **Print Layout** for final map composition
"""
    
    instructions_file = OUTPUT_DIR / "QGIS_IMPORT_INSTRUCTIONS.md"
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print(f"  ✅ Instructions saved: {instructions_file}")
    return instructions_file

def main():
    """Main export function"""
    print("🚀 Exporting Data for QGIS...")
    print("=" * 60)
    
    # Export all layers
    exported_files = []
    
    exported_files.append(export_districts_with_population())
    exported_files.append(export_landuse_categorized())
    exported_files.append(export_roads_categorized())
    exported_files.append(export_pt_stops_categorized())
    exported_files.append(export_city_boundary())
    
    # Create QGIS project configuration
    config_file = create_qgis_project_config()
    
    # Create import instructions
    instructions_file = create_import_instructions()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 QGIS Export Complete!")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"🗺️ Layers exported: {len([f for f in exported_files if f is not None])}")
    print(f"📋 QGIS config: {config_file}")
    print(f"📖 Instructions: {instructions_file}")
    print("\n💡 Ready to import into QGIS!")
    print("💡 Check QGIS_IMPORT_INSTRUCTIONS.md for detailed steps")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    main()

