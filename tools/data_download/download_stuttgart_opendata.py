#!/usr/bin/env python3
"""
Download Real Stuttgart District Boundaries from Official Open Data API
Using Stuttgart's official open data portal: https://opendata.stuttgart.de/api/3
"""

import requests
import json
import geopandas as gpd
import pandas as pd
from pathlib import Path
import logging
from typing import Optional, Dict, Any

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def explore_stuttgart_api():
    """Explore Stuttgart Open Data API to find district boundaries"""
    logger = setup_logging()
    
    base_url = "https://opendata.stuttgart.de/api/3"
    
    logger.info("🔍 Exploring Stuttgart Open Data API...")
    
    try:
        # Get API info
        response = requests.get(f"{base_url}/action/status_show", timeout=30)
        response.raise_for_status()
        
        logger.info("✅ API is accessible")
        
        # Search for datasets related to districts/boundaries/parcels/planning
        search_terms = [
            "stadtbezirk", "bezirk", "district", "administrative", 
            "boundary", "grenze", "stadtteil", "ortsbeirat",
            "parcels", "parzelle", "flurstück", "grundstück",
            "bebauungsplan", "bplan", "planning", "planung",
            "kleinräumige", "gliederung", "statistical", "statistisch"
        ]
        
        datasets = []
        for term in search_terms:
            try:
                search_url = f"{base_url}/action/package_search"
                params = {
                    'q': term,
                    'rows': 20
                }
                
                response = requests.get(search_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get('success') and data.get('result', {}).get('results'):
                    for dataset in data['result']['results']:
                        if dataset not in datasets:
                            datasets.append(dataset)
                            logger.info(f"   Found: {dataset.get('name', 'Unknown')} - {dataset.get('title', 'No title')}")
                
            except Exception as e:
                logger.warning(f"   Search for '{term}' failed: {e}")
                continue
        
        return datasets
        
    except Exception as e:
        logger.error(f"❌ Error exploring API: {e}")
        return []

def download_dataset_by_id(dataset_id: str) -> Optional[gpd.GeoDataFrame]:
    """Download a specific dataset by ID"""
    logger = setup_logging()
    
    base_url = "https://opendata.stuttgart.de/api/3"
    
    try:
        # Get dataset info
        response = requests.get(f"{base_url}/action/package_show", 
                              params={'id': dataset_id}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data.get('success'):
            logger.error(f"API returned error for dataset {dataset_id}")
            return None
        
        dataset = data['result']
        logger.info(f"📦 Dataset: {dataset.get('title', dataset_id)}")
        
        # Look for GeoJSON or Shapefile resources
        resources = dataset.get('resources', [])
        geo_resources = []
        
        for resource in resources:
            format_type = resource.get('format', '').lower()
            url = resource.get('url', '')
            
            if format_type in ['geojson', 'json', 'shp', 'shapefile', 'zip'] or 'geo' in format_type:
                geo_resources.append(resource)
                logger.info(f"   📄 Found geo resource: {resource.get('name', 'Unnamed')} ({format_type})")
        
        # Try to download the best resource
        for resource in geo_resources:
            try:
                url = resource.get('url')
                format_type = resource.get('format', '').lower()
                
                logger.info(f"⬇️ Downloading: {url}")
                
                if format_type == 'geojson' or 'geojson' in url.lower():
                    # Direct GeoJSON download
                    gdf = gpd.read_file(url)
                    logger.info(f"✅ Loaded GeoJSON: {len(gdf)} features")
                    return gdf
                    
                elif format_type in ['shp', 'shapefile', 'zip']:
                    # Shapefile download
                    gdf = gpd.read_file(url)
                    logger.info(f"✅ Loaded Shapefile: {len(gdf)} features")
                    return gdf
                    
                else:
                    # Try generic file reading
                    gdf = gpd.read_file(url)
                    logger.info(f"✅ Loaded file: {len(gdf)} features")
                    return gdf
                    
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to load resource: {e}")
                continue
        
        logger.warning(f"No suitable geo resources found in dataset {dataset_id}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error downloading dataset {dataset_id}: {e}")
        return None

def categorize_datasets(datasets):
    """Categorize datasets by type"""
    categories = {
        'districts': [],
        'parcels': [],
        'planning': [],
        'statistical': [],
        'other': []
    }
    
    for dataset in datasets:
        name = dataset.get('name', '').lower()
        title = dataset.get('title', '').lower()
        description = dataset.get('notes', '').lower()
        
        text = f"{name} {title} {description}"
        
        # Categorize based on keywords
        if any(kw in text for kw in ['stadtbezirk', 'bezirk', 'district', 'ortsbeirat', 'stadtteil']):
            categories['districts'].append(dataset)
        elif any(kw in text for kw in ['parzelle', 'flurstück', 'grundstück', 'parcels', 'parcel']):
            categories['parcels'].append(dataset)
        elif any(kw in text for kw in ['bebauungsplan', 'bplan', 'planning', 'planung', 'development']):
            categories['planning'].append(dataset)
        elif any(kw in text for kw in ['kleinräumige', 'gliederung', 'statistical', 'statistisch', 'census']):
            categories['statistical'].append(dataset)
        else:
            categories['other'].append(dataset)
    
    return categories

def download_datasets_by_category():
    """Download datasets for all categories"""
    logger = setup_logging()
    
    logger.info("🔍 Searching for Stuttgart spatial datasets...")
    
    # First explore available datasets
    datasets = explore_stuttgart_api()
    
    if not datasets:
        logger.error("No datasets found in Stuttgart Open Data API")
        return {}
    
    # Categorize datasets
    categories = categorize_datasets(datasets)
    
    results = {}
    
    for category, datasets_list in categories.items():
        if not datasets_list:
            logger.info(f"📂 {category.title()}: No datasets found")
            continue
            
        logger.info(f"📂 {category.title()}: Found {len(datasets_list)} datasets")
        
        # Try downloading the most relevant datasets from each category
        for dataset in datasets_list[:3]:  # Try top 3 per category
            dataset_id = dataset.get('name') or dataset.get('id')
            dataset_title = dataset.get('title', dataset_id)
            
            logger.info(f"🔄 Trying {category}: {dataset_title}")
            
            gdf = download_dataset_by_id(dataset_id)
            if gdf is not None and len(gdf) > 0:
                logger.info(f"✅ Downloaded {category}: {len(gdf)} features")
                
                if category not in results:
                    results[category] = []
                results[category].append({
                    'name': dataset_title,
                    'id': dataset_id,
                    'data': gdf,
                    'feature_count': len(gdf)
                })
                break  # Use first successful download per category
    
    return results

def save_datasets_by_category(results: Dict[str, Any]):
    """Save downloaded datasets to appropriate locations"""
    logger = setup_logging()
    
    if not results:
        logger.warning("No results to save")
        return
    
    # Create output directories
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pipeline_dir = Path("../pipeline/areas/stuttgart/data_final/raw")
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    
    saved_datasets = {}
    
    for category, datasets_list in results.items():
        logger.info(f"💾 Saving {category} datasets...")
        
        for i, dataset_info in enumerate(datasets_list):
            gdf = dataset_info['data']
            dataset_name = dataset_info['name']
            
            # Ensure CRS is WGS84
            if gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')
            
            # Clean dataset name for filename
            clean_name = dataset_name.lower().replace(' ', '_').replace('-', '_')
            clean_name = ''.join(c for c in clean_name if c.isalnum() or c == '_')
            
            # Create filename
            if i == 0:
                filename = f"stuttgart_{category}"
            else:
                filename = f"stuttgart_{category}_{i+1}"
            
            # Save as GeoJSON in spatial_analysis
            geojson_path = output_dir / f"{filename}.geojson"
            gdf.to_file(geojson_path, driver='GeoJSON')
            logger.info(f"✅ {category.title()}: {geojson_path}")
            
            # Also save to pipeline
            pipeline_path = pipeline_dir / f"{filename}_official.geojson"
            gdf.to_file(pipeline_path, driver='GeoJSON')
            
            # Create info CSV
            try:
                # Try to find name column
                name_columns = [col for col in gdf.columns if 'name' in col.lower() and gdf[col].dtype == 'object']
                if not name_columns:
                    name_columns = [col for col in gdf.columns if gdf[col].dtype == 'object'][:1]
                
                name_col = name_columns[0] if name_columns else None
                
                info_data = {
                    'feature_id': range(1, len(gdf) + 1),
                    'area_m2': gdf.geometry.to_crs('EPSG:25832').area,
                    'area_km2': gdf.geometry.to_crs('EPSG:25832').area / 1000000,
                    'centroid_lon': gdf.geometry.centroid.x,
                    'centroid_lat': gdf.geometry.centroid.y,
                    'category': category,
                    'source': 'Stuttgart Open Data API',
                    'dataset': dataset_name
                }
                
                if name_col:
                    info_data['name'] = gdf[name_col].fillna(f'{category}_feature')
                else:
                    info_data['name'] = [f'{category}_feature_{i+1}' for i in range(len(gdf))]
                
                info_df = pd.DataFrame(info_data)
                
                info_path = output_dir / f"{filename}_info.csv"
                info_df.to_csv(info_path, index=False)
                logger.info(f"   📊 Info CSV: {info_path}")
                
            except Exception as e:
                logger.warning(f"   ⚠️ Could not create info CSV: {e}")
            
            # Store for summary
            if category not in saved_datasets:
                saved_datasets[category] = []
            saved_datasets[category].append({
                'name': dataset_name,
                'features': len(gdf),
                'path': geojson_path
            })
    
    # Print summary
    logger.info(f"\n📊 Stuttgart Open Data Download Summary:")
    total_features = 0
    for category, datasets in saved_datasets.items():
        category_features = sum(d['features'] for d in datasets)
        total_features += category_features
        logger.info(f"   📂 {category.title()}: {len(datasets)} dataset(s), {category_features} features")
        for dataset in datasets:
            logger.info(f"      - {dataset['name']}: {dataset['features']} features")
    
    logger.info(f"   🎯 Total: {total_features} features across {len(saved_datasets)} categories")
    logger.info(f"   📁 Saved to: {output_dir}")
    logger.info(f"   📁 Also copied to: {pipeline_dir}")
    
    return saved_datasets

def main():
    """Main function"""
    logger = setup_logging()
    
    print("🚀 Stuttgart Official Boundaries Downloader")
    print("Using Stuttgart Open Data API: https://opendata.stuttgart.de/api/3")
    print("=" * 60)
    
    try:
        # Download district boundaries
        gdf = find_and_download_districts()
        
        if gdf is None:
            logger.error("❌ Failed to download district boundaries")
            return 1
        
        # Save the data
        final_gdf = save_stuttgart_boundaries(gdf)
        
        logger.info("\n🎉 Success! Real Stuttgart district boundaries downloaded!")
        logger.info("📁 Files saved in: spatial_analysis/data/raw/")
        logger.info("📁 Also copied to: pipeline/areas/stuttgart/data_final/raw/")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
