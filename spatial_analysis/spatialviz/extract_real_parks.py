import geopandas as gpd
import pandas as pd
from pathlib import Path
import os

# Load Stuttgart data
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
PROCESSED_DIR = DATA_DIR / "processed"
STAGING_DIR = DATA_DIR / "staging"
PLOT_CRS = "EPSG:3857"

print("🏞️ Extracting real parks from OSM data...")

# First, let's check if we can access the raw OSM file
raw_osm_file = DATA_DIR / "raw" / "baden-wuerttemberg-latest.osm.pbf"
if raw_osm_file.exists():
    print(f"✅ Found raw OSM file: {raw_osm_file}")
    print(f"   Size: {raw_osm_file.stat().st_size / (1024*1024):.1f} MB")
else:
    print(f"❌ Raw OSM file not found: {raw_osm_file}")
    exit(1)

# Check if we have access to osmium or other OSM tools
print(f"\n🔍 Checking for OSM processing tools...")
try:
    import osmium
    print(f"✅ PyOsmium available")
    has_osmium = True
except ImportError:
    print(f"❌ PyOsmium not available - trying alternative approach")
    has_osmium = False

# Alternative approach: Check if we can use GDAL/OGR to read OSM data
try:
    from osgeo import gdal, ogr
    print(f"✅ GDAL/OGR available")
    has_gdal = True
except ImportError:
    print(f"❌ GDAL/OGR not available")
    has_gdal = False

# Let's try to extract parks using available tools
print(f"\n🔍 Attempting to extract parks...")

if has_osmium:
    print(f"  Using PyOsmium to extract parks...")
    try:
        # This would require a more complex implementation with PyOsmium
        print(f"  PyOsmium implementation would go here")
    except Exception as e:
        print(f"  PyOsmium error: {e}")
        has_osmium = False

if has_gdal and not has_osmium:
    print(f"  Using GDAL/OGR to extract parks...")
    try:
        # Extract parks using GDAL/OGR
        print(f"  Extracting parks with GDAL/OGR...")
        
        # Open the OSM file with interleaved reading option
        osm_ds = ogr.Open(str(raw_osm_file), gdal.OF_VECTOR)
        if osm_ds is None:
            print(f"    ❌ Could not open OSM file")
            has_gdal = False
        else:
            print(f"    ✅ Opened OSM file successfully")
            
            # Set interleaved reading option
            osm_ds.SetConfigOption('OGR_INTERLEAVED_READING', 'YES')
            
            # List available layers
            layer_count = osm_ds.GetLayerCount()
            print(f"    Found {layer_count} layers")
            
            for i in range(layer_count):
                layer = osm_ds.GetLayerByIndex(i)
                layer_name = layer.GetName()
                feature_count = layer.GetFeatureCount()
                print(f"      Layer {i}: {layer_name} - {feature_count} features")
                
                # Look for layers that might contain parks
                if "multipolygons" in layer_name.lower() or "polygons" in layer_name.lower():
                    print(f"        Checking {layer_name} for parks...")
                    
                    # Get the schema
                    layer_def = layer.GetLayerDefn()
                    field_count = layer_def.GetFieldCount()
                    print(f"        Fields: {[layer_def.GetFieldDefn(j).GetName() for j in range(field_count)]}")
                    
                    # Look for leisure=park features
                    layer.ResetReading()
                    park_features = []
                    
                    for feature in layer:
                        # Check if this feature has leisure=park
                        leisure_value = feature.GetField("leisure")
                        if leisure_value and "park" in str(leisure_value).lower():
                            # Get the name if available
                            name_value = feature.GetField("name")
                            if name_value:
                                print(f"          Found park: {name_value} (leisure: {leisure_value})")
                            else:
                                print(f"          Found unnamed park (leisure: {leisure_value})")
                            
                            # Get geometry
                            geom = feature.GetGeometryRef()
                            if geom:
                                # Convert to WKT for GeoPandas
                                wkt = geom.ExportToWkt()
                                park_features.append({
                                    'name': name_value or f"Unnamed Park {len(park_features)+1}",
                                    'leisure': leisure_value,
                                    'geometry': wkt
                                })
                    
                    if park_features:
                        print(f"        Found {len(park_features)} parks in {layer_name}")
                        
                        # Convert to GeoDataFrame
                        import shapely.wkt
                        parks_gdf = gpd.GeoDataFrame(park_features)
                        parks_gdf['geometry'] = parks_gdf['geometry'].apply(shapely.wkt.loads)
                        
                        # Set CRS (OSM data is typically EPSG:4326)
                        parks_gdf.set_crs("EPSG:4326", inplace=True)
                        
                        # Transform to plot CRS
                        parks_gdf = parks_gdf.to_crs(PLOT_CRS)
                        
                        # Save parks data
                        parks_output = PROCESSED_DIR / "parks_extracted.parquet"
                        parks_gdf.to_parquet(parks_output)
                        print(f"        ✅ Saved {len(parks_gdf)} parks to {parks_output}")
                        
                        # Show park names
                        print(f"        Park names: {parks_gdf['name'].tolist()}")
                        
                        # Store parks_gdf for later use
                        extracted_parks = parks_gdf
                    else:
                        print(f"        No parks found in {layer_name}")
            
            osm_ds = None  # Close the dataset
            
    except Exception as e:
        print(f"  GDAL/OGR error: {e}")
        has_gdal = False

# If no OSM tools available, let's try to work with what we have
if not has_osmium and not has_gdal:
    print(f"\n🔍 No OSM tools available - trying alternative approach...")
    
    # Check if we can find parks in the existing data by looking for patterns
    print(f"  Checking existing data for park-like areas...")
    
    # Load all available data
    try:
        landuse = gpd.read_parquet(PROCESSED_DIR / "landuse_categorized.parquet")
        landuse = landuse.to_crs(PLOT_CRS)
        print(f"  ✅ Loaded landuse: {len(landuse)} areas")
        
        amenities = gpd.read_parquet(PROCESSED_DIR / "amenities_categorized.parquet")
        amenities = amenities.to_crs(PLOT_CRS)
        print(f"  ✅ Loaded amenities: {len(amenities)} areas")
        
        buildings = gpd.read_parquet(PROCESSED_DIR / "buildings_categorized.parquet")
        buildings = buildings.to_crs(PLOT_CRS)
        print(f"  ✅ Loaded buildings: {len(buildings)} areas")
        
    except Exception as e:
        print(f"  ❌ Error loading data: {e}")
        exit(1)
    
    # Look for any areas that might be parks based on existing tags
    print(f"\n🔍 Searching for park-like areas in existing data...")
    
    # Check amenities for recreation-related areas
    if "category" in amenities.columns and "recreation" in amenities["category"].values:
        recreation_areas = amenities[amenities["category"] == "recreation"]
        print(f"  Found {len(recreation_areas)} recreation areas")
        
        # Check if any of these have names
        if "name" in recreation_areas.columns:
            named_recreation = recreation_areas[recreation_areas["name"].notna()]
            print(f"  Found {len(named_recreation)} named recreation areas")
            if len(named_recreation) > 0:
                print(f"    Names: {named_recreation['name'].unique()}")
    
    # Check for any areas with park-related names in any dataset
    print(f"\n🔍 Searching for park-related names across all datasets...")
    
    for dataset_name, dataset in [("Landuse", landuse), ("Amenities", amenities), ("Buildings", buildings)]:
        name_columns = [col for col in dataset.columns if 'name' in col.lower()]
        if name_columns:
            print(f"  {dataset_name} has name columns: {name_columns}")
            for col in name_columns:
                # Look for park-related names
                park_keywords = ["park", "garten", "garden", "schloss", "rosenstein", "recreation", "leisure"]
                for keyword in park_keywords:
                    matches = dataset[dataset[col].str.contains(keyword, case=False, na=False)]
                    if len(matches) > 0:
                        print(f"    Found '{keyword}' in {col}: {len(matches)} areas")
                        if len(matches) <= 10:
                            print(f"      Names: {matches[col].unique()}")

print(f"\n💡 To get real parks like Schlossgarten and Rosenstein, we need to:")
print(f"  1. Install PyOsmium: pip install osmium")
print(f"  2. Extract leisure=park areas from the raw OSM file")
print(f"  3. Preserve names and geometry during extraction")
print(f"  4. Integrate with the existing mapping pipeline")
