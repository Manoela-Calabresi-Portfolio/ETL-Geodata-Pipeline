import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

# --- Load Stuttgart data ---
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
PROCESSED_DIR = DATA_DIR / "processed"
PLOT_CRS = "EPSG:3857"

print("📁 Loading Stuttgart data...")

# Load all layers
districts = gpd.read_file(DATA_DIR / "districts_with_population.geojson")
districts = districts.to_crs(PLOT_CRS)

pt_stops = gpd.read_parquet(PROCESSED_DIR / "pt_stops_categorized.parquet")
pt_stops = pt_stops.to_crs(PLOT_CRS)

landuse = gpd.read_parquet(PROCESSED_DIR / "landuse_categorized.parquet")
landuse = landuse.to_crs(PLOT_CRS)

roads = gpd.read_parquet(PROCESSED_DIR / "roads_categorized.parquet")
roads = roads.to_crs(PLOT_CRS)

print(f"✅ Loaded {len(districts)} districts, {len(pt_stops)} PT stops, {len(landuse)} land use areas, {len(roads)} roads")

# Create city boundary
city_boundary = districts.unary_union
extent = tuple(districts.total_bounds)

# --- Plot 1: Just districts (basemap) ---
fig, ax = plt.subplots(1, 1, figsize=(15, 10))
districts.plot(ax=ax, color="#f0f0f0", edgecolor="white", linewidth=0.5)
city_boundary_geom = gpd.GeoSeries([city_boundary], crs=PLOT_CRS)
city_boundary_geom.boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.8)
ax.set_title("1. Districts Only (Basemap)", fontsize=14, weight="bold")
ax.set_axis_off()
ax.set_xlim(extent[0], extent[2])
ax.set_ylim(extent[1], extent[3])
ax.set_aspect("equal")
plt.savefig("debug_01_districts_only.png", dpi=300, bbox_inches='tight')
print("💾 Saved: debug_01_districts_only.png")

# --- Plot 2: Districts + Land use ---
fig, ax = plt.subplots(1, 1, figsize=(15, 10))
districts.plot(ax=ax, color="#f0f0f0", edgecolor="white", linewidth=0.5)
city_boundary_geom.boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.8)

# Plot land use
landuse_clipped = landuse[landuse.intersects(city_boundary)]
if len(landuse_clipped) > 0:
    landuse_colors = {
        "forest": "#8FBC8F", "farmland": "#90EE90", "residential": "#F0E68C",
        "industrial": "#D3D3D3", "commercial": "#FFB6C1", "park": "#98FB98",
        "meadow": "#B8D4B8"
    }
    
    for category, color in landuse_colors.items():
        category_data = landuse_clipped[
            (landuse_clipped["landuse"] == category) | 
            (landuse_clipped["natural"] == category)
        ]
        if len(category_data) > 0:
            category_data.plot(ax=ax, color=color, alpha=0.4, edgecolor="none")

ax.set_title("2. Districts + Land Use", fontsize=14, weight="bold")
ax.set_axis_off()
ax.set_xlim(extent[0], extent[2])
ax.set_ylim(extent[1], extent[3])
ax.set_aspect("equal")
plt.savefig("debug_02_districts_landuse.png", dpi=300, bbox_inches='tight')
print("💾 Saved: debug_02_districts_landuse.png")

# --- Plot 3: Districts + Land use + Roads ---
fig, ax = plt.subplots(1, 1, figsize=(15, 10))
districts.plot(ax=ax, color="#f0f0f0", edgecolor="white", linewidth=0.5)
city_boundary_geom.boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.8)

# Plot land use
for category, color in landuse_colors.items():
    category_data = landuse_clipped[
        (landuse_clipped["landuse"] == category) | 
        (landuse_clipped["natural"] == category)
    ]
    if len(category_data) > 0:
        category_data.plot(ax=ax, color=color, alpha=0.4, edgecolor="none")

# Plot roads
roads_clipped = roads[roads.intersects(city_boundary)]
if len(roads_clipped) > 0:
    roads_clipped.plot(ax=ax, color="#c0c0c0", linewidth=0.8, alpha=0.5)

ax.set_title("3. Districts + Land Use + Roads", fontsize=14, weight="bold")
ax.set_axis_off()
ax.set_xlim(extent[0], extent[2])
ax.set_ylim(extent[1], extent[3])
ax.set_aspect("equal")
plt.savefig("debug_03_districts_landuse_roads.png", dpi=300, bbox_inches='tight')
print("💾 Saved: debug_03_districts_landuse_roads.png")

# --- Plot 4: Districts + Land use + Roads + PT Stops ---
fig, ax = plt.subplots(1, 1, figsize=(15, 10))
districts.plot(ax=ax, color="#f0f0f0", edgecolor="white", linewidth=0.5)
city_boundary_geom.boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.8)

# Plot land use
for category, color in landuse_colors.items():
    category_data = landuse_clipped[
        (landuse_clipped["landuse"] == category) | 
        (landuse_clipped["natural"] == category)
    ]
    if len(category_data) > 0:
        category_data.plot(ax=ax, color=color, alpha=0.4, edgecolor="none")

# Plot roads
roads_clipped.plot(ax=ax, color="#c0c0c0", linewidth=0.8, alpha=0.5)

# Plot PT stops
pt_clipped = pt_stops[pt_stops.intersects(city_boundary)]
if len(pt_clipped) > 0:
    pt_clipped.plot(ax=ax, markersize=6, alpha=0.8, color="#2c7bb6", edgecolor="white", linewidth=0.2)

ax.set_title("4. Districts + Land Use + Roads + PT Stops", fontsize=14, weight="bold")
ax.set_axis_off()
ax.set_xlim(extent[0], extent[2])
ax.set_ylim(extent[1], extent[3])
ax.set_aspect("equal")
plt.savefig("debug_04_all_layers.png", dpi=300, bbox_inches='tight')
print("💾 Saved: debug_04_all_layers.png")

# --- Plot 5: Just PT stops to see their distribution ---
fig, ax = plt.subplots(1, 1, figsize=(15, 10))
districts.plot(ax=ax, color="#f0f0f0", edgecolor="white", linewidth=0.5)
city_boundary_geom.boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.8)

# Plot PT stops with different colors by type
if len(pt_clipped) > 0:
    # Check what fields exist for categorization
    print(f"PT stops columns: {pt_clipped.columns.tolist()}")
    
    # Plot all PT stops in red to see where they are
    pt_clipped.plot(ax=ax, markersize=8, alpha=1.0, color="red", edgecolor="black", linewidth=0.5)

ax.set_title("5. Just PT Stops (Red) - Look for green dots!", fontsize=14, weight="bold")
ax.set_axis_off()
ax.set_xlim(extent[0], extent[2])
ax.set_ylim(extent[1], extent[3])
ax.set_aspect("equal")
plt.savefig("debug_05_pt_stops_only.png", dpi=300, bbox_inches='tight')
print("💾 Saved: debug_05_pt_stops_only.png")

print("\n🔍 Debug complete! Check the PNG files to see where the green dots come from.")
print("If you see green dots in the forest areas, they're likely coming from:")
print("1. Land use data (forest/farmland categories)")
print("2. Some PT stops with different colors")
print("3. Other data we haven't identified yet")
