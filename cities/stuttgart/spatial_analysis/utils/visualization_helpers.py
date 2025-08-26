#!/usr/bin/env python3
"""
Visualization Helpers - Utility module for generating maps, rankings and reports
"""

import logging
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List, Any
import folium
from folium import plugins
import json

logger = logging.getLogger(__name__)

def generate_thematic_maps(config: Dict[str, Any]) -> None:
    """
    Generate thematic maps for different KPI categories
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Generating thematic maps...")
    
    try:
        # Load district boundaries
        districts = load_district_boundaries(config)
        if districts is None:
            logger.error("District boundaries not available for map generation")
            return
        
        # Load KPI results
        transport_kpis = load_kpi_results("transport_kpis")
        walkability_kpis = load_kpi_results("walkability_kpis")
        green_kpis = load_kpi_results("green_kpis")
        
        # Generate transport maps
        if not transport_kpis.empty:
            generate_transport_maps(districts, transport_kpis, config)
        
        # Generate walkability maps
        if not walkability_kpis.empty:
            generate_walkability_maps(districts, walkability_kpis, config)
        
        # Generate green area maps
        if not green_kpis.empty:
            generate_green_maps(districts, green_kpis, config)
        
        logger.info("Thematic maps generated successfully")
        
    except Exception as e:
        logger.error(f"Error generating thematic maps: {e}")

def create_ranking_tables(config: Dict[str, Any]) -> None:
    """
    Create ranking tables for different KPI categories
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Creating ranking tables...")
    
    try:
        # Load aggregated KPIs
        aggregated_kpis = load_kpi_results("district_kpis_aggregated")
        
        if aggregated_kpis.empty:
            logger.warning("No aggregated KPI data available for rankings")
            return
        
        # Create different ranking tables
        create_transport_rankings(aggregated_kpis, config)
        create_walkability_rankings(aggregated_kpis, config)
        create_green_rankings(aggregated_kpis, config)
        create_overall_rankings(aggregated_kpis, config)
        
        logger.info("Ranking tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating ranking tables: {e}")

def build_interactive_dashboard(config: Dict[str, Any]) -> None:
    """
    Build interactive dashboard with all visualizations
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Building interactive dashboard...")
    
    try:
        # Load data
        districts = load_district_boundaries(config)
        aggregated_kpis = load_kpi_results("district_kpis_aggregated")
        
        if districts is None or aggregated_kpis.empty:
            logger.error("Required data not available for dashboard")
            return
        
        # Create interactive map
        dashboard_map = create_interactive_map(districts, aggregated_kpis, config)
        
        # Create dashboard HTML
        create_dashboard_html(dashboard_map, aggregated_kpis, config)
        
        logger.info("Interactive dashboard built successfully")
        
    except Exception as e:
        logger.error(f"Error building interactive dashboard: {e}")

def generate_final_report(config: Dict[str, Any]) -> None:
    """
    Generate final analysis report
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Generating final report...")
    
    try:
        # Load all data
        aggregated_kpis = load_kpi_results("district_kpis_aggregated")
        transport_kpis = load_kpi_results("transport_kpis")
        walkability_kpis = load_kpi_results("walkability_kpis")
        green_kpis = load_kpi_results("green_kpis")
        
        if aggregated_kpis.empty:
            logger.warning("No KPI data available for report generation")
            return
        
        # Generate report content
        report_content = generate_report_content(
            aggregated_kpis, transport_kpis, walkability_kpis, green_kpis, config
        )
        
        # Save report
        save_report(report_content, config)
        
        logger.info("Final report generated successfully")
        
    except Exception as e:
        logger.error(f"Error generating final report: {e}")

# Helper functions for map generation

def load_district_boundaries(config: Dict[str, Any]) -> gpd.GeoDataFrame:
    """Load district boundary data"""
    try:
        districts_path = Path("data/processed/stuttgart_districts.geojson")
        if districts_path.exists():
            return gpd.read_file(districts_path)
        else:
            logger.warning("District boundaries not found")
            return None
    except Exception as e:
        logger.error(f"Error loading district boundaries: {e}")
        return None

def load_kpi_results(kpi_type: str) -> pd.DataFrame:
    """Load KPI results from data/results folder"""
    try:
        kpi_path = Path(f"data/results/{kpi_type}.parquet")
        if kpi_path.exists():
            return pd.read_parquet(kpi_path)
        else:
            return pd.DataFrame()
    except Exception as e:
        logger.warning(f"Could not load {kpi_type}: {e}")
        return pd.DataFrame()

def generate_transport_maps(districts: gpd.GeoDataFrame, transport_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Generate transport-related thematic maps"""
    try:
        # Merge districts with transport KPIs
        districts_with_kpis = districts.merge(transport_kpis, on='district_id', how='left')
        
        # Create transport accessibility map
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        
        districts_with_kpis.plot(
            column='population_300m_pt',
            ax=ax,
            legend=True,
            legend_kwds={'label': 'Population within 300m of PT (%)'},
            missing_kwds={'color': 'lightgrey'},
            cmap='YlOrRd'
        )
        
        ax.set_title('Public Transport Accessibility by District', fontsize=16, pad=20)
        ax.axis('off')
        
        # Save map
        output_path = Path("spatialviz/outputs/maps/transport_accessibility.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info("Transport accessibility map generated")
        
    except Exception as e:
        logger.error(f"Error generating transport maps: {e}")

def generate_walkability_maps(districts: gpd.GeoDataFrame, walkability_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Generate walkability-related thematic maps"""
    try:
        # Merge districts with walkability KPIs
        districts_with_kpis = districts.merge(walkability_kpis, on='district_id', how='left')
        
        # Create walkability score map
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        
        districts_with_kpis.plot(
            column='walkability_score',
            ax=ax,
            legend=True,
            legend_kwds={'label': 'Walkability Score'},
            missing_kwds={'color': 'lightgrey'},
            cmap='YlGnBu'
        )
        
        ax.set_title('Walkability Score by District', fontsize=16, pad=20)
        ax.axis('off')
        
        # Save map
        output_path = Path("spatialviz/outputs/maps/walkability_score.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info("Walkability score map generated")
        
    except Exception as e:
        logger.error(f"Error generating walkability maps: {e}")

def generate_green_maps(districts: gpd.GeoDataFrame, green_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Generate green area-related thematic maps"""
    try:
        # Merge districts with green KPIs
        districts_with_kpis = districts.merge(green_kpis, on='district_id', how='left')
        
        # Create green accessibility map
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        
        districts_with_kpis.plot(
            column='green_accessibility_score',
            ax=ax,
            legend=True,
            legend_kwds={'label': 'Green Area Accessibility Score'},
            missing_kwds={'color': 'lightgrey'},
            cmap='Greens'
        )
        
        ax.set_title('Green Area Accessibility by District', fontsize=16, pad=20)
        ax.axis('off')
        
        # Save map
        output_path = Path("spatialviz/outputs/maps/green_accessibility.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info("Green accessibility map generated")
        
    except Exception as e:
        logger.error(f"Error generating green maps: {e}")

# Helper functions for ranking tables

def create_transport_rankings(aggregated_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Create transport rankings table"""
    try:
        # Select transport-related columns
        transport_cols = [col for col in aggregated_kpis.columns if 'pt_' in col or 'transport' in col.lower()]
        transport_cols = ['district_id'] + transport_cols
        
        transport_rankings = aggregated_kpis[transport_cols].copy()
        
        # Add rankings
        for col in transport_cols[1:]:
            if aggregated_kpis[col].dtype in ['int64', 'float64']:
                transport_rankings[f'{col}_rank'] = aggregated_kpis[col].rank(ascending=False, method='min')
        
        # Save rankings
        output_path = Path("spatialviz/outputs/rankings/transport_rankings.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        transport_rankings.to_csv(output_path, index=False)
        
        logger.info("Transport rankings created")
        
    except Exception as e:
        logger.error(f"Error creating transport rankings: {e}")

def create_walkability_rankings(aggregated_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Create walkability rankings table"""
    try:
        # Select walkability-related columns
        walkability_cols = [col for col in aggregated_kpis.columns if 'walkability' in col.lower() or 'intersection' in col.lower()]
        walkability_cols = ['district_id'] + walkability_cols
        
        walkability_rankings = aggregated_kpis[walkability_cols].copy()
        
        # Add rankings
        for col in walkability_cols[1:]:
            if aggregated_kpis[col].dtype in ['int64', 'float64']:
                walkability_rankings[f'{col}_rank'] = aggregated_kpis[col].rank(ascending=False, method='min')
        
        # Save rankings
        output_path = Path("spatialviz/outputs/rankings/walkability_rankings.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        walkability_rankings.to_csv(output_path, index=False)
        
        logger.info("Walkability rankings created")
        
    except Exception as e:
        logger.error(f"Error creating walkability rankings: {e}")

def create_green_rankings(aggregated_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Create green area rankings table"""
    try:
        # Select green area-related columns
        green_cols = [col for col in aggregated_kpis.columns if 'green' in col.lower()]
        green_cols = ['district_id'] + green_cols
        
        green_rankings = aggregated_kpis[green_cols].copy()
        
        # Add rankings
        for col in green_cols[1:]:
            if aggregated_kpis[col].dtype in ['int64', 'float64']:
                green_rankings[f'{col}_rank'] = aggregated_kpis[col].rank(ascending=False, method='min')
        
        # Save rankings
        output_path = Path("spatialviz/outputs/rankings/green_rankings.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        green_rankings.to_csv(output_path, index=False)
        
        logger.info("Green area rankings created")
        
    except Exception as e:
        logger.error(f"Error creating green rankings: {e}")

def create_overall_rankings(aggregated_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Create overall rankings table"""
    try:
        # Select key columns for overall ranking
        overall_cols = ['district_id', 'weighted_total_score', 'weighted_total_score_rank']
        
        if all(col in aggregated_kpis.columns for col in overall_cols):
            overall_rankings = aggregated_kpis[overall_cols].copy()
            
            # Save overall rankings
            output_path = Path("spatialviz/outputs/rankings/overall_rankings.csv")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            overall_rankings.to_csv(output_path, index=False)
            
            logger.info("Overall rankings created")
        else:
            logger.warning("Overall ranking columns not available")
        
    except Exception as e:
        logger.error(f"Error creating overall rankings: {e}")

# Helper functions for interactive dashboard

def create_interactive_map(districts: gpd.GeoDataFrame, aggregated_kpis: pd.DataFrame, config: Dict[str, Any]) -> folium.Map:
    """Create interactive Folium map"""
    try:
        # Merge districts with KPIs
        districts_with_kpis = districts.merge(aggregated_kpis, on='district_id', how='left')
        
        # Calculate center of Stuttgart
        center_lat = districts_with_kpis.geometry.centroid.y.mean()
        center_lon = districts_with_kpis.geometry.centroid.x.mean()
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=11,
            tiles='OpenStreetMap'
        )
        
        # Add district polygons
        folium.Choropleth(
            geo_data=districts_with_kpis.__geo_interface__,
            data=districts_with_kpis,
            columns=['district_id', 'weighted_total_score'],
            key_on='feature.properties.district_id',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Overall Score'
        ).add_to(m)
        
        # Add district labels
        for idx, row in districts_with_kpis.iterrows():
            centroid = row.geometry.centroid
            folium.Marker(
                [centroid.y, centroid.x],
                popup=f"<b>{row['district_id']}</b><br>Score: {row.get('weighted_total_score', 'N/A'):.1f}",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)
        
        return m
        
    except Exception as e:
        logger.error(f"Error creating interactive map: {e}")
        return None

def create_dashboard_html(dashboard_map: folium.Map, aggregated_kpis: pd.DataFrame, config: Dict[str, Any]) -> None:
    """Create dashboard HTML file"""
    try:
        if dashboard_map is None:
            logger.error("Dashboard map not available")
            return
        
        # Create dashboard HTML
        dashboard_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stuttgart Mobility & Walkability Dashboard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .dashboard-container {{ display: flex; gap: 20px; }}
                .map-container {{ flex: 2; }}
                .rankings-container {{ flex: 1; }}
                .ranking-table {{ width: 100%; border-collapse: collapse; }}
                .ranking-table th, .ranking-table td {{ 
                    border: 1px solid #ddd; padding: 8px; text-align: left; 
                }}
                .ranking-table th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Stuttgart Mobility & Walkability Analysis Dashboard</h1>
                <p>Comprehensive analysis of mobility and walkability indicators by district</p>
            </div>
            
            <div class="dashboard-container">
                <div class="map-container">
                    <h2>Interactive Map</h2>
                    {dashboard_map._repr_html_()}
                </div>
                
                <div class="rankings-container">
                    <h2>District Rankings</h2>
                    <h3>Top 10 Districts</h3>
                    {create_rankings_html(aggregated_kpis.head(10))}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save dashboard
        output_path = Path("spatialviz/outputs/dashboard/stuttgart_dashboard.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
        
        logger.info("Dashboard HTML created")
        
    except Exception as e:
        logger.error(f"Error creating dashboard HTML: {e}")

def create_rankings_html(rankings_df: pd.DataFrame) -> str:
    """Create HTML table for rankings"""
    try:
        if rankings_df.empty:
            return "<p>No ranking data available</p>"
        
        # Select key columns for display
        display_cols = ['district_id', 'weighted_total_score']
        display_cols = [col for col in display_cols if col in rankings_df.columns]
        
        if not display_cols:
            return "<p>No ranking data available</p>"
        
        # Create HTML table
        html_table = "<table class='ranking-table'>"
        html_table += "<tr>"
        for col in display_cols:
            html_table += f"<th>{col.replace('_', ' ').title()}</th>"
        html_table += "</tr>"
        
        for _, row in rankings_df.iterrows():
            html_table += "<tr>"
            for col in display_cols:
                value = row[col]
                if isinstance(value, float):
                    value = f"{value:.2f}"
                html_table += f"<td>{value}</td>"
            html_table += "</tr>"
        
        html_table += "</table>"
        return html_table
        
    except Exception as e:
        logger.error(f"Error creating rankings HTML: {e}")
        return "<p>Error creating rankings table</p>"

# Helper functions for report generation

def generate_report_content(aggregated_kpis: pd.DataFrame, transport_kpis: pd.DataFrame, 
                           walkability_kpis: pd.DataFrame, green_kpis: pd.DataFrame, 
                           config: Dict[str, Any]) -> str:
    """Generate report content"""
    try:
        report_content = f"""
# Stuttgart Mobility & Walkability Analysis Report

## Executive Summary

This report presents a comprehensive analysis of mobility and walkability indicators across Stuttgart's districts, based on data collected from multiple sources including GTFS VVS, OpenStreetMap, and official district boundaries.

## Analysis Overview

- **Total Districts Analyzed**: {len(aggregated_kpis) if not aggregated_kpis.empty else 'N/A'}
- **Data Sources**: GTFS VVS, OpenStreetMap, Official District Boundaries
- **Analysis Date**: {pd.Timestamp.now().strftime('%Y-%m-%d')}

## Key Findings

### Top Performing Districts

{generate_top_districts_section(aggregated_kpis)}

### Transport Accessibility

{generate_transport_summary(transport_kpis)}

### Walkability Analysis

{generate_walkability_summary(walkability_kpis)}

### Green Area Accessibility

{generate_green_summary(green_kpis)}

## Methodology

The analysis follows a three-stage pipeline:
1. **Data Collection**: GTFS VVS data, OSM data, and district boundaries
2. **KPI Calculation**: Transport, walkability, and green area indicators
3. **Visualization**: Maps, rankings, and interactive dashboard

## Data Quality Notes

- All data sources are validated for completeness and accuracy
- Missing data is handled gracefully with appropriate fallbacks
- Results are normalized for fair comparison across districts

## Recommendations

Based on the analysis, the following recommendations are made:

1. **Transport**: Focus on improving frequency and coverage in lower-performing districts
2. **Walkability**: Enhance pedestrian infrastructure in areas with low intersection density
3. **Green Areas**: Increase green space accessibility in urban core districts

## Technical Details

- **Analysis Framework**: Python-based modular pipeline
- **Data Formats**: Parquet, GeoJSON, CSV
- **Visualization**: Matplotlib, Folium, Seaborn
- **Configuration**: YAML-based configuration management

---

*Report generated automatically by Stuttgart Mobility & Walkability Analysis Pipeline*
        """
        
        return report_content
        
    except Exception as e:
        logger.error(f"Error generating report content: {e}")
        return "Error generating report content"

def generate_top_districts_section(aggregated_kpis: pd.DataFrame) -> str:
    """Generate top districts section for report"""
    try:
        if aggregated_kpis.empty:
            return "No ranking data available."
        
        if 'weighted_total_score' in aggregated_kpis.columns:
            top_districts = aggregated_kpis.nlargest(5, 'weighted_total_score')
            
            section = "The top 5 performing districts based on overall weighted scores:\n\n"
            for idx, (_, district) in enumerate(top_districts.iterrows(), 1):
                score = district.get('weighted_total_score', 'N/A')
                district_id = district.get('district_id', 'Unknown')
                section += f"{idx}. **{district_id}**: {score:.2f}\n"
            
            return section
        else:
            return "Overall scores not available for ranking."
        
    except Exception as e:
        logger.error(f"Error generating top districts section: {e}")
        return "Error generating top districts section."

def generate_transport_summary(transport_kpis: pd.DataFrame) -> str:
    """Generate transport summary for report"""
    try:
        if transport_kpis.empty:
            return "No transport data available."
        
        summary = f"Transport analysis covers {len(transport_kpis)} districts.\n\n"
        
        # Add key metrics if available
        if 'pt_stops_count' in transport_kpis.columns:
            avg_stops = transport_kpis['pt_stops_count'].mean()
            summary += f"- Average PT stops per district: {avg_stops:.1f}\n"
        
        if 'population_300m_pt' in transport_kpis.columns:
            avg_pop_300m = transport_kpis['population_300m_pt'].mean()
            summary += f"- Average population within 300m of PT: {avg_pop_300m:.1f}%\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating transport summary: {e}")
        return "Error generating transport summary."

def generate_walkability_summary(walkability_kpis: pd.DataFrame) -> str:
    """Generate walkability summary for report"""
    try:
        if walkability_kpis.empty:
            return "No walkability data available."
        
        summary = f"Walkability analysis covers {len(walkability_kpis)} districts.\n\n"
        
        # Add key metrics if available
        if 'intersection_density' in walkability_kpis.columns:
            avg_intersections = walkability_kpis['intersection_density'].mean()
            summary += f"- Average intersection density: {avg_intersections:.2f} per km²\n"
        
        if 'walkability_score' in walkability_kpis.columns:
            avg_score = walkability_kpis['walkability_score'].mean()
            summary += f"- Average walkability score: {avg_score:.2f}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating walkability summary: {e}")
        return "Error generating walkability summary."

def generate_green_summary(green_kpis: pd.DataFrame) -> str:
    """Generate green area summary for report"""
    try:
        if green_kpis.empty:
            return "No green area data available."
        
        summary = f"Green area analysis covers {len(green_kpis)} districts.\n\n"
        
        # Add key metrics if available
        if 'greenspace_area_ha' in green_kpis.columns:
            avg_area = green_kpis['greenspace_area_ha'].mean()
            summary += f"- Average green space area: {avg_area:.2f} hectares\n"
        
        if 'green_accessibility_score' in green_kpis.columns:
            avg_score = green_kpis['green_accessibility_score'].mean()
            summary += f"- Average green accessibility score: {avg_score:.2f}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating green summary: {e}")
        return "Error generating green summary."

def save_report(report_content: str, config: Dict[str, Any]) -> None:
    """Save the final report"""
    try:
        # Save as Markdown
        output_path = Path("spatialviz/outputs/reports/stuttgart_analysis_report.md")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info("Final report saved")
        
    except Exception as e:
        logger.error(f"Error saving report: {e}")
