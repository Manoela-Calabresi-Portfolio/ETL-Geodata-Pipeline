# spatialviz/smoke_test_maps.py
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
from style_helpers import apply_style, palette
from h3_utils import hex_polygon

warnings.filterwarnings("ignore", category=UserWarning)

# Updated paths to match current project structure
DATA_DIR = Path("../main_pipeline/areas/stuttgart/data_final")
OUT_DIR  = Path("outputs/maps"); OUT_DIR.mkdir(parents=True, exist_ok=True)
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
    
    print(f"DEBUG: Processing {len(d)} districts")
    print(f"DEBUG: District areas range: {d['area_km2'].min():.2f} to {d['area_km2'].max():.2f} km²")

    # PT stops
    if layers["pt_stops"] is not None:
        stops = layers["pt_stops"].to_crs(PLOT_CRS)
        print(f"DEBUG: PT stops loaded: {len(stops)}")
        j = gpd.sjoin(stops, d[["geometry"]], predicate="within", how="left")
        print(f"DEBUG: Spatial join result: {len(j)} matches")
        cnt = j.groupby(j.index_right).size()
        print(f"DEBUG: PT counts per district: {cnt.describe()}")
        d["pt_stops_count"] = d.index.map(cnt).fillna(0).astype(int)
        d["pt_stops_per_km2"] = d["pt_stops_count"]/d["area_km2"].replace(0,np.nan)
    else:
        print("DEBUG: No PT stops data")
        d["pt_stops_count"]=0; d["pt_stops_per_km2"]=np.nan

    # Greens: area share (parks/forest/meadow/grass/etc.)
    if layers["landuse"] is not None:
        land = layers["landuse"].to_crs(PLOT_CRS)
        land = land[land.geometry.type.isin(["Polygon","MultiPolygon"])].copy()
        print(f"DEBUG: Landuse loaded: {len(land)} features")
        def is_green(row):
            lu = str(row.get("landuse","")).lower()
            nat= str(row.get("natural","")).lower()
            return lu in {"forest","meadow","grass","recreation_ground","park","cemetery","orchard","vineyard","allotments"} \
                or nat in {"wood","scrub","grassland","park"}
        land = land[land.apply(is_green, axis=1)]
        print(f"DEBUG: Green features after filtering: {len(land)}")
        if len(land):
            j = gpd.sjoin(land, d[["geometry"]], predicate="intersects", how="inner")
            print(f"DEBUG: Green spatial join: {len(j)} matches")
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
            print(f"DEBUG: Green areas computed: {d['green_area_km2'].sum():.2f} km² total")
        else:
            print("DEBUG: No green features found")
            d["green_area_km2"]=0.0
    else:
        print("DEBUG: No landuse data")
        d["green_area_km2"]=np.nan
    d["green_share_pct"] = (d["green_area_km2"]/d["area_km2"].replace(0,np.nan))*100

    # Population from districts_with_population
    if "pop" in d.columns:
        d["population"] = d["pop"].fillna(0)
        print(f"DEBUG: Population loaded: {d['population'].sum():,.0f} total")
    else:
        print("DEBUG: No population column found")
        d["population"]=np.nan

    d["pt_stops_per_1k"] = d["pt_stops_count"]/d["population"].replace(0,np.nan)*1000

    # H3 pop-weighted green m² per capita (requires h3_population_res8)
    if layers["h3_pop"] is not None and layers["landuse"] is not None:
        print("DEBUG: Computing H3-based green m² per capita...")
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
            print(f"DEBUG: H3 green m² per capita computed")
        else:
            print("DEBUG: No green features for H3 calculation")
            d["green_m2_per_capita"]=np.nan
    else:
        print("DEBUG: No H3 population data or landuse data")
        d["green_m2_per_capita"]=np.nan

    # Simple normalized access scores (0–100)
    def scale01(s: pd.Series):
        v = s.astype(float).replace([np.inf,-np.inf], np.nan)
        qlo,qhi = v.quantile([0.05,0.95])
        if qhi<=qlo: qhi=qlo+1e-9
        return (v.clip(qlo,qhi)-qlo)/(qhi-qlo)

    d["green_access_score_pop"]  = 100*(scale01(d["green_m2_per_capita"]) + scale01(d["pt_stops_per_1k"])) / 2.0
    d["green_access_score_area"] = 100*(scale01(d["green_share_pct"])      + scale01(d["pt_stops_per_km2"])) / 2.0
    
    print(f"DEBUG: Final KPI summary:")
    print(f"  - PT stops per 1k range: {d['pt_stops_per_1k'].min():.2f} to {d['pt_stops_per_1k'].max():.2f}")
    print(f"  - Green m² per capita range: {d['green_m2_per_capita'].min():.2f} to {d['green_m2_per_capita'].max():.2f}")
    
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

# ---------- Smoke Test Maps (just 2) ----------
def map_01_macro_green_pt(d, pt_stops, extent):
    pal = palette()
    fig, ax = plt.subplots(1,1, figsize=(12,10))
    # choropleth
    vals = d["green_access_score_pop"].astype(float)
    colors = pal["greens"]
    q = vals.quantile(np.linspace(0,1,len(colors)+1)).values
    bins = np.clip(np.digitize(vals, q[1:-1], right=True), 0, len(colors)-1)
    # Fix: assign colors directly to the geometry column
    d_plot = d.to_crs(PLOT_CRS).copy()
    d_plot["_color"] = [colors[i] for i in bins]
    d_plot.plot(ax=ax, color=d_plot["_color"], edgecolor="#555", linewidth=0.5)
    if pt_stops is not None:
        g = pt_stops.to_crs(PLOT_CRS)
        g.plot(ax=ax, color="white", markersize=20, marker="o", edgecolor="#2a4b8d", linewidth=0.6, alpha=0.9)
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Stuttgart — Green Access (Population-weighted) & PT", fontsize=16, fontweight="bold")
    _save(fig, "01_macro_green_pt.png")

def map_04_bivariate_green_vs_pt(d, extent):
    # 3x3 bivariate: X=PT stops per 1k, Y=green m²/capita proxy
    X = d["pt_stops_per_1k"].astype(float); Y = d["green_m2_per_capita"].astype(float)
    qx = X.quantile([1/3, 2/3]).values; qy = Y.quantile([1/3, 2/3]).values
    def binv(v, qs): 
        return 0 if v<=qs[0] else (1 if v<=qs[1] else 2)
    bins = [ (binv(x,qx), binv(y,qy)) for x,y in zip(X,Y) ]
    # palette (low-low to high-high)
    BIV = {
        (0,0): "#e8e8e8",(1,0):"#ace4e4",(2,0):"#5ac8c8",
        (0,1): "#dfb0d6",(1,1):"#a5add3",(2,1):"#5698b9",
        (0,2): "#be64ac",(1,2):"#8c62aa",(2,2):"#3b4994",
    }
    col = [BIV.get(b,"#cccccc") for b in bins]
    fig, ax = plt.subplots(1,1, figsize=(12,10))
    # Fix: assign colors directly to the geometry column
    d_plot = d.to_crs(PLOT_CRS).copy()
    d_plot["_color"] = col
    d_plot.plot(ax=ax, color=d_plot["_color"], edgecolor="#555", linewidth=0.6)
    _add_basemap(ax, extent)
    apply_style(ax, extent)
    ax.set_title("Bivariate: PT stops /1k vs Green m² per capita", fontsize=16, fontweight="bold")

    # draw 3x3 legend
    import matplotlib.patches as mpatches
    x0,y0=0.75,0.12; s=0.06
    for i in range(3):
        for j in range(3):
            ax.add_artist(mpatches.Rectangle(
                (extent[0]+(extent[2]-extent[0])*(x0+i*s), extent[1]+(extent[3]-extent[1])*(y0+j*s)),
                (extent[2]-extent[0])*s*0.9, (extent[3]-extent[1])*s*0.9,
                facecolor=BIV[(i,j)], edgecolor="#333", lw=0.5, alpha=0.95))
    ax.text(ax.get_xlim()[0]+(ax.get_xlim()[1]-ax.get_xlim()[0])*(x0+1.5*s), 
            ax.get_ylim()[0]+(ax.get_ylim()[1]-ax.get_ylim()[0])*(y0-0.03),
            "PT stops per 1k →", fontsize=9, ha="center")
    ax.text(ax.get_xlim()[0]+(ax.get_xlim()[1]-ax.get_xlim()[0])*(x0-0.02), 
            ax.get_ylim()[0]+(ax.get_ylim()[1]-ax.get_ylim()[0])*(y0+1.5*s),
            "Green m² per capita ↑", fontsize=9, rotation=90, va="center")
    _save(fig, "04_bivariate_green_vs_pt.png")

def main():
    print("🧪 SMOKE TEST: Running just 2 maps to verify the system works...")
    
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

    # 1 — Macro: population-weighted access score with PT
    print("\n🗺️ Generating map 1: Macro green access...")
    map_01_macro_green_pt(d_kpi, layers["pt_stops"], extent)
    
    # 4 — Bivariate (PT/1k vs green m²/cap)
    print("🗺️ Generating map 2: Bivariate analysis...")
    map_04_bivariate_green_vs_pt(d_kpi, extent)
    
    print("\n🎉 Smoke test completed successfully!")
    print(f"📁 Check outputs in: {OUT_DIR}")

if __name__ == "__main__":
    main()
