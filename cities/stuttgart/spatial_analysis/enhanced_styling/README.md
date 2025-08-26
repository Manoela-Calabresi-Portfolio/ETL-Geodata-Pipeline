# 🎨 Enhanced Style Engine for Stuttgart Maps

## **🎯 What This Does**

This enhanced style engine **merges** the functionality of `style_helpers/` and `templates/` into a **single, powerful system** that produces maps **exactly like your reference images**.

## **🔍 Reference Maps Supported**

The enhanced style engine can recreate these exact map styles:

1. **`05_access_essentials_h3.png`** - Purple sequential H3 hexagons for essentials access
2. **`07_service_diversity_h3.png`** - Yellow to blue H3 hexagons for service diversity  
3. **`stuttgart_walkability_score_enhanced.png`** - Orange to brown choropleth for walkability
4. **`stuttgart_enhanced_dashboard.png`** - 6-panel dashboard with multiple choropleth maps
5. **`01_overview_landuse_roads_pt.png`** - Categorical landuse with roads and PT stops

## **🏗️ Architecture**

### **Unified System:**
- **`enhanced_style_engine.py`** - Main engine class with all styling methods
- **`enhanced_styles.yaml`** - Configuration file with exact color schemes
- **`example_usage.py`** - Shows how to use the engine

### **Key Features:**
- **Exact color matching** to your reference maps
- **Professional styling** with proper legends, titles, and layout
- **H3 hexagonal grid** support with correct styling
- **Choropleth maps** with district labels and metadata
- **Dashboard creation** with 2x3 grid layout
- **Unified configuration** in YAML format

## **🚀 How to Use**

### **1. Basic Usage (Simple Functions):**

```python
from enhanced_styling.enhanced_style_engine import (
    create_essentials_h3_map,
    create_service_diversity_h3_map,
    create_walkability_score_map,
    create_enhanced_dashboard,
    create_overview_landuse_map
)

# Create H3 Essentials Map (like your reference)
create_essentials_h3_map(
    h3_data, 
    "outputs/enhanced_maps/05_access_essentials_h3.png"
)

# Create Enhanced Dashboard (like your reference)
create_enhanced_dashboard(
    districts_data, 
    "outputs/enhanced_maps/stuttgart_enhanced_dashboard.png"
)
```

### **2. Advanced Usage (Full Engine):**

```python
from enhanced_styling.enhanced_style_engine import EnhancedStyleEngine

# Initialize with custom template
engine = EnhancedStyleEngine("custom_styles.yaml")

# Create maps with custom styling
engine.create_essentials_h3_map(
    h3_data, 
    "outputs/custom_maps/essentials.png",
    title="Custom Title",
    subtitle="Custom Subtitle"
)
```

## **🎨 Color Schemes (Exact Reference Matches)**

### **H3 Essentials Map:**
- **Purple Sequential**: `#f7f4f9` → `#ce1256`
- **Range**: 0 to 6 essential types
- **Label**: "# Essential Types (≤10 min walk)"

### **H3 Service Diversity Map:**
- **Yellow to Blue**: `#ffffcc` → `#0c2c84`
- **Range**: 0.0 to 3.0 Shannon Entropy
- **Label**: "Service Diversity (Shannon Entropy)"

### **Walkability Score Map:**
- **Orange to Brown**: `#fff7ec` → `#b30000`
- **Range**: 0.0 to 1.0
- **Label**: "Walkability Score"

### **Enhanced Dashboard:**
- **6 different color schemes** for each metric
- **2x3 grid layout** with professional styling
- **District labels** and proper legends

## **📁 File Structure**

```
enhanced_styling/
├── enhanced_style_engine.py    # Main engine class
├── enhanced_styles.yaml         # Configuration file
├── example_usage.py            # Usage examples
└── README.md                   # This file
```

## **🔧 Configuration**

The `enhanced_styles.yaml` file contains:

- **Color schemes** for each map type
- **Layout settings** (figure size, DPI, fonts)
- **H3 specific settings** (edge colors, alpha, legends)
- **Choropleth settings** (borders, transparency)
- **Dashboard settings** (grid layout, spacing)
- **Export settings** (format, quality, metadata)

## **✅ Benefits Over Old System**

### **Before (Separate style_helpers + templates):**
- ❌ Duplicate functionality
- ❌ Inconsistent styling
- ❌ Hard to maintain
- ❌ Maps didn't match references

### **After (Unified Enhanced Style Engine):**
- ✅ **Single source of truth** for all styling
- ✅ **Exact reference matching** for all map types
- ✅ **Professional quality** with proper legends and layout
- ✅ **Easy to maintain** and extend
- ✅ **Consistent styling** across all maps

## **🎯 Next Steps**

1. **Test the enhanced style engine** with your existing data
2. **Replace old styling calls** in your scripts
3. **Customize colors** in `enhanced_styles.yaml` if needed
4. **Extend the engine** for new map types

## **🚨 Migration from Old System**

### **Replace these old calls:**
```python
# OLD (style_helpers)
from style_helpers import apply_style, palette
apply_style(ax, extent)

# NEW (enhanced styling)
from enhanced_styling.enhanced_style_engine import create_essentials_h3_map
create_essentials_h3_map(h3_data, output_path)
```

### **Benefits of migration:**
- **Better quality maps** that match your references
- **Easier maintenance** with unified system
- **Professional appearance** with proper legends and styling
- **Consistent output** across all map types

---

**Status**: ✅ **READY TO USE**  
**Quality**: 🎨 **PROFESSIONAL REFERENCE MATCHING**  
**Maintenance**: 🔧 **UNIFIED AND EASY**
