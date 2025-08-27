# 🏙️ Multi-City Support

## 🔺 **Legacy vs New System**

### **Legacy System (DEPRECATED)**
The original system was built around a single pipeline approach with hardcoded city parameters and limited scalability.

#### **Legacy Structure**
```
pipeline/                    # 🔻 Single pipeline approach
├── config/                 # Global configuration
├── scripts/                # City-agnostic scripts
├── areas/                  # City-specific parameters
│   └── stuttgart.yaml      # Hardcoded city config
└── data_final/             # Single data structure
    └── stuttgart/          # City-specific data
```

#### **Legacy Limitations**
- **Single Pipeline**: All cities processed through same pipeline
- **Hardcoded Parameters**: City-specific logic embedded in scripts
- **Limited Scalability**: Adding new cities required code changes
- **Data Isolation**: All city data in single structure
- **Maintenance Overhead**: Changes affected all cities

### **New System (ACTIVE)**
The new system implements a **city-centric architecture** with shared core components and city-specific analysis modules.

#### **New Structure**
```
cities/                     # 🟪 City-centric architecture
├── _template/              # 🟪 Template for new cities
├── stuttgart/              # 🟨 Stuttgart module
├── curitiba/               # 🟨 Curitiba module
└── {new_city}/             # 🟨 Easy addition of new cities

spatial_analysis_core/      # 🔺 Shared core components
├── database/               # Database management
├── data_loader.py          # OSM data extraction
└── utils/                  # Shared utilities
```

#### **New System Benefits**
- **City-Centric**: Each city has its own analysis module
- **Template-Based**: New cities added using templates
- **Shared Infrastructure**: Common database and utilities
- **Independent Development**: Cities can evolve independently
- **Easy Maintenance**: Changes isolated to specific cities

## 🚀 **3-Stage Analysis Pipeline**

### **Pipeline Overview**
The multi-city analysis pipeline consists of three main stages that work together to process geospatial data and generate standardized KPIs across multiple cities.

```
Stage 1: Data Collection → Stage 2: KPI Calculation → Stage 3: Visualization
    ↓                           ↓                        ↓
OSM + GTFS + Boundaries    Transport + Walkability    Maps + Rankings + Dashboards
```

### **Stage 1: Data Collection** 🟣
**Purpose**: Collect and process raw geospatial data from multiple sources

#### **Data Sources**
- **OpenStreetMap (OSM)**: Infrastructure, amenities, buildings, roads
- **GTFS Data**: Public transport schedules and routes
- **Administrative Boundaries**: City districts and neighborhoods
- **External APIs**: City-specific data sources (e.g., GeoCuritiba)

#### **Processing Steps**
```python
# Example: Data collection for any city
from spatial_analysis_core import DataLoader

def collect_city_data(city_name, bbox, osm_pbf_path):
    loader = DataLoader()
    
    # Extract OSM layers
    layers = loader.extract_osm_layers(
        pbf_file=osm_pbf_path,
        bbox=bbox,
        output_name=f"{city_name}_layers"
    )
    
    # Process GTFS data (if available)
    gtfs_data = process_gtfs_data(city_name)
    
    # Load administrative boundaries
    boundaries = load_city_boundaries(city_name)
    
    return {
        'osm_layers': layers,
        'gtfs_data': gtfs_data,
        'boundaries': boundaries
    }
```

#### **Output Data**
- **Staged OSM Layers**: Raw extracted data in standardized format
- **Processed GTFS**: Cleaned and validated transport data
- **Boundary Data**: Administrative and analysis boundaries
- **Metadata**: Data lineage and quality information

### **Stage 2: KPI Calculation** 🟪
**Purpose**: Calculate standardized urban development indicators

#### **Transport KPIs**
- **Public Transport Accessibility**: Distance to nearest PT stop
- **Line Diversity**: Number of different transport lines
- **Frequency**: Service frequency at stops
- **Connectivity**: Network connectivity measures

#### **Walkability KPIs**
- **Intersection Density**: Street network connectivity
- **POI Accessibility**: Distance to points of interest
- **Sidewalk Coverage**: Pedestrian infrastructure
- **Safety Measures**: Crosswalks, traffic signals

#### **Green Space KPIs**
- **Green Space Access**: Distance to parks and gardens
- **Green Coverage**: Percentage of green area
- **Quality Metrics**: Size and amenities of green spaces
- **Connectivity**: Green space network connectivity

#### **Calculation Example**
```python
def calculate_city_kpis(city_data, city_name):
    """Calculate standardized KPIs for any city"""
    
    # Transport accessibility
    transport_kpis = calculate_transport_accessibility(
        city_data['osm_layers']['public_transport'],
        city_data['boundaries']
    )
    
    # Walkability scores
    walkability_kpis = calculate_walkability_scores(
        city_data['osm_layers']['roads'],
        city_data['osm_layers']['amenities'],
        city_data['boundaries']
    )
    
    # Green space access
    green_kpis = calculate_green_space_access(
        city_data['osm_layers']['landuse'],
        city_data['boundaries']
    )
    
    return {
        'transport': transport_kpis,
        'walkability': walkability_kpis,
        'green_space': green_kpis,
        'city_name': city_name,
        'calculation_date': datetime.now()
    }
```

### **Stage 3: Visualization** 🟣
**Purpose**: Generate maps, rankings, and interactive dashboards

#### **Output Types**
- **Static Maps**: High-quality PNG maps for reports
- **Interactive Dashboards**: Web-based exploration tools
- **Ranking Tables**: Comparative analysis across districts
- **Time Series**: Historical development trends

#### **Visualization Example**
```python
def generate_city_visualizations(kpis, city_name):
    """Generate comprehensive visualizations for any city"""
    
    # Create district ranking map
    ranking_map = create_ranking_map(
        kpis['walkability'],
        title=f"{city_name} Walkability Rankings"
    )
    
    # Generate interactive dashboard
    dashboard = create_interactive_dashboard(
        kpis,
        city_name=city_name
    )
    
    # Export results
    export_results(kpis, city_name)
    
    return {
        'ranking_map': ranking_map,
        'dashboard': dashboard
    }
```

## 🏙️ **Multi-City Support**

### **Current Cities**

#### **Stuttgart, Germany** ✅ **Complete Analysis Pipeline**
- **Status**: Production-ready with comprehensive analysis
- **Data**: 544,815 features across 6 layers
- **Analysis**: 23 Stadtbezirke with mobility metrics
- **Outputs**: Enhanced maps and interactive dashboards
- **Performance**: 99%+ categorization success rate

#### **Curitiba, Brazil** ✅ **Fully Operational**
- **Status**: Complete pipeline tested and operational
- **Data**: Ready for OSM extraction (Paraná state PBF)
- **Analysis**: BRT system and green infrastructure focus
- **Integration**: GeoCuritiba ArcGIS services connected
- **Testing**: 5/5 tests passing

### **Future Cities (Template Ready)**

#### **Paris, France** 🟨 **Ready for Implementation**
```yaml
# cities/paris/config/city.yaml
city:
  name: "Paris"
  country: "France"
  bbox: [2.2, 48.8, 2.5, 48.9]
  crs_storage: "EPSG:4326"
  crs_analysis: "EPSG:2154"  # Lambert-93
  osm_pbf: "data/raw/ile-de-france-latest.osm.pbf"
  analysis_focus: ["walkability", "public_transport", "cultural_heritage"]
```

#### **Berlin, Germany** 🟨 **Ready for Implementation**
```yaml
# cities/berlin/config/city.yaml
city:
  name: "Berlin"
  country: "Germany"
  bbox: [13.0, 52.4, 13.8, 52.6]
  crs_storage: "EPSG:4326"
  crs_analysis: "EPSG:25833"  # ETRS89 / UTM zone 33N
  osm_pbf: "data/raw/berlin-latest.osm.pbf"
  analysis_focus: ["mobility", "green_infrastructure", "urban_development"]
```

### **City Template Structure**
```
cities/_template/
├── config/                     # 🟪 Configuration templates
│   ├── city.yaml              # City parameters
│   ├── districts.yaml          # Administrative boundaries
│   ├── analysis.yaml           # Analysis settings
│   └── database.yaml           # Database connection
├── spatial_analysis/           # 🟪 Analysis templates
│   ├── scripts/                # Analysis script templates
│   ├── templates/               # Analysis templates
│   └── utils/                   # Utility templates
└── README.md.template          # Documentation template
```

## 🔄 **Pipeline Execution**

### **Single City Execution**
```bash
# Test city integration
python cities/{city_name}/spatial_analysis/test_{city_name}_pipeline.py

# Run full analysis pipeline
python cities/{city_name}/spatial_analysis/run_analysis.py

# Generate visualizations
python cities/{city_name}/spatial_analysis/generate_maps.py
```

### **Multi-City Batch Processing**
```python
# Process multiple cities simultaneously
from pathlib import Path
import subprocess

def process_multiple_cities(city_list):
    """Process multiple cities in parallel"""
    
    processes = []
    for city in city_list:
        # Start analysis for each city
        cmd = f"python cities/{city}/spatial_analysis/run_analysis.py"
        process = subprocess.Popen(cmd, shell=True)
        processes.append((city, process))
    
    # Wait for all processes to complete
    for city, process in processes:
        process.wait()
        print(f"✅ {city} analysis completed")

# Example usage
cities = ["stuttgart", "curitiba", "paris"]
process_multiple_cities(cities)
```

### **Cross-City Comparison**
```python
def compare_cities(city_list):
    """Generate comparative analysis across cities"""
    
    all_kpis = {}
    
    # Collect KPIs from all cities
    for city in city_list:
        kpis = load_city_kpis(city)
        all_kpis[city] = kpis
    
    # Generate comparative metrics
    comparison = generate_city_comparison(all_kpis)
    
    # Create comparison visualizations
    comparison_map = create_comparison_map(comparison)
    ranking_table = create_ranking_table(comparison)
    
    return {
        'comparison': comparison,
        'map': comparison_map,
        'table': ranking_table
    }
```

## 📊 **Standardized Metrics**

### **Transport Metrics**
| Metric | Description | Unit | Target |
|--------|-------------|------|--------|
| **PT Accessibility** | Distance to nearest PT stop | meters | < 300m |
| **Line Diversity** | Number of different lines | count | > 3 |
| **Service Frequency** | Buses per hour | per hour | > 10 |
| **Network Density** | PT stops per km² | per km² | > 50 |

### **Walkability Metrics**
| Metric | Description | Unit | Target |
|--------|-------------|------|--------|
| **Intersection Density** | Street intersections per km² | per km² | > 100 |
| **POI Accessibility** | Distance to essential services | meters | < 500m |
| **Sidewalk Coverage** | Percentage of streets with sidewalks | % | > 80% |
| **Safety Score** | Crosswalks and traffic signals | score | > 7/10 |

### **Green Space Metrics**
| Metric | Description | Unit | Target |
|--------|-------------|------|--------|
| **Green Access** | Distance to nearest park | meters | < 300m |
| **Green Coverage** | Percentage of green area | % | > 15% |
| **Quality Score** | Park amenities and size | score | > 6/10 |
| **Connectivity** | Green space network density | per km² | > 5 |

## 🔧 **Configuration Management**

### **City Configuration**
```yaml
# cities/{city_name}/config/city.yaml
city:
  name: "City Name"
  country: "Country"
  bbox: [min_lon, min_lat, max_lon, max_lat]
  crs_storage: "EPSG:4326"
  crs_analysis: "EPSG:XXXX"
  osm_pbf: "data/raw/region-latest.osm.pbf"
  
analysis:
  focus_areas: ["mobility", "walkability", "green_infrastructure"]
  custom_metrics: ["brt_accessibility", "cultural_heritage"]
  
database:
  schema_name: "city_name"
  connection_pool: 5
```

### **Analysis Configuration**
```yaml
# cities/{city_name}/config/analysis.yaml
walkability:
  essential_services: ["school", "hospital", "grocery", "pharmacy"]
  max_distance: 500  # meters
  weight_intersections: 0.3
  weight_poi_access: 0.4
  weight_safety: 0.3

transport:
  pt_types: ["bus", "tram", "metro", "train"]
  max_walking_distance: 300  # meters
  frequency_threshold: 10  # per hour
  
green_infrastructure:
  min_park_size: 1000  # square meters
  max_access_distance: 300  # meters
  quality_factors: ["playground", "benches", "paths"]
```

## 🚀 **Scaling to New Cities**

### **Step-by-Step Process**

#### **1. Create City Module**
```bash
# Copy template
cp -r cities/_template cities/your_city_name

# Navigate to city directory
cd cities/your_city_name
```

#### **2. Configure City Parameters**
```bash
# Edit configuration files
nano config/city.yaml
nano config/districts.yaml
nano config/analysis.yaml
```

#### **3. Test Integration**
```bash
# Test database connection
python spatial_analysis_core/database/manage_database.py test-connection

# Test data loader
python spatial_analysis_core/test_data_loader.py --city your_city_name
```

#### **4. Run Analysis**
```bash
# Execute analysis pipeline
python spatial_analysis/run_analysis.py

# Generate visualizations
python spatial_analysis/generate_maps.py
```

### **Validation Checklist**
- ✅ **Database Connection**: PostgreSQL + PostGIS working
- ✅ **Configuration Loading**: City parameters loaded correctly
- ✅ **Data Extraction**: OSM data extracted successfully
- ✅ **KPI Calculation**: Metrics calculated without errors
- ✅ **Visualization**: Maps and dashboards generated
- ✅ **Data Quality**: Results meet quality standards

---

## 🔗 **Related Documentation**

- **[Architecture Overview](architecture.md)** - System design and structure
- **[Database Integration](database.md)** - Database setup and storage
- **[Data Layers](data_layers.md)** - Data processing and categorization
- **[Main Project](../README.md)** - Project overview and quick start

---

*Last Updated: 2025-08-27 - Multi-City Documentation Version 1.0.0*
