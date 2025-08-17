# ETL Geodata Pipeline - Phase 1

A scalable geospatial data extraction and processing pipeline for OpenStreetMap data using QuackOSM.

## Overview

This Phase 1 implementation provides:
- **Local OSM data extraction** from PBF files using QuackOSM
- **Multi-layer thematic extraction** (roads, buildings, landuse, cycling, amenities, public transport, boundaries)
- **YAML-based configuration** for areas and category mappings
- **Automated category mapping** for landuse and roads layers
- **GeoParquet output** for efficient storage and processing

## Directory Structure

```
ETL-Geodata-Pipeline/
├── config/                     # Phase 1 pipeline configuration
│   ├── settings.yaml           # Main pipeline settings
│   ├── osm_filters.yaml        # QuackOSM extraction filters
│   ├── landuse_rules.yaml      # Landuse category mappings
│   └── roads_rules.yaml        # Roads category mappings
├── scripts/                    # Phase 1 pipeline scripts
│   ├── extract_quackosm.py     # OSM data extraction
│   └── process_layers.py       # Category mapping and processing
├── data/                       # Data directories
│   ├── staging/                # Raw extracted layers
│   ├── processed/              # Categorized and processed layers
│   └── osm/                    # OSM source files
├── stuttgart-etl/              # Area-specific configurations and outputs
│   ├── config/areas.yaml       # Area definitions (Stuttgart, etc.)
│   └── data/raw/               # Area-specific OSM data
└── requirements.txt            # Python dependencies
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Data Source

Ensure you have the Stuttgart OSM data:
```bash
ls stuttgart-etl/data/raw/baden-wuerttemberg-latest.osm.pbf
```

### 3. Run Phase 1 Pipeline

```bash
# Extract OSM layers
python scripts/extract_quackosm.py

# Apply category mappings
python scripts/process_layers.py
```

### 4. Verify Results

Check the output:
```bash
ls data/staging/     # Raw extracted layers
ls data/processed/   # Categorized layers
```

## Configuration

### Area Configuration (stuttgart-etl/config/areas.yaml)

Defines geographic areas with bounding boxes:
```yaml
areas:
  stuttgart:
    name: Stuttgart region (Baden-Württemberg)
    geofabrik_region: europe/germany/baden-wuerttemberg
    bbox: 9.0,48.6,9.4,48.9  # lon_min,lat_min,lon_max,lat_max
```

### Pipeline Settings (config/settings.yaml)

Main pipeline configuration:
```yaml
current_area: "stuttgart"          # Area to process
crs: "EPSG:4326"                  # Output coordinate system
pbf_file: "stuttgart-etl/data/raw/baden-wuerttemberg-latest.osm.pbf"
```

### OSM Filters (config/osm_filters.yaml)

Defines what features to extract for each layer:
```yaml
roads:
  highway:
    - motorway
    - primary
    - secondary
    - residential
```

### Category Mappings (config/*_rules.yaml)

Maps raw OSM tags to clean categories:
```yaml
# landuse_rules.yaml
urban:
  - residential
  - commercial
green:
  - park
  - forest
```

## Extracted Layers

| Layer | Description | Output File |
|-------|-------------|-------------|
| **roads** | Highway network | `roads_categorized.parquet` |
| **buildings** | Building footprints | `buildings.parquet` |
| **landuse** | Land use/land cover | `landuse_categorized.parquet` |
| **cycle** | Cycling infrastructure | `cycle.parquet` |
| **amenities** | Schools, hospitals, etc. | `amenities.parquet` |
| **pt_stops** | Public transport stops | `pt_stops.parquet` |
| **boundaries** | Administrative boundaries | `boundaries.parquet` |

## Category Mappings

### Roads Categories
- **motorway**: Motorways and links
- **primary**: Primary roads and links  
- **secondary**: Secondary roads and links
- **tertiary**: Tertiary roads and links
- **residential**: Residential and living streets
- **service**: Service roads and tracks

### Landuse Categories
- **urban**: Residential, commercial, retail
- **agricultural**: Farmland, farms
- **green**: Parks, forests, grassland
- **water**: Water bodies, wetlands

## Logging

Both scripts provide detailed logging:
- Feature counts for each layer
- Geometry type distributions
- Category mapping statistics
- Success/failure status for each step

## Scaling to Other Areas

To process different areas:

1. **Add area to areas.yaml**:
```yaml
areas:
  munich:
    name: Munich region (Bavaria)
    bbox: 11.3,48.0,11.8,48.3
```

2. **Update settings.yaml**:
```yaml
current_area: "munich"
pbf_file: "path/to/bavaria-latest.osm.pbf"
```

3. **Run pipeline** (no code changes needed!)

## Troubleshooting

### Common Issues

**QuackOSM not found**:
```bash
pip install quackosm>=0.10.0
```

**PBF file not found**:
- Check the `pbf_file` path in `config/settings.yaml`
- Download from [Geofabrik](https://download.geofabrik.de/)

**Empty extractions**:
- Verify bounding box covers your area of interest
- Check OSM filters match available tags in your region

### Debug Mode

Add `--verbose` logging by modifying the scripts:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps (Phase 2)

Phase 1 prepares for:
- **Cloud integration** (AWS/GCP)
- **Germany-wide processing**
- **Global scaling**
- **Automated workflows**

The YAML-based configuration ensures Phase 2 requires only config changes, not code changes.

## Dependencies

- **geopandas**: Geospatial data processing
- **quackosm**: OSM data extraction  
- **pyyaml**: Configuration management
- **shapely**: Geometric operations
- **pyproj**: Coordinate transformations
