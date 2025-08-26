# Curitiba - Urban Analysis Module

## 🏙️ **City Overview**

**Curitiba** is the capital and largest city of the Brazilian state of Paraná. Known for its innovative urban planning and sustainable transportation systems, Curitiba serves as a model for sustainable urban development worldwide.

### **Key Characteristics**

- **Country**: Brazil
- **State**: Paraná
- **Population**: ~1.9 million (metropolitan area)
- **Language**: Portuguese (pt-BR)
- **Timezone**: America/Sao_Paulo
- **Urban Form**: Planned grid system with radial corridors
- **Terrain**: Relatively flat with gentle hills
- **Climate**: Subtropical highland climate

### **Unique Urban Features**

#### **🚌 Bus Rapid Transit (BRT) System**
- **Rede Integrada de Transporte (RIT)**
- **Dedicated bus lanes** with high-frequency service
- **Tube stations** for efficient boarding
- **Integrated fare system** across all modes

#### **🌳 Green Belt & Environmental Planning**
- **Parque Barigui** - Large urban park
- **Parque Tanguá** - Environmental preservation area
- **Linear parks** along watercourses
- **Tree-lined boulevards** throughout the city

#### **🏗️ Innovative Urban Planning**
- **Zoning regulations** that promote mixed-use development
- **Pedestrian-friendly** city center
- **Cycling infrastructure** development
- **Waste management** innovations

---

## 📊 **Analysis Focus Areas**

### **1. BRT System Analysis**
- **Route coverage** and accessibility
- **Station distribution** and spacing
- **Service frequency** analysis
- **Integration** with other transport modes

### **2. Green Infrastructure Assessment**
- **Green space accessibility** within walking distance
- **Green belt connectivity** and corridors
- **Environmental quality** indicators
- **Recreation area** distribution

### **3. Urban Planning Effectiveness**
- **Mixed-use development** patterns
- **Pedestrian accessibility** to services
- **Cycling infrastructure** quality
- **Public space** utilization

### **4. District Performance Ranking**
- **Bairro-level analysis** (Curitiba's neighborhoods)
- **Transport accessibility** scores
- **Environmental quality** indicators
- **Quality of life** metrics

---

## 🗺️ **Geographic Configuration**

### **Bounding Box**
```yaml
bbox: [-49.4, -25.6, -49.2, -25.4]  # [min_lon, min_lat, max_lon, max_lat]
```

### **Coordinate Reference Systems**
- **Storage CRS**: EPSG:4326 (WGS84)
- **Analysis CRS**: EPSG:31982 (UTM Zone 22S - Brazil)

### **Administrative Divisions**
- **Bairros** (neighborhoods): ~75 administrative districts
- **Regionais** (administrative regions): 10 regions
- **Municipalities**: Metropolitan area includes 26 municipalities

---

## 📁 **Data Structure**

```
cities/curitiba/
├── config/                          # Curitiba-specific configuration
│   ├── city.yaml                    # City parameters and data sources
│   ├── districts.yaml               # Bairro boundaries and population
│   └── analysis.yaml                # Analysis parameters
├── data/                            # Curitiba-specific data
│   ├── raw/                         # Raw OSM/GTFS data
│   │   ├── parana-latest.osm.pbf    # OSM data for Paraná state
│   │   └── curitiba_gtfs.zip        # GTFS data for RIT system
│   ├── external/                     # External data sources
│   │   ├── bairros_curitiba.geojson # Bairro boundaries
│   │   ├── rit_routes.geojson       # BRT route network
│   │   └── population_curitiba.csv  # Population data by bairro
│   ├── staging/                      # Intermediate processing
│   ├── processed/                    # Final processed data
│   └── outputs/                      # Analysis outputs
├── spatial_analysis/                # Curitiba-specific analysis
│   ├── scripts/                     # Analysis scripts
│   │   ├── curitiba_brt_analysis.py      # BRT system analysis
│   │   ├── curitiba_green_analysis.py    # Green infrastructure analysis
│   │   ├── curitiba_urban_planning.py    # Urban planning analysis
│   │   └── curitiba_district_ranking.py  # District performance ranking
│   ├── config/                      # Analysis configuration
│   │   ├── brt_config.yaml              # BRT-specific parameters
│   │   ├── green_config.yaml            # Green space parameters
│   │   └── kpi_weights.yaml             # KPI weighting for Curitiba
│   └── outputs/                      # Analysis results
│       ├── brt_analysis/              # BRT analysis outputs
│       ├── green_analysis/            # Green infrastructure outputs
│       ├── urban_planning/            # Urban planning outputs
│       └── district_rankings/         # District ranking outputs
└── README.md                         # This documentation
```

---

## 🚀 **Quick Start**

### **1. Setup Curitiba Data**
```bash
# Download OSM data for Paraná state
wget -O cities/curitiba/data/raw/parana-latest.osm.pbf \
  https://download.geofabrik.de/south-america/brazil/parana-latest.osm.pbf

# Download GTFS data for RIT system
# (You'll need to obtain this from Curitiba's transport authority)

# Download bairro boundaries
# (You'll need to obtain this from Curitiba's GIS department)
```

### **2. Configure Analysis Parameters**
```bash
# Edit configuration files for Curitiba-specific parameters
nano cities/curitiba/config/city.yaml
nano cities/curitiba/config/analysis.yaml
nano cities/curitiba/config/districts.yaml
```

### **3. Run Curitiba Analysis**
```bash
# Run BRT analysis
python cities/curitiba/spatial_analysis/scripts/curitiba_brt_analysis.py

# Run green infrastructure analysis
python cities/curitiba/spatial_analysis/scripts/curitiba_green_analysis.py

# Run complete district ranking
python cities/curitiba/spatial_analysis/scripts/curitiba_district_ranking.py
```

---

## 📈 **Expected Analysis Results**

### **BRT System Analysis**
- **Route coverage**: Percentage of population within 300m of BRT stations
- **Service frequency**: High-frequency service coverage (≤15 min headway)
- **Accessibility scores**: Walking and cycling access to BRT stations
- **Integration metrics**: Connection quality with other transport modes

### **Green Infrastructure Assessment**
- **Green space access**: Percentage of population within 500m of parks
- **Green belt connectivity**: Corridor analysis and connectivity metrics
- **Environmental quality**: Tree coverage and natural area distribution
- **Recreation accessibility**: Playground and sports facility access

### **Urban Planning Effectiveness**
- **Mixed-use development**: Land use diversity and service accessibility
- **Pedestrian friendliness**: Sidewalk coverage and crossing facilities
- **Cycling infrastructure**: Dedicated lanes and bike parking availability
- **Public space quality**: Plaza and square accessibility

### **District Performance Rankings**
- **Overall scores**: Weighted combination of all indicators
- **Category rankings**: Performance in specific areas (transport, green, etc.)
- **Comparative analysis**: Bairro-to-bairro performance comparison
- **Improvement recommendations**: Priority areas for development

---

## 🔗 **Data Sources**

### **OpenStreetMap (OSM)**
- **Coverage**: Complete coverage of Curitiba metropolitan area
- **Update frequency**: Real-time updates
- **Data quality**: High quality for transport and land use

### **GTFS Data**
- **Source**: Rede Integrada de Transporte (RIT)
- **Coverage**: Complete BRT and bus network
- **Update frequency**: Regular updates (check with transport authority)

### **Administrative Boundaries**
- **Source**: Prefeitura Municipal de Curitiba
- **Coverage**: All 75 bairros
- **Population data**: IBGE census data integration

---

## 🛠️ **Technical Requirements**

### **Software Dependencies**
- **Python 3.8+** with geospatial libraries
- **PostGIS** for spatial database operations
- **QGIS** for visualization and analysis
- **Docker** for containerized deployment

### **Data Requirements**
- **OSM PBF**: ~100MB for Paraná state
- **GTFS**: ~50MB for RIT system
- **Boundaries**: ~10MB for bairro geometries
- **Population**: ~1MB for demographic data

### **Processing Requirements**
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 2GB for processed data
- **Processing time**: 15-30 minutes for complete analysis

---

## 📚 **References & Resources**

### **Urban Planning**
- **Curitiba Master Plan**: Official urban development guidelines
- **BRT Implementation**: Case study of successful BRT development
- **Green Infrastructure**: Environmental planning and preservation

### **Data Sources**
- **IBGE**: Brazilian Institute of Geography and Statistics
- **OpenStreetMap**: Community-driven mapping platform
- **Curitiba Open Data**: Municipal government data portal

### **Academic Research**
- **Sustainable Urban Development**: Curitiba as a model city
- **Transport Planning**: BRT system effectiveness studies
- **Environmental Planning**: Green infrastructure benefits

---

## 🤝 **Contributing**

### **Local Expertise**
- **Urban planners** familiar with Curitiba's development
- **Transport engineers** with RIT system knowledge
- **Environmental scientists** with local ecosystem expertise
- **GIS specialists** with local data experience

### **Data Updates**
- **Regular updates** of OSM data
- **GTFS data** from transport authority
- **Boundary updates** from municipal government
- **Population data** from IBGE census

---

## 📞 **Support & Contact**

### **Technical Support**
- **Documentation**: Check this README and template files
- **Issues**: Report problems through project issue tracker
- **Questions**: Contact project maintainers

### **Local Support**
- **Curitiba GIS Department**: For official boundary data
- **RIT Administration**: For GTFS and transport data
- **Municipal Planning**: For urban development information

---

*Last Updated: 2024-12-19 - Version 1.0.0*

