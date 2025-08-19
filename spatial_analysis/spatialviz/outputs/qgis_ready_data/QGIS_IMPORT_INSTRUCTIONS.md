# QGIS Import Instructions - Stuttgart Urban Analysis

## 🗺️ How to Import in QGIS:

### 1. Open QGIS and Create New Project
- File → New Project
- Save project as: `stuttgart_urban_analysis.qgz`

### 2. Import Layers (in this order):
1. **01_districts_population.geojson** - Districts with population
2. **02_landuse_categorized.geojson** - Land use categories  
3. **03_roads_categorized.geojson** - Road network
4. **04_pt_stops_categorized.geojson** - PT stops
5. **05_city_boundary.geojson** - City boundary

### 3. Set CRS
- When prompted, set CRS to: **EPSG:4326 (WGS84)**

### 4. Style the Population Density Map:
- Select **01_districts_population** layer
- Right-click → Properties → Symbology
- Change to: **Graduated**
- Column: **pop_density**
- Color ramp: **YlOrRd** (Yellow-Orange-Red)
- Classes: **5**
- Mode: **Quantile**

### 5. Style the Land Use Map:
- Select **02_landuse_categorized** layer
- Right-click → Properties → Symbology
- Change to: **Categorized**
- Column: **landuse**
- Set colors manually:
  - Forest: #4A5D4A (Dark green)
  - Farmland: #7FB069 (Medium green)
  - Residential: #F5F5DC (Light beige)
  - Industrial: #D3D3D3 (Light gray)
  - Commercial: #FFB6C1 (Light pink)

### 6. Style Roads:
- Select **03_roads_categorized** layer
- Color: #8B7355 (Brown)
- Width: 0.5
- Transparency: 70%

### 7. Style PT Stops:
- Select **04_pt_stops_categorized** layer
- Color: #C3423F (Red)
- Size: 3
- Transparency: 20%

### 8. Style City Boundary:
- Select **05_city_boundary** layer
- Fill: Transparent
- Border: #666666 (Gray)
- Width: 3
- Transparency: 60%

## 🎯 Map Templates:

### Template 1: Land Use Map
- **Background:** Land use categories
- **Overlay:** Roads + PT stops
- **Title:** "Stuttgart — Land Use + Roads + PT Stops"

### Template 2: Population Density Map  
- **Background:** Population density (graduated colors)
- **Overlay:** Roads + PT stops
- **Title:** "Stuttgart — Population Density + Roads + PT Stops"

## 💡 Tips:
- Use **Layer Properties** → **Symbology** for styling
- **Save project** frequently
- **Export maps** as PNG/PDF when ready
- Use **Print Layout** for final map composition
