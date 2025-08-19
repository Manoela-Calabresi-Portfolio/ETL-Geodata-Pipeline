import geopandas as gpd
import pandas as pd
from pathlib import Path
import os

# Load Stuttgart data
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
PROCESSED_DIR = DATA_DIR / "processed"
STAGING_DIR = DATA_DIR / "staging"
PLOT_CRS = "EPSG:3857"

print("📁 Loading Stuttgart data...")

# Check all available files in each directory
print("\n🔍 Checking all available files...")

# List all files in processed directory
print(f"\n📁 Processed directory files:")
processed_files = list(PROCESSED_DIR.glob("*.parquet"))
for file in processed_files:
    print(f"  - {file.name}")

# List all files in staging directory
print(f"\n📁 Staging directory files:")
staging_files = list(STAGING_DIR.glob("*.parquet"))
for file in staging_files:
    print(f"  - {file.name}")

# Load all available data files
print("\n🔍 Loading and analyzing all data files...")

# 1. Landuse (processed)
try:
    landuse = gpd.read_parquet(PROCESSED_DIR / "landuse_categorized.parquet")
    landuse = landuse.to_crs(PLOT_CRS)
    print(f"✅ Landuse (processed): {len(landuse)} areas")
except Exception as e:
    print(f"❌ Landuse error: {e}")
    landuse = None

# 2. Landuse (staging - original OSM data)
try:
    osm_landuse = gpd.read_parquet(STAGING_DIR / "osm_landuse.parquet")
    osm_landuse = osm_landuse.to_crs(PLOT_CRS)
    print(f"✅ Landuse (staging/OSM): {len(osm_landuse)} areas")
except Exception as e:
    print(f"❌ OSM Landuse error: {e}")
    osm_landuse = None

# 3. Amenities
try:
    amenities = gpd.read_parquet(PROCESSED_DIR / "amenities_categorized.parquet")
    amenities = amenities.to_crs(PLOT_CRS)
    print(f"✅ Amenities: {len(amenities)} areas")
except Exception as e:
    print(f"❌ Amenities error: {e}")
    amenities = None

# 4. Buildings
try:
    buildings = gpd.read_parquet(PROCESSED_DIR / "buildings_categorized.parquet")
    buildings = buildings.to_crs(PLOT_CRS)
    print(f"✅ Buildings: {len(buildings)} areas")
except Exception as e:
    print(f"❌ Buildings error: {e}")
    buildings = None

# Check for parks in each dataset
print(f"\n🔍 Looking for parks in each dataset...")

# Check OSM landuse (staging) - THIS IS WHERE PARKS SHOULD BE!
if osm_landuse is not None:
    print(f"\n🏞️ OSM Landuse (staging) - THIS IS THE KEY FILE!")
    print(f"  Columns: {osm_landuse.columns.tolist()}")
    
    # Check for leisure column (where parks are typically stored in OSM)
    if "leisure" in osm_landuse.columns:
        leisure_types = osm_landuse["leisure"].value_counts()
        print(f"  Leisure types: {leisure_types.to_dict()}")
        
        # Look for park-related leisure
        park_leisure = {k: v for k, v in leisure_types.items() if 'park' in str(k).lower()}
        if park_leisure:
            print(f"  Park-related leisure: {park_leisure}")
        else:
            print(f"  No park-related leisure found")
    
    # Check for landuse column
    if "landuse" in osm_landuse.columns:
        landuse_types = osm_landuse["landuse"].value_counts()
        print(f"  Landuse types: {landuse_types.to_dict()}")
        
        # Look for recreation-related landuse
        recreation_landuse = {k: v for k, v in landuse_types.items() if 'recreation' in str(k).lower() or 'leisure' in str(k).lower()}
        if recreation_landuse:
            print(f"  Recreation-related landuse: {recreation_landuse}")
        else:
            print(f"  No recreation-related landuse found")
    
    # Check for name column
    if "name" in osm_landuse.columns:
        print(f"  Name column found! Checking for park names...")
        unique_names = osm_landuse["name"].dropna().unique()
        if len(unique_names) <= 50:
            print(f"    All names: {unique_names}")
        else:
            print(f"    Total names: {len(unique_names)} (showing first 50)")
            print(f"      {unique_names[:50]}")
        
        # Look specifically for Schlossgarten and Rosenstein
        schlossgarten = osm_landuse[osm_landuse["name"].str.contains("Schlossgarten", case=False, na=False)]
        rosenstein = osm_landuse[osm_landuse["name"].str.contains("Rosenstein", case=False, na=False)]
        
        if len(schlossgarten) > 0:
            print(f"    Found Schlossgarten: {len(schlossgarten)} areas")
            print(f"      Leisure: {schlossgarten['leisure'].unique() if 'leisure' in schlossgarten.columns else 'No leisure col'}")
            print(f"      Landuse: {schlossgarten['landuse'].unique() if 'landuse' in schlossgarten.columns else 'No landuse col'}")
        
        if len(rosenstein) > 0:
            print(f"    Found Rosenstein: {len(rosenstein)} areas")
            print(f"      Leisure: {rosenstein['leisure'].unique() if 'leisure' in rosenstein.columns else 'No leisure col'}")
            print(f"      Landuse: {rosenstein['landuse'].unique() if 'landuse' in rosenstein.columns else 'No landuse col'}")

# Check landuse (processed) for recreation areas
if landuse is not None:
    print(f"\n🏞️ Landuse (processed) - looking for recreation areas:")
    if "landuse" in landuse.columns:
        landuse_types = landuse["landuse"].value_counts()
        print(f"  Landuse types: {landuse_types.to_dict()}")
    
    if "natural" in landuse.columns:
        natural_types = landuse["natural"].value_counts()
        print(f"  Natural types: {natural_types.to_dict()}")
    
    if "category" in landuse.columns:
        category_types = landuse["category"].value_counts()
        print(f"  Category types: {category_types.to_dict()}")

# Check amenities for parks - FOCUS ON RECREATION CATEGORY
if amenities is not None:
    print(f"\n🏞️ Amenities - looking for parks:")
    if "amenity" in amenities.columns:
        amenity_types = amenities["amenity"].value_counts()
        # Look for park-related amenities
        park_amenities = {k: v for k, v in amenity_types.items() if 'park' in str(k).lower()}
        if park_amenities:
            print(f"  Park-related amenities: {park_amenities}")
        else:
            print(f"  No park-related amenities found")
    
    if "category" in amenities.columns:
        amenity_categories = amenities["category"].value_counts()
        print(f"  Amenity categories: {amenity_categories.to_dict()}")
        
        # FOCUS: Check recreation category specifically
        if "recreation" in amenity_categories.index:
            print(f"\n🎯 RECREATION CATEGORY FOUND! Investigating...")
            recreation_amenities = amenities[amenities["category"] == "recreation"]
            print(f"  Total recreation areas: {len(recreation_amenities)}")
            
            if "amenity" in recreation_amenities.columns:
                rec_amenity_types = recreation_amenities["amenity"].value_counts()
                print(f"  Recreation amenity types: {rec_amenity_types.to_dict()}")
            
            # Check for name columns in recreation
            name_columns = [col for col in recreation_amenities.columns if 'name' in col.lower()]
            if name_columns:
                print(f"  Recreation name columns: {name_columns}")
                for col in name_columns:
                    unique_names = recreation_amenities[col].dropna().unique()
                    if len(unique_names) <= 20:
                        print(f"    {col}: {unique_names}")
                    else:
                        print(f"    {col}: {len(unique_names)} values (showing first 20)")
                        print(f"      {unique_names[:20]}")
            
            # Check for leisure column in recreation
            if "leisure" in recreation_amenities.columns:
                leisure_types = recreation_amenities["leisure"].value_counts()
                print(f"  Recreation leisure types: {leisure_types.to_dict()}")
            
            # Check for landuse column in recreation
            if "landuse" in recreation_amenities.columns:
                landuse_types = recreation_amenities["landuse"].value_counts()
                print(f"  Recreation landuse types: {landuse_types.to_dict()}")

# Check buildings for parks
if buildings is not None:
    print(f"\n🏞️ Buildings - looking for parks:")
    if "building" in buildings.columns:
        building_types = buildings["building"].value_counts()
        # Look for park-related buildings
        park_buildings = {k: v for k, v in building_types.items() if 'park' in str(k).lower()}
        if park_buildings:
            print(f"  Park-related buildings: {park_buildings}")
        else:
            print(f"  No park-related buildings found")

# Check for any name columns that might contain park names
print(f"\n🔍 Looking for name columns...")

for dataset_name, dataset in [("Landuse", landuse), ("Amenities", amenities), ("Buildings", buildings)]:
    if dataset is not None:
        name_columns = [col for col in dataset.columns if 'name' in col.lower() or 'title' in col.lower()]
        if name_columns:
            print(f"\n🏷️ {dataset_name} - name columns: {name_columns}")
            for col in name_columns:
                unique_names = dataset[col].dropna().unique()
                if len(unique_names) <= 20:
                    print(f"  {col}: {unique_names}")
                else:
                    print(f"  {col}: {len(unique_names)} values (showing first 10)")
                    print(f"    {unique_names[:10]}")

# Check for leisure or recreation tags
print(f"\n🔍 Looking for leisure/recreation tags...")

for dataset_name, dataset in [("Landuse", landuse), ("Amenities", amenities), ("Buildings", buildings)]:
    if dataset is not None:
        leisure_columns = [col for col in dataset.columns if 'leisure' in col.lower() or 'recreation' in col.lower()]
        if leisure_columns:
            print(f"\n🎯 {dataset_name} - leisure columns: {leisure_columns}")
            for col in leisure_columns:
                unique_values = dataset[col].dropna().unique()
                if len(unique_values) <= 20:
                    print(f"  {col}: {unique_values}")
                else:
                    print(f"  {col}: {len(unique_values)} values (showing first 10)")
                    print(f"    {unique_values[:10]}")

print(f"\n💡 Based on this comprehensive analysis, we need to identify where parks like Schlossgarten and Rosenstein are stored!")
