#!/usr/bin/env python3
"""
Explore Stuttgart Open Data API
List all available datasets and their details
"""

import requests
import json
import pandas as pd
from pathlib import Path
import logging
from typing import List, Dict, Any

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

def get_all_datasets():
    """Get all datasets from Stuttgart Open Data API"""
    logger = setup_logging()
    
    base_url = "https://opendata.stuttgart.de/api/3"
    
    logger.info("🔍 Exploring Stuttgart Open Data API...")
    logger.info(f"API URL: {base_url}")
    
    try:
        # Get API status
        response = requests.get(f"{base_url}/action/status_show", timeout=30)
        response.raise_for_status()
        logger.info("✅ API is accessible")
        
        # Get all packages/datasets
        all_datasets = []
        start = 0
        rows = 100  # Get 100 at a time
        
        while True:
            logger.info(f"📦 Fetching datasets {start} to {start + rows}...")
            
            search_url = f"{base_url}/action/package_search"
            params = {
                'q': '*:*',  # Get all datasets
                'start': start,
                'rows': rows,
                'sort': 'metadata_created desc'  # Sort by newest first
            }
            
            response = requests.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success'):
                logger.error("API returned error")
                break
            
            result = data.get('result', {})
            datasets = result.get('results', [])
            
            if not datasets:
                break
                
            all_datasets.extend(datasets)
            
            # Check if we got all datasets
            total_count = result.get('count', 0)
            logger.info(f"   Retrieved {len(datasets)} datasets (total so far: {len(all_datasets)}/{total_count})")
            
            if len(all_datasets) >= total_count:
                break
                
            start += rows
        
        logger.info(f"🎯 Total datasets found: {len(all_datasets)}")
        return all_datasets
        
    except Exception as e:
        logger.error(f"❌ Error exploring API: {e}")
        return []

def analyze_datasets(datasets: List[Dict[Any, Any]]):
    """Analyze and categorize datasets"""
    logger = setup_logging()
    
    logger.info("📊 Analyzing datasets...")
    
    # Extract key information
    dataset_info = []
    
    for dataset in datasets:
        # Basic info
        info = {
            'id': dataset.get('id', 'unknown'),
            'name': dataset.get('name', 'unknown'),
            'title': dataset.get('title', 'No title'),
            'notes': dataset.get('notes', '')[:200] + '...' if len(dataset.get('notes', '')) > 200 else dataset.get('notes', ''),
            'author': dataset.get('author', 'Unknown'),
            'maintainer': dataset.get('maintainer', 'Unknown'),
            'license_title': dataset.get('license_title', 'Unknown'),
            'metadata_created': dataset.get('metadata_created', 'Unknown'),
            'metadata_modified': dataset.get('metadata_modified', 'Unknown'),
            'num_resources': len(dataset.get('resources', [])),
            'tags': ', '.join([tag.get('name', '') for tag in dataset.get('tags', [])]),
            'groups': ', '.join([group.get('title', '') for group in dataset.get('groups', [])]),
            'organization': dataset.get('organization', {}).get('title', 'Unknown') if dataset.get('organization') else 'Unknown'
        }
        
        # Resource info
        resources = dataset.get('resources', [])
        resource_formats = []
        resource_types = []
        has_geo_data = False
        
        for resource in resources:
            fmt = resource.get('format', '').lower()
            if fmt:
                resource_formats.append(fmt)
            
            res_type = resource.get('resource_type', '')
            if res_type:
                resource_types.append(res_type)
            
            # Check for geo data
            if any(geo_fmt in fmt for geo_fmt in ['geojson', 'shp', 'kml', 'gpx', 'wms', 'wfs']):
                has_geo_data = True
        
        info['resource_formats'] = ', '.join(set(resource_formats))
        info['resource_types'] = ', '.join(set(resource_types))
        info['has_geo_data'] = has_geo_data
        
        # Categorize
        text = f"{info['name']} {info['title']} {info['notes']} {info['tags']}".lower()
        
        categories = []
        
        # Spatial/Geographic data
        if has_geo_data or any(kw in text for kw in ['geo', 'map', 'spatial', 'coordinates', 'boundary', 'district']):
            categories.append('Geographic')
        
        # Administrative
        if any(kw in text for kw in ['stadtbezirk', 'bezirk', 'district', 'administrative', 'verwaltung', 'ortsbeirat']):
            categories.append('Administrative')
        
        # Planning
        if any(kw in text for kw in ['bebauungsplan', 'bplan', 'planning', 'planung', 'development', 'urban']):
            categories.append('Planning')
        
        # Parcels/Property
        if any(kw in text for kw in ['parzelle', 'flurstück', 'grundstück', 'parcels', 'property', 'cadastr']):
            categories.append('Parcels')
        
        # Statistical
        if any(kw in text for kw in ['statistik', 'statistical', 'census', 'population', 'demograph', 'kleinräumige']):
            categories.append('Statistical')
        
        # Transportation
        if any(kw in text for kw in ['verkehr', 'traffic', 'transport', 'mobility', 'parking', 'bike', 'bus', 'tram']):
            categories.append('Transportation')
        
        # Environment
        if any(kw in text for kw in ['umwelt', 'environment', 'green', 'park', 'tree', 'air', 'noise', 'climate']):
            categories.append('Environment')
        
        # Economy
        if any(kw in text for kw in ['wirtschaft', 'economy', 'business', 'commerce', 'industry', 'employment']):
            categories.append('Economy')
        
        # Social
        if any(kw in text for kw in ['social', 'education', 'school', 'health', 'culture', 'sport']):
            categories.append('Social')
        
        # Energy
        if any(kw in text for kw in ['energy', 'energie', 'power', 'electricity', 'solar', 'renewable']):
            categories.append('Energy')
        
        info['categories'] = ', '.join(categories) if categories else 'Other'
        
        dataset_info.append(info)
    
    return dataset_info

def save_dataset_catalog(dataset_info: List[Dict[str, Any]]):
    """Save dataset catalog to files"""
    logger = setup_logging()
    
    logger.info("💾 Saving dataset catalog...")
    
    # Create output directory
    output_dir = Path("data/catalog")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert to DataFrame
    df = pd.DataFrame(dataset_info)
    
    # Save full catalog
    full_catalog_path = output_dir / "stuttgart_opendata_catalog.csv"
    df.to_csv(full_catalog_path, index=False)
    logger.info(f"✅ Full catalog saved: {full_catalog_path}")
    
    # Save geographic datasets only
    geo_df = df[df['has_geo_data'] == True]
    if len(geo_df) > 0:
        geo_catalog_path = output_dir / "stuttgart_geographic_datasets.csv"
        geo_df.to_csv(geo_catalog_path, index=False)
        logger.info(f"✅ Geographic datasets: {geo_catalog_path} ({len(geo_df)} datasets)")
    
    # Save by categories
    for category in ['Administrative', 'Planning', 'Parcels', 'Statistical', 'Transportation', 'Environment']:
        cat_df = df[df['categories'].str.contains(category, na=False)]
        if len(cat_df) > 0:
            cat_path = output_dir / f"stuttgart_{category.lower()}_datasets.csv"
            cat_df.to_csv(cat_path, index=False)
            logger.info(f"✅ {category} datasets: {cat_path} ({len(cat_df)} datasets)")
    
    # Save summary JSON for easy reading
    summary = {
        'total_datasets': len(df),
        'geographic_datasets': len(geo_df),
        'categories': {},
        'formats': {},
        'organizations': {}
    }
    
    # Category counts
    for category in ['Administrative', 'Planning', 'Parcels', 'Statistical', 'Transportation', 'Environment', 'Economy', 'Social', 'Energy', 'Geographic']:
        count = len(df[df['categories'].str.contains(category, na=False)])
        if count > 0:
            summary['categories'][category] = count
    
    # Format counts
    all_formats = []
    for formats in df['resource_formats'].dropna():
        all_formats.extend(formats.split(', '))
    
    format_counts = pd.Series(all_formats).value_counts().to_dict()
    summary['formats'] = {k: v for k, v in format_counts.items() if v > 1}
    
    # Organization counts
    org_counts = df['organization'].value_counts().to_dict()
    summary['organizations'] = {k: v for k, v in org_counts.items() if v > 1}
    
    summary_path = output_dir / "stuttgart_opendata_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Summary saved: {summary_path}")
    
    return df, summary

def print_summary(df: pd.DataFrame, summary: Dict[str, Any]):
    """Print nice summary to console"""
    logger = setup_logging()
    
    print("\n" + "="*60)
    print("🏛️  STUTTGART OPEN DATA API - DATASET CATALOG")
    print("="*60)
    
    print(f"📊 Total Datasets: {summary['total_datasets']}")
    print(f"🗺️  Geographic Datasets: {summary['geographic_datasets']}")
    
    print(f"\n📂 Categories:")
    for category, count in sorted(summary['categories'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {category}: {count} datasets")
    
    print(f"\n📄 Data Formats:")
    for format_type, count in sorted(summary['formats'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {format_type}: {count} resources")
    
    print(f"\n🏢 Top Organizations:")
    for org, count in sorted(summary['organizations'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {org}: {count} datasets")
    
    # Show some interesting geographic datasets
    geo_df = df[df['has_geo_data'] == True]
    if len(geo_df) > 0:
        print(f"\n🗺️  Sample Geographic Datasets:")
        for _, row in geo_df.head(5).iterrows():
            print(f"   • {row['title']}")
            print(f"     Formats: {row['resource_formats']}")
            print(f"     Categories: {row['categories']}")
            print()
    
    print("="*60)
    print("📁 Files saved in: spatial_analysis/data/catalog/")
    print("="*60)

def main():
    """Main function"""
    logger = setup_logging()
    
    print("🚀 Stuttgart Open Data API Explorer")
    print("Discovering all available datasets...")
    print("="*50)
    
    try:
        # Get all datasets
        datasets = get_all_datasets()
        
        if not datasets:
            logger.error("❌ No datasets found")
            return 1
        
        # Analyze datasets
        dataset_info = analyze_datasets(datasets)
        
        # Save catalog
        df, summary = save_dataset_catalog(dataset_info)
        
        # Print summary
        print_summary(df, summary)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
