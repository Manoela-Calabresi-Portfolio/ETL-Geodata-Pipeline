#!/usr/bin/env python3
"""
Geometry Utilities for Stuttgart Spatial Analysis
Provides common geometric operations and spatial calculations
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
import numpy as np
from typing import List, Tuple, Union
import logging

logger = logging.getLogger(__name__)

def create_buffer_analysis(gdf: gpd.GeoDataFrame, 
                          distance: float, 
                          crs: str = "EPSG:25832") -> gpd.GeoDataFrame:
    """
    Cria buffers ao redor de geometrias para análise de acessibilidade
    
    Args:
        gdf: GeoDataFrame com geometrias
        distance: Distância do buffer em metros
        crs: Sistema de coordenadas para cálculo (deve ser métrico)
    
    Returns:
        GeoDataFrame com buffers
    """
    logger.info(f"Creating {distance}m buffers for {len(gdf)} features")
    
    # Garantir CRS métrico para cálculo preciso
    if gdf.crs != crs:
        gdf_proj = gdf.to_crs(crs)
    else:
        gdf_proj = gdf.copy()
    
    # Criar buffers
    gdf_proj['geometry'] = gdf_proj.geometry.buffer(distance)
    
    return gdf_proj

def calculate_intersection_density(roads_gdf: gpd.GeoDataFrame,
                                 districts_gdf: gpd.GeoDataFrame,
                                 crs: str = "EPSG:25832") -> pd.DataFrame:
    """
    Calcula densidade de cruzamentos por distrito
    
    Args:
        roads_gdf: GeoDataFrame com malha viária
        districts_gdf: GeoDataFrame com distritos
        crs: CRS métrico para cálculos
    
    Returns:
        DataFrame com densidade de cruzamentos por distrito
    """
    logger.info("Calculating intersection density by district")
    
    # Converter para CRS métrico
    roads_proj = roads_gdf.to_crs(crs) if roads_gdf.crs != crs else roads_gdf
    districts_proj = districts_gdf.to_crs(crs) if districts_gdf.crs != crs else districts_gdf
    
    results = []
    
    for idx, district in districts_proj.iterrows():
        district_name = district.get('name', f'District_{idx}')
        district_geom = district.geometry
        district_area_km2 = district_geom.area / 1_000_000  # m² to km²
        
        # Filtrar estradas dentro do distrito
        roads_in_district = roads_proj[roads_proj.intersects(district_geom)]
        
        if len(roads_in_district) == 0:
            results.append({
                'district': district_name,
                'intersections': 0,
                'area_km2': district_area_km2,
                'intersection_density': 0
            })
            continue
        
        # Encontrar cruzamentos (intersections entre linhas)
        interse
        ctions = []
        road_lines = roads_in_district.geometry.tolist()
        
        for i, line1 in enumerate(road_lines):
            for j, line2 in enumerate(road_lines[i+1:], i+1):
                intersection = line1.intersection(line2)
                if intersection.geom_type == 'Point':
                    intersections.append(intersection)
                elif intersection.geom_type == 'MultiPoint':
                    intersections.extend(list(intersection.geoms))
        
        # Remover duplicatas próximas (buffer de 10m)
        if intersections:
            intersections_gdf = gpd.GeoDataFrame(
                geometry=intersections, 
                crs=crs
            )
            # Dissolver intersections próximas
            intersections_buffered = intersections_gdf.buffer(10)
            unique_intersections = unary_union(intersections_buffered)
            
            if hasattr(unique_intersections, 'geoms'):
                num_intersections = len(list(unique_intersections.geoms))
            else:
                num_intersections = 1
        else:
            num_intersections = 0
        
        density = num_intersections / district_area_km2 if district_area_km2 > 0 else 0
        
        results.append({
            'district': district_name,
            'intersections': num_intersections,
            'area_km2': district_area_km2,
            'intersection_density': density
        })
        
        logger.debug(f"{district_name}: {num_intersections} intersections, "
                    f"{density:.2f} intersections/km²")
    
    return pd.DataFrame(results)

def calculate_population_within_buffer(districts_gdf: gpd.GeoDataFrame,
                                     service_points: gpd.GeoDataFrame,
                                     buffer_distance: float,
                                     crs: str = "EPSG:25832") -> pd.DataFrame:
    """
    Calcula percentual da população dentro de buffer de serviços
    
    Args:
        districts_gdf: GeoDataFrame com distritos e população
        service_points: GeoDataFrame com pontos de serviço
        buffer_distance: Distância do buffer em metros
        crs: CRS métrico
    
    Returns:
        DataFrame com percentual de população com acesso
    """
    logger.info(f"Calculating population within {buffer_distance}m of services")
    
    # Converter para CRS métrico
    districts_proj = districts_gdf.to_crs(crs) if districts_gdf.crs != crs else districts_gdf
    services_proj = service_points.to_crs(crs) if service_points.crs != crs else service_points
    
    # Criar buffer único de todos os serviços
    if len(services_proj) == 0:
        logger.warning("No service points provided")
        return pd.DataFrame({
            'district': districts_proj.get('name', districts_proj.index),
            'population': districts_proj.get('population', 0),
            'population_with_access': 0,
            'access_percentage': 0
        })
    
    services_buffered = services_proj.buffer(buffer_distance)
    service_coverage = unary_union(services_buffered)
    
    results = []
    
    for idx, district in districts_proj.iterrows():
        district_name = district.get('name', f'District_{idx}')
        district_geom = district.geometry
        total_population = district.get('population', 0)
        
        # Calcular área com acesso
        if service_coverage.intersects(district_geom):
            access_area = service_coverage.intersection(district_geom)
            access_ratio = access_area.area / district_geom.area
        else:
            access_ratio = 0
        
        # Assumir distribuição uniforme da população
        population_with_access = total_population * access_ratio
        access_percentage = (population_with_access / total_population * 100) if total_population > 0 else 0
        
        results.append({
            'district': district_name,
            'population': total_population,
            'population_with_access': population_with_access,
            'access_percentage': access_percentage
        })
    
    return pd.DataFrame(results)

def normalize_kpi_values(df: pd.DataFrame, 
                        kpi_column: str,
                        method: str = "min_max",
                        min_val: float = None,
                        max_val: float = None) -> pd.Series:
    """
    Normaliza valores de KPI para escala 0-1
    
    Args:
        df: DataFrame com dados
        kpi_column: Nome da coluna com KPI
        method: Método de normalização ("min_max", "z_score", "rank")
        min_val: Valor mínimo de referência (opcional)
        max_val: Valor máximo de referência (opcional)
    
    Returns:
        Series com valores normalizados
    """
    values = df[kpi_column]
    
    if method == "min_max":
        min_v = min_val if min_val is not None else values.min()
        max_v = max_val if max_val is not None else values.max()
        
        if max_v == min_v:
            return pd.Series([0.5] * len(values), index=values.index)
        
        return (values - min_v) / (max_v - min_v)
    
    elif method == "z_score":
        return (values - values.mean()) / values.std()
    
    elif method == "rank":
        return values.rank(pct=True)
    
    else:
        raise ValueError(f"Unknown normalization method: {method}")

def create_population_grid(districts_gdf: gpd.GeoDataFrame,
                          grid_size: float = 100,
                          crs: str = "EPSG:25832") -> gpd.GeoDataFrame:
    """
    Cria grade populacional para análises mais precisas
    
    Args:
        districts_gdf: GeoDataFrame com distritos
        grid_size: Tamanho da célula da grade em metros
        crs: CRS métrico
    
    Returns:
        GeoDataFrame com grade populacional
    """
    logger.info(f"Creating population grid with {grid_size}m cells")
    
    districts_proj = districts_gdf.to_crs(crs) if districts_gdf.crs != crs else districts_gdf
    
    # Obter bounds totais
    total_bounds = districts_proj.total_bounds
    minx, miny, maxx, maxy = total_bounds
    
    # Criar grade
    grid_cells = []
    x_coords = np.arange(minx, maxx + grid_size, grid_size)
    y_coords = np.arange(miny, maxy + grid_size, grid_size)
    
    for x in x_coords[:-1]:
        for y in y_coords[:-1]:
            cell = Polygon([
                (x, y), (x + grid_size, y),
                (x + grid_size, y + grid_size), (x, y + grid_size)
            ])
            grid_cells.append(cell)
    
    grid_gdf = gpd.GeoDataFrame(geometry=grid_cells, crs=crs)
    
    # Atribuir população baseada na intersecção com distritos
    grid_gdf['district'] = None
    grid_gdf['population_density'] = 0
    
    for idx, district in districts_proj.iterrows():
        district_name = district.get('name', f'District_{idx}')
        district_geom = district.geometry
        district_population = district.get('population', 0)
        district_area = district_geom.area
        
        # Encontrar células que intersectam com o distrito
        intersecting = grid_gdf.intersects(district_geom)
        
        if intersecting.any():
            # Calcular densidade populacional
            pop_density = district_population / district_area
            grid_gdf.loc[intersecting, 'district'] = district_name
            grid_gdf.loc[intersecting, 'population_density'] = pop_density
    
    # Calcular população por célula
    grid_gdf['population'] = grid_gdf['population_density'] * (grid_size ** 2)
    
    return grid_gdf
