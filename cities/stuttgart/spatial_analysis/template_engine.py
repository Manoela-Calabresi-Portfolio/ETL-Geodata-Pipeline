#!/usr/bin/env python3
"""
Template Engine for Stuttgart Maps
Reads YAML templates and applies styling automatically
"""

import yaml
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
from pathlib import Path
import geopandas as gpd
import pandas as pd

class MapTemplateEngine:
    """Engine to apply styling templates to maps"""
    
    def __init__(self, template_path):
        """Initialize with template file"""
        self.template_path = Path(template_path)
        self.styles = self.load_template()
        
    def load_template(self):
        """Load YAML template file"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading template: {e}")
            return None
    
    def apply_map_config(self, fig, ax):
        """Apply map configuration from template"""
        config = self.styles['map_config']
        
        # Set figure size
        fig.set_size_inches(*config['figure_size'])
        
        # Set title
        title_config = config['title']
        ax.set_title(
            title_config['english'],
            fontsize=title_config['font_size'],
            fontweight=title_config['font_weight'],
            pad=title_config['padding']
        )
        
        # Set subtitle
        subtitle_config = config['subtitle']
        ax.text(
            0.5, subtitle_config['y_position'],
            title_config['german'],
            transform=ax.transAxes,
            ha='center',
            fontsize=subtitle_config['font_size'],
            fontstyle=subtitle_config['font_style'],
            color=subtitle_config['color']
        )
        
        # Set background
        fig.patch.set_facecolor(config['background_color'])
        
        return fig, ax
    
    def apply_landuse_styles(self, ax, landuse_data, category_column="landuse"):
        """Apply landuse styling from template"""
        styles = self.styles['landuse_styles']
        
        for category, style in styles.items():
            # Filter data for this category
            mask = landuse_data[category_column].str.lower() == category.lower()
            if mask.any():
                category_data = landuse_data[mask]
                category_data.plot(
                    ax=ax,
                    color=style['color'],
                    alpha=style['alpha'],
                    edgecolor=style['edge_color'],
                    label=style['label']
                )
                print(f"  ✅ Applied {category} style: {style['color']}")
        
        return ax
    
    def apply_infrastructure_styles(self, ax, data_dict):
        """Apply infrastructure styling from template"""
        styles = self.styles['infrastructure_styles']
        
        # Roads
        if 'roads' in data_dict and data_dict['roads'] is not None:
            road_style = styles['roads']
            data_dict['roads'].plot(
                ax=ax,
                color=road_style['color'],
                alpha=road_style['alpha'],
                linewidth=road_style['linewidth']
            )
        
        # PT Stops
        if 'pt_stops' in data_dict and data_dict['pt_stops'] is not None:
            pt_style = styles['pt_stops']
            data_dict['pt_stops'].plot(
                ax=ax,
                color=pt_style['color'],
                alpha=pt_style['alpha'],
                markersize=pt_style['markersize']
            )
        
        # City Boundary
        if 'districts' in data_dict and data_dict['districts'] is not None:
            boundary_style = styles['city_boundary']
            districts = data_dict['districts']
            city_boundary = districts.unary_union
            boundary_gdf = gpd.GeoDataFrame(geometry=[city_boundary])
            boundary_gdf.boundary.plot(
                ax=ax,
                color=boundary_style['color'],
                linewidth=boundary_style['linewidth'],
                alpha=boundary_style['alpha']
            )
        
        return ax
    
    def apply_districts_styles(self, ax, districts_data):
        """Apply districts styling from template"""
        styles = self.styles['districts_styles']
        
        districts_data.plot(
            ax=ax,
            color=styles['fill_color'],
            edgecolor=styles['edge_color'],
            linewidth=styles['linewidth'],
            alpha=styles['alpha']
        )
        
        return ax
    
    def create_legend(self, ax):
        """Create legend from template styles"""
        legend_styles = self.styles['legend_styles']
        legend_elements = []
        
        # Add landuse legend items
        for category, style in self.styles['landuse_styles'].items():
            legend_elements.append(
                patches.Rectangle(
                    (0, 0), 1, 1,
                    facecolor=style['color'],
                    alpha=style['alpha'],
                    label=style['label']
                )
            )
        
        # Add infrastructure legend items
        infra_styles = self.styles['infrastructure_styles']
        
        # Roads
        legend_elements.append(
            Line2D([0], [0], color=infra_styles['roads']['color'],
                   alpha=infra_styles['roads']['alpha'],
                   linewidth=infra_styles['roads']['linewidth'],
                   label=infra_styles['roads']['label'])
        )
        
        # PT Stops
        legend_elements.append(
            Line2D([0], [0], marker="o", color=infra_styles['pt_stops']['color'],
                   markersize=infra_styles['pt_stops']['markersize'],
                   label=infra_styles['pt_stops']['label'])
        )
        
        # City Boundary
        legend_elements.append(
            Line2D([0], [0], color=infra_styles['city_boundary']['color'],
                   alpha=infra_styles['city_boundary']['alpha'],
                   linewidth=infra_styles['city_boundary']['linewidth'],
                   label=infra_styles['city_boundary']['label'])
        )
        
        # Create legend
        ax.legend(
            handles=legend_elements,
            loc=legend_styles['position'],
            fontsize=legend_styles['font_size'],
            title=legend_styles['title'],
            title_fontsize=legend_styles['title_font_size'],
            ncol=legend_styles['columns'],
            bbox_to_anchor=tuple(legend_styles['bbox_anchor'])
        )
        
        return ax
    
    def add_scale_bar(self, ax, extent):
        """Add scale bar from template styles"""
        styles = self.styles['scale_bar_styles']
        
        scale_x = extent[0] + (extent[2] - extent[0]) * 0.1
        scale_y = extent[1] + (extent[3] - extent[1]) * 0.1
        
        for i, distance in enumerate(styles['distances']):
            y_offset = scale_y - (i * styles['spacing'])
            
            # Draw scale bar
            ax.plot([scale_x, scale_x + distance], [y_offset, y_offset],
                   color=styles['color'], linewidth=styles['linewidth'])
            
            # Add label
            label = f"{distance//1000} km" if distance >= 1000 else f"{distance} m"
            ax.text(scale_x + distance/2, y_offset - 120, label,
                   ha='center', va='top',
                   fontsize=styles['font_size'],
                   fontweight=styles['font_weight'])
        
        return ax
    
    def export_map(self, fig, output_path, format_type="png"):
        """Export map with template quality settings"""
        quality = self.styles['export_settings']['quality']
        
        if format_type == "png":
            fig.savefig(output_path, dpi=quality['dpi'], 
                       bbox_inches='tight', facecolor='white')
        elif format_type == "pdf":
            fig.savefig(output_path, dpi=quality['dpi'],
                       bbox_inches='tight', facecolor='white')
        elif format_type == "svg":
            fig.savefig(output_path, dpi=quality['dpi'],
                       bbox_inches='tight', facecolor='white')
        
        print(f"💾 Exported: {output_path}")
        return output_path

# Example usage function
def create_map_with_template(template_path, data_dict, output_path):
    """Create a complete map using template styling"""
    
    # Initialize template engine
    engine = MapTemplateEngine(template_path)
    
    if not engine.styles:
        print("❌ Failed to load template")
        return None
    
    # Create figure and axis
    fig, ax = plt.subplots(1, 1)
    
    # Apply template styling
    fig, ax = engine.apply_map_config(fig, ax)
    ax = engine.apply_districts_styles(ax, data_dict['districts'])
    ax = engine.apply_landuse_styles(ax, data_dict['landuse'])
    ax = engine.apply_infrastructure_styles(ax, data_dict)
    ax = engine.create_legend(ax)
    
    # Get extent for scale bar
    extent = tuple(data_dict['districts'].total_bounds)
    ax = engine.add_scale_bar(ax, extent)
    
    # Set plot properties
    ax.set_aspect('equal')
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])
    ax.set_axis_off()
    
    # Export map
    result = engine.export_map(fig, output_path)
    
    plt.close(fig)
    return result

if __name__ == "__main__":
    print("🎨 Template Engine Loaded!")
    print("💡 Use create_map_with_template() function to create styled maps")

