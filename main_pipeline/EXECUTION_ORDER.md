# ETL Geodata Pipeline - Execution Order

## 📋 **Step-by-Step Execution Guide**

### **STEP 0** 🧪 **Test Pipeline** *(Optional)*
```bash
python pipeline/scripts/test_pipeline.py --city stuttgart --test
```
- **Purpose**: Quick validation with small bbox
- **Output**: Test extraction + processing for landuse layer
- **Time**: ~2-3 minutes
- **Use when**: First time setup, debugging, or development

---

### **STEP 1** 📥 **Extract OSM Data** *(Required)*
```bash
python pipeline/scripts/extract_quackosm.py --city stuttgart
```
- **Purpose**: Extract thematic layers from OSM PBF files
- **Input**: `data_final/stuttgart/raw/baden-wuerttemberg-latest.osm.pbf`
- **Output**: 6 layers in `data_final/stuttgart/staging/`
- **Time**: ~15-20 minutes
- **Layers**: roads, buildings, landuse, cycle, amenities, pt_stops

---

### **STEP 2** ⚙️ **Process & Categorize Data** *(Required)*
```bash
python pipeline/scripts/process_layers.py --city stuttgart
```
- **Purpose**: Apply intelligent categorization to extracted layers
- **Input**: Staged layers from Step 1
- **Output**: Categorized data in `data_final/stuttgart/processed/`
- **Time**: ~2-3 minutes
- **Features**: 
  - 20 amenity categories
  - 12 PT stops categories
  - 8 building categories
  - And more!

---

### **STEP 3A** 🗺️ **Generate Clean Maps** *(Recommended)*
```bash
python pipeline/scripts/create_clean_maps.py
```
- **Purpose**: Create clean, readable visualizations
- **Input**: Processed data from Step 2
- **Output**: 3 clean maps in `data_final/stuttgart/maps/clean/`
- **Time**: ~2-3 minutes
- **Maps**: PT stops, overview, key amenities

---

### **STEP 3B** 🗺️ **Generate Detailed Maps** *(Alternative)*
```bash
python pipeline/scripts/create_thematic_maps.py
```
- **Purpose**: Create comprehensive detailed visualizations
- **Input**: Processed data from Step 2
- **Output**: 7 detailed maps in `data_final/stuttgart/maps/detailed/`
- **Time**: ~5-8 minutes
- **Maps**: All layers with full categorization

---

## 🔄 **Complete Pipeline Execution**

For a full run from start to finish:

```bash
# 1. Extract data
python pipeline/scripts/extract_quackosm.py --city stuttgart

# 2. Process data
python pipeline/scripts/process_layers.py --city stuttgart

# 3. Create visualizations (choose one)
python pipeline/scripts/create_clean_maps.py
# OR
python pipeline/scripts/create_thematic_maps.py
```

**Total time**: ~20-30 minutes for complete pipeline

---

## 📁 **Output Locations**

- **Extracted layers**: `data_final/stuttgart/staging/`
- **Processed data**: `data_final/stuttgart/processed/`
- **Clean maps**: `data_final/stuttgart/maps/clean/`
- **Detailed maps**: `data_final/stuttgart/maps/detailed/`

---

## ⚠️ **Important Notes**

1. **Order matters**: Steps must be run in sequence
2. **Step 1 required**: All other steps depend on extracted data
3. **Choose 3A or 3B**: Clean maps for analysis, detailed maps for exploration
4. **City parameter**: Always specify `--city stuttgart` for Steps 1 & 2
5. **Test first**: Use Step 0 to validate setup before full pipeline

---

## 🆘 **Troubleshooting**

- **Step 1 fails**: Check OSM PBF file exists in `data_final/stuttgart/raw/`
- **Step 2 fails**: Ensure Step 1 completed successfully
- **Step 3 fails**: Ensure Step 2 completed successfully
- **Maps empty**: Check bounding box in `pipeline/areas/stuttgart.yaml`
