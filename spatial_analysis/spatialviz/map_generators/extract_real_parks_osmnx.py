import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path

# Load Stuttgart data
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
PROCESSED_DIR = DATA_DIR / "processed"
PLOT_CRS = "EPSG:3857"

print("🏞️ Extracting real parks from OSM using OSMnx...")

# Define Stuttgart area (approximate bounding box)
# Stuttgart coordinates: approximately 48.7758° N, 9.1829° E
stuttgart_bbox = [48.7, 48.85, 9.1, 9.3]  # [south, north, west, east]

print(f"🔍 Searching for parks in Stuttgart area: {stuttgart_bbox}")

try:
    # Extract parks using OSMnx
    print("  Downloading parks from OSM...")
    
    # Get parks (leisure=park) from the area
    parks_gdf = ox.features_from_bbox(
        bbox=(stuttgart_bbox[2], stuttgart_bbox[0], stuttgart_bbox[3], stuttgart_bbox[1]),  # (west, south, east, north)
        tags={'leisure': 'park'}
    )
    
    if len(parks_gdf) > 0:
        print(f"  ✅ Found {len(parks_gdf)} parks!")
        
        # Convert to GeoDataFrame if it's not already
        if not isinstance(parks_gdf, gpd.GeoDataFrame):
            parks_gdf = gpd.GeoDataFrame(parks_gdf)
        
        # Set CRS to WGS84 (OSM default)
        parks_gdf.set_crs("EPSG:4326", inplace=True)
        
        # Show park names
        if 'name' in parks_gdf.columns:
            named_parks = parks_gdf[parks_gdf['name'].notna()]
            print(f"  Named parks: {len(named_parks)}")
            for idx, row in named_parks.iterrows():
                print(f"    - {row['name']}")
        else:
            print(f"  No name column found in parks data")
        
        # Show all columns
        print(f"  Park data columns: {parks_gdf.columns.tolist()}")
        
        # Transform to plot CRS
        parks_gdf_plot = parks_gdf.to_crs(PLOT_CRS)
        
        # Save parks data
        parks_output = PROCESSED_DIR / "parks_extracted_osmnx.parquet"
        parks_gdf_plot.to_parquet(parks_output)
        print(f"  ✅ Saved {len(parks_gdf_plot)} parks to {parks_output}")
        
        # Show summary
        print(f"\n📊 Parks Summary:")
        print(f"  Total parks: {len(parks_gdf_plot)}")
        print(f"  Named parks: {len(parks_gdf_plot[parks_gdf_plot['name'].notna()])}")
        print(f"  Unnamed parks: {len(parks_gdf_plot[parks_gdf_plot['name'].isna()])}")
        
        # Show some statistics
        if 'area' in parks_gdf_plot.columns:
            areas = parks_gdf_plot['area'].dropna()
            if len(areas) > 0:
                print(f"  Area statistics (m²):")
                print(f"    Min: {areas.min():.0f}")
                print(f"    Max: {areas.max():.0f}")
                print(f"    Mean: {areas.mean():.0f}")
        
        # Store parks for later use
        extracted_parks = parks_gdf_plot
        
    else:
        print(f"  ❌ No parks found in the specified area")
        
        # Try a different approach - search by place name
        print(f"  🔍 Trying alternative approach - searching by place name...")
        
        # Search for Stuttgart
        try:
            stuttgart_parks = ox.features_from_place(
                query="Stuttgart, Germany",
                tags={'leisure': 'park'}
            )
            
            if len(stuttgart_parks) > 0:
                print(f"    ✅ Found {len(stuttgart_parks)} parks in Stuttgart!")
                
                # Convert to GeoDataFrame
                if not isinstance(stuttgart_parks, gpd.GeoDataFrame):
                    stuttgart_parks = gpd.GeoDataFrame(stuttgart_parks)
                
                # Set CRS
                stuttgart_parks.set_crs("EPSG:4326", inplace=True)
                
                # Show park names
                if 'name' in stuttgart_parks.columns:
                    named_parks = stuttgart_parks[stuttgart_parks['name'].notna()]
                    print(f"    Named parks: {len(named_parks)}")
                    for idx, row in named_parks.iterrows():
                        print(f"      - {row['name']}")
                
                # Transform and save
                stuttgart_parks_plot = stuttgart_parks.to_crs(PLOT_CRS)
                parks_output = PROCESSED_DIR / "parks_extracted_stuttgart.parquet"
                stuttgart_parks_plot.to_parquet(parks_output)
                print(f"    ✅ Saved parks to {parks_output}")
                
                # Store parks for later use
                extracted_stuttgart_parks = stuttgart_parks_plot
            else:
                print(f"    ❌ No parks found in Stuttgart")
                
        except Exception as e:
            print(f"    ❌ Error searching by place name: {e}")
        
except Exception as e:
    print(f"  ❌ Error extracting parks: {e}")
    print(f"  Error type: {type(e).__name__}")

print(f"\n💡 If no parks were found, we may need to:")
print(f"  1. Adjust the bounding box coordinates")
print(f"  2. Use different OSM tags (e.g., 'landuse=recreation_ground')")
print(f"  3. Check if the area has parks tagged differently")
print(f"  4. Use a different extraction method")

# Try alternative tags
print(f"\n🔍 Trying alternative OSM tags...")

try:
    # Try recreation_ground
    print(f"  Searching for landuse=recreation_ground...")
    recreation_gdf = ox.features_from_bbox(
        bbox=(stuttgart_bbox[2], stuttgart_bbox[0], stuttgart_bbox[3], stuttgart_bbox[1]),  # (west, south, east, north)
        tags={'landuse': 'recreation_ground'}
    )
    
    if len(recreation_gdf) > 0:
        print(f"    ✅ Found {len(recreation_gdf)} recreation areas!")
        
        # Convert and save
        if not isinstance(recreation_gdf, gpd.GeoDataFrame):
            recreation_gdf = gpd.GeoDataFrame(recreation_gdf)
        recreation_gdf.set_crs("EPSG:4326", inplace=True)
        
        # Show names
        if 'name' in recreation_gdf.columns:
            named_recreation = recreation_gdf[recreation_gdf['name'].notna()]
            print(f"    Named areas: {len(named_recreation)}")
            for idx, row in named_recreation.iterrows():
                print(f"      - {row['name']}")
        
        # Save
        recreation_output = PROCESSED_DIR / "recreation_areas_osmnx.parquet"
        recreation_gdf_plot = recreation_gdf.to_crs(PLOT_CRS)
        recreation_gdf_plot.to_parquet(recreation_output)
        print(f"    ✅ Saved to {recreation_output}")
        
    else:
        print(f"    ❌ No recreation areas found")
        
except Exception as e:
    print(f"    ❌ Error searching recreation areas: {e}")
