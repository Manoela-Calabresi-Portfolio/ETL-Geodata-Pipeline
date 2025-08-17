# 🗺️ Kepler Interactive Maps for Stuttgart - VVS Job Application

## 📋 **Project Overview**

This project creates **interactive web-based maps** using **Kepler.gl** for Stuttgart's public transport and green space analysis, specifically designed for a job application at VVS (Stuttgart's public transport company).

## 🎯 **What Was Accomplished**

### ✅ **Files Cleaned Up (Deleted)**
- **Old/duplicate scripts**: `generate_vvs_maps.py`, `test_districts_plot.py`, `test_districts_plot.png`
- **Unused analysis scripts**: `simple_realistic_test.py`, `simple_analysis.py`, `quick_analysis.py`, `create_realistic_boundaries.py`, `create_realistic_districts.py`, `fix_coordinates_stuttgart.py`, `create_detailed_map.py`, `create_thematic_maps.py`, `update_all_maps_realistic.py`, `smoke_test.py`, `fix_scalebar.py`, `test_map.py`, `explore_stuttgart_api.py`, `download_real_boundaries.py`, `1_data_collection.py`
- **Compressed files**: `stuttgart_districts_official.zip`

### 🗺️ **Kepler Interactive Maps Generated**

#### **1. Macro-Level Map: `stuttgart_macro_green_pt.html`**
- **Purpose**: City-wide analysis showing all 23 Stuttgart districts
- **Features**:
  - **Choropleth visualization** of green space percentage per district
  - **Green spaces overlay** (1,973 areas: parks, gardens, forests, meadows)
  - **Public transport stops** (8,299 stops with mode information)
  - **Interactive filters** for green space types
  - **Tooltips** showing district names, green area percentages, and areas

#### **2. Micro-Level Map: `stuttgart_hbf_micro.html`**
- **Purpose**: Detailed analysis around Stuttgart Hauptbahnhof (main station)
- **Features**:
  - **500m walk buffers** around 217 nearby PT stops
  - **Walkable road network** (56,716 segments: residential, footways, pedestrian paths)
  - **Green areas** within walking distance
  - **PT stops** with mode differentiation
  - **Station marker** for Stuttgart Hbf

## 🔧 **Technical Implementation**

### **Data Sources Used**
- **Official Districts**: `spatial_analysis/areas/stuttgart_districts_official/OpenData_KLGL_GENERALISIERT.gpkg`
- **OSM Data**: `main_pipeline/areas/stuttgart/data_final/staging/`
  - `osm_landuse.parquet` → Green spaces (filtered to 1,973 valid polygons)
  - `osm_pt_stops.parquet` → Public transport stops (8,299 stops)
  - `osm_roads.parquet` → Road network (56,716 walkable segments)

### **Key Functions**
- **`compute_green_kpis()`**: Calculates green space metrics per district using UTM coordinates for accurate area calculations
- **`prepare_green_spaces()`**: Filters and validates green space geometries
- **`prepare_pt_stops()`**: Processes PT stops with mode information
- **`prepare_walkable_roads()`**: Extracts pedestrian-friendly road segments
- **`create_walk_buffers()`**: Generates 500m walking distance buffers

### **Coordinate Systems**
- **Input/Output**: EPSG:4326 (WGS84) for web compatibility
- **Calculations**: EPSG:25832 (UTM 32N) for accurate metric measurements
- **Kepler.gl**: Automatically handles CRS transformations

## 🎨 **Visualization Features**

### **Color Schemes**
- **Green spaces**: Sequential green palette (#e8f5e9 → #2e7d32)
- **PT stops**: Blue (#5d6dff) with mode-based differentiation
- **Walk buffers**: Light blue (#007bff) with transparency
- **Roads**: Gray tones for walkable network

### **Interactive Elements**
- **Layer toggles**: Show/hide different data layers
- **Filters**: Multi-select for green space types
- **Tooltips**: Detailed information on hover
- **Zoom/Pan**: Full map navigation
- **Responsive design**: Works on desktop and mobile

## 📁 **File Structure**

```
spatial_analysis/areas/stuttgart_districts_official/outputs/kepler/
├── stuttgart_macro_green_pt.html      # City-wide interactive map
├── stuttgart_hbf_micro.html           # Station area detailed map
├── kepler_config_stuttgart_macro.json # Macro map configuration
└── kepler_config_hbf_micro.json      # Micro map configuration
```

## 🚀 **How to Use**

### **Opening the Maps**
1. **Navigate** to the `kepler/` output directory
2. **Open** either HTML file in a web browser
3. **Interact** with layers, filters, and tooltips
4. **Export** high-resolution images if needed

### **Customization**
- **Modify configurations**: Edit the JSON config files
- **Add new data**: Update the Python script with additional layers
- **Change styling**: Adjust colors, opacity, and visual properties

## 🎯 **VVS Job Application Benefits**

### **Technical Skills Demonstrated**
- **Geospatial Analysis**: Advanced spatial operations and KPI calculations
- **Data Processing**: Large-scale OSM data handling and validation
- **Interactive Visualization**: Modern web-based mapping with Kepler.gl
- **Python Expertise**: Clean, modular, and well-documented code
- **Transport Planning**: Understanding of walkability and accessibility metrics

### **Professional Output**
- **Publication-ready maps**: High-quality interactive visualizations
- **Comprehensive analysis**: Both macro and micro perspectives
- **User-friendly interface**: Intuitive navigation and information display
- **Scalable solution**: Easy to adapt for other cities or projects

## 🔮 **Future Enhancements**

### **Potential Additions**
- **Real-time data**: Live PT arrival times and service status
- **Accessibility metrics**: Wheelchair accessibility and barrier analysis
- **Environmental factors**: Air quality, noise levels, and green connectivity
- **Economic indicators**: Property values, business density, and investment areas
- **Temporal analysis**: Seasonal changes in green spaces and transport usage

### **Technical Improvements**
- **Performance optimization**: Data clustering and level-of-detail rendering
- **Mobile optimization**: Touch-friendly controls and responsive design
- **Data integration**: Real-time APIs and external data sources
- **Export capabilities**: PDF reports and high-resolution image generation

---

**Generated**: Interactive Kepler maps for Stuttgart mobility analysis  
**Purpose**: VVS job application demonstrating geospatial expertise  
**Status**: ✅ Complete and fully functional  
**Output**: 2 interactive HTML maps with comprehensive data visualization
