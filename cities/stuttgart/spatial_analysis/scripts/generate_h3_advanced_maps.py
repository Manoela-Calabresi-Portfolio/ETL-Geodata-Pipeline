#!/usr/bin/env python3
"""
Generate advanced H3-based maps for Stuttgart analysis.
Based on the original stuttgart_maps_plus.py requirements but using the working H3 implementation.
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

# Import our working H3 modules
import sys
sys.path.append("../style_helpers")
sys.path.append("../utils")
from style_helpers import apply_style, palette
from h3_utils import hex_polygon, polyfill_gdf, cells_to_gdf
from h3_helpers import gdf_polygons_to_h3, h3_to_shapely_geometry

warnings.filterwarnings("ignore", category=UserWarning)

# Constants
DATA_DIR = Path("../data")

def get_next_output_dir():
    """Get the next available output directory in the series"""
    outputs_base = Path("outputs")
    if not outputs_base.exists():
        outputs_base.mkdir(parents=True, exist_ok=True)
    
    # Find existing stuttgart_maps_* directories
    existing_dirs = list(outputs_base.glob("stuttgart_maps_*"))
    if not existing_dirs:
        next_num = "001"
    else:
        # Extract numbers and find the highest
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

PLOT_CRS = 3857
OVERVIEW_PAD_M = 2000

# H3 Constants
H3_RES = 8
GRID_SIZE_M = 600
WALK_MIN = 15
WALK_SPEED_MPM = 80
WALK_BUFFER_M = WALK_MIN * WALK_SPEED_MPM
DISTRICTS_FOCUS = ["Mitte", "Nord", "Süd", "West", "Ost", "Bad Cannstatt"]

# PT Type Colors
PT_TYPE_COLORS = {
    "Tram":   "#C3423F",
    "U-Bahn": "#7D2E2E", 
    "S-Bahn": "#8B3A3A",
    "Bus":    "#DAA520",
    "Other":  "#777777"
}

# Weights for modal gravity
PT_WEIGHTS = {"S-Bahn": 3.0, "U-Bahn": 2.5, "Tram": 2.0, "Bus": 1.0, "Other": 0.5}

# Essential amenities
ESSENTIALS = {
    "amenity": {"supermarket", "pharmacy", "school", "hospital", "doctors", "clinic"},
    "shop": {"supermarket"},
    "healthcare": {"hospital", "clinic", "doctor", "doctors"}
}

# === NOVO: Acesso a Parques vs. Florestas (H3 r8) ============================
import networkx as nx
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

# Parâmetros
H3_RES = 8
BOUNDARY_SAMPLE_STEP_M = 80          # amostragem de "entradas" ao longo da borda
PARK_MIN_AREA_M2 = 10_000            # ≥ 1 ha
FOREST_MIN_AREA_M2 = 20_000          # ≥ 2 ha
PARK_TARGET_MIN = 10                 # cobertura alvo parque
FOREST_TARGET_MIN = 15               # cobertura alvo floresta
WALK_SPEED_MPM = 80                  # já definido; mantido aqui por clareza
CANDIDATE_ENTRANCES_K = 8            # nº de candidatos para Dijkstra por célula

PROCESSED_DIR = DATA_DIR / "processed"

def load_layers():
    """Load all required data layers"""
    layers = {}
    
    # Core layers
    layers["districts"] = _read_gdf(DATA_DIR / "districts_with_population.geojson")
    layers["boundary"] = _read_gdf(DATA_DIR / "city_boundary.geojson")
    layers["landuse"] = _read_gdf(DATA_DIR / "processed/landuse_categorized.parquet")
    layers["roads"] = _read_gdf(DATA_DIR / "processed/roads_categorized.parquet")
    layers["pt_stops"] = _read_gdf(DATA_DIR / "processed/pt_stops_categorized.parquet")
    layers["amenities"] = _read_gdf(DATA_DIR / "processed/amenities_categorized.parquet")
    
    # H3 population data
    h3_pop_path = DATA_DIR / "h3_population_res8.parquet"
    if h3_pop_path.exists():
        layers["h3_pop"] = pd.read_parquet(h3_pop_path)
    else:
        layers["h3_pop"] = None
    
    # Set CRS for GeoDataFrames
    for key, gdf in layers.items():
        if gdf is not None and hasattr(gdf, 'crs') and key != "h3_pop":
            if gdf.crs is None:
                layers[key] = gdf.set_crs(4326)
            else:
                layers[key] = gdf.to_crs(4326)
    
    return layers

def _read_gdf(path: Path):
    """Read geodataframe from various formats"""
    if not path.exists():
        return None
    try:
        if path.suffix.lower() in {".geojson", ".json", ".gpkg"}:
            return gpd.read_file(path)
        elif path.suffix.lower() == ".parquet":
            df = pd.read_parquet(path)
            if "geometry" in df.columns:
                if df['geometry'].dtype == 'object' and isinstance(df['geometry'].iloc[0], bytes):
                    from shapely import wkb
                    df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
                return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)
            else:
                return df
        else:
            return pd.read_parquet(path)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def _city_extent_and_boundary(data):
    """Get city extent and boundary"""
    if data["boundary"] is not None:
        boundary = data["boundary"].to_crs(PLOT_CRS)
        extent = boundary.total_bounds
        extent = [extent[0] - OVERVIEW_PAD_M, extent[1] - OVERVIEW_PAD_M,
                 extent[2] + OVERVIEW_PAD_M, extent[3] + OVERVIEW_PAD_M]
        return extent, boundary
    else:
        # Fallback to districts
        boundary = data["districts"].to_crs(PLOT_CRS)
        extent = boundary.total_bounds
        extent = [extent[0] - OVERVIEW_PAD_M, extent[1] - OVERVIEW_PAD_M,
                 extent[2] + OVERVIEW_PAD_M, extent[3] + OVERVIEW_PAD_M]
        return extent, boundary

def make_h3_cover(city_boundary_gdf, res=H3_RES):
    """Generate H3 hexagons covering the city using working implementation"""
    # Use the working H3 implementation
    city_wgs84 = city_boundary_gdf.to_crs(4326)
    
    # Get H3 cells using the working function
    hex_ids = polyfill_gdf(city_wgs84, res)
    
    # Create GeoDataFrame with H3 hexagons
    h3_gdf = cells_to_gdf(hex_ids, to_crs=PLOT_CRS)
    h3_gdf["area_m2"] = h3_gdf.geometry.area
    h3_gdf["centroid"] = h3_gdf.geometry.centroid
    
    print(f"  ✅ Generated {len(h3_gdf)} H3 hexagons (resolution {res})")
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

def ensure_pt_type(pt_gdf):
    """Ensure PT stops have type classification"""
    if pt_gdf is None or len(pt_gdf) == 0:
        return pt_gdf
    
    if "pt_type" not in pt_gdf.columns:
        pt_gdf = pt_gdf.copy()
        pt_gdf["pt_type"] = pt_gdf.apply(_classify_pt, axis=1)
    
    return pt_gdf

def h3_pt_modal_gravity(data, h3gdf):
    """Calculate PT modal gravity for H3 hexagons"""
    if data["pt_stops"] is None:
        h3gdf["pt_gravity"] = 0.0
        h3gdf["pt_gravity_norm"] = 0.0
        return h3gdf
    
    pt_stops = ensure_pt_type(data["pt_stops"].to_crs(PLOT_CRS))
    h3_centroids = gpd.GeoDataFrame(h3gdf[["h3"]].copy(), geometry=h3gdf["centroid"], crs=PLOT_CRS)
    
    # Calculate gravity for each hexagon
    gravity_scores = []
    
    for idx, hex_row in h3_centroids.iterrows():
        hex_point = hex_row.geometry
        total_gravity = 0.0
        
        for _, stop_row in pt_stops.iterrows():
            stop_point = stop_row.geometry
            distance = hex_point.distance(stop_point)
            
            if distance > 0:
                pt_type = stop_row.get("pt_type", "Other")
                weight = PT_WEIGHTS.get(pt_type, 0.5)
                gravity = weight / (distance ** 2)
                total_gravity += gravity
        
        gravity_scores.append(total_gravity)
    
    h3gdf = h3gdf.copy()
    h3gdf["pt_gravity"] = gravity_scores
    
    # Normalize
    max_gravity = max(gravity_scores) if gravity_scores else 1.0
    h3gdf["pt_gravity_norm"] = h3gdf["pt_gravity"] / max_gravity if max_gravity > 0 else 0.0
    
    return h3gdf

def _is_essential(row):
    """Check if amenity is essential"""
    for key, values in ESSENTIALS.items():
        if key in row and str(row[key]).lower() in values:
            return True
    return False

def h3_access_essentials(data, h3gdf):
    """Calculate access to essentials within 10-min walk for H3 hexagons"""
    if data.get("amenities") is None:
        h3gdf["ess_cov"] = 0.0
        return h3gdf
    
    amenities = data["amenities"].to_crs(PLOT_CRS)
    essentials = amenities[amenities.apply(_is_essential, axis=1)]
    
    if len(essentials) == 0:
        h3gdf["ess_cov"] = 0.0
        return h3gdf
    
    # Create 10-minute walking buffers around essentials
    walk_10min_m = 800  # 10 minutes at 80m/min
    essential_buffers = essentials.geometry.buffer(walk_10min_m)
    coverage_union = unary_union(essential_buffers)
    
    # Calculate coverage for each hexagon
    coverage_ratios = []
    for _, hex_row in h3gdf.iterrows():
        hex_geom = hex_row.geometry
        if coverage_union.intersects(hex_geom):
            intersection_area = hex_geom.intersection(coverage_union).area
            coverage_ratio = intersection_area / hex_geom.area
        else:
            coverage_ratio = 0.0
        coverage_ratios.append(min(coverage_ratio, 1.0))
    
    h3gdf = h3gdf.copy()
    h3gdf["ess_cov"] = coverage_ratios
    
    return h3gdf

def _add_basemap_custom(ax, extent, alpha=0.30):
    """Add CartoDB Positron basemap"""
    try:
        cx.add_basemap(ax, crs=PLOT_CRS, source=cx.providers.CartoDB.Positron, 
                      alpha=alpha, zoom='auto')
    except Exception as e:
        print(f"  ⚠️ Basemap failed: {e}")

def _add_scale_bar(ax, extent):
    """Add scale bar to map"""
    try:
        # Simple scale bar implementation
        x_range = extent[2] - extent[0]
        scale_length = 5000  # 5km
        bar_x = extent[0] + x_range * 0.05
        bar_y = extent[1] + (extent[3] - extent[1]) * 0.05
        
        ax.plot([bar_x, bar_x + scale_length], [bar_y, bar_y], 
                'k-', linewidth=3, solid_capstyle='butt')
        ax.text(bar_x + scale_length/2, bar_y + 200, '5 km', 
                ha='center', va='bottom', fontsize=8, weight='bold')
    except Exception as e:
        print(f"  ⚠️ Scale bar failed: {e}")

def _save_map(fig, filename):
    """Save map to outputs directory"""
    filepath = OUT_DIR / filename
    fig.savefig(filepath, dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"  ✅ Saved: {filename}")

def _h3_poly(h):
    # Use our working H3 implementation
    return h3_to_shapely_geometry(h)

def make_h3_cover(city_poly_wgs, res=H3_RES):
    # Use our working H3 implementation
    if hasattr(city_poly_wgs, 'geometry'):
        # If it's already a GeoDataFrame, use it directly
        hex_ids = polyfill_gdf(city_poly_wgs, res)
    else:
        # If it's a single geometry, wrap it in a GeoDataFrame
        hex_ids = polyfill_gdf(gpd.GeoDataFrame(geometry=[city_poly_wgs], crs=4326), res)
    
    gdf = cells_to_gdf(hex_ids, to_crs=PLOT_CRS)
    gdf["centroid"] = gdf.geometry.centroid
    gdf["area_m2"] = gdf.geometry.area
    return gdf

def _build_walk_graph(roads_gdf):
    """Grafo de caminhada (leve): inclui vias caminháveis e caminhos; exclui motorways puras."""
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
                w = LineString([na, nb]).length
                if w > 0: G.add_edge(na, nb, weight=w)
    # cache de nós para buscas rápidas
    _nearest_graph_node._arr = np.array(list(G.nodes)) if len(G) else np.empty((0,2))
    return G

def _nearest_graph_node(G, pt):
    arr = _nearest_graph_node._arr
    if arr.size == 0: 
        return None
    d = np.hypot(arr[:,0]-pt.x, arr[:,1]-pt.y)
    return tuple(arr[int(np.argmin(d))])

def _sample_boundary_points(polys, step_m=BOUNDARY_SAMPLE_STEP_M):
    """Amostra pontos ao longo da borda dos polígonos (≈ "entradas" genéricas)."""
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
    """Carrega/deriva parques e florestas; corta pela cidade; aplica área mínima."""
    districts = gpd.read_file(DATA_DIR/"districts_with_population.geojson").to_crs(PLOT_CRS)
    city = districts.unary_union.buffer(100)

    # Parques
    parks = None
    pfile = PROCESSED_DIR / "parks_extracted_osmnx.parquet"
    if pfile.exists():
        parks = gpd.read_parquet(pfile).to_crs(PLOT_CRS)
    else:
        gfile = PROCESSED_DIR / "green_areas_categorized.parquet"
        if gfile.exists():
            g = gpd.read_parquet(gfile).to_crs(PLOT_CRS)
            parks = g[(g.get("osm_tag_key","")== "leisure") & (g.get("osm_tag_value","")== "park")].copy()
    if parks is None: parks = gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    parks = parks[parks.geometry.type.isin(["Polygon","MultiPolygon"])]
    parks["geometry"] = parks.geometry.intersection(city)
    parks = parks[~parks.geometry.is_empty]
    parks["area_m2"] = parks.geometry.area
    parks = parks[parks["area_m2"] >= PARK_MIN_AREA_M2]

    # Florestas
    forests = None
    if (DATA_DIR/"processed/landuse_categorized.parquet").exists():
        lu = gpd.read_parquet(DATA_DIR/"processed/landuse_categorized.parquet").to_crs(PLOT_CRS)
    else:
        lu = gpd.read_file(DATA_DIR/"processed/landuse_categorized.parquet") if (DATA_DIR/"processed/landuse_categorized.parquet").exists() else None

    if lu is not None:
        for col in ["landuse","natural"]:
            if col not in lu.columns: lu[col] = ""
        forests = lu[(lu["landuse"].astype(str).str.lower()=="forest") | (lu["natural"].astype(str).str.lower().isin(["wood","forest"]))].copy()
    else:
        forests = gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)

    forests = forests[forests.geometry.type.isin(["Polygon","MultiPolygon"])]
    forests["geometry"] = forests.geometry.intersection(city)
    forests = forests[~forests.geometry.is_empty]
    forests["area_m2"] = forests.geometry.area
    forests = forests[forests["area_m2"] >= FOREST_MIN_AREA_M2]

    return parks, forests, city

def _candidate_entrances(parks, forests, roads):
    """Retorna pontos de acesso candidatos para parques e florestas."""
    # 1) interseções foot/caminháveis com bordas (quando possível)
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

    # 2) fallback: amostrar borda
    if park_int.empty:
        park_int = _sample_boundary_points(parks)
    if forest_int.empty:
        forest_int = _sample_boundary_points(forests)

    return park_int, forest_int

def _access_time_h3(G, h3gdf, target_points, minutes_cap=None):
    """Minutos na rede (a 80 m/min) do centróide do hex até o target mais próximo."""
    if target_points.empty or len(G)==0:
        return pd.Series([np.nan]*len(h3gdf), index=h3gdf.index)

    # nós de destino no grafo
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
            times.append(np.nan); continue
        # top-K candidatos euclidianos
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
                tmin = min(tmin, minutes_cap)  # trunca legenda, se quiser
            times.append(tmin)
    return pd.Series(times, index=h3gdf.index)

def generate_h3_pt_gravity_map(data):
    """Generate H3 PT Modal Gravity map"""
    print("🧩 Generating H3 PT Modal Gravity map...")
    
    extent, boundary = _city_extent_and_boundary(data)
    h3_gdf = make_h3_cover(boundary, res=H3_RES)
    h3_with_gravity = h3_pt_modal_gravity(data, h3_gdf)
    
    # Create map
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.30)
    
    # Plot H3 hexagons with gravity scores
    if len(h3_with_gravity) > 0:
        h3_with_gravity.plot(ax=ax, column='pt_gravity_norm', 
                           cmap='Reds', alpha=0.7, edgecolor='white', linewidth=0.1,
                           legend=True, legend_kwds={'shrink': 0.8})
    
    # Add boundary
    if boundary is not None:
        boundary.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=2)
    
    # Add PT stops
    if data["pt_stops"] is not None:
        pt_stops = ensure_pt_type(data["pt_stops"].to_crs(PLOT_CRS))
        for pt_type, color in PT_TYPE_COLORS.items():
            type_stops = pt_stops[pt_stops["pt_type"] == pt_type]
            if len(type_stops) > 0:
                type_stops.plot(ax=ax, color=color, markersize=15, alpha=0.8, label=pt_type)
    
    ax.set_title("Stuttgart — PT Modal Gravity (H3 r8)", fontsize=16, weight='bold', pad=20)
    ax.set_xlabel("Σ (Weight / Distance²), S>U>Tram>Bus — H3 Raster r8", fontsize=12)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    # Add legend
    ax.legend(loc='upper right', bbox_to_anchor=(0.98, 0.98))
    
    _save_map(fig, "04_pt_modal_gravity_h3.png")
    
    # Export to Kepler
    try:
        kepler_data = h3_with_gravity[["h3", "pt_gravity", "pt_gravity_norm", "geometry"]].to_crs(4326)
        kepler_data.to_file(KEPLER_DIR / "h3_pt_gravity.geojson", driver='GeoJSON')
        print("  ✅ Exported to Kepler: h3_pt_gravity.geojson")
    except Exception as e:
        print(f"  ⚠️ Kepler export failed: {e}")

def generate_h3_essentials_map(data):
    """Generate H3 Access to Essentials map"""
    print("🧩 Generating H3 Access to Essentials map...")
    
    extent, boundary = _city_extent_and_boundary(data)
    h3_gdf = make_h3_cover(boundary, res=H3_RES)
    h3_with_essentials = h3_access_essentials(data, h3_gdf)
    
    # Create map
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.30)
    
    # Plot H3 hexagons with essentials coverage
    if len(h3_with_essentials) > 0:
        h3_with_essentials.plot(ax=ax, column='ess_cov', 
                              cmap='Greens', alpha=0.7, edgecolor='white', linewidth=0.1,
                              legend=True, legend_kwds={'shrink': 0.8})
    
    # Add boundary
    if boundary is not None:
        boundary.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=2)
    
    # Add essential amenities
    if data.get("amenities") is not None:
        amenities = data["amenities"].to_crs(PLOT_CRS)
        essentials = amenities[amenities.apply(_is_essential, axis=1)]
        if len(essentials) > 0:
            essentials.plot(ax=ax, color='darkgreen', markersize=20, alpha=0.8, label='Essentials')
    
    ax.set_title("Stuttgart — Essentials within 10-min Walk (H3 r8)", fontsize=16, weight='bold', pad=20)
    ax.set_xlabel("Coverage ratio: Supermarkets, Pharmacies, Schools, Hospitals", fontsize=12)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    # Add legend
    ax.legend(loc='upper right', bbox_to_anchor=(0.98, 0.98))
    
    _save_map(fig, "04b_access_essentials_h3.png")
    
    # Export to Kepler
    try:
        kepler_data = h3_with_essentials[["h3", "ess_cov", "geometry"]].to_crs(4326)
        kepler_data.to_file(KEPLER_DIR / "h3_essentials_access.geojson", driver='GeoJSON')
        print("  ✅ Exported to Kepler: h3_essentials_access.geojson")
    except Exception as e:
        print(f"  ⚠️ Kepler export failed: {e}")

def generate_population_pt_grid_map(data):
    """Generate population density vs PT stops grid map"""
    print("🗺️ Generating Population vs PT Density Grid map...")
    
    extent, boundary = _city_extent_and_boundary(data)
    
    # Create regular grid
    x_min, y_min, x_max, y_max = extent
    cell_size = GRID_SIZE_M
    
    x_coords = np.arange(x_min, x_max, cell_size)
    y_coords = np.arange(y_min, y_max, cell_size)
    
    grid_cells = []
    for x in x_coords:
        for y in y_coords:
            cell_poly = box(x, y, x + cell_size, y + cell_size)
            grid_cells.append(cell_poly)
    
    grid_gdf = gpd.GeoDataFrame({'geometry': grid_cells}, crs=PLOT_CRS)
    
    # Clip to city boundary
    if boundary is not None:
        grid_gdf = gpd.overlay(grid_gdf, boundary, how='intersection')
    
    # Calculate population density using H3 data if available
    if data["h3_pop"] is not None:
        h3_pop = data["h3_pop"]
        # Convert H3 to GeoDataFrame
        h3_polys = [h3_to_shapely_geometry(h) for h in h3_pop["h3"]]
        h3_gdf = gpd.GeoDataFrame(h3_pop, geometry=h3_polys, crs=4326).to_crs(PLOT_CRS)
        
        # Spatial join to get population for grid cells
        grid_with_pop = gpd.sjoin(grid_gdf, h3_gdf, how='left', predicate='intersects')
        pop_by_grid = grid_with_pop.groupby(grid_with_pop.index)['pop'].sum().fillna(0)
        grid_gdf['population'] = pop_by_grid
    else:
        grid_gdf['population'] = 0
    
    # Calculate PT stop density
    if data["pt_stops"] is not None:
        pt_stops = data["pt_stops"].to_crs(PLOT_CRS)
        pt_joined = gpd.sjoin(pt_stops, grid_gdf, how='right', predicate='within')
        if 'index_right' in pt_joined.columns:
            pt_counts = pt_joined.groupby(pt_joined['index_right']).size().fillna(0)
        else:
            pt_counts = pt_joined.groupby(pt_joined.index).size().fillna(0)
        grid_gdf['pt_density'] = pt_counts
    else:
        grid_gdf['pt_density'] = 0
    
    # Create map
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.30)
    
    # Plot population density as background
    if 'population' in grid_gdf.columns and grid_gdf['population'].sum() > 0:
        grid_gdf.plot(ax=ax, column='population', cmap='Blues', alpha=0.5, 
                     edgecolor='white', linewidth=0.1, legend=True, 
                     legend_kwds={'shrink': 0.8, 'label': 'Population'})
    
    # Plot PT density as overlay
    if 'pt_density' in grid_gdf.columns and grid_gdf['pt_density'].sum() > 0:
        pt_grid = grid_gdf[grid_gdf['pt_density'] > 0]
        pt_grid.plot(ax=ax, column='pt_density', cmap='Reds', alpha=0.7,
                    edgecolor='white', linewidth=0.1)
    
    # Add boundary
    if boundary is not None:
        boundary.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=2)
    
    ax.set_title("Stuttgart — Population Density vs PT Stop Density", fontsize=16, weight='bold', pad=20)
    ax.set_xlabel(f"Grid: {GRID_SIZE_M}m cells | Blue: Population | Red: PT Stops", fontsize=12)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    _save_map(fig, "02_pop_vs_pt_density_grid.png")

def generate_h3_green_access_maps(data):
    """Gera mapas H3 de acesso a PARQUES e FLORESTAS"""
    print("🌳 Gerando acesso a parques vs florestas (H3 r8)…")

    # polígono cidade (WGS84) e H3
    dists = data["districts"].to_crs(4326)
    city_poly_wgs = gpd.GeoSeries([dists.unary_union], crs=4326).iloc[0]
    h3g = make_h3_cover(city_poly_wgs, res=H3_RES)  # CRS=3857

    # recortes/template
    extent, boundary = _city_extent_and_boundary(data)

    # camadas verdes
    parks, forests, city = _load_parks_and_forests()
    if parks.empty and forests.empty:
        print("⚠️ Sem parques/florestas detectados — abortando mapas verdes.")
        return

    # rede caminhável
    roads = data["roads"].to_crs(PLOT_CRS) if data["roads"] is not None else gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    G = _build_walk_graph(roads)

    # "entradas"
    park_ent, forest_ent = _candidate_entrances(parks, forests, roads)

    # tempos mínimos por hex
    h3g = h3g.copy()
    h3g["tmin_park"] = _access_time_h3(G, h3g, park_ent)
    h3g["tmin_forest"] = _access_time_h3(G, h3g, forest_ent)

    # coberturas binárias e "gap"
    h3g["cov_park_10"] = (h3g["tmin_park"] <= PARK_TARGET_MIN).fillna(False)
    h3g["cov_forest_15"] = (h3g["tmin_forest"] <= FOREST_TARGET_MIN).fillna(False)
    h3g["green_gap"] = ~(h3g["cov_park_10"] | h3g["cov_forest_15"])

    # 8) tempo até parque
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g.plot(ax=ax, column="tmin_park", cmap="Greens", linewidth=0, alpha=0.9,
             legend=True, legend_kwds={"label":"Minutos a pé até PARQUE","orientation":"horizontal","shrink":0.6})
    
    # Add boundary
    if boundary is not None:
        boundary.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=2)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.30)
    
    ax.set_title("Stuttgart — Walk Access to Parks (H3 r8)", fontsize=16, weight='bold', pad=20)
    ax.set_xlabel(f"Zeit zu Fuß bis nächster Park — Ziel ≤ {PARK_TARGET_MIN} Min", fontsize=12)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    _save_map(fig, "08_park_access_time_h3.png")

    # 9) tempo até floresta
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g.plot(ax=ax, column="tmin_forest", cmap="Greens", linewidth=0, alpha=0.9,
             legend=True, legend_kwds={"label":"Minutos a pé até FLORESTA","orientation":"horizontal","shrink":0.6})
    
    # Add boundary
    if boundary is not None:
        boundary.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=2)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.30)
    
    ax.set_title("Stuttgart — Walk Access to Forests (H3 r8)", fontsize=16, weight='bold', pad=20)
    ax.set_xlabel(f"Zeit zu Fuß bis nächster Wald — Ziel ≤ {FOREST_TARGET_MIN} Min", fontsize=12)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    _save_map(fig, "09_forest_access_time_h3.png")

    # 10) gaps combinados
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g[~h3g["green_gap"]].plot(ax=ax, color="#9DC183", alpha=0.35, linewidth=0)  # cobertos
    h3g[h3g["green_gap"]].plot(ax=ax, color="#C3423F", alpha=0.85, linewidth=0)   # descobertos
    
    # Add boundary
    if boundary is not None:
        boundary.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=2)
    
    # Add basemap
    _add_basemap_custom(ax, extent, alpha=0.30)
    
    ax.set_title("Stuttgart — Green Access Gaps (Parks ≤10' OR Forests ≤15')", fontsize=16, weight='bold', pad=20)
    ax.set_xlabel("Hexagone rot = ohne Park (≤10 Min) UND ohne Wald (≤15 Min)", fontsize=12)
    ax.axis('off')
    
    # Add scale bar
    _add_scale_bar(ax, extent)
    
    # Add legend
    from matplotlib.patches import Rectangle
    ax.legend(handles=[
        Rectangle((0,0),1,1, fc="#9DC183", alpha=0.35, label="Covered"),
        Rectangle((0,0),1,1, fc="#C3423F", alpha=0.85, label="Uncovered")
    ], loc="lower right", frameon=True, fontsize=9, title="Legend")
    
    _save_map(fig, "10_green_gaps_h3.png")

    # exporta para Kepler
    try:
        kepler_data = h3g[["h3","tmin_park","cov_park_10","geometry"]].to_crs(4326)
        kepler_data.to_file(KEPLER_DIR / "15_h3_park_access.geojson", driver="GeoJSON")
        
        kepler_data = h3g[["h3","tmin_forest","cov_forest_15","geometry"]].to_crs(4326)
        kepler_data.to_file(KEPLER_DIR / "16_h3_forest_access.geojson", driver="GeoJSON")
        
        kepler_data = h3g[["h3","green_gap","geometry"]].to_crs(4326)
        kepler_data.to_file(KEPLER_DIR / "17_h3_green_gaps.geojson", driver="GeoJSON")
        
        print("  ✅ Exported: 15_h3_park_access.geojson, 16_h3_forest_access.geojson, 17_h3_green_gaps.geojson")
    except Exception as e:
        print(f"  ⚠️ Kepler export (green access) falhou: {e}")

def main():
    """Main execution function"""
    print("🚀 Generating Advanced H3 Maps for Stuttgart...")
    
    # Load data
    print("📊 Loading data layers...")
    data = load_layers()
    
    # Generate maps
    generate_h3_pt_gravity_map(data)
    generate_h3_essentials_map(data)
    generate_population_pt_grid_map(data)
    
    print("\n🌳 Generating Green Access (parks vs forests)…")
    generate_h3_green_access_maps(data)
    
    print("🎉 All advanced H3 maps generated successfully!")
    print(f"📁 Check outputs in: {OUT_DIR}")
    print(f"📁 Kepler data in: {KEPLER_DIR}")

if __name__ == "__main__":
    main()
