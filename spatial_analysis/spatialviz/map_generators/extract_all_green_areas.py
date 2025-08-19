import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path

# Load Stuttgart data
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
PROCESSED_DIR = DATA_DIR / "processed"
PLOT_CRS = "EPSG:3857"

print("🌿 Extracting ALL green areas from OSM...")

# Define Stuttgart area (approximate bounding box)
stuttgart_bbox = [48.7, 48.85, 9.1, 9.3]  # [south, north, west, east]

print(f"🔍 Searching for green areas in Stuttgart: {stuttgart_bbox}")

# Define all the green-related OSM tags we want to capture
green_tags = {
    # Parks and recreation
    'leisure': ['park', 'garden', 'playground', 'sports_centre', 'fitness_centre', 'dog_park'],
    
    # Land use - green areas
    'landuse': ['grass', 'meadow', 'allotments', 'orchard', 'vineyard', 'recreation_ground', 
                'village_green', 'greenfield', 'brownfield', 'flowerbed', 'plant_nursery'],
    
    # Natural features
    'natural': ['grassland', 'heath', 'scrub', 'wood', 'tree_row', 'tree', 'hedge', 'wetland',
                'water', 'spring', 'stream', 'river', 'lake', 'pond'],
    
    # Amenities - green spaces
    'amenity': ['grave_yard', 'cemetery', 'school', 'university', 'college', 'hospital'],
    
    # Buildings with green areas
    'building': ['greenhouse', 'conservatory', 'glasshouse']
}

print(f"🌱 Searching for green areas with tags: {green_tags}")

all_green_areas = []

try:
    # Extract all green areas using OSMnx
    print("  Downloading green areas from OSM...")
    
    for tag_key, tag_values in green_tags.items():
        for tag_value in tag_values:
            print(f"    Searching for {tag_key}={tag_value}...")
            
            try:
                # Get features with this tag
                features = ox.features_from_bbox(
                    bbox=(stuttgart_bbox[2], stuttgart_bbox[0], stuttgart_bbox[3], stuttgart_bbox[1]),
                    tags={tag_key: tag_value}
                )
                
                if len(features) > 0:
                    print(f"      ✅ Found {len(features)} {tag_key}={tag_value}")
                    
                    # Convert to GeoDataFrame if needed
                    if not isinstance(features, gpd.GeoDataFrame):
                        features = gpd.GeoDataFrame(features)
                    
                    # Add tag information
                    features['osm_tag_key'] = tag_key
                    features['osm_tag_value'] = tag_value
                    
                    all_green_areas.append(features)
                    
            except Exception as e:
                print(f"      ❌ Error with {tag_key}={tag_value}: {e}")
    
    if all_green_areas:
        print(f"\n🌿 Combining all green areas...")
        
        # Combine all green areas
        combined_green = pd.concat(all_green_areas, ignore_index=True)
        
        # Remove duplicates based on geometry
        print(f"  Total features found: {len(combined_green)}")
        
        # Set CRS
        combined_green.set_crs("EPSG:4326", inplace=True)
        
        # Transform to plot CRS
        combined_green_plot = combined_green.to_crs(PLOT_CRS)
        
        # Calculate areas and filter out very small ones (< 100 m²)
        combined_green_plot['area_m2'] = combined_green_plot.geometry.area
        
        # Filter out very small areas (shrubs, tiny features)
        min_area = 100  # 100 square meters
        filtered_green = combined_green_plot[combined_green_plot['area_m2'] >= min_area].copy()
        
        print(f"  After filtering small areas (< {min_area} m²): {len(filtered_green)} features")
        
        # Show breakdown by tag
        print(f"\n📊 Green areas breakdown:")
        tag_breakdown = filtered_green.groupby(['osm_tag_key', 'osm_tag_value']).size().sort_values(ascending=False)
        for (key, value), count in tag_breakdown.head(20).items():
            print(f"  {key}={value}: {count} areas")
        
        # Show named areas
        if 'name' in filtered_green.columns:
            named_areas = filtered_green[filtered_green['name'].notna()]
            print(f"\n🏷️ Named green areas: {len(named_areas)}")
            if len(named_areas) > 0:
                # Show first 20 named areas
                for idx, row in named_areas.head(20).iterrows():
                    tag_info = f"{row['osm_tag_key']}={row['osm_tag_value']}"
                    print(f"  - {row['name']} ({tag_info})")
        
        # Save all green areas
        green_output = PROCESSED_DIR / "all_green_areas_osmnx.parquet"
        filtered_green.to_parquet(green_output)
        print(f"\n✅ Saved {len(filtered_green)} green areas to {green_output}")
        
        # Show area statistics
        areas = filtered_green['area_m2']
        print(f"\n📏 Area statistics:")
        print(f"  Min: {areas.min():.0f} m²")
        print(f"  Max: {areas.max():.0f} m²")
        print(f"  Mean: {areas.mean():.0f} m²")
        print(f"  Median: {areas.median():.0f} m²")
        
        # Categorize green areas for mapping
        print(f"\n🎨 Categorizing green areas for mapping...")
        
        # Create categories for different types of green areas
        green_categories = {
            'parks': filtered_green[
                (filtered_green['osm_tag_key'] == 'leisure') & 
                (filtered_green['osm_tag_value'] == 'park')
            ],
            'gardens': filtered_green[
                (filtered_green['osm_tag_key'] == 'leisure') & 
                (filtered_green['osm_tag_value'] == 'garden')
            ],
            'allotments': filtered_green[
                (filtered_green['osm_tag_key'] == 'landuse') & 
                (filtered_green['osm_tag_value'] == 'allotments')
            ],
            'meadows': filtered_green[
                (filtered_green['osm_tag_key'] == 'landuse') & 
                (filtered_green['osm_tag_value'] == 'meadow')
            ],
            'grasslands': filtered_green[
                (filtered_green['osm_tag_key'] == 'natural') & 
                (filtered_green['osm_tag_value'] == 'grassland')
            ],
            'cemeteries': filtered_green[
                (filtered_green['osm_tag_key'] == 'amenity') & 
                (filtered_green['osm_tag_value'] == 'grave_yard')
            ],
            'other_green': filtered_green[
                ~((filtered_green['osm_tag_key'] == 'leisure') & (filtered_green['osm_tag_value'] == 'park')) &
                ~((filtered_green['osm_tag_key'] == 'leisure') & (filtered_green['osm_tag_value'] == 'garden')) &
                ~((filtered_green['osm_tag_key'] == 'landuse') & (filtered_green['osm_tag_value'] == 'allotments')) &
                ~((filtered_green['osm_tag_key'] == 'landuse') & (filtered_green['osm_tag_value'] == 'meadow')) &
                ~((filtered_green['osm_tag_key'] == 'natural') & (filtered_green['osm_tag_value'] == 'grassland')) &
                ~((filtered_green['osm_tag_key'] == 'amenity') & (filtered_green['osm_tag_value'] == 'grave_yard'))
            ]
        }
        
        # Show category breakdown
        print(f"\n🏷️ Green areas by category:")
        for category, data in green_categories.items():
            if len(data) > 0:
                print(f"  {category}: {len(data)} areas")
                if 'name' in data.columns:
                    named_in_category = data[data['name'].notna()]
                    if len(named_in_category) > 0:
                        print(f"    Named examples: {', '.join(named_in_category['name'].head(3).tolist())}")
        
        # Save categorized green areas
        categorized_output = PROCESSED_DIR / "green_areas_categorized.parquet"
        filtered_green.to_parquet(categorized_output)
        print(f"\n✅ Saved categorized green areas to {categorized_output}")
        
    else:
        print(f"❌ No green areas found")
        
except Exception as e:
    print(f"❌ Error extracting green areas: {e}")
    print(f"Error type: {type(e).__name__}")

print(f"\n💡 Next steps:")
print(f"  1. Integrate these green areas into the main map")
print(f"  2. Use different colors for different green categories")
print(f"  3. Ensure no white areas remain on the map")
