#!/usr/bin/env python3
"""
Prepare Data for QGIS using DuckDB
Converts parquet files to GeoJSON and organizes them for QGIS import
"""

import duckdb
import pandas as pd
from pathlib import Path
import json

# Configuration
DATA_DIR = Path("../../../main_pipeline/areas/stuttgart/data_final")
OUTPUT_DIR = Path("../outputs/qgis_ready_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def setup_duckdb():
    """Setup DuckDB with spatial extensions"""
    print("🦆 Setting up DuckDB...")
    
    # Connect to DuckDB
    con = duckdb.connect(':memory:')
    
    # Load spatial extension
    con.execute("INSTALL spatial")
    con.execute("LOAD spatial")
    
    print("✅ DuckDB spatial extension loaded")
    return con

def convert_parquet_to_geojson(con, parquet_path, output_name, geometry_column="geometry"):
    """Convert parquet file to GeoJSON using DuckDB"""
    print(f"🔄 Converting {parquet_path.name} to GeoJSON...")
    
    try:
        # Read parquet file
        df = pd.read_parquet(parquet_path)
        
        # Check if geometry column exists
        if geometry_column not in df.columns:
            print(f"⚠️  No geometry column found in {parquet_path.name}")
            return None
        
        # Convert to DuckDB table
        con.execute("CREATE TABLE temp_data AS SELECT * FROM df")
        
        # Export to GeoJSON
        output_path = OUTPUT_DIR / f"{output_name}.geojson"
        
        # Use DuckDB to export with proper geometry handling
        con.execute(f"""
            COPY (
                SELECT * FROM temp_data 
                WHERE {geometry_column} IS NOT NULL
            ) TO '{output_path}' 
            WITH (FORMAT GDAL, DRIVER 'GeoJSON')
        """)
        
        # Clean up temp table
        con.execute("DROP TABLE temp_data")
        
        print(f"✅ Saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error converting {parquet_path.name}: {e}")
        return None

def prepare_districts_data():
    """Prepare districts data (already in GeoJSON)"""
    print("🏘️ Preparing districts data...")
    
    districts_file = DATA_DIR / "districts_with_population.geojson"
    if districts_file.exists():
        # Copy districts file
        output_path = OUTPUT_DIR / "01_districts.geojson"
        import shutil
        shutil.copy2(districts_file, output_path)
        print(f"✅ Districts copied: {output_path}")
        return output_path
    else:
        print("❌ Districts file not found")
        return None

def create_qgis_project_file():
    """Create a QGIS project file with layer configurations"""
    print("🗺️ Creating QGIS project file...")
    
    project_content = {
        "name": "Stuttgart Urban Analysis",
        "description": "Stuttgart land use, roads, and PT stops analysis",
        "layers": [
            {
                "name": "Districts",
                "file": "01_districts.geojson",
                "type": "polygon",
                "style": "districts_style.qml"
            },
            {
                "name": "Land Use",
                "file": "02_landuse.geojson", 
                "type": "polygon",
                "style": "landuse_style.qml"
            },
            {
                "name": "Roads",
                "file": "03_roads.geojson",
                "type": "line",
                "style": "roads_style.qml"
            },
            {
                "name": "PT Stops",
                "file": "04_pt_stops.geojson",
                "type": "point",
                "style": "pt_stops_style.qml"
            }
        ],
        "crs": "EPSG:4326",
        "extent": [9.0, 48.7, 9.3, 48.8]  # Stuttgart area
    }
    
    project_file = OUTPUT_DIR / "stuttgart_analysis.qgz"
    
    # Note: This creates a JSON config, not actual QGIS project file
    # You'll need to import layers manually in QGIS
    config_file = OUTPUT_DIR / "qgis_config.json"
    with open(config_file, 'w') as f:
        json.dump(project_content, f, indent=2)
    
    print(f"✅ QGIS config saved: {config_file}")
    return config_file

def create_readme():
    """Create a README file with QGIS import instructions"""
    print("📝 Creating README...")
    
    readme_content = """# QGIS Data Preparation

## 📁 Files Ready for QGIS:

### 1. Districts (01_districts.geojson)
- **Type:** Polygon
- **CRS:** EPSG:4326 (WGS84)
- **Content:** Administrative districts with population data

### 2. Land Use (02_landuse.geojson)
- **Type:** Polygon  
- **CRS:** EPSG:4326 (WGS84)
- **Content:** Land use categories (forest, farmland, residential, etc.)

### 3. Roads (03_roads.geojson)
- **Type:** Line
- **CRS:** EPSG:4326 (WGS84)
- **Content:** Road network categorized by type

### 4. PT Stops (04_pt_stops.geojson)
- **Type:** Point
- **CRS:** EPSG:4326 (WGS84)
- **Content:** Public transport stops

## 🗺️ How to Import in QGIS:

1. **Open QGIS**
2. **Add Vector Layer** (Ctrl+Shift+V)
3. **Browse** to each .geojson file
4. **Set CRS** to EPSG:4326 if prompted
5. **Style layers** as desired

## 🎨 Suggested Styling:

### Districts:
- **Fill:** Light blue with transparency
- **Border:** Dark blue, 0.5mm

### Land Use:
- **Forest:** Dark green (#4A5D4A)
- **Farmland:** Medium green (#7FB069)  
- **Residential:** Light yellow (#F5F5DC)
- **Industrial:** Light gray (#D3D3D3)
- **Commercial:** Light pink (#FFB6C1)

### Roads:
- **Color:** Brown (#8B7355)
- **Width:** 0.3mm

### PT Stops:
- **Color:** Red (#C3423F)
- **Size:** 1.5mm

## 💡 Tips:
- Use **Layer Properties** → **Symbology** for styling
- **Save project** as .qgz file
- **Export map** as PNG/PDF when ready
"""
    
    readme_file = OUTPUT_DIR / "README_QGIS.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README created: {readme_file}")

def main():
    """Main function to prepare all data for QGIS"""
    print("🚀 Preparing Data for QGIS...")
    print("=" * 50)
    
    # Setup DuckDB
    con = setup_duckdb()
    
    # Prepare districts (already GeoJSON)
    districts_file = prepare_districts_data()
    
    # Convert parquet files to GeoJSON
    data_files = [
        (DATA_DIR / "processed/landuse_categorized.parquet", "02_landuse"),
        (DATA_DIR / "processed/roads_categorized.parquet", "03_roads"),
        (DATA_DIR / "processed/pt_stops_categorized.parquet", "04_pt_stops"),
    ]
    
    converted_files = []
    for parquet_path, output_name in data_files:
        if parquet_path.exists():
            result = convert_parquet_to_geojson(con, parquet_path, output_name)
            if result:
                converted_files.append(result)
        else:
            print(f"⚠️  File not found: {parquet_path}")
    
    # Create QGIS project config
    project_config = create_qgis_project_file()
    
    # Create README
    create_readme()
    
    # Close DuckDB connection
    con.close()
    
    print("\n" + "=" * 50)
    print("🎉 QGIS Data Preparation Complete!")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"🗺️ Files ready for QGIS: {len(converted_files) + 1}")
    print(f"📖 Check README: {OUTPUT_DIR}/README_QGIS.md")
    print("=" * 50)
    
    return 0

if __name__ == "__main__":
    main()

