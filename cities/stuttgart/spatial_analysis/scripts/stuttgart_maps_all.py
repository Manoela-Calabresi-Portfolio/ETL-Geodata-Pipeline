#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stuttgart Urban Analysis Suite — FULL

Gera:
01_overview_landuse_roads_pt.png
01b_overview_population_density_roads_pt.png
02_pop_vs_pt_density_grid.png
03_access_<district>.png  (6 distritos foco)

H3 (04–10):
04_pt_modal_gravity_h3.png
05_access_essentials_h3.png
06_detour_factor_h3.png
07_service_diversity_h3.png
08_park_access_time_h3.png
09_forest_access_time_h3.png
10_green_gaps_h3.png

Extras de leitura (sem sobreposição de gradientes):
04a_mismatch_diverging_h3.png
04b_small_multiples_h3.png
"""

from __future__ import annotations
from pathlib import Path
import warnings, json, sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point, box, Polygon, LineString
from shapely import wkb
import jinja2  # (usado no dashboard)
warnings.filterwarnings("ignore", category=UserWarning)

# ======== dependências opcionais usadas nos patches ========
try:
    import h3
except Exception:
    h3 = None

# caminhos (ajuste se necessário)
DATA_DIR = Path("../data")

# helpers externos (opcional; apenas para alguns mapas coropléticos)
sys.path.append('..')
try:
    from style_helpers.style_helpers import apply_style, palette  # opcional
except Exception:
    def apply_style(ax, extent): pass
    palette = {}

# ---------- config geral ----------
PLOT_CRS = 3857
SELECTED_DISTRICTS = ["Mitte", "Bad Cannstatt", "Vaihingen", "Zuffenhausen", "Degerloch"]
DISTRICTS_FOCUS = ["Mitte", "Nord", "Süd", "West", "Ost", "Bad Cannstatt"]

# OVERVIEW (Mapa 01)
OVERVIEW_PAD_M = 4000
PT_MARKERSIZE = 9
ROAD_LW = 0.5
ROAD_ALPHA = 0.30
PT_ALPHA = 0.80

# grid (Mapa 02)
GRID_SIZE_M = 600
WALK_SPEED_MPM = 80
WALK_MIN = 15
WALK_BUFFER_M = WALK_MIN * WALK_SPEED_MPM

PT_TYPE_COLORS = {
    "Tram":   "#C3423F",
    "U-Bahn": "#7D2E2E",
    "S-Bahn": "#8B3A3A",
    "Bus":    "#DAA520",
    "Other":  "#777777"
}

# ---------- util saída ----------
def get_next_run_number():
    base_dir = Path("../outputs")
    base_dir.mkdir(exist_ok=True)
    runs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("stuttgart_maps_")]
    if not runs: return 1
    nums = []
    for d in runs:
        try:
            nums.append(int(d.name.split("_")[-1]))
        except: pass
    return max(nums) + 1 if nums else 1

RUN_NUMBER = get_next_run_number()
OUT_DIR = Path(f"../outputs/stuttgart_maps_{RUN_NUMBER:03d}")
MAPS_DIR = OUT_DIR / "maps"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)

def _save(fig, name):
    out = MAPS_DIR / name
    fig.savefig(out, dpi=200, bbox_inches="tight", pad_inches=0.5, facecolor="white")
    print(f"  💾 Saved: {name}")
    plt.close(fig)

# ---------- carregamento ----------
def load_data():
    def read_any(p: Path):
        if not p.exists(): return None
        try:
            if p.suffix.lower() in {".geojson", ".json", ".gpkg"}:
                return gpd.read_file(p)
            if p.suffix.lower() == ".parquet":
                df = pd.read_parquet(p)
                if "geometry" in df.columns:
                    # Handle WKB geometry data
                    try:
                        # Try to convert WKB to shapely geometries
                        df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(x) if x else None)
                        return gpd.GeoDataFrame(df, geometry='geometry', crs=4326)
                    except Exception as wkb_error:
                        print(f"  ⚠️ WKB conversion failed for {p.name}: {wkb_error}")
                        # Try direct GeoDataFrame creation
                        try:
                            return gpd.GeoDataFrame(df, geometry='geometry', crs=4326)
                        except Exception as gdf_error:
                            print(f"  ❌ GeoDataFrame creation failed for {p.name}: {gdf_error}")
                            return None
                return df
        except Exception as e:
            print(f"Error reading {p}: {e}")
            return None

    data = {
        "districts": read_any(DATA_DIR/"districts_with_population.geojson"),
        "pt_stops":  read_any(DATA_DIR/"processed/pt_stops_categorized.parquet"),
        "amenities": read_any(DATA_DIR/"processed/amenities_categorized.parquet"),
        "cycle":     read_any(DATA_DIR/"processed/cycle_categorized.parquet"),
        "landuse":   read_any(DATA_DIR/"processed/landuse_categorized.parquet"),
        "roads":     read_any(DATA_DIR/"processed/roads_categorized.parquet"),
    }
    for k, gdf in data.items():
        if gdf is not None and hasattr(gdf, 'crs'):
            data[k] = gdf.set_crs(4326) if gdf.crs is None else gdf.to_crs(4326)
    return data

# ---------- helpers de plot ----------
def _add_basemap_custom(ax, extent, basemap_source="CartoDB.Positron", basemap_alpha=0.30):
    try:
        src = {
            "CartoDB.Positron": cx.providers.CartoDB.Positron,
            "CartoDB.DarkMatter": cx.providers.CartoDB.DarkMatter,
            "OpenStreetMap": cx.providers.OpenStreetMap.Mapnik,
            "Stamen.Terrain": cx.providers.Stamen.Terrain,
            "Stamen.Toner": cx.providers.Stamen.Toner,
            "Stamen.Watercolor": cx.providers.Stamen.Watercolor
        }.get(basemap_source, cx.providers.CartoDB.Positron)
        cx.add_basemap(ax, source=src, alpha=basemap_alpha, crs=PLOT_CRS)
    except Exception as e:
        print(f"  ❌ Basemap: {e}")

def _add_basemap(ax, extent): _add_basemap_custom(ax, extent, "CartoDB.Positron", 0.30)

def _add_scale_bar(ax, extent, km_marks=(1,5,10)):
    import matplotlib.patches as mpatches
    xmin, ymin, xmax, ymax = extent
    width_m = xmax - xmin; height_m = ymax - ymin
    choices = [20,15,10,5,2,1] if width_m > 40000 else [10,5,2,1]
    max_km = next((k for k in choices if (k*1000) <= 0.35*width_m), 1)
    x0 = xmin + 0.06*width_m; y0 = ymin + 0.06*height_m
    unit = 1000.0; h = 0.006*height_m
    for k in range(int(max_km)):
        face = 'black' if k%2==0 else 'white'
        ax.add_patch(mpatches.Rectangle((x0+k*unit, y0), unit, h, facecolor=face,
                        edgecolor='black', linewidth=0.8, zorder=10, alpha=0.7))
    ax.add_patch(mpatches.Rectangle((x0, y0), max_km*unit, h, facecolor='none',
                    edgecolor='black', linewidth=0.8, zorder=11, alpha=0.7))
    labels = [0] + [m for m in km_marks if m <= max_km]
    for lab in labels:
        xl = x0 + lab*unit
        ax.text(xl, y0 + 1.5*h, f'{lab}', ha='center', va='bottom',
                fontsize=9, fontweight='bold', zorder=12, alpha=0.7)
    ax.text(x0 + (max_km*unit)/2.0, y0 - 0.8*h, 'km', ha='center', va='top',
            fontsize=10, fontweight='bold', zorder=12, alpha=0.7)

def _classify_pt(row):
    g = lambda k: str(row.get(k, "")).lower()
    if g("railway") in {"tram_stop","tram_station"} or g("tram") in {"yes","stop","station","1"}:
        return "Tram"
    if g("railway") in {"subway","subway_entrance"} or g("subway") in {"yes","1"}:
        return "U-Bahn"
    if (g("railway") in {"halt","stop","station"} and g("train") in {"yes","1"}) or g("railway") == "stop":
        return "S-Bahn"
    if g("highway") == "bus_stop" or g("bus") in {"yes","1"} or g("amenity") == "bus_station":
        return "Bus"
    return "Other"

def _slug(s: str) -> str:
    return (str(s).lower().replace(" ", "_")
            .replace("ü","u").replace("ö","o").replace("ä","a").replace("ß","ss"))

def _city_extent_and_boundary(data):
    districts = data["districts"].to_crs(PLOT_CRS)
    city_boundary = districts.union_all()
    city_boundary_buffered = city_boundary.buffer(100)
    extent = tuple(gpd.GeoSeries([city_boundary.buffer(OVERVIEW_PAD_M)], crs=PLOT_CRS).total_bounds)
    return districts, city_boundary, city_boundary_buffered, extent

def apply_map_template(ax, extent, english_title, german_subtitle, city_boundary_buffered,
                      figsize=(20,16), basemap_source="CartoDB.Positron", basemap_alpha=0.30):
    gpd.GeoSeries([city_boundary_buffered], crs=PLOT_CRS).boundary.plot(
        ax=ax, color="#666666", linewidth=3, alpha=0.4)
    _add_basemap(ax, extent)
    ax.set_aspect("equal"); ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])
    ax.set_axis_off()
    ax.set_title(english_title, fontsize=18, fontweight="normal", pad=20)
    ax.text(0.5, 0.92, german_subtitle, transform=plt.gcf().transFigure,
            ha='center', fontsize=14, style='italic')
    _add_scale_bar(ax, extent)
    return figsize

# ---------- MAPA 01 ----------
def generate_overview_maps(data):
    print("🗺️ Generating overview maps…")
    districts = data["districts"].to_crs(PLOT_CRS)
    city_boundary = districts.union_all()
    city_boundary_buffered = city_boundary.buffer(100)
    extent = tuple(gpd.GeoSeries([city_boundary.buffer(OVERVIEW_PAD_M)], crs=PLOT_CRS).total_bounds)

    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    ax.set_aspect("equal"); ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])

    # green/landuse simplificado
    if data["landuse"] is not None:
        lu = data["landuse"].to_crs(PLOT_CRS)
        lu = lu[lu.intersects(city_boundary_buffered)].copy()
        lu["geometry"] = lu.geometry.intersection(city_boundary_buffered)
        lu = lu[~lu.geometry.is_empty]
        lu["area_m2"] = lu.geometry.area
        min_area = 5000

        forest = lu[((lu["landuse"]=="forest") | (lu["natural"]=="forest")) & (lu["area_m2"]>=min_area)]
        if len(forest): forest.plot(ax=ax, color="#4A5D4A", alpha=0.2, edgecolor="none")
        farmland = lu[((lu["landuse"]=="farmland") | (lu["natural"]=="farmland")) & (lu["area_m2"]>=min_area)]
        if len(farmland): farmland.plot(ax=ax, color="#7FB069", alpha=0.2, edgecolor="none")
        residential = lu[(lu["landuse"]=="residential") & (lu["area_m2"]>=min_area)]
        if len(residential): residential.plot(ax=ax, color="#F5F5DC", alpha=0.8, edgecolor="none")
        industrial = lu[(lu["landuse"]=="industrial") & (lu["area_m2"]>=min_area)]
        if len(industrial): industrial.plot(ax=ax, color="#D3D3D3", alpha=0.8, edgecolor="none")
        commercial = lu[((lu["landuse"].isin(["commercial","retail"]))) & (lu["area_m2"]>=min_area)]
        if len(commercial): commercial.plot(ax=ax, color="#FFB6C1", alpha=0.8, edgecolor="none")

    # roads
    if data["roads"] is not None:
        roads = data["roads"].to_crs(PLOT_CRS)
        roads = roads[roads.intersects(city_boundary_buffered)].copy()
        roads["geometry"] = roads.geometry.intersection(city_boundary_buffered)
        roads = roads[~roads.geometry.is_empty]
        roads.plot(ax=ax, color="#8B7355", linewidth=ROAD_LW, alpha=ROAD_ALPHA)

    # PT stops
    if data["pt_stops"] is not None:
        pt = data["pt_stops"].to_crs(PLOT_CRS)
        pt = pt[pt.intersects(city_boundary_buffered)].copy()
        # tipos principais
        sb = pt[pt["railway"]=="stop"]
        if len(sb): sb.plot(ax=ax, marker="o", color="#C3423F", markersize=PT_MARKERSIZE, alpha=PT_ALPHA,
                            edgecolor="white", linewidth=0.5, label="S-Bahn Stop")
        ub = pt[pt["railway"]=="subway_entrance"]
        if len(ub): ub.plot(ax=ax, marker="o", color="#C3423F", markersize=PT_MARKERSIZE, alpha=PT_ALPHA,
                            edgecolor="white", linewidth=0.5, label="U-Bahn Entrance")
        tr = pt[pt["railway"]=="tram_stop"]
        if len(tr): tr.plot(ax=ax, marker="o", color="#C3423F", markersize=PT_MARKERSIZE, alpha=PT_ALPHA,
                            edgecolor="white", linewidth=0.5, label="Tram Stop")
        remaining = pt[~pt.index.isin(pd.concat([sb,ub,tr]).index)]
        if len(remaining): remaining.plot(ax=ax, marker="o", color="#C3423F", markersize=PT_MARKERSIZE,
                                          alpha=PT_ALPHA, edgecolor="white", linewidth=0.5)

    # distritos (contorno)
    districts.boundary.plot(ax=ax, color="#2F4F4F", linewidth=1.5, alpha=0.1)
    _add_basemap(ax, extent); ax.set_axis_off()

    # legenda simples
    legend_elements = [
        plt.Line2D([0], [0], color='#8B7355', alpha=0.3, linewidth=2, label='Roads / Straßen'),
        plt.Line2D([0], [0], color='#666666', alpha=0.4, linewidth=3, label='City Boundary / Stadtgrenze'),
        plt.Line2D([0], [0], marker="o", color="#C3423F", markersize=8, label="PT Stop / ÖPNV-Haltestelle")
    ]
    ax.legend(handles=legend_elements, loc="lower right", ncol=1, fontsize=8,
              title="Map Legend / Kartenlegende", frameon=True, framealpha=0.95)

    fig.suptitle("Stuttgart — Land Use + Roads + PT Stops", fontsize=18, fontweight="normal", y=0.95)
    ax.text(0.5, 0.92, "Flächennutzung + Straßen + ÖPNV-Haltestellen",
            transform=fig.transFigure, ha='center', fontsize=14, style='italic')
    _add_scale_bar(ax, extent)
    _save(fig, "01_overview_landuse_roads_pt.png")

    # ===== 01b: Pop density como fundo =====
    generate_population_density_map(data, city_boundary_buffered)

def generate_population_density_map(data, city_boundary_buffered):
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    districts = data["districts"].to_crs(PLOT_CRS)
    districts["area_km2"] = districts.geometry.area / 1e6
    districts["pop_density"] = districts["pop"] / districts["area_km2"]
    districts.plot(ax=ax, column="pop_density", cmap="YlOrBr", alpha=0.7, legend=True,
                   legend_kwds={"label": "Population Density (people/km²)",
                                "orientation": "horizontal", "shrink": 0.6,
                                "aspect": 20, "pad": 0.05})
    if data["roads"] is not None:
        roads = data["roads"].to_crs(PLOT_CRS)
        roads.plot(ax=ax, color="#8B7355", alpha=0.3, linewidth=0.5)
    if data["pt_stops"] is not None:
        pts = data["pt_stops"].to_crs(PLOT_CRS)
        pts.plot(ax=ax, color="#C3423F", alpha=PT_ALPHA, markersize=PT_MARKERSIZE)
    extent = tuple(gpd.GeoSeries([city_boundary_buffered], crs=PLOT_CRS).total_bounds)
    gpd.GeoSeries([city_boundary_buffered], crs=PLOT_CRS).boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.4)
    fig.suptitle("Stuttgart — Population Density + Roads + PT Stops", fontsize=18, y=0.95)
    ax.text(0.5, 0.92, "Bevölkerungsdichte + Straßen + ÖPNV-Haltestellen",
            transform=fig.transFigure, ha='center', fontsize=14, style='italic')
    ax.set_aspect("equal"); ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])
    _add_basemap_custom(ax, extent, "CartoDB.Positron", 0.30)
    _add_scale_bar(ax, extent)
    ax.axis('off')
    _save(fig, "01b_overview_population_density_roads_pt.png")

# ---------- MAPA 02 ----------
def _make_fishnet(extent, cell_size):
    xmin, ymin, xmax, ymax = extent
    xs = np.arange(xmin, xmax + cell_size, cell_size)
    ys = np.arange(ymin, ymax + cell_size, cell_size)
    polys = [box(x, y, x + cell_size, y + cell_size) for x in xs[:-1] for y in ys[:-1]]
    return gpd.GeoDataFrame({"geometry": polys}, crs=PLOT_CRS)

def generate_pop_vs_pt_mosaic_map(data):
    districts, city_boundary, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    d = districts.copy()
    d["area_km2"] = d.geometry.area / 1e6
    d["pop_density"] = d["pop"] / d["area_km2"]

    grid = _make_fishnet(tuple(city_boundary.bounds), GRID_SIZE_M)
    grid = grid[grid.intersects(city_boundary_buffered)].copy()
    grid["geometry"] = grid.geometry.intersection(city_boundary_buffered)

    if data["pt_stops"] is None:
        print("❌ pt_stops ausente para o Mapa 02"); return
    pts = data["pt_stops"].to_crs(PLOT_CRS)[["geometry"]].copy()
    grid = grid.reset_index().rename(columns={"index":"cell_id"})
    join = gpd.sjoin(pts, grid[["cell_id","geometry"]], how="left", predicate="within")
    counts = join.groupby("cell_id").size()
    grid["pt_count"] = grid["cell_id"].map(counts).fillna(0).astype(int)
    grid["area_km2"] = grid.geometry.area / 1e6
    grid["pt_density_km2"] = (grid["pt_count"] / grid["area_km2"]).round(2)
    grid_nz = grid[grid["pt_count"] > 0].copy()

    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    d.plot(ax=ax, column="pop_density", cmap="YlOrBr", alpha=0.65, legend=True,
           legend_kwds={"label":"Population Density (people/km²)",
                        "orientation":"horizontal","shrink":0.6,"aspect":20,"pad":0.05})
    if len(grid_nz) > 0:
        grid_nz.plot(ax=ax, column="pt_density_km2", cmap="Reds", alpha=0.6, linewidth=0)
    gpd.GeoSeries([city_boundary], crs=PLOT_CRS).boundary.plot(ax=ax, color="#666666", linewidth=3, alpha=0.4)
    fig.suptitle("Stuttgart — Population vs PT Stop Density (600 m grid)", fontsize=18, y=0.95)
    ax.text(0.5, 0.92, "Bevölkerungsdichte (Hintergrund) + ÖPNV-Haltestellen (Dichte, Raster 600 m)",
            transform=fig.transFigure, ha='center', fontsize=14, style='italic')
    ax.set_aspect("equal"); ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])
    _add_basemap_custom(ax, extent, "CartoDB.Positron", 0.30)
    _add_scale_bar(ax, extent); ax.set_axis_off()
    _save(fig, "02_pop_vs_pt_density_grid.png")

# ---------- MAPA 03 ----------
def generate_district_accessibility_maps(data, focus_names=DISTRICTS_FOCUS):
    districts = data["districts"].to_crs(PLOT_CRS).copy()
    all_names = [str(x) for x in districts["district_norm"].unique()]
    matched = []
    for q in focus_names:
        ql = q.lower()
        cand = next((n for n in all_names if ql in n.lower()), None)
        if cand: matched.append(cand)
    if data["pt_stops"] is None:
        print("❌ pt_stops ausente para Mapa 03"); return
    pt = data["pt_stops"].to_crs(PLOT_CRS).copy()
    if "pt_type" not in pt.columns:
        pt["pt_type"] = pt.apply(_classify_pt, axis=1)

    for name in matched:
        dist = districts.loc[districts["district_norm"] == name].iloc[0]
        geom = dist.geometry
        buffer_view = geom.buffer(1000)
        extent = tuple(buffer_view.bounds)
        roads_clip = None
        if data["roads"] is not None:
            roads_clip = data["roads"].to_crs(PLOT_CRS)
            roads_clip = roads_clip[roads_clip.intersects(buffer_view)]
        pt_clip = pt[pt.intersects(buffer_view)]
        coverage = None
        if len(pt_clip) > 0:
             cov_union = pt_clip.buffer(WALK_BUFFER_M).union_all()
             cov_in_district = cov_union.intersection(geom)
             coverage = gpd.GeoDataFrame(geometry=[cov_in_district], crs=PLOT_CRS)
        cover_txt = ""
        if coverage is not None and not coverage.geometry.iloc[0].is_empty:
            cov_area_km2 = coverage.geometry.area.iloc[0] / 1e6
            dist_area_km2 = geom.area / 1e6
            pct = (cov_area_km2 / dist_area_km2 * 100)
            cover_txt = f" — 15-min coverage: {pct:.0f}%"

        fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
        if roads_clip is not None and len(roads_clip) > 0:
            roads_clip.plot(ax=ax, color="#8B7355", linewidth=0.8, alpha=0.6)
        if coverage is not None and not coverage.geometry.iloc[0].is_empty:
            coverage.plot(ax=ax, color="#9DC183", alpha=0.25, linewidth=0)
        for cat, color in PT_TYPE_COLORS.items():
            pts_cat = pt_clip[pt_clip["pt_type"] == cat]
            if len(pts_cat) > 0:
                pts_cat.plot(ax=ax, marker="o", color=color, markersize=PT_MARKERSIZE*1.2,
                             alpha=0.9, edgecolor="white", linewidth=0.5, label=cat)
        gpd.GeoSeries([geom], crs=PLOT_CRS).boundary.plot(ax=ax, color="#2F4F4F", linewidth=2, alpha=0.6)
        fig.suptitle(f"Stuttgart — {name} — PT by mode + 15-min Walk", fontsize=18, y=0.95)
        ax.text(0.5, 0.92, f"Straßen (Hintergrund) + ÖPNV nach Modus + 15 Min Zufuß{cover_txt}",
                transform=fig.transFigure, ha='center', fontsize=14, style='italic')
        ax.set_aspect("equal"); ax.set_xlim(extent[0], extent[2]); ax.set_ylim(extent[1], extent[3])
        _add_basemap_custom(ax, extent, "CartoDB.Positron", 0.30)
        _add_scale_bar(ax, extent); ax.set_axis_off()
        legend_items = [plt.Line2D([0],[0], color='#8B7355', linewidth=2, alpha=0.6, label="Roads"),
                        plt.Rectangle((0,0),1,1, facecolor="#9DC183", alpha=0.25, label="15-min walk coverage")]
        present = [cat for cat in PT_TYPE_COLORS if cat in list(pt_clip["pt_type"].unique())]
        for cat in present:
            legend_items.append(plt.Line2D([0],[0], marker="o", color=PT_TYPE_COLORS[cat],
                                           markerfacecolor=PT_TYPE_COLORS[cat], markersize=8,
                                           linewidth=0, label=cat))
        ax.legend(handles=legend_items, loc="lower right", fontsize=9, ncol=2,
                  frameon=True, fancybox=True, framealpha=0.95, title="Map Legend")
        _save(fig, f"03_access_{_slug(name)}.png")

# =====================[ PATCH H3 MAPS 04–10 ]=====================
H3_RES = 8
PT_WEIGHTS = {"S-Bahn": 3.0, "U-Bahn": 2.5, "Tram": 2.0, "Bus": 1.0, "Other": 0.5}
PT_GRAVITY_MAX_DIST_M = 1500
PT_GRAVITY_DIST_FLOOR_M = 50
DETOUR_BARRIER_THRESHOLD = 1.4
WALK_10MIN_M = 800
PARK_MAX_MIN = 10
FOREST_MAX_MIN = 15

def _city_h3_grid_3857(data, res=H3_RES):
    if h3 is None:
        raise RuntimeError("Pacote 'h3' não disponível.")
    
    # Import our H3 helpers
    import sys
    sys.path.append("../utils")
    from h3_helpers import gdf_polygons_to_h3, h3_to_shapely_geometry
    
    d_wgs = data["districts"].to_crs(4326)
    city_wgs = gpd.GeoSeries([d_wgs.union_all()], crs=4326).iloc[0]
    
    # Use our helper function to get H3 cells
    try:
        hex_ids = list(gdf_polygons_to_h3(gpd.GeoDataFrame(geometry=[city_wgs], crs=4326), res))
        print(f"  ✅ Generated {len(hex_ids)} H3 hexagons using helper functions")
    except Exception as e:
        print(f"  ⚠️ H3 helper failed: {e}")
        # Fallback: create a simple grid manually
        bounds = city_wgs.bounds
        min_lat, min_lng, max_lat, max_lng = bounds
        lat_step = (max_lat - min_lat) / 20
        lng_step = (max_lng - min_lng) / 20
        hex_ids = []
        for i in range(20):
            for j in range(20):
                lat = min_lat + i * lat_step
                lng = min_lng + j * lng_step
                try:
                    hex_id = h3.latlng_to_cell(lat, lng, res)
                    hex_ids.append(hex_id)
                except:
                    pass
    
    # Convert H3 cells to polygons using our helper
    poly_coords = []
    for hx in hex_ids:
        try:
            poly = h3_to_shapely_geometry(hx)
            poly_coords.append(poly)
        except Exception as e:
            print(f"  ⚠️ H3 to polygon conversion failed for {hx}: {e}")
            continue
    
    gdf = gpd.GeoDataFrame({"h3": hex_ids, "geometry": poly_coords}, crs=4326).to_crs(PLOT_CRS)
    gdf["centroid"] = gdf.geometry.centroid
    gdf["area_m2"] = gdf.geometry.area
    return gdf

ESSENTIAL_KEYS = {"supermarket","pharmacy","school","doctors","hospital"}
def _is_essential(row):
    a = str(row.get("amenity","")).lower()
    s = str(row.get("shop","")).lower()
    return (a in {"pharmacy","school","doctors","hospital","clinic"} or
            s in {"supermarket"} or a == "marketplace")

def _parks_polygons_3857():
    base = Path("../data/processed")
    fn = base/"parks_extracted_osmnx.parquet"
    if fn.exists():
        try:
            g = gpd.read_parquet(fn).to_crs(PLOT_CRS)
            return g[g.geometry.type.isin(["Polygon","MultiPolygon"])]
        except Exception:
            pass
    fn2 = base/"green_areas_categorized.parquet"
    if fn2.exists():
        try:
            g = gpd.read_parquet(fn2).to_crs(PLOT_CRS)
            parks = g[(g.get("osm_tag_key")=="leisure") & (g.get("osm_tag_value")=="park")]
            return parks[parks.geometry.type.isin(["Polygon","MultiPolygon"])]
        except Exception:
            pass
    return gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)

def _forests_polygons_3857(data):
    if data["landuse"] is None: 
        return gpd.GeoDataFrame(geometry=[], crs=PLOT_CRS)
    lu = data["landuse"].to_crs(PLOT_CRS)
    forests = lu[((lu.get("landuse")=="forest") | (lu.get("natural")=="wood")) &
                 (lu.geometry.type.isin(["Polygon","MultiPolygon"]))].copy()
    return forests

def map04_pt_modal_gravity_h3(data):
    print("  🧩 Generating H3 PT Modal Gravity map...")
    try:
        h3g = _city_h3_grid_3857(data)
        if len(h3g) == 0:
            print("  ❌ No H3 grid generated"); return
        print(f"  ✅ H3 grid created with {len(h3g)} hexagons")
    except Exception as e:
        print(f"  ❌ H3 grid creation failed: {e}"); return
    
    if data["pt_stops"] is None:
        print("❌ pt_stops ausente"); return
    stops = data["pt_stops"].to_crs(PLOT_CRS).copy()
    if "pt_type" not in stops.columns:
        stops["pt_type"] = stops.apply(_classify_pt, axis=1)
    sidx = stops.sindex
    scores = []
    for c in h3g["centroid"]:
        ring = c.buffer(PT_GRAVITY_MAX_DIST_M)
        idx = list(sidx.query(ring, predicate="intersects"))
        if not idx:
            scores.append(0.0); continue
        sub = stops.iloc[idx]
        s = 0.0
        for _, r in sub.iterrows():
            d = max(c.distance(r.geometry), PT_GRAVITY_DIST_FLOOR_M)
            s += PT_WEIGHTS.get(r["pt_type"], 0.5) / (d*d)
        scores.append(s)
    h3g["pt_gravity"] = scores
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    valid = h3g["pt_gravity"]>0
    h3g.loc[valid, "q"] = pd.qcut(h3g.loc[valid,"pt_gravity"], q=5, labels=False, duplicates="drop")
    h3g.plot(ax=ax, column="q", cmap="OrRd", linewidth=0, alpha=0.75)
    apply_map_template(ax, extent,
        "Stuttgart — PT Modal Gravity (H3 r8)",
        "ÖPNV-Gravitation (S=3, U=2.5, Tram=2, Bus=1; Σ Gewicht/d²)",
        city_boundary_buffered)
    _save(fig, "04_pt_modal_gravity_h3.png")
    out = (MAPS_DIR.parent/"kepler_data"); out.mkdir(exist_ok=True)
    h3g[["h3","pt_gravity","geometry"]].to_crs(4326).to_file(out/"13_pt_modal_gravity_h3.geojson", driver="GeoJSON")

def map05_access_essentials_h3(data):
    if data["amenities"] is None:
        print("❌ amenities ausente"); return
    h3g = _city_h3_grid_3857(data)
    amen = data["amenities"].to_crs(PLOT_CRS).copy()
    amen["is_ess"] = amen.apply(_is_essential, axis=1)
    ess = amen[amen["is_ess"]]
    if len(ess)==0:
        print("⚠️ nenhum essencial encontrado"); return
    sidx = ess.sindex
    counts = []
    for c in h3g["centroid"]:
        ring = c.buffer(WALK_10MIN_M)
        idx = list(sidx.query(ring, predicate="intersects"))
        if not idx: counts.append(0); continue
        sub = ess.iloc[idx]
        types = set()
        for _, r in sub.iterrows():
            a = str(r.get("amenity","")).lower(); s = str(r.get("shop","")).lower()
            if s=="supermarket": types.add("supermarket")
            elif a in {"pharmacy","school","doctors","hospital","clinic","marketplace"}: types.add(a)
        counts.append(len(types))
    h3g["ess_types"] = counts  # 0..5
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g.plot(ax=ax, column="ess_types", cmap="Greens", linewidth=0, alpha=0.8,
             vmin=0, vmax=5, legend=True, legend_kwds={"label":"# essential types ≤10 min"})
    apply_map_template(ax, extent,
        "Stuttgart — Access to Essentials (≤10 min walk, H3 r8)",
        "Erreichbarkeit von Grundversorgern (≤10 Min zu Fuß) — Anzahl von Kategorien",
        city_boundary_buffered)
    _save(fig, "05_access_essentials_h3.png")
    out = (MAPS_DIR.parent/"kepler_data"); out.mkdir(exist_ok=True)
    h3g[["h3","ess_types","geometry"]].to_crs(4326).to_file(out/"14_access_essentials_h3.geojson", driver="GeoJSON")



def map07_service_diversity_h3(data):
    if data["amenities"] is None:
        print("❌ amenities ausente"); return
    h3g = _city_h3_grid_3857(data)
    amen = data["amenities"].to_crs(PLOT_CRS).copy()
    aidx = amen.sindex
    ent = []
    for c in h3g["centroid"]:
        idx = list(aidx.query(c.buffer(300), predicate="intersects"))
        if not idx: ent.append(0.0); continue
        sub = amen.iloc[idx]
        counts = sub["amenity"].fillna("other").astype(str).str.lower().value_counts()
        p = counts / counts.sum()
        H = float(-(p * np.log(p)).sum())
        ent.append(H)
    h3g["amen_entropy"] = ent
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g.plot(ax=ax, column="amen_entropy", cmap="PuBuGn", linewidth=0, alpha=0.85,
             legend=True, legend_kwds={"label":"Amenity diversity (Shannon entropy)"})
    apply_map_template(ax, extent,
        "Stuttgart — Service Diversity (H3 r8)",
        "Nutzungsmischung / Dienstleistungs-Diversität (Shannon-Entropie)",
        city_boundary_buffered)
    _save(fig, "07_service_diversity_h3.png")
    out = (MAPS_DIR.parent/"kepler_data"); out.mkdir(exist_ok=True)
    h3g[["h3","amen_entropy","geometry"]].to_crs(4326).to_file(out/"16_service_diversity_h3.geojson", driver="GeoJSON")

def _access_time_minutes(h3g, targets):
    if targets is None or len(targets)==0:
        return pd.Series(np.nan, index=h3g.index)
    t = targets.copy()
    t = t[t.geometry.type.isin(["Polygon","MultiPolygon"])].copy()
    if len(t)==0:
        return pd.Series(np.nan, index=h3g.index)
    tidx = t.sindex
    mins = []
    for c in h3g["centroid"]:
        idx = list(tidx.query(c.buffer(2000), predicate="intersects"))
        if not idx: mins.append(np.nan); continue
        sub = t.iloc[idx]
        d = sub.distance(c).min()          # m
        mins.append(d / WALK_SPEED_MPM)    # min
    return pd.Series(mins, index=h3g.index)

def map08_park_access_time_h3(data):
    h3g = _city_h3_grid_3857(data); parks = _parks_polygons_3857()
    h3g["park_min"] = _access_time_minutes(h3g, parks)
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g.plot(ax=ax, column="park_min", cmap="Greens_r", linewidth=0, alpha=0.85,
             legend=True, legend_kwds={"label":"Minutes to nearest Park (walk)"} )
    apply_map_template(ax, extent,
        "Stuttgart — Access Time to Parks (H3 r8)",
        "Fußweg-Zeit bis zum nächsten Park (Minuten, niedr. = melhor)",
        city_boundary_buffered)
    _save(fig, "08_park_access_time_h3.png")
    out = (MAPS_DIR.parent/"kepler_data"); out.mkdir(exist_ok=True)
    h3g[["h3","park_min","geometry"]].to_crs(4326).to_file(out/"17_park_access_time_h3.geojson", driver="GeoJSON")

def map09_forest_access_time_h3(data):
    h3g = _city_h3_grid_3857(data); forests = _forests_polygons_3857(data)
    h3g["forest_min"] = _access_time_minutes(h3g, forests)
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g.plot(ax=ax, column="forest_min", cmap="YlGn_r", linewidth=0, alpha=0.85,
             legend=True, legend_kwds={"label":"Minutes to nearest Forest (walk)"} )
    apply_map_template(ax, extent,
        "Stuttgart — Access Time to Forests (H3 r8)",
        "Fußweg-Zeit bis zum Wald (Minuten, niedr. = melhor)",
        city_boundary_buffered)
    _save(fig, "09_forest_access_time_h3.png")
    out = (MAPS_DIR.parent/"kepler_data"); out.mkdir(exist_ok=True)
    h3g[["h3","forest_min","geometry"]].to_crs(4326).to_file(out/"18_forest_access_time_h3.geojson", driver="GeoJSON")

def map10_green_gaps_h3(data):
    h3g = _city_h3_grid_3857(data)
    parks = _parks_polygons_3857()
    forests = _forests_polygons_3857(data)
    h3g["park_min"] = _access_time_minutes(h3g, parks)
    h3g["forest_min"] = _access_time_minutes(h3g, forests)
    h3g["green_gap"] = ((h3g["park_min"] > PARK_MAX_MIN) | (h3g["park_min"].isna())) & \
                       ((h3g["forest_min"] > FOREST_MAX_MIN) | (h3g["forest_min"].isna()))
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    h3g.plot(ax=ax, color="#eeeeee", linewidth=0, alpha=0.6)
    gaps = h3g[h3g["green_gap"]==True]
    if len(gaps): gaps.plot(ax=ax, color="#E74C3C", linewidth=0, alpha=0.9)
    apply_map_template(ax, extent,
        "Stuttgart — Green Access Gaps (H3 r8)",
        "Hexágonos sem Parque (≤10 min) e sem Floresta (≤15 min)",
        city_boundary_buffered)
    _save(fig, "10_green_gaps_h3.png")
    out = (MAPS_DIR.parent/"kepler_data"); out.mkdir(exist_ok=True)
    h3g[["h3","park_min","forest_min","green_gap","geometry"]].to_crs(4326).to_file(out/"19_green_gaps_h3.geojson", driver="GeoJSON")

# ---------- Visões legíveis (sem overlay de dois gradientes) ----------
from matplotlib.colors import TwoSlopeNorm

def _attach_h3_population_density(data, h3g):
    d = data["districts"].to_crs(PLOT_CRS)[["district_norm","pop","geometry"]].copy()
    d["area_m2"] = d.geometry.area
    inter = gpd.overlay(h3g[["h3","geometry"]], d, how="intersection")
    if len(inter) == 0:
        h3g["pop_hex"] = 0.0; h3g["pop_density"] = 0.0; return h3g
    inter["inter_area"] = inter.geometry.area
    inter["pop_part"] = inter["pop"] * (inter["inter_area"] / d.set_index(d.index)["area_m2"].reindex(inter.index, fill_value=inter["inter_area"]).values)
    by_hex = inter.groupby("h3")[["pop_part","inter_area"]].sum()
    h3g = h3g.merge(by_hex, left_on="h3", right_index=True, how="left")
    h3g["pop_part"] = h3g["pop_part"].fillna(0.0)
    h3g["pop_hex"] = h3g["pop_part"]
    h3g["pop_density"] = h3g["pop_hex"] / (h3g["area_m2"] / 1e6)
    return h3g

def _compute_pt_gravity(h3g, stops):
    sidx = stops.sindex; vals = []
    for c in h3g["centroid"]:
        ring = c.buffer(PT_GRAVITY_MAX_DIST_M)
        idx = list(sidx.query(ring, predicate="intersects"))
        if not idx: vals.append(0.0); continue
        sub = stops.iloc[idx]; s = 0.0
        for _, r in sub.iterrows():
            d = max(c.distance(r.geometry), PT_GRAVITY_DIST_FLOOR_M)
            s += PT_WEIGHTS.get(r["pt_type"], 0.5) / (d*d)
        vals.append(s)
    return pd.Series(vals, index=h3g.index, dtype=float)

def map04a_pt_pop_mismatch_h3(data):
    h3g = _city_h3_grid_3857(data); h3g = _attach_h3_population_density(data, h3g)
    if data["pt_stops"] is None: print("❌ pt_stops ausente"); return
    stops = data["pt_stops"].to_crs(PLOT_CRS).copy()
    if "pt_type" not in stops.columns: stops["pt_type"] = stops.apply(_classify_pt, axis=1)
    h3g["pt_gravity"] = _compute_pt_gravity(h3g, stops)
    h3g["pop_rank"] = h3g["pop_density"].rank(pct=True)
    h3g["pt_rank"]  = h3g["pt_gravity"].rank(pct=True)
    h3g["mismatch"] = h3g["pop_rank"] - h3g["pt_rank"]
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, ax = plt.subplots(1,1, figsize=(20,16), dpi=200)
    norm = TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    h3g.plot(ax=ax, column="mismatch", cmap="RdBu_r", norm=norm,
             linewidth=0, alpha=0.9, legend=True,
             legend_kwds={"label":"Descompasso: pop – PT (rank)", "shrink":0.7})
    hot = h3g[h3g["mismatch"] >= h3g["mismatch"].quantile(0.8)]
    if len(hot): hot.boundary.plot(ax=ax, color="#8B0000", linewidth=0.8, alpha=0.9)
    apply_map_template(ax, extent,
        "Stuttgart — PT vs Population Mismatch (H3 r8)",
        "Divergência oferta × demanda (azul = sobra PT, vermelho = falta PT)",
        city_boundary_buffered)
    _save(fig, "04a_mismatch_diverging_h3.png")
    out = (MAPS_DIR.parent/"kepler_data"); out.mkdir(exist_ok=True)
    h3g[["h3","pop_density","pt_gravity","mismatch","geometry"]].to_crs(4326)\
        .to_file(out/"20_pt_pop_mismatch_h3.geojson", driver="GeoJSON")

def map04b_pt_pop_small_multiples_h3(data):
    h3g = _city_h3_grid_3857(data); h3g = _attach_h3_population_density(data, h3g)
    if data["pt_stops"] is None: print("❌ pt_stops ausente"); return
    stops = data["pt_stops"].to_crs(PLOT_CRS).copy()
    if "pt_type" not in stops.columns: stops["pt_type"] = stops.apply(_classify_pt, axis=1)
    h3g["pt_gravity"] = _compute_pt_gravity(h3g, stops)
    districts, _, city_boundary_buffered, extent = _city_extent_and_boundary(data)
    fig, axes = plt.subplots(1, 2, figsize=(22,16), dpi=200)
    ax = axes[0]
    h3g.plot(ax=ax, column="pop_density", cmap="Greys", linewidth=0, alpha=0.95,
             legend=True, legend_kwds={"label":"Population Density (people/km²)", "shrink":0.7})
    apply_map_template(ax, extent, "H3 Population Density (r8)",
                       "Bevölkerungsdichte (Graustufen)", city_boundary_buffered)
    ax = axes[1]
    valid = h3g["pt_gravity"] > 0
    h3g.loc[valid, "pt_q"] = pd.qcut(h3g.loc[valid,"pt_gravity"], q=5, labels=False, duplicates="drop")
    h3g.plot(ax=ax, column="pt_q", cmap="OrRd", linewidth=0, alpha=0.95,
             legend=True, legend_kwds={"label":"PT gravity (quintiles)", "shrink":0.7})
    apply_map_template(ax, extent, "H3 PT Modal Gravity (r8)",
                       "ÖPNV-Gravitation (S>U>Tram>Bus)", city_boundary_buffered)
    fig.suptitle("Stuttgart — Population vs PT Gravity (H3 r8, painéis)", fontsize=18, y=0.96)
    _save(fig, "04b_small_multiples_h3.png")

# ---------- MAIN ----------
def main():
    print("🚀 Stuttgart Urban Analysis Suite — FULL")
    print("="*60)
    print(f"📁 Run #{RUN_NUMBER:03d}  →  {OUT_DIR}")
    print("="*60)

    # info
    run_info = {
        "run_number": RUN_NUMBER,
        "timestamp": pd.Timestamp.now().isoformat(),
        "output_directory": str(OUT_DIR),
        "features": [
            "Map 01 overview + 01b pop density",
            "Map 02 grid Pop vs PT",
            "Map 03 district accessibility",
            "H3 diagnostics 04–10",
            "Legible views 04a/04b",
        ]
    }
    with open(OUT_DIR/"run_info.json", "w") as f: json.dump(run_info, f, indent=2)

    data = load_data()
    if data["districts"] is None:
        print("❌ districts não encontrados"); return
    print(f"✅ Loaded {len(data['districts'])} districts")

    # 01 + 01b
    generate_overview_maps(data)
    # 02
    generate_pop_vs_pt_mosaic_map(data)
    # 03
    generate_district_accessibility_maps(data, DISTRICTS_FOCUS)

    # 04–10 (H3)
    print("\n🗺️ Generating MAP 4–10 (H3 diagnostics + green access)…")
    map04_pt_modal_gravity_h3(data)
    map05_access_essentials_h3(data)
    # map06_detour_factor_h3(data)  # Function not implemented yet
    map07_service_diversity_h3(data)
    map08_park_access_time_h3(data)
    map09_forest_access_time_h3(data)
    map10_green_gaps_h3(data)

    # versões legíveis
    print("\n🗺️ Building legible H3 views…")
    try:
        map04a_pt_pop_mismatch_h3(data)
        map04b_pt_pop_small_multiples_h3(data)
    except Exception as e:
        print(f"⚠️ Skipped legible views: {e}")

    print("\n🎉 Done!")
    print(f"📁 Output: {OUT_DIR}\n🗺️ Maps: {MAPS_DIR}")

if __name__ == "__main__":
    main()
