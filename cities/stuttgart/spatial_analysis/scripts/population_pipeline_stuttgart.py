# spatialviz/population_pipeline_stuttgart.py
#!/usr/bin/env python3
from __future__ import annotations
import io, json
from pathlib import Path
import requests
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid
from utils.h3_helpers import polygon_geom_to_h3_cells, h3_to_shapely_geometry

# CKAN resource: Einwohner nach Altersgruppen und Stadtbezirken
CKAN_CSV_URL = (
    "https://opendata.stuttgart.de/dataset/85a06c70-d65e-46fd-861b-2de52c008579/resource/"
    "2842140d-8787-475d-b1b9-35a496b503e3/download/"
    "einwohner-in-stuttgart-nach-altersgruppen-und-stadtbezirken-seit-1986.csv"
)

# Updated paths to match current project structure
DATA_DIR = Path("../data")
OUT_DIR  = DATA_DIR
DISTRICTS_PATH = Path("../spatial_analysis/areas/stuttgart_districts_official/OpenData_KLGL_GENERALISIERT.gpkg")
H3_RES = 8  # Using resolution 8 as requested

def _read_ckan_csv(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    # Stuttgart CSV uses semicolon separators
    return pd.read_csv(io.StringIO(r.text), sep=';')

def _latest_totals(df: pd.DataFrame) -> pd.DataFrame:
    # Handle the actual Stuttgart CSV structure
    df = df.rename(columns=lambda c: c.strip())
    
    # Check if we have the expected columns, if not, try to parse the single column
    if len(df.columns) == 1 and 'Stichtag;Stadtbezirk;Alter in 10 Gruppen;Einwohner' in df.columns:
        # Split the single column into multiple columns
        df = df['Stichtag;Stadtbezirk;Alter in 10 Gruppen;Einwohner'].str.split(';', expand=True)
        df.columns = ['Stichtag', 'Stadtbezirk', 'Alter in 10 Gruppen', 'Einwohner']
    
    # Rename columns to our expected format
    ren = {"Stichtag":"year","Stadtbezirk":"district","Einwohner":"pop","Alter in 10 Gruppen":"age"}
    df = df.rename(columns={k:v for k,v in ren.items() if k in df.columns})
    
    # Extract year from date string (format: DD.MM.YYYY)
    if "year" in df.columns:
        df["year"] = df["year"].astype(str).str.extract(r'(\d{4})').astype(int)
    
    # Find the latest year
    latest = int(df["year"].max())
    d = df[df["year"]==latest].copy()
    
    # Check if we have age groups, if so, look for total population
    if "age" in d.columns:
        m = d["age"].astype(str).str.lower().isin(["insgesamt","total","summe","alle"])
        if m.any(): 
            d = d[m]
        else: 
            # If no total row, sum by district
            d = d.groupby("district",as_index=False)["pop"].sum().assign(year=latest)
    
    # Clean district names
    d["district"] = d["district"].astype(str).str.replace(r"\s+"," ",regex=True).str.strip()
    d = d.groupby(["district","year"],as_index=False)["pop"].sum()
    
    return d

def _load_districts() -> gpd.GeoDataFrame:
    # Read the specific layer for city districts
    g = gpd.read_file(DISTRICTS_PATH, layer="KLGL_BRUTTO_STADTBEZIRK")
    g = g.set_crs(4326) if g.crs is None else g.to_crs(4326)
    
    # Debug: print available columns
    print(f"Available columns: {g.columns.tolist()}")
    
    name_col = None
    for c in ["district_norm","name","bezirk","district","GEN","STADTBEZIRKNAME"]: 
        if c in g.columns: 
            name_col=c; 
            break
    
    if name_col is None:
        # If no standard name column found, use the first string column
        string_cols = [col for col in g.columns if g[col].dtype == 'object']
        if string_cols:
            name_col = string_cols[0]
            print(f"Using column '{name_col}' as district name")
        else:
            raise ValueError("No suitable name column found in districts file")
    
    if name_col != "district_norm":
        g["district_norm"] = g[name_col].astype(str).str.replace(r"\s+"," ",regex=True).str.strip()
    
    g["geometry"] = g.geometry.apply(make_valid)
    return g

def _areal_weight_to_h3(districts: gpd.GeoDataFrame, totals: pd.DataFrame, res: int) -> pd.DataFrame:
    d = districts.merge(totals.rename(columns={"district":"district_norm"}), on="district_norm", how="left")
    d["pop"]=d["pop"].fillna(0).astype(float)
    d_wm = d.to_crs(3857)

    rows=[]
    for idx,row in d.iterrows():
        # Use the new h3 helper function
        hexes = list(polygon_geom_to_h3_cells(row.geometry, res))
        if not hexes: continue
        dpoly = d_wm.loc[idx,"geometry"]; dA=dpoly.area
        if dA<=0: continue
        for h in hexes:
            # Use our custom helper to get the boundary
            poly = h3_to_shapely_geometry(h)
            p = gpd.GeoSeries([poly], crs=4326).to_crs(3857).iloc[0]
            inter = p.intersection(dpoly)
            if inter.is_empty: continue
            frac = float(inter.area/dA)
            if frac<=0: continue
            rows.append({"h3":h,"district_norm":row["district_norm"],"frac":frac})
    if not rows: return pd.DataFrame(columns=["h3","pop"])

    hx = pd.DataFrame(rows)
    s = hx.groupby("district_norm")["frac"].sum().replace(0,1.0)
    hx = hx.join(s, on="district_norm", rsuffix="_sum")
    hx["w"] = hx["frac"]/hx["frac_sum"]
    pop_map = d.set_index("district_norm")["pop"].to_dict()
    hx["pop"] = hx["district_norm"].map(pop_map).fillna(0)*hx["w"]
    out = hx.groupby("h3", as_index=False)["pop"].sum()
    return out

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Fetching population CSV from Stuttgart Open Data…")
    raw = _read_ckan_csv(CKAN_CSV_URL)
    latest = _latest_totals(raw)
    (OUT_DIR/"population_by_district.csv").write_text(latest.to_csv(index=False), encoding="utf-8")
    print("Saved population_by_district.csv")

    print("Loading districts geometry…")
    districts = _load_districts()
    joined = districts.merge(latest.rename(columns={"district":"district_norm"}), on="district_norm", how="left")
    joined["pop"]=joined["pop"].fillna(0)
    # density
    A_km2 = joined.to_crs(3857).area/1e6
    joined["pop_density_km2"] = (joined["pop"]/A_km2.replace(0,np.nan)).round(1)
    joined.to_file(OUT_DIR/"districts_with_population.geojson", driver="GeoJSON")
    print("Saved districts_with_population.geojson")

    print(f"Computing H3 surface (res={H3_RES})…")
    h3df = _areal_weight_to_h3(districts, latest, H3_RES)
    h3df.to_parquet(OUT_DIR/f"h3_population_res{H3_RES}.parquet", index=False)
    print(f"Saved h3_population_res{H3_RES}.parquet")

if __name__ == "__main__":
    main()
