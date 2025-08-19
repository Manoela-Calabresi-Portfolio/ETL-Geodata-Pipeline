# Kepler.gl Data Export

This folder contains all the map layers exported from the Stuttgart analysis for use in Kepler.gl.

## Files:

1. **01_city_boundary.geojson** - City administrative boundary
2. **02_districts.geojson** - District boundaries with population data
3. **03_roads.geojson** - Road network
4. **04_pt_stops.geojson** - Public transport stops
5. **05_landuse.geojson** - Land use categories (Forest, Farmland, Residential, Industrial, Commercial, Other)
6. **06_green_areas.geojson** - OSM green areas (Parks, Allotments, Gardens, Meadows, Grass, Playgrounds, Other Green)

## Styling Suggestions:

### Land Use Colors (Sage Green Theme):
- **Forest**: #4A5D4A (darkest sage)
- **Farmland**: #7FB069 (medium sage)
- **Residential**: #DAA520 (burned yellow)
- **Industrial**: #D3D3D3 (light gray)
- **Commercial**: #FFB6C1 (light pink)

### Green Areas Colors:
- **Parks**: #9DC183 (light sage)
- **Allotments**: #5A7C65 (darker sage)
- **Gardens**: #7FB069 (medium sage)
- **Meadows**: #9DC183 (light sage)
- **Grass**: #B8D4BA (very light sage)
- **Playgrounds**: #A8E6CF (mint green)

### Transparency:
- Green areas: 20% (more opaque)
- Urban areas: 70% (more transparent)

## Import Instructions:
1. Open Kepler.gl
2. Import each GeoJSON file as a separate layer
3. Apply the suggested colors and transparency
4. Adjust as needed for your visualization
