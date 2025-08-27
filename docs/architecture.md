# 🏗️ Architecture Overview

## 🔺 **Project Structure with Emojis**

```
ETL-Geodata-Pipeline/
├── cities/                     # 🟪 City-Centric Architecture (ACTIVE)
│   ├── _template/              # 🟪 Template for new cities
│   │   ├── config/             # Configuration templates
│   │   │   ├── city.yaml       # City parameters template
│   │   │   ├── districts.yaml  # Districts configuration
│   │   │   ├── analysis.yaml   # Analysis settings
│   │   │   └── database.yaml   # Database connection
│   │   ├── spatial_analysis/   # City-specific analysis
│   │   └── README.md.template  # Documentation template
│   ├── stuttgart/              # 🟨 Stuttgart City Module
│   │   ├── config/             # Stuttgart configurations
│   │   ├── spatial_analysis/   # Stuttgart analysis scripts
│   │   └── README.md           # Stuttgart documentation
│   └── curitiba/               # 🟨 Curitiba City Module ✅ **FULLY OPERATIONAL**
│       ├── config/             # Curitiba configurations
│       ├── spatial_analysis/   # Curitiba analysis scripts
│       └── README.md           # Curitiba documentation
├── spatial_analysis_core/      # 🔺 Shared Analysis Core ✅ **PRODUCTION READY**
│   ├── __init__.py             # Core module exports
│   ├── data_loader.py          # 🟪 Multi-source data loader (QuackOSM)
│   └── database/               # 🟪 PostGIS Integration ✅ **FULLY WORKING**
│       ├── __init__.py         # Database module exports
│       ├── database_manager.py # PostgreSQL database management
│       ├── postgis_manager.py  # PostGIS extension management
│       ├── manage_database.py  # Command-line interface
│       └── README.md           # Database documentation
├── pipeline/                   # 🔻 Legacy Pipeline (DEPRECATED)
│   ├── config/                 # 🟪 Configuration Files
│   ├── scripts/                # 🔻 Python Scripts
│   └── areas/                  # 🟨 City-Specific Configurations
├── spatial_analysis/           # 🔻 Legacy Multi-City Analysis (DEPRECATED)
│   ├── config/                 # 🟪 Analysis configuration
│   ├── scripts/                # 🔻 Reusable pipeline (1,2,3)
│   └── data/                   # 🟨 Multi-city data structure
├── credentials/                # 🟪 Secure Database Credentials
├── map_examples/               # 🟪 Generated map examples
├── tools/                      # 🟪 Utility tools and scripts
└── .gitignore                  # 🟪 Comprehensive file filtering
```

## 🏙️ **City-Centric Design**

### **Core Philosophy**
The architecture is built around the principle that **each city is unique** and deserves its own analysis pipeline while sharing common infrastructure.

### **Key Design Principles**

#### 🟪 **Separation of Concerns**
- **Configuration**: City-specific parameters in YAML files
- **Analysis Logic**: Custom scripts for each city's unique characteristics
- **Shared Infrastructure**: Common database, data loading, and utilities
- **Data Storage**: Isolated data folders per city

#### 🟪 **Template-Based Scalability**
```
cities/_template/               # 🟪 Master template
├── config/                     # Configuration templates
├── spatial_analysis/           # Analysis script templates
└── README.md.template          # Documentation template

cities/your_city/               # 🟨 New city instance
├── config/                     # City-specific configs
├── spatial_analysis/           # Custom analysis logic
└── README.md                   # City documentation
```

#### 🟪 **Configuration-Driven Architecture**
```yaml
# cities/curitiba/config/city.yaml
city:
  name: "Curitiba"
  country: "Brazil"
  bbox: [-49.4, -25.6, -49.2, -25.4]
  crs_storage: "EPSG:4326"
  crs_analysis: "EPSG:5880"
  osm_pbf: "data/raw/parana-latest.osm.pbf"
```

### **City Module Structure**
Each city follows the same structure:
```
cities/{city_name}/
├── config/                     # 🟪 City configuration files
│   ├── city.yaml              # Main city parameters
│   ├── districts.yaml          # Administrative boundaries
│   ├── analysis.yaml           # Analysis settings
│   └── database.yaml           # Database connection
├── data/                       # 🟨 City-specific data
│   ├── raw/                    # Original OSM PBF files
│   ├── external/               # External data sources
│   ├── staging/                # Intermediate processing
│   ├── processed/              # Final processed data
│   └── outputs/                # Analysis results
├── spatial_analysis/           # 🟪 City-specific analysis
│   ├── scripts/                # Analysis scripts
│   ├── templates/               # Analysis templates
│   └── utils/                   # City utilities
└── README.md                   # City documentation
```

## 🧠 **Shared Core Components**

### **spatial_analysis_core/ Module**

#### 🟪 **Database Integration**
- **DatabaseManager**: PostgreSQL connection and management
- **PostGISManager**: Spatial extension management
- **CLI Interface**: Full command-line database operations
- **Secure Credentials**: YAML-based configuration management

#### 🟪 **Data Loading**
- **DataLoader**: Multi-source OSM data extraction
- **QuackOSM Integration**: Fast and efficient OSM processing
- **City-Agnostic**: Works with any city, any bounding box
- **Multiple Formats**: Parquet, GeoJSON, GPKG output

#### 🟪 **Core Utilities**
- **Configuration Loading**: YAML configuration management
- **Data Validation**: Input validation and error handling
- **Progress Tracking**: Extraction and processing monitoring
- **Error Handling**: Comprehensive error management

### **Core Module Architecture**
```python
spatial_analysis_core/
├── __init__.py                 # Main exports
├── data_loader.py              # OSM data extraction
├── database/                   # Database management
│   ├── __init__.py            # Database exports
│   ├── database_manager.py    # PostgreSQL management
│   ├── postgis_manager.py     # PostGIS extension
│   └── manage_database.py     # CLI interface
└── utils/                      # Shared utilities
```

## 🚀 **Scalability Features**

### **Horizontal Scaling**
- **Multi-City Support**: Add unlimited cities using templates
- **Parallel Processing**: Process multiple cities simultaneously
- **Isolated Data**: Each city has independent data storage
- **Shared Infrastructure**: Common database and utilities

### **Vertical Scaling**
- **Memory Optimization**: Efficient data processing for large cities
- **Database Performance**: PostgreSQL + PostGIS for large datasets
- **Modular Architecture**: Easy to add new analysis modules
- **Configuration Management**: Scalable YAML-based configuration

### **Technology Scaling**
- **Cloud Ready**: Docker containerization support
- **Database Scaling**: PostgreSQL clustering capabilities
- **API Integration**: RESTful interfaces for external systems
- **Monitoring**: Comprehensive logging and error tracking

## 🔄 **Data Flow Architecture**

### **Input Layer**
```
OSM PBF Files → City Configuration → Bounding Box Filtering
```

### **Processing Layer**
```
Data Extraction → Category Processing → Spatial Analysis → Database Storage
```

### **Output Layer**
```
Analysis Results → Visualization → Maps & Dashboards → Reports
```

### **Data Pipeline Flow**
```
Raw OSM Data → QuackOSM Extraction → Category Classification → 
Spatial Analysis → Database Storage → Visualization → Output Maps
```

## 🏗️ **Architecture Benefits**

### **For Developers**
- **Clean Separation**: Clear boundaries between components
- **Easy Testing**: Isolated components for unit testing
- **Simple Extension**: Add new cities or analysis methods easily
- **Code Reuse**: Shared utilities across all cities

### **For Urban Planners**
- **City-Specific Analysis**: Custom logic for each city's needs
- **Standardized Outputs**: Consistent analysis methodology
- **Easy Comparison**: Compare cities using same metrics
- **Rapid Deployment**: New cities in minutes, not days

### **For Organizations**
- **Scalable Growth**: Add cities without architectural changes
- **Maintenance Efficiency**: Common infrastructure reduces overhead
- **Quality Assurance**: Standardized testing and validation
- **Professional Standards**: Industry-standard tools and practices

## 🔮 **Future Architecture Extensions**

### **Real-Time Processing**
- **Streaming Data**: Apache Kafka for real-time OSM updates
- **Live Analysis**: Real-time urban metrics calculation
- **Dynamic Dashboards**: Live-updating visualizations

### **Cloud Deployment**
- **Containerization**: Docker and Kubernetes support
- **Auto-Scaling**: Cloud-native scaling capabilities
- **Global Distribution**: Multi-region deployment

### **Advanced Analytics**
- **Machine Learning**: AI-powered urban analysis
- **Predictive Modeling**: Future urban development forecasting
- **Interactive Exploration**: 3D and VR visualization support

---

## 🔗 **Related Documentation**

- **[Database Integration](database.md)** - Detailed database setup and API
- **[Multi-City Support](multi_city.md)** - Pipeline execution and city management
- **[Data Layers](data_layers.md)** - Data processing and categorization
- **[Main Project](../README.md)** - Project overview and quick start

---

*Last Updated: 2025-08-27 - Architecture Documentation Version 1.0.0*
