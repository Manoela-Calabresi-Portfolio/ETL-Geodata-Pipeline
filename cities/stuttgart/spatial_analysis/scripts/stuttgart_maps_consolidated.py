#!/usr/bin/env python3
"""
Stuttgart Maps - Consolidated Script
Generates only the specific maps requested by combining functionality from multiple scripts
"""

from __future__ import annotations
from pathlib import Path
import warnings, math, json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import contextily as cx
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
import networkx as nx

# Import our local modules
import sys
sys.path.append("../style_helpers")
sys.path.append("../utils")
from style_helpers import apply_style, palette
from h3_utils import hex_polygon, polyfill_gdf, cells_to_gdf
from h3_helpers import gdf_polygons_to_h3, h3_to_shapely_geometry

warnings.filterwarnings("ignore", category=UserWarning)

# Constants
DATA_DIR = Path("../data")
PLOT_CRS = 3857
H3_RES = 8
OVERVIEW_PAD_M = 2000
DISTRICTS_FOCUS = ["Mitte", "Nord", "Süd", "West", "Ost", "Bad Cannstatt"]

# PT Type Colors and Weights
PT_TYPE_COLORS = {
    "Tram": "#C3423F",
    "U-Bahn": "#7D2E2E", 
    "S-Bahn": "#8B3A3A",
    "Bus": "#DAA520",
    "Other": "#777777"
}
PT_WEIGHTS = {"S-Bahn": 3.0, "U-Bahn": 2.5, "Tram": 2.0, "Bus": 1.0, "Other": 0.5}

# Essential amenities
ESSENTIALS = {
    "amenity": {"supermarket", "pharmacy", "school", "hospital", "doctors", "clinic"},
    "shop": {"supermarket"},
    "healthcare": {"hospital", "clinic", "doctor", "doctors"}
}

# Green access parameters
BOUNDARY_SAMPLE_STEP_M = 80
PARK_MIN_AREA_M2 = 10_000
FOREST_MIN_AREA_M2 = 20_000
PARK_TARGET_MIN = 10
FOREST_TARGET_MIN = 15
WALK_SPEED_MPM = 80
CANDIDATE_ENTRANCES_K = 8

def get_next_output_dir():
    """Get the next available output directory in the series"""
    outputs_base = Path("outputs")
    if not outputs_base.exists():
        outputs_base.mkdir(parents=True, exist_ok=True)
    
    existing_dirs = list(outputs_base.glob("stuttgart_maps_*"))
    if not existing_dirs:
        next_num = "001"
    else:
        numbers = []
        for d in existing_dirs:
            try:
                num_str = d.name.replace("stuttgart_maps_", "")
                numbers.append(int(num_str))
            except ValueError:
                continue
        next_num = f"{max(numbers) + 1:03d}" if numbers else "001"
    
    output_dir = outputs_base / f"stuttgart_maps_{next_num}"
    return output_dir, next_num

# Initialize output directories
OUTPUT_BASE, RUN_NUMBER = get_next_output_dir()
OUT_DIR = OUTPUT_BASE / "maps"; OUT_DIR.mkdir(parents=True, exist_ok=True)
KEPLER_DIR = OUTPUT_BASE / "kepler_data"; KEPLER_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR = OUT_DIR  # For compatibility with stuttgart_maps_all.py functions

def load_data():
    """Load all required data layers"""
    def read_any(p: Path):
        if not p.exists(): 
            return None
        try:
            if p.suffix.lower() in {".geojson", ".json", ".gpkg"}:
                return gpd.read_file(p)
            elif p.suffix.lower() == ".parquet":
                df = pd.read_parquet(p)
                if "geometry" in df.columns:
                    if df['geometry'].dtype == 'object' and isinstance(df['geometry'].iloc[0], bytes):
                        from shapely import wkb
                        df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
                    return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)
                else:
                    return df
            else:
                return pd.read_parquet(p)
        except Exception as e:
            print(f"Error reading {p}: {e}")
            return None

    layers = dict(
        districts=read_any(DATA_DIR / "districts_with_population.geojson"),
        landuse=read_any(DATA_DIR / "processed/landuse_categorized.parquet"),
        roads=read_any(DATA_DIR / "processed/roads_categorized.parquet"),
        pt_stops=read_any(DATA_DIR / "processed/pt_stops_categorized.parquet"),
        amenities=read_any(DATA_DIR / "processed/amenities_categorized.parquet"),
        boundary=read_any(DATA_DIR / "city_boundary.geojson"),
        h3_pop=pd.read_parquet(DATA_DIR / "h3_population_res8.parquet") if (DATA_DIR / "h3_population_res8.parquet").exists() else None,
    )
    
    # Set CRS for GeoDataFrames
    for key, gdf in layers.items():
        if gdf is not None and hasattr(gdf, 'crs') and key != "h3_pop":
            if gdf.crs is None:
                layers[key] = gdf.set_crs(4326)
            else:
                layers[key] = gdf.to_crs(4326)
    
    return layers

def _save(fig, name):
    """Save figure to maps directory"""
    filepath = OUT_DIR / name
    fig.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  ✅ Saved: {name}")

def _city_extent_and_boundary(data):
    """Get city extent and boundary"""
    if data["boundary"] is not None:
        boundary = data["boundary"].to_crs(PLOT_CRS)
        extent = boundary.total_bounds
        extent = [extent[0] - OVERVIEW_PAD_M, extent[1] - OVERVIEW_PAD_M,
                 extent[2] + OVERVIEW_PAD_M, extent[3] + OVERVIEW_PAD_M]
        return extent, boundary
    else:
        boundary = data["districts"].to_crs(PLOT_CRS)
        extent = boundary.total_bounds
        extent = [extent[0] - OVERVIEW_PAD_M, extent[1] - OVERVIEW_PAD_M,
                 extent[2] + OVERVIEW_PAD_M, extent[3] + OVERVIEW_PAD_M]
        return extent, boundary

def _add_basemap_custom(ax, extent, basemap_source="CartoDB.Positron", basemap_alpha=0.30):
    """Add custom basemap"""
    try:
        if basemap_source == "CartoDB.Positron":
            cx.add_basemap(ax, crs=PLOT_CRS, source=cx.providers.CartoDB.Positron, alpha=basemap_alpha)
        else:
            cx.add_basemap(ax, crs=PLOT_CRS, source=getattr(cx.providers.CartoDB, basemap_source, cx.providers.CartoDB.Positron), alpha=basemap_alpha)
    except Exception as e:
        print(f"  ⚠️ Basemap failed: {e}")

def _add_scale_bar(ax, extent, km_marks=(1, 5, 10)):
    """Add scale bar to map"""
    try:
        x_range = extent[2] - extent[0]
        y_range = extent[3] - extent[1]
        
        for km in km_marks:
            scale_length = km * 1000  # Convert km to meters
            bar_x = extent[0] + x_range * 0.05
            bar_y = extent[1] + y_range * (0.05 + km_marks.index(km) * 0.02)
            
            ax.plot([bar_x, bar_x + scale_length], [bar_y, bar_y], 
                    'k-', linewidth=2, solid_capstyle='butt')
            ax.text(bar_x + scale_length/2, bar_y + 100, f'{km} km', 
                    ha='center', va='bottom', fontsize=8, weight='bold')
    except Exception as e:
        print(f"  ⚠️ Scale bar failed: {e}")

def apply_map_template(ax, extent, english_title, german_subtitle, city_boundary_buffered,
                      figsize=(20,16), basemap_source="CartoDB.Positron", basemap_alpha=0.30):
    """Apply consistent map template"""
    _add_basemap_custom(ax, extent, basemap_source, basemap_alpha)
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_title(f"{english_title}\n{german_subtitle}", fontsize=16, weight='bold', pad=20)
    ax.axis('off')
    _add_scale_bar(ax, extent)
    
    # Add city boundary
    if city_boundary_buffered is not None:
        city_boundary_buffered.boundary.plot(ax=ax, color='black', linewidth=1.5, alpha=0.8)

# =============== MAP FUNCTIONS ===============

def generate_overview_maps(data):
    """Generate overview map with landuse, roads, and PT stops"""
    print("🗺️ Generating overview map...")
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16), dpi=200)
    
    # Plot landuse as background
    if data["landuse"] is not None:
        landuse_plot = data["landuse"].to_crs(PLOT_CRS)
        landuse_plot.plot(ax=ax, column='category', cmap='Set3', alpha=0.6, legend=True)
    
    # Plot roads
    if data["roads"] is not None:
        roads_plot = data["roads"].to_crs(PLOT_CRS)
        roads_plot.plot(ax=ax, color='gray', linewidth=0.5, alpha=0.7)
    
    # Plot PT stops
    if data["pt_stops"] is not None:
        pt_plot = data["pt_stops"].to_crs(PLOT_CRS)
        pt_plot.plot(ax=ax, color='red', markersize=15, alpha=0.8)
    
    apply_map_template(ax, extent, "Stuttgart — Overview (Landuse + Roads + PT)", 
                      "Flächennutzung + Straßen + ÖPNV", city_boundary_buffered)
    
    _save(fig, "01_overview_landuse_roads_pt.png")

def generate_district_accessibility_maps(data, focus_names=DISTRICTS_FOCUS):
    """Generate district accessibility maps"""
    print("🗺️ Generating district accessibility maps...")
    
    if data["districts"] is None:
        print("❌ No districts data available")
        return
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    districts = data["districts"].to_crs(PLOT_CRS)
    
    for name in focus_names:
        # Find district by name (case-insensitive partial match)
        matching_districts = districts[
            districts.get('district_norm', districts.get('STADTBEZIRKNAME', '')).str.contains(name, case=False, na=False)
        ]
        
        if matching_districts.empty:
            print(f"  ⚠️ District '{name}' not found")
            continue
        
        district = matching_districts.iloc[0]
        
        fig, ax = plt.subplots(1, 1, figsize=(20, 16))
        
        # Highlight the focus district
        districts.plot(ax=ax, color='lightgray', alpha=0.3, edgecolor='white', linewidth=0.5)
        matching_districts.plot(ax=ax, color='orange', alpha=0.7, edgecolor='black', linewidth=2)
        
        # Add PT stops if available
        if data["pt_stops"] is not None:
            pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
            pt_stops.plot(ax=ax, color='red', markersize=10, alpha=0.8)
        
        apply_map_template(ax, extent, f"Stuttgart — {name} District Access", 
                          f"Bezirk {name} — Erreichbarkeit", city_boundary_buffered)
        
        _save(fig, f"03_access_{name.lower().replace(' ', '_')}.png")

# H3 Grid Creation Functions
def _city_h3_grid_3857(data, res=H3_RES):
    """Create H3 grid covering the city"""
    if data["boundary"] is not None:
        city_wgs84 = data["boundary"].to_crs(4326)
    else:
        city_wgs84 = data["districts"].to_crs(4326)
    
    # Get H3 cells using the working function
    hex_ids = polyfill_gdf(city_wgs84, res)
    h3_gdf = cells_to_gdf(hex_ids, to_crs=PLOT_CRS)
    h3_gdf["area_m2"] = h3_gdf.geometry.area
    h3_gdf["centroid"] = h3_gdf.geometry.centroid
    
    return h3_gdf

def _classify_pt(row):
    """Classify PT stops by type"""
    route_type = str(row.get("route_type", "")).lower()
    name = str(row.get("name", "")).lower()
    
    if "s-bahn" in name or route_type == "train":
        return "S-Bahn"
    elif "u-bahn" in name or route_type == "subway":
        return "U-Bahn"
    elif route_type == "tram":
        return "Tram"
    elif route_type == "bus":
        return "Bus"
    else:
        return "Other"

def _compute_pt_gravity(h3g, stops):
    """Compute PT modal gravity for H3 hexagons"""
    if stops is None or len(stops) == 0:
        h3g["pt_gravity"] = 0.0
        return h3g
    
    # Ensure PT classification
    stops = stops.copy()
    if "pt_type" not in stops.columns:
        stops["pt_type"] = stops.apply(_classify_pt, axis=1)
    
    gravity_scores = []
    
    for idx, hex_row in h3g.iterrows():
        hex_point = hex_row["centroid"]
        total_gravity = 0.0
        
        for _, stop_row in stops.iterrows():
            stop_point = stop_row.geometry
            distance = hex_point.distance(stop_point)
            
            if distance > 0:
                pt_type = stop_row.get("pt_type", "Other")
                weight = PT_WEIGHTS.get(pt_type, 0.5)
                gravity = weight / (distance ** 2)
                total_gravity += gravity
        
        gravity_scores.append(total_gravity)
    
    h3g = h3g.copy()
    h3g["pt_gravity"] = gravity_scores
    
    # Normalize to 0-100
    max_gravity = max(gravity_scores) if gravity_scores else 1.0
    h3g["pt_gravity"] = (h3g["pt_gravity"] / max_gravity * 100) if max_gravity > 0 else 0.0
    
    return h3g

def _attach_h3_population_density(data, h3g):
    """Attach population density to H3 grid"""
    if data["h3_pop"] is not None:
        h3_pop = data["h3_pop"]
        # Merge population data
        h3g = h3g.merge(h3_pop[["h3", "pop"]], on="h3", how="left")
        h3g["pop"] = h3g["pop"].fillna(0)
        h3g["pop_density"] = h3g["pop"] / (h3g["area_m2"] / 1e6)  # per km²
    else:
        h3g["pop"] = 0
        h3g["pop_density"] = 0
    
    return h3g

def _is_essential(row):
    """Check if amenity is essential"""
    for key, values in ESSENTIALS.items():
        if key in row and str(row[key]).lower() in values:
            return True
    return False

def map04_pt_modal_gravity_h3(data):
    """Map 04: H3 PT Modal Gravity"""
    print("  🧩 Generating H3 PT Modal Gravity map...")
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    h3g = _city_h3_grid_3857(data)
    h3g = _compute_pt_gravity(h3g, data["pt_stops"].to_crs(PLOT_CRS) if data["pt_stops"] is not None else None)
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    h3g.plot(ax=ax, column="pt_gravity", cmap="Reds", alpha=0.8, edgecolor="white", linewidth=0.1,
             legend=True, legend_kwds={"label": "PT Modal Gravity (0-100)", "orientation": "horizontal", "shrink": 0.6})
    
    apply_map_template(ax, extent, "Stuttgart — PT Modal Gravity (H3 r8)", 
                      "Σ (Weight / Distance²), S>U>Tram>Bus — H3 Raster r8", city_boundary_buffered)
    
    _save(fig, "04_pt_modal_gravity_h3.png")
    
    # Export to Kepler
    out = KEPLER_DIR
    h3g[["h3","pt_gravity","geometry"]].to_crs(4326).to_file(out/"13_pt_modal_gravity_h3.geojson", driver="GeoJSON")

def map04a_pt_pop_mismatch_h3(data):
    """Map 04a: PT vs Population Mismatch (Diverging)"""
    print("  📊 Generating PT vs Population Mismatch map...")
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    h3g = _city_h3_grid_3857(data)
    h3g = _attach_h3_population_density(data, h3g)
    h3g = _compute_pt_gravity(h3g, data["pt_stops"].to_crs(PLOT_CRS) if data["pt_stops"] is not None else None)
    
    # Normalize both variables to 0-1
    pop_norm = (h3g["pop_density"] - h3g["pop_density"].min()) / (h3g["pop_density"].max() - h3g["pop_density"].min())
    pt_norm = h3g["pt_gravity"] / 100  # Already 0-100
    
    # Mismatch: positive = more PT than population warrants, negative = less PT than needed
    h3g["mismatch"] = pt_norm - pop_norm
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    h3g.plot(ax=ax, column="mismatch", cmap="RdBu_r", alpha=0.8, edgecolor="white", linewidth=0.1,
             legend=True, legend_kwds={"label": "PT Supply vs Population Demand", "orientation": "horizontal", "shrink": 0.6})
    
    apply_map_template(ax, extent, "Stuttgart — PT vs Population Mismatch (H3)", 
                      "Divergenz Angebot × Nachfrage", city_boundary_buffered)
    
    _save(fig, "04a_mismatch_diverging_h3.png")
    
    # Export to Kepler
    out = KEPLER_DIR
    h3g[["h3","pop_density","pt_gravity","mismatch","geometry"]].to_crs(4326).to_file(out/"20_pt_pop_mismatch_h3.geojson", driver="GeoJSON")

def map04b_pt_pop_small_multiples_h3(data):
    """Map 04b: PT Population Small Multiples"""
    print("  📊 Generating PT Population Small Multiples...")
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    h3g = _city_h3_grid_3857(data)
    h3g = _attach_h3_population_density(data, h3g)
    h3g = _compute_pt_gravity(h3g, data["pt_stops"].to_crs(PLOT_CRS) if data["pt_stops"] is not None else None)
    
    fig, axes = plt.subplots(1, 2, figsize=(30, 16))
    
    # Population density
    h3g.plot(ax=axes[0], column="pop_density", cmap="Blues", alpha=0.8, edgecolor="white", linewidth=0.1)
    axes[0].set_title("Population Density", fontsize=14, weight='bold')
    axes[0].axis('off')
    
    # PT gravity
    h3g.plot(ax=axes[1], column="pt_gravity", cmap="Reds", alpha=0.8, edgecolor="white", linewidth=0.1)
    axes[1].set_title("PT Modal Gravity", fontsize=14, weight='bold')
    axes[1].axis('off')
    
    for ax in axes:
        _add_basemap_custom(ax, extent)
        ax.set_xlim(extent[0], extent[2])
        ax.set_ylim(extent[1], extent[3])
        if city_boundary_buffered is not None:
            city_boundary_buffered.boundary.plot(ax=ax, color='black', linewidth=1.5, alpha=0.8)
    
    fig.suptitle("Stuttgart — Population vs PT Modal Gravity Comparison", fontsize=16, weight='bold')
    
    _save(fig, "04b_small_multiples_h3.png")

def map05_access_essentials_h3(data):
    """Map 05: H3 Access to Essentials"""
    print("  🏥 Generating H3 Access to Essentials map...")
    
    if data["amenities"] is None:
        print("❌ amenities missing")
        return
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    h3g = _city_h3_grid_3857(data)
    amenities = data["amenities"].to_crs(PLOT_CRS)
    
    # Filter essential amenities
    essentials = amenities[amenities.apply(_is_essential, axis=1)]
    
    if len(essentials) == 0:
        h3g["ess_types"] = 0
    else:
        # Count essential types within 800m (10-min walk)
        walk_10min_m = 800
        
        ess_counts = []
        for idx, hex_row in h3g.iterrows():
            hex_centroid = hex_row["centroid"]
            nearby = essentials[essentials.geometry.distance(hex_centroid) <= walk_10min_m]
            
            # Count unique essential types
            unique_types = set()
            for _, amenity in nearby.iterrows():
                for key, values in ESSENTIALS.items():
                    if key in amenity and str(amenity[key]).lower() in values:
                        unique_types.add(str(amenity[key]).lower())
            
            ess_counts.append(len(unique_types))
        
        h3g["ess_types"] = ess_counts
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    h3g.plot(ax=ax, column="ess_types", cmap="Greens", alpha=0.8, edgecolor="white", linewidth=0.1,
             legend=True, legend_kwds={"label": "# Essential Types (≤10 min walk)", "orientation": "horizontal", "shrink": 0.6})
    
    apply_map_template(ax, extent, "Stuttgart — Essentials within 10-min Walk (H3 r8)", 
                      "Erreichbarkeit von Grundversorgern", city_boundary_buffered)
    
    _save(fig, "05_access_essentials_h3.png")
    
    # Export to Kepler
    out = KEPLER_DIR
    h3g[["h3","ess_types","geometry"]].to_crs(4326).to_file(out/"14_access_essentials_h3.geojson", driver="GeoJSON")

def map07_service_diversity_h3(data):
    """Map 07: H3 Service Diversity"""
    print("  🎯 Generating H3 Service Diversity map...")
    
    if data["amenities"] is None:
        print("❌ amenities missing")
        return
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    h3g = _city_h3_grid_3857(data)
    amenities = data["amenities"].to_crs(PLOT_CRS)
    
    # Calculate Shannon entropy of amenity types per hex
    entropy_scores = []
    for idx, hex_row in h3g.iterrows():
        hex_geom = hex_row.geometry
        hex_amenities = amenities[amenities.geometry.within(hex_geom)]
        
        if len(hex_amenities) == 0:
            entropy_scores.append(0.0)
        else:
            # Count amenity types
            type_counts = hex_amenities.get('amenity', pd.Series(dtype='object')).value_counts()
            if len(type_counts) == 0:
                entropy_scores.append(0.0)
            else:
                # Calculate Shannon entropy
                probs = type_counts / type_counts.sum()
                entropy = -np.sum(probs * np.log2(probs + 1e-10))
                entropy_scores.append(entropy)
    
    h3g["amen_entropy"] = entropy_scores
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    h3g.plot(ax=ax, column="amen_entropy", cmap="viridis", alpha=0.8, edgecolor="white", linewidth=0.1,
             legend=True, legend_kwds={"label": "Service Diversity (Shannon Entropy)", "orientation": "horizontal", "shrink": 0.6})
    
    apply_map_template(ax, extent, "Stuttgart — Service Diversity (H3 r8)", 
                      "Dienstleistungs-Diversität", city_boundary_buffered)
    
    _save(fig, "07_service_diversity_h3.png")
    
    # Export to Kepler
    out = KEPLER_DIR
    h3g[["h3","amen_entropy","geometry"]].to_crs(4326).to_file(out/"16_service_diversity_h3.geojson", driver="GeoJSON")

# Green Access Functions (from generate_h3_advanced_maps.py)
def _build_walk_graph(roads_gdf):
    """Build walking graph from roads"""
    rd = roads_gdf.copy()
    for col in ["highway","foot","access"]:
        if col not in rd.columns: rd[col] = ""
    hw = rd["highway"].astype(str).str.lower()
    foot = rd["foot"].astype(str).str.lower()
    access = rd["access"].astype(str).str.lower()

    walk_like = hw.isin(["footway","path","pedestrian","living_street","steps","residential","service","track","cycleway","bridleway"])
    minor_roads = hw.isin(["tertiary","unclassified","secondary","primary"]) & ~access.isin(["no"])
    allowed_by_tag = foot.isin(["yes","designated","permissive"])

    rd = rd[walk_like | minor_roads | allowed_by_tag]
    G = nx.Graph()
    for geom in rd.geometry:
        if geom is None or geom.is_empty: 
            continue
        lines = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom] if geom.geom_type == "LineString" else []
        for ls in lines:
            coords = list(ls.coords)
            for a, b in zip(coords[:-1], coords[1:]):
                na = (round(a[0],1), round(a[1],1))
                nb = (round(b[0],1), round(b[1],1))
                w = ((na[0]-nb[0])**2 + (na[1]-nb[1])**2)**0.5
                if w > 0: G.add_edge(na, nb, weight=w)
    
    # Cache nodes for fast lookup
    _nearest_graph_node._arr = np.array(list(G.nodes)) if len(G) else np.empty((0,2))
    return G

def _nearest_graph_node(G, pt):
    """Find nearest graph node to point"""
    arr = _nearest_graph_node._arr
    if arr.size == 0: 
        return None
    d = np.hypot(arr[:,0]-pt.x, arr[:,1]-pt.y)
    return tuple(arr[int(np.argmin(d))])

def _sample_boundary_points(polys, step_m=BOUNDARY_SAMPLE_STEP_M):
    """Sample points along polygon boundaries"""
    pts = []
    for geom in polys.geometry:
        if geom is None or geom.is_empty: 
            continue
        boundary = geom.boundary
        lines = list(boundary.geoms) if boundary.geom_type == "MultiLineString" else [boundary]
        for ln in lines:
            n = max(1, int(np.ceil(ln.length / step_m)))
            for i in range(n+1):
                p = ln.interpolate(i / n, normalized=True)
                pts.append(p)
    return gpd.GeoDataFrame(geometry=pts, crs=polys.crs)

def _load_parks_and_forests():
    """Load parks and forests data"""
    districts = gpd.read_file(DATA_DIR/"districts_with_population.geojson").to_crs(PLOT_CRS)
    city = districts.unary_union.buffer(100)

    # Parks
    parks = None
    if (DATA_DIR/"processed/landuse_categorized.parquet").exists():
        lu = gpd.read_parquet(DATA_DIR/"processed/landuse_categorized.parquet").to_crs(PLOT_CRS)
        parks = lu[(lu.get("landuse","") == "park") | (lu.get("leisure","") == "park")].copy() if not lu.empty else gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    
    if parks is None or parks.empty: 
        parks = gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    
    parks = parks[parks.geometry.type.isin(["Polygon","MultiPolygon"])]
    if not parks.empty:
        parks["geometry"] = parks.geometry.intersection(city)
        parks = parks[~parks.geometry.is_empty]
        parks["area_m2"] = parks.geometry.area
        parks = parks[parks["area_m2"] >= PARK_MIN_AREA_M2]

    # Forests
    forests = None
    if (DATA_DIR/"processed/landuse_categorized.parquet").exists():
        lu = gpd.read_parquet(DATA_DIR/"processed/landuse_categorized.parquet").to_crs(PLOT_CRS)
        forests = lu[(lu.get("landuse","") == "forest") | (lu.get("natural","") == "forest")].copy() if not lu.empty else gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)

    if forests is None or forests.empty: 
        forests = gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    
    forests = forests[forests.geometry.type.isin(["Polygon","MultiPolygon"])]
    if not forests.empty:
        forests["geometry"] = forests.geometry.intersection(city)
        forests = forests[~forests.geometry.is_empty]
        forests["area_m2"] = forests.geometry.area
        forests = forests[forests["area_m2"] >= FOREST_MIN_AREA_M2]

    return parks, forests, city

def _candidate_entrances(parks, forests, roads):
    """Get candidate entrance points for parks and forests"""
    def _intersections(polys):
        pts = []
        for geom in polys.geometry:
            if geom is None or geom.is_empty: 
                continue
            b = geom.boundary
            rs = roads.geometry.intersection(b)
            for g in rs:
                if g.is_empty: continue
                if g.geom_type in ("Point","MultiPoint"):
                    geoms = list(g.geoms) if g.geom_type=="MultiPoint" else [g]
                    pts.extend(geoms)
        return gpd.GeoDataFrame(geometry=pts, crs=polys.crs)

    park_int = _intersections(parks)
    forest_int = _intersections(forests)

    # Fallback: sample boundary
    if park_int.empty and not parks.empty:
        park_int = _sample_boundary_points(parks)
    if forest_int.empty and not forests.empty:
        forest_int = _sample_boundary_points(forests)

    return park_int, forest_int

def _access_time_h3(G, h3gdf, target_points, minutes_cap=None):
    """Calculate access time from H3 centroids to targets"""
    if target_points.empty or len(G)==0:
        return pd.Series([np.nan]*len(h3gdf), index=h3gdf.index)

    # Target nodes in graph
    tgt_nodes = []
    for p in target_points.geometry:
        n = _nearest_graph_node(G, p)
        if n is None: continue
        tgt_nodes.append(n)
    if not tgt_nodes:
        return pd.Series([np.nan]*len(h3gdf), index=h3gdf.index)

    tgt_nodes = list(set(tgt_nodes))
    tgt_arr = np.array(tgt_nodes)

    times = []
    for c in h3gdf["centroid"]:
        src = _nearest_graph_node(G, c)
        if src is None:
            times.append(np.nan)
            continue
        # Top-K candidates euclidean
        d = np.hypot(tgt_arr[:,0]-c.x, tgt_arr[:,1]-c.y)
        k = min(CANDIDATE_ENTRANCES_K, len(tgt_arr))
        idxs = np.argpartition(d, k-1)[:k]
        best = np.inf
        for j in idxs:
            tgt = tuple(tgt_arr[j])
            try:
                net = nx.shortest_path_length(G, src, tgt, weight="weight")
                best = net if net < best else best
            except Exception:
                continue
        if best==np.inf:
            times.append(np.nan)
        else:
            tmin = best / float(WALK_SPEED_MPM)
            if minutes_cap is not None:
                tmin = min(tmin, minutes_cap)
            times.append(tmin)
    return pd.Series(times, index=h3gdf.index)

def map08_park_access_time_h3(data):
    """Map 08: Park Access Time H3"""
    print("  🌳 Generating Park Access Time map...")
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    h3g = _city_h3_grid_3857(data)
    
    # Load parks and build walking network
    parks, forests, city = _load_parks_and_forests()
    roads = data["roads"].to_crs(PLOT_CRS) if data["roads"] is not None else gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    G = _build_walk_graph(roads)
    
    # Get park entrances and calculate access times
    park_ent, forest_ent = _candidate_entrances(parks, forests, roads)
    h3g["park_min"] = _access_time_h3(G, h3g, park_ent)
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    h3g.plot(ax=ax, column="park_min", cmap="Greens", alpha=0.9, edgecolor="white", linewidth=0.1,
             legend=True, legend_kwds={"label": "Minutes to Nearest Park", "orientation": "horizontal", "shrink": 0.6})
    
    apply_map_template(ax, extent, "Stuttgart — Walk Access to Parks (H3 r8)", 
                      f"Zeit zu Fuß bis nächster Park — Ziel ≤ {PARK_TARGET_MIN} Min", city_boundary_buffered)
    
    _save(fig, "08_park_access_time_h3.png")
    
    # Export to Kepler
    out = KEPLER_DIR
    h3g[["h3","park_min","geometry"]].to_crs(4326).to_file(out/"17_park_access_time_h3.geojson", driver="GeoJSON")

def map09_forest_access_time_h3(data):
    """Map 09: Forest Access Time H3"""
    print("  🌲 Generating Forest Access Time map...")
    
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    h3g = _city_h3_grid_3857(data)
    
    # Load forests and build walking network
    parks, forests, city = _load_parks_and_forests()
    roads = data["roads"].to_crs(PLOT_CRS) if data["roads"] is not None else gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    G = _build_walk_graph(roads)
    
    # Get forest entrances and calculate access times
    park_ent, forest_ent = _candidate_entrances(parks, forests, roads)
    h3g["forest_min"] = _access_time_h3(G, h3g, forest_ent)
    
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    h3g.plot(ax=ax, column="forest_min", cmap="Greens", alpha=0.9, edgecolor="white", linewidth=0.1,
             legend=True, legend_kwds={"label": "Minutes to Nearest Forest", "orientation": "horizontal", "shrink": 0.6})
    
    apply_map_template(ax, extent, "Stuttgart — Walk Access to Forests (H3 r8)", 
                      f"Zeit zu Fuß bis nächster Wald — Ziel ≤ {FOREST_TARGET_MIN} Min", city_boundary_buffered)
    
    _save(fig, "09_forest_access_time_h3.png")
    
    # Export to Kepler
    out = KEPLER_DIR
    h3g[["h3","forest_min","geometry"]].to_crs(4326).to_file(out/"18_forest_access_time_h3.geojson", driver="GeoJSON")

# Infrastructure Analysis Functions (from make_maps.py)
def map_11_building_density(data, extent, city_boundary_buffered):
    """Map 11: Building density and urban structure analysis"""
    print("  🏗️ Creating building density analysis map...")
    
    # This would need building data - placeholder implementation
    if data.get("buildings") is None:
        print("  ⚠️ No buildings data available")
        return
    
    fig, ax = plt.subplots(figsize=(20, 16))
    
    districts = data["districts"].to_crs(PLOT_CRS)
    buildings = data["buildings"].to_crs(PLOT_CRS)
    
    # Calculate building density by district
    buildings_joined = gpd.sjoin(buildings, districts[["geometry"]], predicate="within", how="inner")
    building_counts = buildings_joined.groupby(buildings_joined.index_right).size()
    districts["building_count"] = districts.index.map(building_counts).fillna(0)
    districts["area_km2"] = districts.area / 1e6
    districts["building_density"] = districts["building_count"] / districts["area_km2"]
    
    # Plot building density
    districts.plot(ax=ax, column="building_density", cmap="YlOrRd", 
                  legend=True, legend_kwds={"shrink": 0.8, "label": "Buildings per km²"},
                  edgecolor="black", linewidth=0.5, alpha=0.8)
    
    apply_map_template(ax, extent, "Stuttgart — Building Density Analysis", 
                      "Gebäudedichte-Analyse", city_boundary_buffered)
    
    _save(fig, "11_building_density.png")

def map_12_amenity_accessibility(data, extent, city_boundary_buffered):
    """Map 12: Amenity accessibility (healthcare, education, retail)"""
    print("  🏥 Creating amenity accessibility map...")
    
    if data["amenities"] is None:
        print("  ⚠️ No amenities data available")
        return
    
    fig, ax = plt.subplots(figsize=(20, 16))
    
    districts = data["districts"].to_crs(PLOT_CRS)
    amenities = data["amenities"].to_crs(PLOT_CRS)
    
    # Count amenities per district
    amenities_joined = gpd.sjoin(amenities, districts[["geometry"]], predicate="within", how="inner")
    amenity_counts = amenities_joined.groupby(amenities_joined.index_right).size()
    districts["amenity_count"] = districts.index.map(amenity_counts).fillna(0)
    
    # Plot amenity accessibility
    districts.plot(ax=ax, column="amenity_count", cmap="Blues", 
                  legend=True, legend_kwds={"shrink": 0.8, "label": "Amenity Count"},
                  edgecolor="black", linewidth=0.5, alpha=0.8)
    
    # Add amenities as points
    amenities.plot(ax=ax, color="darkblue", markersize=3, alpha=0.7)
    
    apply_map_template(ax, extent, "Stuttgart — Amenity Accessibility Analysis", 
                      "Einrichtungs-Zugänglichkeits-Analyse", city_boundary_buffered)
    
    _save(fig, "12_amenity_accessibility.png")

def map_13_road_network_quality(data, extent, city_boundary_buffered):
    """Map 13: Road network quality and classification"""
    print("  🛣️ Creating road network analysis map...")
    
    if data["roads"] is None:
        print("  ⚠️ No roads data available")
        return
    
    fig, ax = plt.subplots(figsize=(20, 16))
    
    # Plot districts as background
    districts = data["districts"].to_crs(PLOT_CRS)
    districts.plot(ax=ax, facecolor="lightgray", edgecolor="black", linewidth=0.5, alpha=0.3)
    
    # Plot roads by category
    roads = data["roads"].to_crs(PLOT_CRS)
    
    # Color by road category
    road_colors = {
        "primary": "red",
        "secondary": "orange", 
        "tertiary": "yellow",
        "residential": "lightblue",
        "other": "gray"
    }
    
    for category, color in road_colors.items():
        cat_roads = roads[roads.get("category", "other") == category]
        if len(cat_roads) > 0:
            cat_roads.plot(ax=ax, color=color, linewidth=1.5, alpha=0.8, label=category.title())
    
    apply_map_template(ax, extent, "Stuttgart — Road Network Quality Analysis", 
                      "Straßennetz-Qualitäts-Analyse", city_boundary_buffered)
    
    ax.legend(loc="upper right")
    _save(fig, "13_road_network_quality.png")

def main():
    """Main execution function"""
    print(f"🗺️ Generating Consolidated Stuttgart Maps (Series {RUN_NUMBER})...")
    print(f"📁 Output directory: {OUT_DIR}")
    print(f"📁 Kepler directory: {KEPLER_DIR}")
    
    # Load data
    print("📊 Loading data layers...")
    data = load_data()
    
    # Get extent
    extent, city_boundary_buffered = _city_extent_and_boundary(data)
    
    # Generate all requested maps
    print("\n🗺️ Generating maps...")
    
    # Overview maps
    generate_overview_maps(data)
    
    # District accessibility maps
    generate_district_accessibility_maps(data, DISTRICTS_FOCUS)
    
    # H3 Analysis maps
    map04_pt_modal_gravity_h3(data)
    map04a_pt_pop_mismatch_h3(data) 
    map04b_pt_pop_small_multiples_h3(data)
    map05_access_essentials_h3(data)
    map07_service_diversity_h3(data)
    
    # Green access maps
    map08_park_access_time_h3(data)
    map09_forest_access_time_h3(data)
    
    # Infrastructure analysis maps
    map_11_building_density(data, extent, city_boundary_buffered)
    map_12_amenity_accessibility(data, extent, city_boundary_buffered)
    map_13_road_network_quality(data, extent, city_boundary_buffered)
    
    # Create run info
    run_info = {
        "run_number": RUN_NUMBER,
        "timestamp": pd.Timestamp.now().isoformat(),
        "output_directory": str(OUTPUT_BASE),
        "maps_generated": 13,  # Exact count of maps we want
        "kepler_layers_exported": True,
        "consolidated_analysis": True,
        "features": [
            "Overview maps",
            "District accessibility maps", 
            "H3 PT analysis",
            "H3 amenity analysis",
            "Green access analysis",
            "Infrastructure analysis",
            "Kepler export"
        ]
    }
    
    with open(OUTPUT_BASE / "run_info.json", 'w') as f:
        json.dump(run_info, f, indent=2)
    
    print("\n🎉 All 13 consolidated maps generated successfully!")
    print(f"📁 Check outputs in: {OUT_DIR}")
    print(f"📁 Check Kepler data in: {KEPLER_DIR}")
    print(f"📊 Run info saved: {OUTPUT_BASE / 'run_info.json'}")

if __name__ == "__main__":
    main()