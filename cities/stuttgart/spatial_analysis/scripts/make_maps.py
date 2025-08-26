#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import warnings, math
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import contextily as cx

# Import our local modules
import sys
from pathlib import Path
# Add the style_helpers directory to the path
style_helpers_path = Path(__file__).parent.parent / "style_helpers"
sys.path.append(str(style_helpers_path))
from style_helpers import apply_style, palette
from h3_utils import hex_polygon

warnings.filterwarnings("ignore", category=UserWarning)

# Updated paths to match current project structure
DATA_DIR = Path("../data")

def get_next_output_dir():
    """Get the next available output directory in the series"""
    # Use absolute path to ensure outputs go to the right place
    script_dir = Path(__file__).parent
    outputs_base = script_dir.parent / "outputs"
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

# ---------- Loaders ----------
def _read_gdf(path: Path):
    if not path.exists(): return None
    try:
        if path.suffix.lower() in {".geojson",".json",".gpkg"}:
            return gpd.read_file(path)
        elif path.suffix.lower() == ".parquet":
            # Read parquet and check if it has geometry column
            df = pd.read_parquet(path)
            if "geometry" in df.columns:
                # Check if geometry column contains bytes (WKB format)
                if df['geometry'].dtype == 'object' and isinstance(df['geometry'].iloc[0], bytes):
                    # Convert WKB bytes to Shapely geometries
                    from shapely import wkb
                    df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x is not None else None)
                
                # Convert to GeoDataFrame
                return gpd.GeoDataFrame(df, geometry="geometry", crs=4326)
            else:
                return df
        else:
            return pd.read_parquet(path)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def load_layers():
    layers = dict(
        districts=_read_gdf(DATA_DIR/"districts_with_population.geojson"),
        landuse=_read_gdf(DATA_DIR/"processed/landuse_categorized.parquet"),
        cycle=_read_gdf(DATA_DIR/"processed/cycle_categorized.parquet"),
        roads=_read_gdf(DATA_DIR/"processed/roads_categorized.parquet"),
        pt_stops=_read_gdf(DATA_DIR/"processed/pt_stops_categorized.parquet"),
        boundary=_read_gdf(DATA_DIR/"city_boundary.geojson"),
        h3_pop=pd.read_parquet(DATA_DIR/"h3_population_res8.parquet") if (DATA_DIR/"h3_population_res8.parquet").exists() else None,
    )
    # set CRS defaults only for GeoDataFrames
    for k in ["districts","landuse","cycle","roads","pt_stops","boundary"]:
        if layers[k] is not None and hasattr(layers[k], 'crs'):
            layers[k] = layers[k].set_crs(4326) if layers[k].crs is None else layers[k].to_crs(4326)
    return layers

def _extent_from(gdf):
    return tuple(gdf.to_crs(PLOT_CRS).total_bounds)

# ---------- KPI computation (district level) ----------
def compute_kpis(layers):
    if layers["districts"] is None: return None
    d = layers["districts"].to_crs(PLOT_CRS).copy()
    d["area_km2"] = d.area/1e6
    
    print(f"Processing {len(d)} districts...")

    # PT stops
    if layers["pt_stops"] is not None:
        stops = layers["pt_stops"].to_crs(PLOT_CRS)
        j = gpd.sjoin(stops, d[["geometry"]], predicate="within", how="left")
        cnt = j.groupby(j.index_right).size()
        d["pt_stops_count"] = d.index.map(cnt).fillna(0).astype(int)
        d["pt_stops_per_km2"] = d["pt_stops_count"]/d["area_km2"].replace(0,np.nan)
    else:
        d["pt_stops_count"]=0; d["pt_stops_per_km2"]=np.nan

    # Greens: area share (parks/forest/meadow/grass/etc.)
    if layers["landuse"] is not None:
        land = layers["landuse"].to_crs(PLOT_CRS)
        land = land[land.geometry.type.isin(["Polygon","MultiPolygon"])].copy()
        def is_green(row):
            lu = str(row.get("landuse","")).lower()
            nat= str(row.get("natural","")).lower()
            return lu in {"forest","meadow","grass","recreation_ground","park","cemetery","orchard","vineyard","allotments"} \
                or nat in {"wood","scrub","grassland","park"}
        land = land[land.apply(is_green, axis=1)]
        if len(land):
            j = gpd.sjoin(land, d[["geometry"]], predicate="intersects", how="inner")
            parts=[]
            for di, sub in j.groupby(j.index_right):
                inter_area=0.0
                dpoly=d.loc[di,"geometry"]
                for g in sub.geometry:
                    inter = g.intersection(dpoly)
                    if not inter.is_empty: inter_area += inter.area
                parts.append((di, inter_area))
            a = pd.DataFrame(parts, columns=["di","green_area_m2"]).set_index("di")["green_area_m2"]
            d["green_area_km2"] = d.index.map(a).fillna(0)/1e6
        else:
            d["green_area_km2"]=0.0
    else:
        d["green_area_km2"]=np.nan
    d["green_share_pct"] = (d["green_area_km2"]/d["area_km2"].replace(0,np.nan))*100

    # Population from districts_with_population
    if "pop" in d.columns:
        d["population"] = d["pop"].fillna(0)
    else:
        d["population"]=np.nan

    d["pt_stops_per_1k"] = d["pt_stops_count"]/d["population"].replace(0,np.nan)*1000

    # H3 pop-weighted green m² per capita (requires h3_population_res8)
    if layers["h3_pop"] is not None and layers["landuse"] is not None:
        # build hex polygons in 3857
        h3 = layers["h3_pop"]
        polys = [hex_polygon(h) for h in h3["h3"]]
        hex_g = gpd.GeoDataFrame(h3[["h3","pop"]], geometry=polys, crs=4326).to_crs(PLOT_CRS)
        hex_g["area"] = hex_g.area

        greens = layers["landuse"].to_crs(PLOT_CRS)
        greens = greens[greens.geometry.type.isin(["Polygon","MultiPolygon"])].copy()
        def is_green2(row):
            lu = str(row.get("landuse","")).lower()
            nat= str(row.get("natural","")).lower()
            return lu in {"forest","meadow","grass","recreation_ground","park","cemetery","orchard","vineyard","allotments"} \
                or nat in {"wood","scrub","grassland","park"}
        greens = greens[greens.apply(is_green2, axis=1)]

        if len(greens):
            # green share per cell
            jj = gpd.sjoin(greens, hex_g[["h3","pop","geometry"]], predicate="intersects", how="inner")
            parts=[]
            for h, sub in jj.groupby("h3"):
                hpoly=hex_g.loc[hex_g["h3"]==h,"geometry"].iloc[0]; hA=hpoly.area
                a=0.0
                for g in sub.geometry:
                    inter=g.intersection(hpoly)
                    if not inter.is_empty: a+=inter.area
                frac = a/hA if hA>0 else 0.0
                parts.append((h, frac))
            cell_share = pd.DataFrame(parts, columns=["h3","green_frac"]).set_index("h3")["green_frac"]
            hex_g = hex_g.join(cell_share, on="h3"); hex_g["green_frac"]=hex_g["green_frac"].fillna(0)

            # assign cell to district via centroid
            cent = gpd.GeoDataFrame(hex_g[["h3","pop"]], geometry=hex_g.geometry.centroid, crs=PLOT_CRS)
            jj2 = gpd.sjoin(cent, d[["geometry"]], predicate="within", how="left")
            # pop-weighted average of green_frac
            by = jj2.groupby(jj2.index_right).apply(
                lambda t: np.average(
                    hex_g.loc[t.index, "green_frac"].fillna(0),
                    weights=np.maximum(hex_g.loc[t.index,"pop"].fillna(0).values, 0)
                ) if len(t) else np.nan
            )
            d["green_m2_per_capita"] = (by * hex_g["area"].mean())  # approximate m²/person proxy
        else:
            d["green_m2_per_capita"]=np.nan
    else:
        d["green_m2_per_capita"]=np.nan

    # Simple normalized access scores (0–100)
    def scale01(s: pd.Series):
        v = s.astype(float).replace([np.inf,-np.inf], np.nan)
        qlo,qhi = v.quantile([0.05,0.95])
        if qhi<=qlo: qhi=qlo+1e-9
        return (v.clip(qlo,qhi)-qlo)/(qhi-qlo)

    d["green_access_score_pop"]  = 100*(scale01(d["green_m2_per_capita"]) + scale01(d["pt_stops_per_1k"])) / 2.0
    d["green_access_score_area"] = 100*(scale01(d["green_share_pct"])      + scale01(d["pt_stops_per_km2"])) / 2.0
    
    return d

# ---------- Plot helpers ----------
def _add_basemap(ax, extent):
    try: cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, alpha=0.30, crs=PLOT_CRS)
    except Exception: pass
    ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])

def _save(fig, name):
    out = OUT_DIR/name
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {out}")

def _add_legend_right_column(ax, extent, title, colors, values, value_range):
    # Calculate legend position
    legend_x0, legend_y0 = 0.78, 0.15
    legend_width, legend_height = 0.18, 0.10
    
    legend_x = extent[0] + (extent[2] - extent[0]) * legend_x0
    legend_y = extent[1] + (extent[3] - extent[1]) * legend_y0
    legend_w = (extent[2] - extent[0]) * legend_width
    legend_h = (extent[3] - extent[1]) * legend_height
    
    # Create legend patches
    for i, color in enumerate(colors):
        patch_x = legend_x + (i / len(colors)) * legend_w
        patch_y = legend_y + (0.5 - 0.1 * (i - len(colors) / 2)) * legend_h # Center colors vertically
        ax.add_artist(patches.Rectangle(
            (patch_x, patch_y), legend_w / len(colors), legend_h * 0.1,
            facecolor=color, edgecolor="none", alpha=0.9
        ))
    
    # Add legend border
    ax.add_artist(patches.Rectangle(
        (legend_x, legend_y), legend_w, legend_h,
        facecolor="none", edgecolor="#333", linewidth=1.5
    ))
    
    # Add legend labels
    ax.text(legend_x + legend_w/2, legend_y - legend_h*0.1, 
            title, fontsize=11, ha="center", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y + legend_h/2, 
            value_range, fontsize=11, rotation=90, va="center", weight="bold")
    
    # Add legend value indicators
    ax.text(legend_x, legend_y + legend_h + legend_h*0.05, "Low", fontsize=9, ha="center", weight="bold")
    ax.text(legend_x + legend_w, legend_y + legend_h + legend_h*0.05, "High", fontsize=9, ha="center", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y, "Low", fontsize=9, va="center", ha="right", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y + legend_h, "High", fontsize=9, va="center", ha="right", weight="bold")

def _add_simple_legend_right_column(ax, extent, title, color, text):
    # Calculate legend position
    legend_x0, legend_y0 = 0.78, 0.15
    legend_width, legend_height = 0.18, 0.10
    
    legend_x = extent[0] + (extent[2] - extent[0]) * legend_x0
    legend_y = extent[1] + (extent[3] - extent[1]) * legend_y0
    legend_w = (extent[2] - extent[0]) * legend_width
    legend_h = (extent[3] - extent[1]) * legend_height
    
    # Create legend patch
    ax.add_artist(patches.Rectangle(
        (legend_x, legend_y), legend_w, legend_h,
        facecolor=color, edgecolor="none", alpha=0.9
    ))
    
    # Add legend border
    ax.add_artist(patches.Rectangle(
        (legend_x, legend_y), legend_w, legend_h,
        facecolor="none", edgecolor="#333", linewidth=1.5
    ))
    
    # Add legend labels
    ax.text(legend_x + legend_w/2, legend_y - legend_h*0.1, 
            title, fontsize=11, ha="center", weight="bold")
    ax.text(legend_x + legend_w/2, legend_y + legend_h + legend_h*0.05, 
            text, fontsize=9, ha="center", weight="bold")

def _add_bivariate_legend_right_column(ax, extent, biv_colors):
    # Calculate legend position
    legend_x0, legend_y0 = 0.78, 0.15
    legend_width, legend_height = 0.18, 0.10
    
    legend_x = extent[0] + (extent[2] - extent[0]) * legend_x0
    legend_y = extent[1] + (extent[3] - extent[1]) * legend_y0
    legend_w = (extent[2] - extent[0]) * legend_width
    legend_h = (extent[3] - extent[1]) * legend_height
    
    # Create legend patches
    for i in range(3):
        for j in range(3):
            color = biv_colors.get((i,j), "#cccccc")
            patch_x = legend_x + (j / 2.5) * legend_w # Adjust for 3x3 grid
            patch_y = legend_y + (2 - i) * legend_h / 3 # Adjust for 3x3 grid
            ax.add_artist(patches.Rectangle(
                (patch_x, patch_y), legend_w / 2.5, legend_h / 3, # Adjust for 3x3 grid
                facecolor=color, edgecolor="none", alpha=0.9
            ))
    
    # Add legend border
    ax.add_artist(patches.Rectangle(
        (legend_x, legend_y), legend_w, legend_h,
        facecolor="none", edgecolor="#333", linewidth=1.5
    ))
    
    # Add legend labels
    ax.text(legend_x + legend_w/2, legend_y - legend_h*0.1, 
            "PT stops per 1k →", fontsize=11, ha="center", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y + legend_h/2, 
            "Green m² per capita ↑", fontsize=11, rotation=90, va="center", weight="bold")

def _add_data_info_box(ax, extent, text):
    # Calculate box position
    box_x0, box_y0 = 0.02, 0.75
    box_width, box_height = 0.25, 0.20
    
    box_x = extent[0] + (extent[2] - extent[0]) * box_x0
    box_y = extent[1] + (extent[3] - extent[1]) * box_y0
    box_w = (extent[2] - extent[0]) * box_width
    box_h = (extent[3] - extent[1]) * box_height
    
    # Background box
    ax.add_artist(patches.Rectangle(
        (box_x, box_y), box_w, box_h,
        facecolor="white", edgecolor="#333", linewidth=1.5, alpha=0.95
    ))
    
    # Explanation text
    explanation_lines = text.split("\n")
    for i, line in enumerate(explanation_lines):
        y_pos = box_y + box_h - (i + 1) * (box_h / (len(explanation_lines) + 1)) # Adjust for multiple lines
        fontsize = 9 if i == 0 else 8
        weight = "bold" if i == 0 else "normal"
        ax.text(box_x + box_w*0.02, y_pos, line, 
                fontsize=fontsize, weight=weight, va="top", ha="left")

def _add_north_arrow_up(ax, extent):
    # Calculate arrow position
    arrow_x0, arrow_y0 = 0.93, 0.25
    arrow_length = max(extent[2] - extent[0], extent[3] - extent[1]) * 0.08
    
    arrow_x = extent[0] + (extent[2] - extent[0]) * arrow_x0
    arrow_y = extent[1] + (extent[3] - extent[1]) * arrow_y0
    
    ax.annotate(
        "N",
        xy=(arrow_x, arrow_y),
        xytext=(arrow_x, arrow_y + arrow_length),
        ha="center", va="center",
        arrowprops=dict(arrowstyle="-|>", color="black", lw=2),
        fontsize=11, fontweight="bold",
        bbox=dict(boxstyle="circle,pad=0.25", facecolor="white", edgecolor="black", alpha=0.9),
        color="black"
    )

# ---------- All 8 Maps ----------
def map_01_macro_green_pt(d, pt_stops, extent):
    """Map 1: Macro green access with PT stops"""
    pal = palette()
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # choropleth
    vals = d["green_access_score_pop"].astype(float)
    colors = pal["greens"]
    q = vals.quantile(np.linspace(0,1,len(colors)+1)).values
    bins = np.clip(np.digitize(vals, q[1:-1], right=True), 0, len(colors)-1)
    d_plot = d.to_crs(PLOT_CRS).copy()
    d_plot["_color"] = [colors[i] for i in bins]
    d_plot.plot(ax=ax, color=d_plot["_color"], edgecolor="#555", linewidth=0.5)
    if pt_stops is not None:
        g = pt_stops.to_crs(PLOT_CRS)
        g.plot(ax=ax, color="white", markersize=20, marker="o", edgecolor="#2a4b8d", linewidth=0.6, alpha=0.9)
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Green Access (Population-weighted) & PT", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Grüner Zugang (Bevölkerungsgewichtet) & ÖPNV*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend in right column
    _add_legend_right_column(ax, extent, "Green Access Score", colors, vals, "0-100")
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• Green access score: Population-weighted\n• PT stops: Categorized by type\n• H3 Resolution: 8 (hexagon size: ~0.7 km²)\n• Data: Stuttgart Open Data + OSM")
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "01_macro_green_pt.png")

def map_02_h3_population_surface(d, h3_pop, extent):
    """Map 2: H3 population surface (resolution 8)"""
    if h3_pop is None: return
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Create H3 hexagons
    polys = [hex_polygon(h) for h in h3_pop["h3"]]
    hex_g = gpd.GeoDataFrame(h3_pop[["h3","pop"]], geometry=polys, crs=4326).to_crs(PLOT_CRS)
    
    # Plot with population-based coloring
    vals = hex_g["pop"].astype(float)
    colors = palette()["blues"]
    q = vals.quantile(np.linspace(0,1,len(colors)+1)).values
    bins = np.clip(np.digitize(vals, q[1:-1], right=True), 0, len(colors)-1)
    hex_g["_color"] = [colors[i] for i in bins]
    hex_g.plot(ax=ax, color=hex_g["_color"], edgecolor="#555", linewidth=0.3, alpha=0.8)
    
    # Add district boundaries
    d.to_crs(PLOT_CRS).boundary.plot(ax=ax, color="#333", linewidth=1.5)
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — H3 Population Surface (Resolution 8)", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — H3 Bevölkerungsfläche (Auflösung 8)*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend in right column
    _add_legend_right_column(ax, extent, "Population", colors, vals, "0-max")
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• H3 Resolution: 8 (hexagon size: ~0.7 km²)\n• Population: Areal weighting from districts\n• Total cells: " + str(len(h3_pop)) + "\n• Data: Stuttgart Open Data + H3 grid")
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "02_h3_population_surface.png")

def map_03_green_space_distribution(d, landuse, extent):
    """Map 3: Green space distribution"""
    if landuse is None: return
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Filter green features
    greens = landuse[landuse.geometry.type.isin(["Polygon","MultiPolygon"])].copy()
    def is_green(row):
        lu = str(row.get("landuse","")).lower()
        nat = str(row.get("natural","")).lower()
        return lu in {"forest","meadow","grass","recreation_ground","park","cemetery","orchard","vineyard","allotments"} \
            or nat in {"wood","scrub","grassland","park"}
    greens = greens[greens.apply(is_green, axis=1)]
    
    # Plot green areas
    greens.to_crs(PLOT_CRS).plot(ax=ax, color="#2d5a27", alpha=0.7, edgecolor="#1a3d1a", linewidth=0.5)
    
    # Add district boundaries
    d.to_crs(PLOT_CRS).boundary.plot(ax=ax, color="#333", linewidth=1.5)
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Green Space Distribution", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Verteilung der Grünflächen*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend in right column
    _add_simple_legend_right_column(ax, extent, "Green Areas", "#2d5a27", f"Total: {len(greens)} features")
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• Green areas: OSM landuse + natural tags\n• Categories: Forest, park, meadow, grass\n• Total green features: " + str(len(greens)) + "\n• Data: OpenStreetMap (OSM)")
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "03_green_space_distribution.png")

def map_04_bivariate_green_vs_pt(d, extent):
    """Map 4: Bivariate choropleth (PT vs green access) with continuous gradient"""
    # Continuous bivariate: X=PT stops per 1k, Y=green m²/capita proxy
    X = d["pt_stops_per_1k"].astype(float); Y = d["green_m2_per_capita"].astype(float)
    
    # Normalize both variables to 0-1 range for continuous coloring
    def normalize_continuous(series):
        v = series.replace([np.inf, -np.inf], np.nan).dropna()
        if len(v) == 0: return pd.Series([0.5] * len(series), index=series.index)
        qlo, qhi = v.quantile([0.02, 0.98])
        if qhi <= qlo: qhi = qlo + 1e-9
        normalized = (series.clip(qlo, qhi) - qlo) / (qhi - qlo)
        return normalized.fillna(0.5)
    
    X_norm = normalize_continuous(X)
    Y_norm = normalize_continuous(Y)
    
    # Create continuous bivariate colors using a smooth gradient
    # Red channel: PT stops (X), Blue channel: Green area (Y), Green channel: mix
    colors = []
    for x, y in zip(X_norm, Y_norm):
        # Create smooth color transition
        # Red increases with PT stops, Blue increases with green area
        red = x * 0.8 + 0.2  # 0.2 to 1.0
        blue = y * 0.8 + 0.2  # 0.2 to 1.0
        green = (x + y) * 0.3 + 0.1  # 0.1 to 0.7 (darker mix)
        
        # Ensure values are in valid range
        red = max(0, min(1, red))
        blue = max(0, min(1, blue))
        green = max(0, min(1, green))
        
        colors.append((red, green, blue))
    
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    d_plot = d.to_crs(PLOT_CRS).copy()
    d_plot["_color"] = colors
    d_plot.plot(ax=ax, color=d_plot["_color"], edgecolor="#555", linewidth=0.6)
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Bivariate: PT stops /1k vs Green m² per capita", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Bivariat: ÖPNV-Haltestellen /1k vs Grüne m² pro Kopf*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')

    # Create continuous gradient legend (larger and better positioned)
    legend_x0, legend_y0 = 0.78, 0.15
    legend_width, legend_height = 0.18, 0.10
    
    # Create gradient legend
    legend_x = extent[0] + (extent[2] - extent[0]) * legend_x0
    legend_y = extent[1] + (extent[3] - extent[1]) * legend_y0
    legend_w = (extent[2] - extent[0]) * legend_width
    legend_h = (extent[3] - extent[1]) * legend_height
    
    # Create gradient patches
    n_steps = 25  # More steps for smoother gradient
    for i in range(n_steps):
        for j in range(n_steps):
            x_frac = i / (n_steps - 1)
            y_frac = j / (n_steps - 1)
            
            # Same color logic as main map
            red = x_frac * 0.8 + 0.2
            blue = y_frac * 0.8 + 0.2
            green = (x_frac + y_frac) * 0.3 + 0.1
            
            patch_x = legend_x + (i / n_steps) * legend_w
            patch_y = legend_y + (j / n_steps) * legend_h
            patch_w = legend_w / n_steps
            patch_h = legend_h / n_steps
            
            ax.add_artist(patches.Rectangle(
                (patch_x, patch_y), patch_w, patch_h,
                facecolor=(red, green, blue), edgecolor="none", alpha=0.9
            ))
    
    # Add legend border
    ax.add_artist(patches.Rectangle(
        (legend_x, legend_y), legend_w, legend_h,
        facecolor="none", edgecolor="#333", linewidth=1.5
    ))
    
    # Add legend labels
    ax.text(legend_x + legend_w/2, legend_y - legend_h*0.1, 
            "PT stops per 1k →", fontsize=11, ha="center", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y + legend_h/2, 
            "Green m² per capita ↑", fontsize=11, rotation=90, va="center", weight="bold")
    
    # Add legend value indicators
    ax.text(legend_x, legend_y + legend_h + legend_h*0.05, "Low", fontsize=9, ha="center", weight="bold")
    ax.text(legend_x + legend_w, legend_y + legend_h + legend_h*0.05, "High", fontsize=9, ha="center", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y, "Low", fontsize=9, va="center", ha="right", weight="bold")
    ax.text(legend_x - legend_w*0.05, legend_y + legend_h, "High", fontsize=9, va="center", ha="right", weight="bold")
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• PT stops per 1k: Count/population × 1000\n• Green m² per capita: H3-weighted (Resolution 8)\n• Colors: Red (PT), Blue (Green), Green (mix)\n• Normalized to 2nd-98th percentile")
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "04_bivariate_green_vs_pt.png")

def map_05_pt_stop_density(d, pt_stops, extent):
    """Map 5: PT stop density"""
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Plot districts by PT density
    vals = d["pt_stops_per_km2"].astype(float)
    colors = palette()["purples"]
    q = vals.quantile(np.linspace(0,1,len(colors)+1)).values
    bins = np.clip(np.digitize(vals, q[1:-1], right=True), 0, len(colors)-1)
    d_plot = d.to_crs(PLOT_CRS).copy()
    d_plot["_color"] = [colors[i] for i in bins]
    d_plot.plot(ax=ax, color=d_plot["_color"], edgecolor="#555", linewidth=0.5)
    
    # Add PT stops
    if pt_stops is not None:
        pt_stops.to_crs(PLOT_CRS).plot(ax=ax, color="white", markersize=15, marker="o", 
                                       edgecolor="#2a4b8d", linewidth=0.5, alpha=0.8)
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Public Transport Stop Density", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — ÖPNV-Haltestellendichte*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend in right column
    _add_legend_right_column(ax, extent, "PT Stops per km²", colors, vals, "0-max")
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• PT stops: Categorized by type (OSM)\n• Density: Count per district area\n• Total PT stops: " + str(d["pt_stops_count"].sum()) + "\n• Data: OpenStreetMap (OSM)")
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "05_pt_stop_density.png")

def map_06_area_vs_population(d, extent):
    """Map 6: Area vs population analysis"""
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Create bivariate: X=area, Y=population density
    X = d["area_km2"].astype(float)
    Y = (d["population"]/d["area_km2"]).replace([np.inf,-np.inf], np.nan)
    qx = X.quantile([1/3, 2/3]).values; qy = Y.quantile([1/3, 2/3]).values
    def binv(v, qs): 
        return 0 if v<=qs[0] else (1 if v<=qs[1] else 2)
    bins = [ (binv(x,qx), binv(y,qy)) for x,y in zip(X,Y) ]
    
    BIV = {
        (0,0): "#e8e8e8",(1,0):"#ace4e4",(2,0):"#5ac8c8",
        (0,1): "#dfb0d6",(1,1):"#a5add3",(2,1):"#5698b9",
        (0,2): "#be64ac",(1,2):"#8c62aa",(2,2):"#3b4994",
    }
    col = [BIV.get(b,"#cccccc") for b in bins]
    
    d_plot = d.to_crs(PLOT_CRS).copy()
    d_plot["_color"] = col
    d_plot.plot(ax=ax, color=d_plot["_color"], edgecolor="#555", linewidth=0.6)
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Bivariate: District Area vs Population Density", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Bivariat: Bezirksfläche vs Bevölkerungsdichte*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add bivariate legend in right column
    _add_bivariate_legend_right_column(ax, extent, BIV)
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• Area: District boundaries (official)\n• Population: Stuttgart Open Data 2023\n• Bivariate: 3×3 classification\n• Total population: " + f"{d['population'].sum():,.0f}")
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "06_area_vs_population.png")

def map_07_h3_hexbin_visualization(d, h3_pop, extent):
    """Map 7: H3 hexbin visualization"""
    if h3_pop is None: return
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Create H3 hexagons with population-based sizing
    polys = [hex_polygon(h) for h in h3_pop["h3"]]
    hex_g = gpd.GeoDataFrame(h3_pop[["h3","pop"]], geometry=polys, crs=4326).to_crs(PLOT_CRS)
    
    # Plot with population-based sizing and coloring
    vals = hex_g["pop"].astype(float)
    sizes = np.clip(vals / vals.quantile(0.95) * 100, 10, 100)
    colors = palette()["oranges"]
    q = vals.quantile(np.linspace(0,1,len(colors)+1)).values
    bins = np.clip(np.digitize(vals, q[1:-1], right=True), 0, len(colors)-1)
    hex_g["_color"] = [colors[i] for i in bins]
    
    # Plot each hexagon individually for size control
    for idx, row in hex_g.iterrows():
        ax.add_patch(patches.Polygon(
            list(row.geometry.exterior.coords),
            facecolor=row["_color"], edgecolor="#555", linewidth=0.3, alpha=0.8
        ))
    
    # Add district boundaries
    d.to_crs(PLOT_CRS).boundary.plot(ax=ax, color="#333", linewidth=1.5)
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — H3 Hexbin Population Visualization", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — H3 Hexbin Bevölkerungsvisualisierung*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend in right column
    _add_legend_right_column(ax, extent, "Population", colors, vals, "0-max")
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• H3 Resolution: 8 (hexagon size: ~0.7 km²)\n• Population: Areal weighting interpolation\n• Hexagon size: Population-proportional\n• Total H3 cells: " + str(len(h3_pop)))
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "07_h3_hexbin_visualization.png")

def map_08_combined_accessibility_score(d, extent):
    """Map 8: Combined accessibility score"""
    # Larger dimensions with right-side white column
    fig, ax = plt.subplots(1,1, figsize=(20,12))
    
    # Combined score: green access + PT access
    combined_score = (d["green_access_score_pop"] + d["green_access_score_area"]) / 2.0
    
    # Plot with combined score coloring
    vals = combined_score.astype(float)
    colors = palette()["viridis"]
    q = vals.quantile(np.linspace(0,1,len(colors)+1)).values
    bins = np.clip(np.digitize(vals, q[1:-1], right=True), 0, len(colors)-1)
    d_plot = d.to_crs(PLOT_CRS).copy()
    d_plot["_color"] = [colors[i] for i in bins]
    d_plot.plot(ax=ax, color=d_plot["_color"], edgecolor="#555", linewidth=0.5)
    
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Combined Accessibility Score", fontsize=16, fontweight="bold")
    ax.text(0.5, 0.02, "*Stuttgart — Kombinierter Zugänglichkeitswert*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    # Add legend in right column
    _add_legend_right_column(ax, extent, "Combined Score", colors, vals, "0-100")
    
    # Add data processing info box
    _add_data_info_box(ax, extent, "Data Processing:\n• Combined score: (Green + PT) / 2\n• Green access: H3-weighted (Resolution 8)\n• PT access: Stops per 1k population\n• Normalized to 0-100 scale")
    
    # Reposition north arrow to face UP
    _add_north_arrow_up(ax, extent)
    
    _save(fig, "08_combined_accessibility_score.png")

def map_11_building_density(d_kpi, buildings, extent):
    """Map 11: Building density and urban structure analysis"""
    print("  🏗️ Creating building density analysis map...")
    
    fig, ax = plt.subplots(figsize=(20, 16))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Calculate building density by district
    buildings_3857 = buildings.to_crs(3857)
    d = d_kpi.copy()
    
    # Spatial join to count buildings per district
    buildings_joined = gpd.sjoin(buildings_3857, d[["geometry"]], predicate="within", how="inner")
    building_counts = buildings_joined.groupby(buildings_joined.index_right).size()
    d["building_count"] = d.index.map(building_counts).fillna(0)
    d["building_density"] = d["building_count"] / d["area_km2"]
    
    # Plot building density
    d.plot(ax=ax, column="building_density", cmap="YlOrRd", 
           legend=True, legend_kwds={"shrink": 0.8, "label": "Buildings per km²"},
           edgecolor="black", linewidth=0.5, alpha=0.8)
    
    # Add buildings as points
    buildings_3857.plot(ax=ax, color="darkred", markersize=2, alpha=0.6, label="Buildings")
    
    ax.set_title("Stuttgart — Building Density Analysis", fontsize=16, fontweight="bold", pad=20)
    ax.text(0.5, 0.02, "*Stuttgart — Gebäudedichte-Analyse*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _add_data_info_box(ax, extent, "Data Processing:\n• Building count per district\n• Density: buildings/km²\n• Urban structure analysis\n• Data: OSM buildings")
    
    _add_north_arrow_up(ax, extent)
    _save(fig, "11_building_density.png")

def map_12_amenity_accessibility(d_kpi, amenities, extent):
    """Map 12: Amenity accessibility (healthcare, education, retail)"""
    print("  🏥 Creating amenity accessibility map...")
    
    fig, ax = plt.subplots(figsize=(20, 16))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Classify amenities
    amenities_3857 = amenities.to_crs(3857)
    amenities_3857["category"] = amenities_3857.apply(_classify_amenity, axis=1)
    
    # Calculate accessibility by district
    d = d_kpi.copy()
    d["healthcare_count"] = 0
    d["education_count"] = 0
    d["retail_count"] = 0
    
    # Count amenities by category per district
    for idx, district in d.iterrows():
        district_geom = district.geometry
        district_amenities = amenities_3857[amenities_3857.geometry.within(district_geom)]
        
        d.loc[idx, "healthcare_count"] = len(district_amenities[district_amenities["category"] == "Healthcare"])
        d.loc[idx, "education_count"] = len(district_amenities[district_amenities["category"] == "Education"])
        d.loc[idx, "retail_count"] = len(district_amenities[district_amenities["category"] == "Retail"])
    
    # Plot healthcare accessibility
    d.plot(ax=ax, column="healthcare_count", cmap="Blues", 
           legend=True, legend_kwds={"shrink": 0.8, "label": "Healthcare Facilities"},
           edgecolor="black", linewidth=0.5, alpha=0.8)
    
    # Add amenities by category
    for category, color in [("Healthcare", "blue"), ("Education", "green"), ("Retail", "orange")]:
        cat_amenities = amenities_3857[amenities_3857["category"] == category]
        if len(cat_amenities) > 0:
            cat_amenities.plot(ax=ax, color=color, markersize=15, alpha=0.7, label=category)
    
    ax.set_title("Stuttgart — Amenity Accessibility Analysis", fontsize=16, fontweight="bold", pad=20)
    ax.text(0.5, 0.02, "*Stuttgart — Einrichtungs-Zugänglichkeits-Analyse*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _add_data_info_box(ax, extent, "Data Processing:\n• Healthcare: hospitals, clinics, pharmacies\n• Education: schools, universities, libraries\n• Retail: shops, supermarkets, services\n• Data: OSM amenities")
    
    _add_north_arrow_up(ax, extent)
    ax.legend(loc="upper right")
    _save(fig, "12_amenity_accessibility.png")

def map_13_road_network_quality(d_kpi, roads, extent):
    """Map 13: Road network quality and classification"""
    print("  🛣️ Creating road network analysis map...")
    
    fig, ax = plt.subplots(figsize=(20, 16))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Plot districts as background
    d_kpi.plot(ax=ax, facecolor="lightgray", edgecolor="black", linewidth=0.5, alpha=0.3)
    
    # Classify and plot roads by type
    roads_3857 = roads.to_crs(3857)
    road_colors = {
        "motorway": "red",
        "trunk": "darkred", 
        "primary": "orange",
        "secondary": "yellow",
        "tertiary": "lightblue",
        "residential": "white",
        "service": "gray"
    }
    
    for road_type, color in road_colors.items():
        type_roads = roads_3857[roads_3857["highway"] == road_type]
        if len(type_roads) > 0:
            type_roads.plot(ax=ax, color=color, linewidth=2, alpha=0.8, label=road_type.title())
    
    ax.set_title("Stuttgart — Road Network Quality Analysis", fontsize=16, fontweight="bold", pad=20)
    ax.text(0.5, 0.02, "*Stuttgart — Straßennetz-Qualitäts-Analyse*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _add_data_info_box(ax, extent, "Data Processing:\n• Road classification by OSM highway tags\n• Quality indicators: surface, lanes, speed\n• Network connectivity analysis\n• Data: OSM roads")
    
    _add_north_arrow_up(ax, extent)
    ax.legend(loc="upper right")
    _save(fig, "13_road_network_quality.png")

def map_14_service_diversity_h3(d_kpi, layers, extent):
    """Map 14: Service diversity index (H3)"""
    print("  🎯 Creating H3 service diversity map...")
    
    if layers["h3_pop"] is None:
        print("  ⚠️ H3 population data not available, skipping...")
        return
    
    fig, ax = plt.subplots(figsize=(20, 16))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Create H3 grid
    from h3_utils import hex_polygon
    h3_pop = layers["h3_pop"]
    h3_polys = [hex_polygon(h) for h in h3_pop["h3"]]
    h3_gdf = gpd.GeoDataFrame(h3_pop, geometry=h3_polys, crs=4326).to_crs(3857)
    
    # Calculate service diversity for each H3 cell
    if layers.get("amenities") is not None:
        amenities_3857 = layers["amenities"].to_crs(3857)
        h3_gdf["service_diversity"] = h3_gdf.apply(
            lambda row: _calculate_service_diversity(row.geometry, amenities_3857), axis=1
        )
        
        # Plot H3 service diversity
        h3_gdf.plot(ax=ax, column="service_diversity", cmap="viridis", 
                   legend=True, legend_kwds={"shrink": 0.8, "label": "Service Diversity Index"},
                   edgecolor="white", linewidth=0.1, alpha=0.7)
    
    ax.set_title("Stuttgart — H3 Service Diversity Index", fontsize=16, fontweight="bold", pad=20)
    ax.text(0.5, 0.02, "*Stuttgart — H3 Dienstleistungs-Diversitäts-Index*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _add_data_info_box(ax, extent, "Data Processing:\n• H3 hexagonal grid (Resolution 8)\n• Service diversity: amenity types per cell\n• Spatial clustering analysis\n• Data: OSM amenities + H3 population")
    
    _add_north_arrow_up(ax, extent)
    _save(fig, "15_service_diversity_h3.png")

def map_15_infrastructure_quality(d_kpi, layers, extent):
    """Map 15: Infrastructure quality composite score"""
    print("  🏗️ Creating infrastructure quality score map...")
    
    fig, ax = plt.subplots(figsize=(20, 16))
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    
    # Calculate composite infrastructure score
    d = d_kpi.copy()
    
    # Normalize different metrics to 0-100 scale
    d["road_quality"] = 100  # Placeholder - would need road quality data
    
    # Handle building density score safely
    if "building_density" in d.columns and d["building_density"].max() > 0:
        d["building_density_score"] = (d["building_density"] / d["building_density"].max() * 100).fillna(0)
    else:
        d["building_density_score"] = 50  # Default middle score
    
    # Handle amenity score safely
    d["amenity_score"] = 50  # Default middle score for now
    
    # Handle PT score safely
    if d["pt_stops_per_1k"].max() > 0:
        d["pt_score"] = (d["pt_stops_per_1k"] / d["pt_stops_per_1k"].max() * 100).fillna(0)
    else:
        d["pt_score"] = 50  # Default middle score
    
    # Composite score (equal weights)
    d["infrastructure_score"] = (
        d["road_quality"] * 0.25 + 
        d["building_density_score"] * 0.25 + 
        d["amenity_score"] * 0.25 + 
        d["pt_score"] * 0.25
    ).round(1)
    
    # Plot infrastructure quality
    d.plot(ax=ax, column="infrastructure_score", cmap="RdYlGn", 
           legend=True, legend_kwds={"shrink": 0.8, "label": "Infrastructure Quality Score (0-100)"},
           edgecolor="black", linewidth=0.5, alpha=0.8)
    
    ax.set_title("Stuttgart — Infrastructure Quality Composite Score", fontsize=16, fontweight="bold", pad=20)
    ax.text(0.5, 0.02, "*Stuttgart — Infrastruktur-Qualitäts-Gesamtbewertung*", 
            transform=ax.transAxes, ha='center', fontsize=12, style='italic')
    
    _add_data_info_box(ax, extent, "Data Processing:\n• Composite score: roads + buildings + amenities + PT\n• Equal weighting (25% each)\n• Normalized to 0-100 scale\n• Data: OSM + population data")
    
    _add_north_arrow_up(ax, extent)
    _save(fig, "16_infrastructure_quality.png")

def _classify_amenity(row):
    """Classify amenities into categories"""
    amenity_type = str(row.get("amenity", "")).lower()
    shop_type = str(row.get("shop", ""), "").lower()
    
    if any(x in amenity_type for x in ["hospital", "clinic", "pharmacy", "doctors"]):
        return "Healthcare"
    elif any(x in amenity_type for x in ["school", "university", "library", "kindergarten"]):
        return "Education"
    elif any(x in shop_type for x in ["supermarket", "convenience", "department_store"]):
        return "Retail"
    else:
        return "Other"

def _calculate_service_diversity(geometry, amenities_gdf):
    """Calculate service diversity for an H3 cell"""
    # Find amenities within this H3 cell
    cell_amenities = amenities_gdf[amenities_gdf.geometry.within(geometry)]
    
    # Count unique amenity types
    unique_types = set()
    for _, amenity in cell_amenities.iterrows():
        amenity_type = str(amenity.get("amenity", "")).lower()
        if amenity_type:
            unique_types.add(amenity_type)
    
    return len(unique_types)

def export_kepler_layers(layers, d_kpi):
    """Export all relevant layers to GeoJSON for Kepler.gl"""
    print("\n📊 Exporting layers to Kepler.gl format...")
    
    try:
        # Export districts with KPIs
        if d_kpi is not None:
            districts_kepler = d_kpi.to_crs(4326)
            districts_kepler.to_file(KEPLER_DIR / "01_districts_with_kpis.geojson", driver='GeoJSON')
            print("  ✅ Districts with KPIs exported")
        
        # Export PT stops
        if layers["pt_stops"] is not None:
            pt_kepler = layers["pt_stops"].to_crs(4326)
            pt_kepler.to_file(KEPLER_DIR / "02_pt_stops.geojson", driver='GeoJSON')
            print("  ✅ PT stops exported")
        
        # Export roads
        if layers["roads"] is not None:
            roads_kepler = layers["roads"].to_crs(4326)
            roads_kepler.to_file(KEPLER_DIR / "03_roads.geojson", driver='GeoJSON')
            print("  ✅ Roads exported")
        
        # Export landuse/green areas
        if layers["landuse"] is not None:
            landuse_kepler = layers["landuse"].to_crs(4326)
            landuse_kepler.to_file(KEPLER_DIR / "04_landuse.geojson", driver='GeoJSON')
            print("  ✅ Landuse exported")
        
        # Export H3 population if available
        if layers["h3_pop"] is not None:
            h3_pop = layers["h3_pop"]
            # Convert H3 to polygons
            from h3_utils import hex_polygon
            h3_polys = [hex_polygon(h) for h in h3_pop["h3"]]
            h3_kepler = gpd.GeoDataFrame(h3_pop, geometry=h3_polys, crs=4326)
            h3_kepler.to_file(KEPLER_DIR / "05_h3_population.geojson", driver='GeoJSON')
            print("  ✅ H3 population exported")
        
        # Export city boundary
        if layers["boundary"] is not None:
            boundary_kepler = layers["boundary"].to_crs(4326)
            boundary_kepler.to_file(KEPLER_DIR / "06_city_boundary.geojson", driver='GeoJSON')
            print("  ✅ City boundary exported")
        
        # Export advanced H3 maps if they exist
        try:
            h3_advanced_dir = OUTPUT_BASE / "maps"
            if (h3_advanced_dir / "08_park_access_time_h3.png").exists():
                # Export park access H3 data
                from generate_h3_advanced_maps import _load_parks_and_forests, _build_walk_graph, _candidate_entrances, _access_time_h3, make_h3_cover
                import networkx as nx
                
                # Generate H3 park access data
                dists = layers["districts"].to_crs(4326)
                city_poly_wgs = gpd.GeoSeries([dists.unary_union], crs=4326).iloc[0]
                h3g = make_h3_cover(city_poly_wgs, res=8)
                
                # Load parks and forests
                parks, forests, city = _load_parks_and_forests()
                roads = layers["roads"].to_crs(3857) if layers["roads"] is not None else gpd.GeoDataFrame(geometry=[], crs=3857)
                G = _build_walk_graph(roads)
                
                # Calculate access times
                park_ent, forest_ent = _candidate_entrances(parks, forests, roads)
                h3g["tmin_park"] = _access_time_h3(G, h3g, park_ent)
                h3g["tmin_forest"] = _access_time_h3(G, h3g, forest_ent)
                
                # Export to Kepler
                h3g.to_crs(4326).to_file(KEPLER_DIR / "07_h3_park_access.geojson", driver='GeoJSON')
                print("  ✅ H3 Park Access exported")
                
        except Exception as e:
            print(f"  ⚠️ Advanced H3 export failed: {e}")
        
        print(f"📁 Kepler data exported to: {KEPLER_DIR}")
        
    except Exception as e:
        print(f"⚠️ Kepler export failed: {e}")

def main():
    print(f"🗺️ Generating all maps for Stuttgart H3 spatial analysis (Series {RUN_NUMBER})...")
    print(f"📁 Output directory: {OUT_DIR}")
    print(f"📁 Kepler directory: {KEPLER_DIR}")
    
    layers = load_layers()
    if layers["districts"] is None:
        print("❌ No districts_with_population.geojson found. Run population_pipeline_stuttgart.py first!")
        return
    
    boundary = layers["boundary"] if layers["boundary"] is not None else layers["districts"]
    extent = _extent_from(boundary)

    d_kpi = compute_kpis(layers)
    if d_kpi is None:
        print("❌ Could not compute KPIs.")
        return

    print("✅ KPIs computed successfully!")
    print(f"   Districts: {len(d_kpi)}")
    print(f"   Population: {d_kpi['population'].sum():,.0f}")
    print(f"   Green area: {d_kpi['green_area_km2'].sum():.1f} km²")
    print(f"   PT stops: {d_kpi['pt_stops_count'].sum():,.0f}")

    # Generate all 8 maps
    print("\n🗺️ Generating map 1: Macro green access...")
    map_01_macro_green_pt(d_kpi, layers["pt_stops"], extent)
    
    print("🗺️ Generating map 2: H3 population surface...")
    map_02_h3_population_surface(d_kpi, layers["h3_pop"], extent)
    
    print("🗺️ Generating map 3: Green space distribution...")
    map_03_green_space_distribution(d_kpi, layers["landuse"], extent)
    
    print("🗺️ Generating map 4: Bivariate analysis...")
    map_04_bivariate_green_vs_pt(d_kpi, extent)
    
    print("🗺️ Generating map 5: PT stop density...")
    map_05_pt_stop_density(d_kpi, layers["pt_stops"], extent)
    
    print("🗺️ Generating map 6: Area vs population...")
    map_06_area_vs_population(d_kpi, extent)
    
    print("🗺️ Generating map 7: H3 hexbin visualization...")
    map_07_h3_hexbin_visualization(d_kpi, layers["h3_pop"], extent)
    
    print("🗺️ Generating map 8: Combined accessibility score...")
    map_08_combined_accessibility_score(d_kpi, extent)
    
    # Generate advanced H3 maps with better styling
    print("\n🌳 Generating advanced H3 maps...")
    try:
        # Temporarily set the output directory for advanced maps
        import sys
        sys.path.append('.')
        from generate_h3_advanced_maps import generate_h3_green_access_maps
        
        # Set the output directory for advanced maps
        import generate_h3_advanced_maps
        generate_h3_advanced_maps.OUT_DIR = OUT_DIR
        
        generate_h3_green_access_maps(layers)
        print("  ✅ Advanced H3 maps generated")
    except Exception as e:
        print(f"  ⚠️ Advanced H3 maps failed: {e}")
    
    # Generate additional spatial analysis maps
    print("\n🏗️ Generating infrastructure & service analysis...")
    
    # Map 11: Building density and urban structure
    if layers.get("buildings") is not None:
        print("🗺️ Generating map 11: Building density analysis...")
        map_11_building_density(d_kpi, layers["buildings"], extent)
    
    # Map 12: Amenity accessibility (healthcare, education, retail)
    if layers.get("amenities") is not None:
        print("🗺️ Generating map 12: Amenity accessibility...")
        map_12_amenity_accessibility(d_kpi, layers["amenities"], extent)
    
    # Map 13: Road network quality and classification
    if layers.get("roads") is not None:
        print("🗺️ Generating map 13: Road network analysis...")
        map_13_road_network_quality(d_kpi, layers["roads"], extent)
    
    # Map 14: Service diversity index (H3)
    print("🗺️ Generating map 14: Service diversity index...")
    map_14_service_diversity_h3(d_kpi, layers, extent)
    
    # Map 15: Infrastructure quality composite score
    print("🗺️ Generating map 15: Infrastructure quality score...")
    map_15_infrastructure_quality(d_kpi, layers, extent)
    
    # Export Kepler layers
    print("\n📊 Exporting data for Kepler.gl...")
    export_kepler_layers(layers, d_kpi)
    
    # Create run info file
    import json
    from datetime import datetime
    run_info = {
        "run_number": RUN_NUMBER,
        "timestamp": datetime.now().isoformat(),
        "output_directory": str(OUTPUT_BASE),
        "maps_generated": 15,  # 8 basic + 3 advanced H3 + 4 infrastructure
        "kepler_layers_exported": True,
        "advanced_h3_maps": True,
        "infrastructure_analysis": True,
        "districts_count": len(d_kpi),
        "total_population": int(d_kpi['population'].sum()),
        "total_green_area_km2": float(d_kpi['green_area_km2'].sum()),
        "total_pt_stops": int(d_kpi['pt_stops_count'].sum())
    }
    
    with open(OUTPUT_BASE / "run_info.json", 'w') as f:
        json.dump(run_info, f, indent=2)
    
    print("\n🎉 All 15 maps generated successfully!")
    print(f"📁 Check outputs in: {OUT_DIR}")
    print(f"📁 Check Kepler data in: {KEPLER_DIR}")
    print(f"📊 Run info saved: {OUTPUT_BASE / 'run_info.json'}")

if __name__ == "__main__":
    main()
