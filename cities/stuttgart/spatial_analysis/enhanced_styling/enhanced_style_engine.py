#!/usr/bin/env python3
"""
Enhanced Style Engine for Stuttgart Maps
Merges style_helpers and templates functionality to produce professional maps
"""

import yaml
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import geopandas as gpd
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

class EnhancedStyleEngine:
    """
    Enhanced style engine that produces maps exactly like the reference images
    """
    
    def __init__(self, template_path: str = None):
        """Initialize with optional template file"""
        self.template_path = Path(template_path) if template_path else None
        self.styles = self._load_default_styles()
        if self.template_path and self.template_path.exists():
            self.styles.update(self._load_template())
    
    def _load_default_styles(self) -> Dict[str, Any]:
        """Load default professional styling based on reference maps"""
        return {
            # Color schemes matching reference maps exactly
            "color_schemes": {
                "essentials_h3": {
                    "name": "Purple Sequential",
                    "colors": ["#f7f4f9", "#e7e1ef", "#d4b9da", "#c994c7", "#df65b0", "#e7298a", "#ce1256"],
                    "range": (0, 6),
                    "label": "# Essential Types (≤10 min walk)"
                },
                "service_diversity_h3": {
                    "name": "Yellow to Blue",
                    "colors": ["#ffffcc", "#c7e9b4", "#7fcdbb", "#41b6c4", "#1d91c0", "#225ea8", "#0c2c84"],
                    "range": (0.0, 3.0),
                    "label": "Service Diversity (Shannon Entropy)"
                },
                "walkability_score": {
                    "name": "Orange to Brown",
                    "colors": ["#fff7ec", "#fee8c8", "#fdd49e", "#fdbb84", "#fc8d59", "#e34a33", "#b30000"],
                    "range": (0.0, 1.0),
                    "label": "Walkability Score"
                },
                "pt_density": {
                    "name": "Light to Dark Blue",
                    "colors": ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c"],
                    "range": (0.0, 1.0),
                    "label": "PT Stop Density"
                },
                "green_space_ratio": {
                    "name": "Light to Dark Green",
                    "colors": ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45"],
                    "range": (0.0, 1.0),
                    "label": "Green Space Ratio (%)"
                },
                "mobility_score": {
                    "name": "Red to Green",
                    "colors": ["#d73027", "#f46d43", "#fdae61", "#fee08b", "#d9ef8b", "#a6d96a", "#66bd63"],
                    "range": (0.0, 1.0),
                    "label": "Mobility Score"
                },
                "overview_landuse": {
                    "name": "Land Use Categories",
                    "categories": {
                        "forest": "#2d5a27",
                        "farmland": "#8fbc8f", 
                        "parks": "#32cd32",
                        "other_green": "#90ee90",
                        "residential": "#ffb6c1",
                        "industrial": "#808080",
                        "commercial": "#ffc0cb"
                    }
                }
            },
            
            # Map layout settings
            "layout": {
                "figure_size": (20, 16),
                "dpi": 300,
                "title_fontsize": 16,
                "subtitle_fontsize": 12,
                "legend_fontsize": 11,
                "label_fontsize": 10,
                "grid_alpha": 0.3,
                "boundary_linewidth": 2,
                "boundary_color": "#000000"
            },
            
            # H3 specific settings
            "h3": {
                "edge_color": "#ffffff",
                "edge_linewidth": 0.1,
                "alpha": 0.8,
                "legend_position": "right",
                "legend_orientation": "vertical"
            },
            
            # Choropleth settings
            "choropleth": {
                "edge_color": "#555555",
                "edge_linewidth": 0.5,
                "alpha": 0.8,
                "legend_position": "right",
                "legend_orientation": "vertical"
            }
        }
    
    def _load_template(self) -> Dict[str, Any]:
        """Load additional styles from template file"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load template {self.template_path}: {e}")
            return {}
    
    def create_essentials_h3_map(self, h3_gdf: gpd.GeoDataFrame, 
                                output_path: str, 
                                title: str = "Stuttgart — Access to Essentials (H3)",
                                subtitle: str = "Erreichbarkeit von Grundversorgern (H3)") -> None:
        """
        Create H3 essentials map exactly like the reference
        """
        fig, ax = plt.subplots(figsize=self.styles["layout"]["figure_size"])
        
        # Plot H3 hexagons with essentials coverage
        scheme = self.styles["color_schemes"]["essentials_h3"]
        h3_gdf.plot(
            ax=ax, 
            column='ess_cov', 
            cmap=LinearSegmentedColormap.from_list("essentials", scheme["colors"]),
            linewidth=self.styles["h3"]["edge_linewidth"],
            edgecolor=self.styles["h3"]["edge_color"],
            alpha=self.styles["h3"]["alpha"],
            legend=True,
            legend_kwds={
                "shrink": 0.8,
                "label": scheme["label"],
                "orientation": self.styles["h3"]["legend_orientation"]
            }
        )
        
        # Add city boundary
        self._add_city_boundary(ax)
        
        # Add title and subtitle
        ax.set_title(f"{title}\n{subtitle}", 
                    fontsize=self.styles["layout"]["title_fontsize"], 
                    fontweight="bold", pad=20)
        
        # Remove axes
        ax.axis('off')
        
        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.styles["layout"]["dpi"], 
                   bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Essentials H3 map created: {output_path}")
    
    def create_service_diversity_h3_map(self, h3_gdf: gpd.GeoDataFrame, 
                                      output_path: str,
                                      title: str = "Stuttgart — Service Diversity (H3)",
                                      subtitle: str = "Dienstleistungs-Diversität (H3)") -> None:
        """
        Create H3 service diversity map exactly like the reference
        """
        fig, ax = plt.subplots(figsize=self.styles["layout"]["figure_size"])
        
        # Plot H3 hexagons with service diversity
        scheme = self.styles["color_schemes"]["service_diversity_h3"]
        h3_gdf.plot(
            ax=ax, 
            column='amen_entropy', 
            cmap=LinearSegmentedColormap.from_list("diversity", scheme["colors"]),
            linewidth=self.styles["h3"]["edge_linewidth"],
            edgecolor=self.styles["h3"]["edge_color"],
            alpha=self.styles["h3"]["alpha"],
            legend=True,
            legend_kwds={
                "shrink": 0.8,
                "label": scheme["label"],
                "orientation": self.styles["h3"]["legend_orientation"]
            }
        )
        
        # Add city boundary
        self._add_city_boundary(ax)
        
        # Add title and subtitle
        ax.set_title(f"{title}\n{subtitle}", 
                    fontsize=self.styles["layout"]["title_fontsize"], 
                    fontweight="bold", pad=20)
        
        # Remove axes
        ax.axis('off')
        
        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.styles["layout"]["dpi"], 
                   bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Service Diversity H3 map created: {output_path}")
    
    def create_walkability_score_map(self, districts_gdf: gpd.GeoDataFrame, 
                                   output_path: str,
                                   title: str = "Walkability Score") -> None:
        """
        Create walkability score map exactly like the reference
        """
        fig, ax = plt.subplots(figsize=self.styles["layout"]["figure_size"])
        
        # Plot districts with walkability scores
        scheme = self.styles["color_schemes"]["walkability_score"]
        districts_gdf.plot(
            ax=ax, 
            column='walkability_score', 
            cmap=LinearSegmentedColormap.from_list("walkability", scheme["colors"]),
            linewidth=self.styles["choropleth"]["edge_linewidth"],
            edgecolor=self.styles["choropleth"]["edge_color"],
            alpha=self.styles["choropleth"]["alpha"],
            legend=True,
            legend_kwds={
                "shrink": 0.8,
                "label": scheme["label"],
                "orientation": "horizontal"
            }
        )
        
        # Add district labels
        self._add_district_labels(ax, districts_gdf)
        
        # Add title
        ax.set_title(title, fontsize=self.styles["layout"]["title_fontsize"], 
                    fontweight="bold", pad=20)
        
        # Add metadata box
        self._add_metadata_box(ax, f"Total Districts: {len(districts_gdf)}")
        
        # Add north arrow and scale
        self._add_north_arrow(ax)
        self._add_scale_bar(ax)
        
        # Remove axes
        ax.axis('off')
        
        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.styles["layout"]["dpi"], 
                   bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Walkability Score map created: {output_path}")
    
    def create_enhanced_dashboard(self, districts_gdf: gpd.GeoDataFrame, 
                                output_path: str,
                                title: str = "Stuttgart Enhanced Mobility & Infrastructure Dashboard") -> None:
        """
        Create enhanced dashboard with 6 choropleth maps exactly like the reference
        """
        fig, axes = plt.subplots(2, 3, figsize=(24, 16))
        fig.suptitle(title, fontsize=20, fontweight="bold", y=0.98)
        
        # Define the 6 maps to create
        maps = [
            ("Overall Mobility Score", "mobility_score", "mobility_score"),
            ("Public Transport Density", "pt_density", "pt_density"),
            ("Walkability Score", "walkability_score", "walkability_score"),
            ("Amenity Density", "amenity_density", "amenity_density"),
            ("Green Space Ratio", "green_space_ratio", "green_space_ratio"),
            ("District Area (km²)", "area_km2", "district_area")
        ]
        
        for idx, (map_title, column, scheme_name) in enumerate(maps):
            row, col = idx // 3, idx % 3
            ax = axes[row, col]
            
            # Get the appropriate color scheme
            if scheme_name in self.styles["color_schemes"]:
                scheme = self.styles["color_schemes"][scheme_name]
                cmap = LinearSegmentedColormap.from_list(scheme_name, scheme["colors"])
                label = scheme["label"]
            else:
                # Default scheme
                cmap = "viridis"
                label = map_title
            
            # Plot the choropleth
            districts_gdf.plot(
                ax=ax, 
                column=column, 
                cmap=cmap,
                linewidth=self.styles["choropleth"]["edge_linewidth"],
                edgecolor=self.styles["choropleth"]["edge_color"],
                alpha=self.styles["choropleth"]["alpha"],
                legend=True,
                legend_kwds={
                    "shrink": 0.8,
                    "label": label,
                    "orientation": "vertical"
                }
            )
            
            # Add district labels
            self._add_district_labels(ax, districts_gdf)
            
            # Set title
            ax.set_title(map_title, fontsize=14, fontweight="bold")
            
            # Remove axes
            ax.axis('off')
        
        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        
        # Save
        plt.savefig(output_path, dpi=self.styles["layout"]["dpi"], 
                   bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Enhanced Dashboard created: {output_path}")
    
    def create_overview_landuse_map(self, landuse_gdf: gpd.GeoDataFrame, 
                                  roads_gdf: gpd.GeoDataFrame,
                                  pt_stops_gdf: gpd.GeoDataFrame,
                                  city_boundary_gdf: gpd.GeoDataFrame,
                                  output_path: str,
                                  title: str = "Stuttgart — Land Use + Roads + PT Stops",
                                  subtitle: str = "Flächennutzung + Straßen + ÖPNV-Haltestellen") -> None:
        """
        Create overview landuse map exactly like the reference
        """
        fig, ax = plt.subplots(figsize=self.styles["layout"]["figure_size"])
        
        # Plot landuse with category colors
        scheme = self.styles["color_schemes"]["overview_landuse"]
        categories = scheme["categories"]
        
        for category, color in categories.items():
            if category in landuse_gdf.columns:
                category_data = landuse_gdf[landuse_gdf[category] == True]
                if len(category_data) > 0:
                    category_data.plot(ax=ax, color=color, alpha=0.7, 
                                     edgecolor='none', label=category.replace('_', ' ').title())
        
        # Plot roads
        roads_gdf.plot(ax=ax, color='#808080', linewidth=0.5, alpha=0.6, label='Roads')
        
        # Plot PT stops
        pt_stops_gdf.plot(ax=ax, color='#ff0000', markersize=20, alpha=0.8, 
                          label='PT Stops')
        
        # Add city boundary
        city_boundary_gdf.boundary.plot(ax=ax, color=self.styles["layout"]["boundary_color"], 
                                       linewidth=self.styles["layout"]["boundary_linewidth"])
        
        # Add title and subtitle
        ax.set_title(f"{title}\n{subtitle}", 
                    fontsize=self.styles["layout"]["title_fontsize"], 
                    fontweight="bold", pad=20)
        
        # Add legend
        ax.legend(loc='upper right', bbox_to_anchor=(0.98, 0.98))
        
        # Remove axes
        ax.axis('off')
        
        # Save
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.styles["layout"]["dpi"], 
                   bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"✅ Overview Landuse map created: {output_path}")
    
    def _add_city_boundary(self, ax):
        """Add city boundary to map"""
        # This would need to be implemented based on your data structure
        pass
    
    def _add_district_labels(self, ax, districts_gdf):
        """Add district labels to map"""
        for idx, row in districts_gdf.iterrows():
            centroid = row.geometry.centroid
            ax.annotate(
                row.get('name', f'District {idx}'),
                xy=(centroid.x, centroid.y),
                ha='center', va='center',
                fontsize=8, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', 
                         edgecolor='black', alpha=0.8)
            )
    
    def _add_metadata_box(self, ax, text):
        """Add metadata box to map"""
        ax.text(0.02, 0.98, text, transform=ax.transAxes, 
               fontsize=10, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.5", facecolor='white', 
                        edgecolor='black', alpha=0.9),
               verticalalignment='top')
    
    def _add_north_arrow(self, ax):
        """Add north arrow to map"""
        ax.annotate(
            'N', xy=(0.95, 0.95), xycoords='axes fraction',
            xytext=(0.95, 0.85),
            ha='center', va='center',
            arrowprops=dict(arrowstyle='->', color='black', lw=2),
            fontsize=12, fontweight='bold',
            bbox=dict(boxstyle="circle,pad=0.3", facecolor='white', 
                     edgecolor='black', alpha=0.9)
        )
    
    def _add_scale_bar(self, ax):
        """Add scale bar to map"""
        # This would need to be implemented based on your map extent
        pass

# Convenience functions for easy use
def create_essentials_h3_map(h3_gdf: gpd.GeoDataFrame, output_path: str, **kwargs):
    """Create essentials H3 map with enhanced styling"""
    engine = EnhancedStyleEngine()
    engine.create_essentials_h3_map(h3_gdf, output_path, **kwargs)

def create_service_diversity_h3_map(h3_gdf: gpd.GeoDataFrame, output_path: str, **kwargs):
    """Create service diversity H3 map with enhanced styling"""
    engine = EnhancedStyleEngine()
    engine.create_service_diversity_h3_map(h3_gdf, output_path, **kwargs)

def create_walkability_score_map(districts_gdf: gpd.GeoDataFrame, output_path: str, **kwargs):
    """Create walkability score map with enhanced styling"""
    engine = EnhancedStyleEngine()
    engine.create_walkability_score_map(districts_gdf, output_path, **kwargs)

def create_enhanced_dashboard(districts_gdf: gpd.GeoDataFrame, output_path: str, **kwargs):
    """Create enhanced dashboard with enhanced styling"""
    engine = EnhancedStyleEngine()
    engine.create_enhanced_dashboard(districts_gdf, output_path, **kwargs)

def create_overview_landuse_map(landuse_gdf: gpd.GeoDataFrame, roads_gdf: gpd.GeoDataFrame,
                               pt_stops_gdf: gpd.GeoDataFrame, city_boundary_gdf: gpd.GeoDataFrame,
                               output_path: str, **kwargs):
    """Create overview landuse map with enhanced styling"""
    engine = EnhancedStyleEngine()
    engine.create_overview_landuse_map(landuse_gdf, roads_gdf, pt_stops_gdf, city_boundary_gdf, 
                                     output_path, **kwargs)
