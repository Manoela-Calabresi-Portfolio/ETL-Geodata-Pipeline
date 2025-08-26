"""
Visualization Base for Spatial Analysis Core
Provides city-agnostic visualization utilities for maps and charts.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import contextily as ctx
import numpy as np

logger = logging.getLogger(__name__)


class VisualizationBase:
    """
    Base visualization class with common map styling and export capabilities.
    """
    
    def __init__(self, city_config: Dict[str, Any]):
        """
        Initialize visualization base with city configuration.
        
        Args:
            city_config: City configuration dictionary
        """
        self.city_config = city_config
        self.city_name = city_config.get('city', {}).get('name', 'Unknown City')
        self.crs_analysis = city_config.get('city', {}).get('crs_analysis', 'EPSG:4326')
        self.output_dir = city_config.get('outputs', {}).get('maps_dir', 'outputs/maps')
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set default style
        plt.style.use('default')
        
    def create_base_map(self, 
                       districts: Optional[gpd.GeoDataFrame] = None,
                       title: str = None,
                       figsize: Tuple[int, int] = (12, 10)) -> Tuple[plt.Figure, plt.Axes]:
        """
        Create a base map with optional district boundaries.
        
        Args:
            districts: District boundaries GeoDataFrame
            title: Map title
            figsize: Figure size (width, height)
            
        Returns:
            Tuple of (figure, axes)
        """
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        
        if title is None:
            title = f"{self.city_name} - Spatial Analysis"
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        
        # Add district boundaries if provided
        if districts is not None:
            districts.plot(ax=ax, 
                         edgecolor='black', 
                         facecolor='none', 
                         linewidth=0.5,
                         alpha=0.7)
        
        # Remove axes
        ax.set_axis_off()
        
        return fig, ax
    
    def add_amenities_layer(self, 
                           ax: plt.Axes, 
                           amenities: gpd.GeoDataFrame,
                           color_column: str = None,
                           size: int = 20,
                           alpha: float = 0.7) -> None:
        """
        Add amenities layer to the map.
        
        Args:
            ax: Matplotlib axes
            amenities: Amenities GeoDataFrame
            color_column: Column to use for coloring
            size: Point size
            alpha: Transparency
        """
        if amenities is None or len(amenities) == 0:
            logger.warning("No amenities data to plot")
            return
        
        # Plot amenities
        if color_column and color_column in amenities.columns:
            # Color by category
            unique_categories = amenities[color_column].unique()
            colors = plt.cm.Set3(np.linspace(0, 1, len(unique_categories)))
            
            for i, category in enumerate(unique_categories):
                category_data = amenities[amenities[color_column] == category]
                category_data.plot(ax=ax, 
                                 color=colors[i], 
                                 markersize=size, 
                                 alpha=alpha,
                                 label=category)
        else:
            # Single color
            amenities.plot(ax=ax, 
                         color='red', 
                         markersize=size, 
                         alpha=alpha,
                         label='Amenities')
    
    def add_transit_layer(self, 
                         ax: plt.Axes, 
                         transit_stops: gpd.GeoDataFrame,
                         color: str = 'blue',
                         size: int = 15,
                         alpha: float = 0.8) -> None:
        """
        Add transit stops layer to the map.
        
        Args:
            ax: Matplotlib axes
            transit_stops: Transit stops GeoDataFrame
            color: Point color
            size: Point size
            alpha: Transparency
        """
        if transit_stops is None or len(transit_stops) == 0:
            logger.warning("No transit stops data to plot")
            return
        
        transit_stops.plot(ax=ax, 
                          color=color, 
                          markersize=size, 
                          alpha=alpha,
                          label='Transit Stops')
    
    def add_roads_layer(self, 
                       ax: plt.Axes, 
                       roads: gpd.GeoDataFrame,
                       width_column: str = None,
                       color: str = 'gray',
                       alpha: float = 0.6) -> None:
        """
        Add roads layer to the map.
        
        Args:
            ax: Matplotlib axes
            roads: Roads GeoDataFrame
            width_column: Column to use for road width
            color: Road color
            alpha: Transparency
        """
        if roads is None or len(roads) == 0:
            logger.warning("No roads data to plot")
            return
        
        if width_column and width_column in roads.columns:
            # Vary width by road importance
            roads.plot(ax=ax, 
                      color=color, 
                      linewidth=roads[width_column] * 0.5, 
                      alpha=alpha,
                      label='Roads')
        else:
            # Fixed width
            roads.plot(ax=ax, 
                      color=color, 
                      linewidth=0.8, 
                      alpha=alpha,
                      label='Roads')
    
    def add_landuse_layer(self, 
                         ax: plt.Axes, 
                         landuse: gpd.GeoDataFrame,
                         color_column: str = 'landuse',
                         alpha: float = 0.5) -> None:
        """
        Add land use layer to the map.
        
        Args:
            ax: Matplotlib axes
            landuse: Land use GeoDataFrame
            color_column: Column to use for coloring
            alpha: Transparency
        """
        if landuse is None or len(landuse) == 0:
            logger.warning("No land use data to plot")
            return
        
        if color_column and color_column in landuse.columns:
            # Color by land use type
            unique_types = landuse[color_column].unique()
            colors = plt.cm.Pastel1(np.linspace(0, 1, len(unique_types)))
            
            for i, land_type in enumerate(unique_types):
                type_data = landuse[landuse[color_column] == land_type]
                type_data.plot(ax=ax, 
                             color=colors[i], 
                             alpha=alpha,
                             label=land_type)
        else:
            # Single color
            landuse.plot(ax=ax, 
                        color='lightgreen', 
                        alpha=alpha,
                        label='Land Use')
    
    def add_legend(self, ax: plt.Axes, location: str = 'upper right') -> None:
        """
        Add legend to the map.
        
        Args:
            ax: Matplotlib axes
            location: Legend location
        """
        ax.legend(loc=location, 
                 bbox_to_anchor=(1.05, 1), 
                 borderaxespad=0.,
                 fontsize=10)
    
    def add_scale_bar(self, ax: plt.Axes, location: str = 'lower left') -> None:
        """
        Add scale bar to the map.
        
        Args:
            ax: Matplotlib axes
            location: Scale bar location
        """
        # This is a placeholder - would need proper scale bar implementation
        logger.info("Scale bar not yet implemented")
    
    def add_north_arrow(self, ax: plt.Axes, location: str = 'upper left') -> None:
        """
        Add north arrow to the map.
        
        Args:
            ax: Matplotlib axes
            location: North arrow location
        """
        # This is a placeholder - would need proper north arrow implementation
        logger.info("North arrow not yet implemented")
    
    def save_map(self, 
                fig: plt.Figure, 
                filename: str, 
                dpi: int = 300,
                bbox_inches: str = 'tight') -> str:
        """
        Save map to file.
        
        Args:
            fig: Matplotlib figure
            filename: Output filename
            dpi: Image resolution
            bbox_inches: Bounding box handling
            
        Returns:
            Full path to saved file
        """
        # Ensure filename has extension
        if not filename.endswith(('.png', '.jpg', '.pdf', '.svg')):
            filename += '.png'
        
        # Create full path
        output_path = os.path.join(self.output_dir, filename)
        
        # Save figure
        fig.savefig(output_path, 
                   dpi=dpi, 
                   bbox_inches=bbox_inches,
                   facecolor='white',
                   edgecolor='none')
        
        logger.info(f"Map saved to: {output_path}")
        return output_path
    
    def export_for_qgis(self, 
                        gdf: gpd.GeoDataFrame, 
                        filename: str,
                        format: str = 'geojson') -> str:
        """
        Export data for use in QGIS.
        
        Args:
            gdf: GeoDataFrame to export
            filename: Output filename
            format: Export format ('geojson', 'shp', 'gpkg')
            
        Returns:
            Full path to exported file
        """
        # Create QGIS export directory
        qgis_dir = os.path.join(self.output_dir, 'qgis_ready')
        os.makedirs(qgis_dir, exist_ok=True)
        
        # Ensure filename has correct extension
        if format == 'geojson' and not filename.endswith('.geojson'):
            filename += '.geojson'
        elif format == 'shp' and not filename.endswith('.shp'):
            filename += '.shp'
        elif format == 'gpkg' and not filename.endswith('.gpkg'):
            filename += '.gpkg'
        
        # Create full path
        output_path = os.path.join(qgis_dir, filename)
        
        try:
            if format == 'geojson':
                gdf.to_file(output_path, driver='GeoJSON')
            elif format == 'shp':
                gdf.to_file(output_path, driver='ESRI Shapefile')
            elif format == 'gpkg':
                gdf.to_file(output_path, driver='GPKG')
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            logger.info(f"Data exported for QGIS: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export data for QGIS: {e}")
            return None
    
    def create_choropleth_map(self, 
                             gdf: gpd.GeoDataFrame,
                             value_column: str,
                             title: str = None,
                             cmap: str = 'viridis',
                             figsize: Tuple[int, int] = (12, 10)) -> Tuple[plt.Figure, plt.Axes]:
        """
        Create a choropleth map.
        
        Args:
            gdf: GeoDataFrame with values to map
            value_column: Column containing values to color
            title: Map title
            cmap: Colormap name
            figsize: Figure size
            
        Returns:
            Tuple of (figure, axes)
        """
        if title is None:
            title = f"{self.city_name} - {value_column.replace('_', ' ').title()}"
        
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        
        # Create choropleth
        gdf.plot(column=value_column, 
                ax=ax, 
                cmap=cmap, 
                legend=True,
                legend_kwds={'label': value_column.replace('_', ' ').title()})
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_axis_off()
        
        return fig, ax
