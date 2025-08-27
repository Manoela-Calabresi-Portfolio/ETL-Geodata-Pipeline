# 📊 Data Layers & Categories

## 🔺 **Overview of Data Processing**

The ETL Geodata Pipeline processes **6 thematic layers** from OpenStreetMap data, applying intelligent categorization to reduce "other" categories from 60,000+ to less than 1%. This intelligent processing transforms raw OSM data into meaningful, categorized datasets ready for urban analysis.

## 🚌 **Public Transport (12 Categories)**

| Category | Count | Description | OSM Tags |
|----------|-------|-------------|----------|
| **bus** | 3,836 | Regular bus stops | `highway=bus_stop` |
| **railway_station** | 816 | Train stations | `railway=station` |
| **railway_platform** | 550 | Train platforms | `railway=platform` |
| **platform** | 350 | General PT platforms | `public_transport=platform` |
| **stop_position** | 2,198 | Stop positions | `public_transport=stop_position` |
| **transport_service** | 157 | Info boards, entrances | `public_transport=*` |
| **taxi** | 130 | Taxi stands | `amenity=taxi` |
| **u_bahn** | 112 | Subway entrances | `railway=subway_entrance` |
| **tram** | 107 | Tram stops | `railway=tram_stop` |
| **bus_station** | 24 | Bus terminals | `amenity=bus_station` |
| **transport_hub** | 15 | Major interchanges | `public_transport=station` |
| **other** | 4 | Unclassified (0.05%) | Unmatched tags |

### **Public Transport Rules File**
```yaml
# pt_stops_comprehensive_rules.yaml
categories:
  bus:
    tags:
      highway: ["bus_stop"]
      public_transport: ["bus_stop"]
  
  railway_station:
    tags:
      railway: ["station"]
      public_transport: ["station"]
  
  railway_platform:
    tags:
      railway: ["platform"]
      public_transport: ["platform"]
  
  # ... additional categories
```

## 🏪 **Amenities (21 Categories)**

| Category | Count | Description | OSM Tags |
|----------|-------|-------------|----------|
| **parking** | 19,850 | Parking spaces & facilities | `amenity=parking` |
| **street_furniture** | 14,379 | Benches, shelters, fountains | `amenity=bench`, `amenity=shelter` |
| **waste_management** | 8,517 | Bins, recycling, disposal | `amenity=waste_basket`, `amenity=recycling` |
| **utilities** | 4,347 | Vending machines, toilets | `amenity=vending_machine`, `amenity=toilets` |
| **food_beverage** | 4,316 | Restaurants, cafes, bars | `amenity=restaurant`, `amenity=cafe` |
| **transport** | 2,125 | Fuel, charging stations | `amenity=fuel`, `amenity=charging_station` |
| **education** | 1,868 | Schools, universities | `amenity=school`, `amenity=university` |
| **public_services** | 1,831 | Libraries, post offices | `amenity=library`, `amenity=post_office` |
| **community** | 1,659 | Places of worship, centers | `amenity=place_of_worship`, `amenity=community_centre` |
| **healthcare** | 1,382 | Hospitals, clinics, pharmacies | `amenity=hospital`, `amenity=clinic` |
| **financial** | 621 | Banks, ATMs | `amenity=bank`, `amenity=atm` |
| **emergency** | 233 | Fire stations, police | `amenity=fire_station`, `amenity=police` |
| **maintenance** | 113 | Repair stations | `amenity=repair` |
| **animal_services** | 91 | Veterinary, shelters | `amenity=veterinary`, `amenity=animal_shelter` |
| **commercial** | 66 | Marketplaces, shops | `amenity=marketplace`, `shop=*` |
| **recreation** | 59 | BBQ, picnic sites | `amenity=bbq`, `leisure=picnic_table` |
| **construction_logistics** | 53 | Loading docks | `amenity=loading_dock` |
| **funeral_services** | 42 | Funeral halls, crematoriums | `amenity=funeral_hall` |
| **research_education** | 8 | Research institutes | `amenity=research_institute` |
| **accommodation** | 5 | Dormitories | `amenity=dormitory` |
| **other** | 522 | Unclassified (0.8%) | Unmatched tags |

### **Amenities Rules File**
```yaml
# amenities_comprehensive_rules.yaml
categories:
  parking:
    tags:
      amenity: ["parking"]
      parking: ["*"]
  
  street_furniture:
    tags:
      amenity: ["bench", "shelter", "drinking_water"]
      leisure: ["picnic_table"]
  
  waste_management:
    tags:
      amenity: ["waste_basket", "recycling", "waste_disposal"]
      waste: ["*"]
  
  # ... additional categories with comprehensive tag coverage
```

## 🏢 **Buildings (8 Categories)**

| Category | Count | Description | OSM Tags |
|----------|-------|-------------|----------|
| **residential** | 141,478 | Houses, apartments | `building=house`, `building=apartments` |
| **transport** | 36,568 | Garages, parking structures | `building=garage`, `building=carport` |
| **commercial** | 7,666 | Offices, retail, industrial | `building=commercial`, `building=retail` |
| **agriculture** | 2,647 | Barns, farm buildings | `building=barn`, `building=farm` |
| **civic** | 1,310 | Schools, hospitals, government | `building=civic`, `building=government` |
| **utility** | 852 | Power, water infrastructure | `building=utility`, `building=industrial` |
| **religious** | 523 | Churches, temples | `building=church`, `building=temple` |
| **other** | 188,975 | Unspecified buildings | `building=yes`, `building=*` |

### **Buildings Rules File**
```yaml
# buildings_rules.yaml
categories:
  residential:
    tags:
      building: ["house", "apartments", "residential", "detached", "semi"]
      residential: ["*"]
  
  transport:
    tags:
      building: ["garage", "carport", "parking", "bus_station"]
      parking: ["*"]
  
  # ... additional categories
```

## 🛣️ **Roads (7 Categories)**

| Category | Count | Description | OSM Tags |
|----------|-------|-------------|----------|
| **service** | 33,128 | Service roads, driveways | `highway=service` |
| **residential** | 27,714 | Residential streets | `highway=residential` |
| **secondary** | 8,029 | Secondary roads | `highway=secondary` |
| **tertiary** | 5,125 | Tertiary roads | `highway=tertiary` |
| **primary** | 1,330 | Primary roads | `highway=primary` |
| **motorway** | 428 | Highways | `highway=motorway` |
| **other** | 866 | Unclassified roads | Unmatched highway types |

### **Roads Rules File**
```yaml
# roads_rules.yaml
categories:
  service:
    tags:
      highway: ["service", "unclassified"]
  
  residential:
    tags:
      highway: ["residential", "living_street"]
  
  secondary:
    tags:
      highway: ["secondary", "secondary_link"]
  
  # ... additional categories
```

## 🌳 **Land Use (4 Categories)**

| Category | Count | Description | OSM Tags |
|----------|-------|-------------|----------|
| **agricultural** | 4,438 | Farmland, crops | `landuse=agricultural`, `landuse=farmland` |
| **green** | 2,459 | Parks, forests | `landuse=recreation_ground`, `natural=forest` |
| **urban** | 1,081 | Residential, commercial | `landuse=residential`, `landuse=commercial` |
| **other** | 4,935 | Mixed/unclassified | Other landuse types |

### **Land Use Rules File**
```yaml
# landuse_rules.yaml
categories:
  agricultural:
    tags:
      landuse: ["agricultural", "farmland", "orchard", "vineyard"]
      natural: ["scrub"]
  
  green:
    tags:
      landuse: ["recreation_ground", "grass", "park"]
      natural: ["forest", "wood", "park"]
      leisure: ["park", "garden"]
  
  # ... additional categories
```

## 🚴 **Cycling Infrastructure (2 Categories)**

| Category | Count | Description | OSM Tags |
|----------|-------|-------------|----------|
| **dedicated_cycleway** | 698 | Dedicated bike paths | `highway=cycleway` |
| **other** | 4,179 | Shared paths, lanes | `highway=path`, `cycleway=lane` |

### **Cycle Rules File**
```yaml
# cycle_rules.yaml
categories:
  dedicated_cycleway:
    tags:
      highway: ["cycleway"]
      cycleway: ["*"]
  
  other:
    tags:
      highway: ["path", "footway"]
      cycleway: ["lane", "shared_lane"]
```

## 🔧 **OSM Filters Configuration**

### **Extraction Filters**
```yaml
# osm_filters.yaml
roads:
  highway: 
    - motorway
    - trunk
    - primary
    - secondary
    - tertiary
    - residential
    - service
    - unclassified

buildings:
  building: ["*"]  # All building types

amenities:
  amenity: ["*"]   # All amenity types
  shop: ["*"]      # All shop types

landuse:
  landuse: ["*"]   # All landuse types
  natural: ["*"]   # Natural features
  leisure: ["*"]   # Leisure areas

public_transport:
  public_transport: ["*"]
  railway: ["*"]
  highway: ["bus_stop"]

cycle_infrastructure:
  highway: ["cycleway", "path", "footway"]
  cycleway: ["*"]
```

### **Tag Filtering Examples**
```yaml
# Specific amenity filtering
amenities_filtered:
  amenity:
    - restaurant
    - cafe
    - school
    - hospital
    - bank
    - post_office
  exclude:
    - amenity: ["waste_basket"]  # Exclude specific types
```

## 📊 **Data Quality Metrics**

### **Categorization Success Rates**
- **Amenities**: 99.2% categorized (522 "other" out of 62,087)
- **PT Stops**: 99.995% categorized (4 "other" out of 8,299)
- **Buildings**: 50.3% categorized (functional categories only)
- **Roads**: 98.9% categorized (866 "other" out of 76,620)
- **Land Use**: 85.2% categorized (4,935 "other" out of 31,913)

### **Data Processing Statistics**
- **Total Features**: 544,815 across all layers
- **Processing Time**: ~25-30 minutes for Stuttgart
- **Memory Usage**: 2-4 GB peak during building processing
- **Output Formats**: Parquet, GeoJSON, GPKG

## 🗂️ **Rules File Structure**

### **Standard Rules File Format**
```yaml
# layer_rules.yaml
layer_name: "amenities"
version: "1.0"
description: "Comprehensive amenity categorization rules"

categories:
  category_name:
    description: "Human-readable description"
    tags:
      primary_tag: ["value1", "value2"]
      secondary_tag: ["value3", "value4"]
    exclude:
      tag: ["excluded_value"]
    priority: 1  # Higher numbers = higher priority

metadata:
  author: "Urban Analysis Team"
  created: "2025-08-27"
  last_updated: "2025-08-27"
  data_source: "OpenStreetMap"
```

### **Rules File Locations**
```
pipeline/config/
├── amenities_comprehensive_rules.yaml
├── buildings_rules.yaml
├── cycle_rules.yaml
├── landuse_rules.yaml
├── osm_filters.yaml
├── pt_stops_comprehensive_rules.yaml
└── roads_rules.yaml
```

## 🔄 **Data Processing Pipeline**

### **Step 1: OSM Data Extraction**
```python
from spatial_analysis_core import DataLoader

loader = DataLoader()
gdf = loader.extract_osm_layers(
    pbf_file="city.osm.pbf",
    bbox=(min_lon, min_lat, max_lon, max_lat),
    output_name="city_layers",
    layers=["amenities", "buildings", "roads", "landuse"]
)
```

### **Step 2: Category Application**
```python
# Load rules
with open("pipeline/config/amenities_comprehensive_rules.yaml", 'r') as f:
    rules = yaml.safe_load(f)

# Apply categorization
categorized_gdf = apply_categorization_rules(gdf, rules)
```

### **Step 3: Data Validation**
```python
# Validate categorization results
validation_results = validate_categorization(categorized_gdf, rules)

# Generate quality report
quality_report = generate_quality_report(validation_results)
```

## 📈 **Performance Optimization**

### **Memory Management**
- **Chunked Processing**: Process large datasets in chunks
- **Efficient Data Types**: Use appropriate data types for memory optimization
- **Garbage Collection**: Explicit memory cleanup for large operations

### **Processing Speed**
- **Parallel Processing**: Multi-core processing for independent operations
- **Vectorized Operations**: Use pandas/geopandas vectorized functions
- **Efficient Filtering**: Optimize OSM tag filtering for speed

### **Storage Optimization**
- **Compression**: Use compressed formats (Parquet) for storage
- **Indexing**: Create spatial and attribute indexes for fast queries
- **Partitioning**: Partition data by categories or geographic regions

---

## 🔗 **Related Documentation**

- **[Architecture Overview](architecture.md)** - System design and structure
- **[Database Integration](database.md)** - Database setup and storage
- **[Multi-City Support](multi_city.md)** - Pipeline execution and city management
- **[Main Project](../README.md)** - Project overview and quick start

---

*Last Updated: 2025-08-27 - Data Layers Documentation Version 1.0.0*
