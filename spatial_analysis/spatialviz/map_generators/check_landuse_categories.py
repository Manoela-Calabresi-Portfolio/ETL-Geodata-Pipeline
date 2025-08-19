import geopandas as gpd
import pandas as pd
from pathlib import Path

# --- Load Stuttgart data ---
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
PROCESSED_DIR = DATA_DIR / "processed"
PLOT_CRS = "EPSG:3857"

print("📁 Loading land use data...")

# Load land use data
landuse = gpd.read_parquet(PROCESSED_DIR / "landuse_categorized.parquet")
landuse = landuse.to_crs(PLOT_CRS)

print(f"✅ Loaded {len(landuse)} land use areas")

# Check what columns exist
print(f"\n📋 Land use columns: {landuse.columns.tolist()}")

# Check unique values in landuse and natural columns
if "landuse" in landuse.columns:
    print(f"\n🏗️ Land use categories:")
    landuse_counts = landuse["landuse"].value_counts()
    for category, count in landuse_counts.items():
        print(f"  - {category}: {count} areas")

if "natural" in landuse.columns:
    print(f"\n🌿 Natural categories:")
    natural_counts = landuse["natural"].value_counts()
    for category, count in natural_counts.items():
        print(f"  - {category}: {count} areas")

# Check if there are other relevant columns
other_columns = [col for col in landuse.columns if col not in ["geometry", "landuse", "natural"]]
if other_columns:
    print(f"\n🔍 Other relevant columns:")
    for col in other_columns:
        if landuse[col].dtype == 'object':  # Only check string columns
            unique_vals = landuse[col].dropna().unique()
            if len(unique_vals) <= 20:  # Don't print too many values
                print(f"  - {col}: {unique_vals[:10]}")  # Show first 10 values
            else:
                print(f"  - {col}: {len(unique_vals)} unique values")

# Check the current color mapping from debug script
print(f"\n🎨 Current color mapping in debug script:")
landuse_colors = {
    "forest": "#8FBC8F",        # dark sea green
    "farmland": "#90EE90",      # light green  
    "residential": "#F0E68C",   # khaki
    "industrial": "#D3D3D3",    # light grey
    "commercial": "#FFB6C1",    # light pink
    "park": "#98FB98",          # pale green
    "meadow": "#B8D4B8"         # sage green
}

for category, color in landuse_colors.items():
    print(f"  - {category}: {color}")

# Check if any of these categories exist in the data
print(f"\n🔍 Categories found in data vs colors:")
for category, color in landuse_colors.items():
    in_landuse = category in landuse["landuse"].values if "landuse" in landuse.columns else False
    in_natural = category in landuse["natural"].values if "natural" in landuse.columns else False
    status = "✅" if (in_landuse or in_natural) else "❌"
    print(f"  {status} {category}: {color} (landuse: {in_landuse}, natural: {in_natural})")

# Check for any other green-colored categories that might be causing dots
print(f"\n🌱 Looking for potential green dot sources...")
if "landuse" in landuse.columns:
    all_categories = set(landuse["landuse"].dropna().unique())
    if "natural" in landuse.columns:
        all_categories.update(landuse["natural"].dropna().unique())
    
    green_keywords = ["green", "forest", "park", "garden", "meadow", "grass", "farm", "agriculture", "nature"]
    potential_green_categories = [cat for cat in all_categories if any(keyword in str(cat).lower() for keyword in green_keywords)]
    
    if potential_green_categories:
        print(f"  Potential green categories found:")
        for cat in potential_green_categories:
            count = len(landuse[landuse["landuse"] == cat]) + len(landuse[landuse["natural"] == cat])
            print(f"    - {cat}: {count} areas")
    else:
        print(f"  No obvious green categories found")

print(f"\n💡 The green dots are likely coming from:")
print(f"  1. Land use categories with green colors")
print(f"  2. Natural categories with green colors") 
print(f"  3. Categories that aren't in our color mapping")
