#!/usr/bin/env python3
"""
Enhanced Stuttgart layers visualization with comprehensive reporting.
Creates maps AND detailed quality reports for each layer.
"""

from __future__ import annotations

import sys
import warnings
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

import matplotlib

# Ensure non-interactive backend for headless environments
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import geopandas as gpd
import pandas as pd
from etl.utils import ensure_directory
from etl.validation import validate_pipeline_data

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Stuttgart bounding box (from config/areas.yaml)
STUTTGART_BBOX: Tuple[float, float, float, float] = (9.0, 48.6, 9.4, 48.9)
# Plotting CRS (metric, preserves shapes/angles locally). 25832 is standard for Baden-Württemberg
PLOT_CRS: str = "EPSG:25832"

# Layer styling configuration
LAYER_STYLES: Dict[str, Dict[str, Any]] = {
    "roads": {"color": "#333333", "linewidth": 0.5, "alpha": 0.8},
    "buildings": {"facecolor": "#8B4513", "edgecolor": "#654321", "linewidth": 0.1, "alpha": 0.7},
    "landuse": {"facecolor": "#90EE90", "edgecolor": "#228B22", "linewidth": 0.2, "alpha": 0.6},
    "cycle": {"color": "#FF6B35", "linewidth": 0.8, "alpha": 0.9},
    "pt_stops": {"color": "#FF1493", "markersize": 1.5, "alpha": 0.8},
    "boundaries": {"facecolor": "none", "edgecolor": "#800080", "linewidth": 1.5, "alpha": 0.9},
    "amenities": {"color": "#FFD700", "markersize": 2.0, "alpha": 0.8},
}


class LayerAnalyzer:
    """Analyze layer data quality and generate detailed reports."""

    def __init__(self, analytics_crs: str = "EPSG:25832") -> None:
        self.analytics_crs = analytics_crs

    def analyze_layer(self, gdf: Optional[gpd.GeoDataFrame], layer_name: str) -> Dict[str, Any]:
        """Comprehensive layer analysis."""
        if gdf is None or gdf.empty:
            return {
                "layer_name": layer_name,
                "status": "EMPTY",
                "total_features": 0,
                "issues": ["Layer is empty or could not be loaded"],
                "warnings": [],
                "recommendations": ["Check if data extraction completed successfully"],
                "statistics": {},
                "geometry_analysis": {},
                "attribute_analysis": {},
                "spatial_analysis": {},
            }

        analysis: Dict[str, Any] = {
            "layer_name": layer_name,
            "total_features": int(len(gdf)),
            "status": "UNKNOWN",
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "statistics": {},
            "geometry_analysis": {},
            "attribute_analysis": {},
            "spatial_analysis": {},
        }

        # Basic statistics
        analysis["statistics"] = {
            "feature_count": int(len(gdf)),
            "crs": str(gdf.crs),
            "columns": list(gdf.columns),
            "memory_usage_mb": round(float(gdf.memory_usage(deep=True).sum()) / 1024.0 / 1024.0, 2),
        }

        # Geometry analysis
        analysis["geometry_analysis"] = self._analyze_geometries(gdf)

        # Attribute analysis
        analysis["attribute_analysis"] = self._analyze_attributes(gdf)

        # Spatial analysis
        analysis["spatial_analysis"] = self._analyze_spatial_properties(gdf, layer_name)

        # Overall status determination
        total_issues = len(analysis["issues"])
        total_warnings = len(analysis["warnings"])

        if total_issues == 0 and total_warnings <= 2:
            analysis["status"] = "GOOD"
        elif total_issues == 0 and total_warnings <= 5:
            analysis["status"] = "OK"
        elif total_issues <= 2:
            analysis["status"] = "ISSUES"
        else:
            analysis["status"] = "CRITICAL"

        return analysis

    def _analyze_geometries(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Analyze geometry quality."""
        geom_analysis: Dict[str, Any] = {
            "geometry_types": {},
            "invalid_geometries": 0,
            "empty_geometries": 0,
            "null_geometries": 0,
            "topology_issues": [],
        }

        # Geometry types
        try:
            geom_types = gdf.geometry.geom_type.value_counts().to_dict()
            geom_analysis["geometry_types"] = {str(k): int(v) for k, v in geom_types.items()}
        except Exception:
            geom_analysis["geometry_types"] = {}

        # Invalid geometries
        try:
            invalid_mask = ~gdf.geometry.is_valid
            invalid_count = int(invalid_mask.sum())
            geom_analysis["invalid_geometries"] = invalid_count

            if invalid_count > 0:
                # Sample some invalid geometries for details
                invalid_sample = gdf[invalid_mask].head(3)
                try:
                    from shapely.validation import explain_validity

                    for idx, geom in invalid_sample.geometry.items():
                        try:
                            explanation = explain_validity(geom)
                            geom_analysis["topology_issues"].append(f"Feature {idx}: {explanation}")
                        except Exception:
                            geom_analysis["topology_issues"].append(f"Feature {idx}: Invalid geometry")
                except Exception:
                    pass
        except Exception:
            geom_analysis["invalid_geometries"] = "Could not check"

        # Empty and null geometries
        try:
            empty_count = int(gdf.geometry.is_empty.sum())
            null_count = int(gdf.geometry.isnull().sum())
            geom_analysis["empty_geometries"] = empty_count
            geom_analysis["null_geometries"] = null_count
        except Exception:
            pass

        return geom_analysis

    def _analyze_attributes(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Analyze attribute quality."""
        attr_analysis: Dict[str, Any] = {
            "total_columns": max(0, int(len(gdf.columns) - 1)),  # Exclude geometry
            "null_analysis": {},
            "data_types": {},
            "unique_values": {},
        }

        # Analyze each non-geometry column
        for col in gdf.columns:
            if col == "geometry":
                continue

            # Data types
            try:
                attr_analysis["data_types"][col] = str(gdf[col].dtype)
            except Exception:
                attr_analysis["data_types"][col] = "unknown"

            # Null analysis
            try:
                null_count = int(gdf[col].isnull().sum())
                null_pct = (null_count / float(len(gdf))) * 100.0 if len(gdf) > 0 else 0.0
                attr_analysis["null_analysis"][col] = {
                    "null_count": null_count,
                    "null_percentage": round(null_pct, 1),
                }
            except Exception:
                pass

            # Unique values (for small datasets)
            try:
                if len(gdf) < 10000:
                    unique_count = int(gdf[col].nunique())
                    attr_analysis["unique_values"][col] = unique_count
            except Exception:
                pass

        return attr_analysis

    def _analyze_spatial_properties(self, gdf: gpd.GeoDataFrame, layer_name: str) -> Dict[str, Any]:
        """Analyze spatial properties."""
        spatial_analysis: Dict[str, Any] = {
            "bounding_box": [],
            "extent_analysis": {},
            "density_analysis": {},
            "size_analysis": {},
        }

        try:
            # Bounding box
            bounds = gdf.total_bounds
            spatial_analysis["bounding_box"] = [float(x) for x in bounds]

            # Check if within Stuttgart bounds (approx)
            stuttgart_bounds = STUTTGART_BBOX
            within_stuttgart = (
                bounds[0] >= stuttgart_bounds[0]
                and bounds[1] >= stuttgart_bounds[1]
                and bounds[2] <= stuttgart_bounds[2]
                and bounds[3] <= stuttgart_bounds[3]
            )
            spatial_analysis["extent_analysis"]["within_stuttgart"] = bool(within_stuttgart)

            # Convert to metric CRS for size analysis
            gdf_metric = gdf.to_crs(self.analytics_crs)

            # Size analysis for polygons
            polygon_mask = gdf_metric.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
            if bool(polygon_mask.any()):
                areas = gdf_metric[polygon_mask].geometry.area
                spatial_analysis["size_analysis"]["polygons"] = {
                    "count": int(len(areas)),
                    "min_area_m2": float(areas.min()) if len(areas) > 0 else 0.0,
                    "max_area_m2": float(areas.max()) if len(areas) > 0 else 0.0,
                    "mean_area_m2": float(areas.mean()) if len(areas) > 0 else 0.0,
                    "tiny_features": int((areas < 1.0).sum()) if len(areas) > 0 else 0,
                }

            # Size analysis for lines
            line_mask = gdf_metric.geometry.geom_type.isin(["LineString", "MultiLineString"])
            if bool(line_mask.any()):
                lengths = gdf_metric[line_mask].geometry.length
                spatial_analysis["size_analysis"]["lines"] = {
                    "count": int(len(lengths)),
                    "min_length_m": float(lengths.min()) if len(lengths) > 0 else 0.0,
                    "max_length_m": float(lengths.max()) if len(lengths) > 0 else 0.0,
                    "mean_length_m": float(lengths.mean()) if len(lengths) > 0 else 0.0,
                    "tiny_features": int((lengths < 1.0).sum()) if len(lengths) > 0 else 0,
                }

            # Density analysis (rough estimate)
            # Approximate area for bbox in km^2 using naive conversion (sufficient for indicator)
            bbox_width_deg = STUTTGART_BBOX[2] - STUTTGART_BBOX[0]
            bbox_height_deg = STUTTGART_BBOX[3] - STUTTGART_BBOX[1]
            km_per_deg = 111.0
            approx_area_km2 = max(0.0, bbox_width_deg * bbox_height_deg * km_per_deg * km_per_deg)
            if approx_area_km2 > 0:
                density_per_km2 = float(len(gdf)) / approx_area_km2
            else:
                density_per_km2 = 0.0
            spatial_analysis["density_analysis"]["features_per_km2"] = round(density_per_km2, 2)

        except Exception as e:
            spatial_analysis["error"] = str(e)

        return spatial_analysis


def load_layer_with_analysis(staging_dir: Path, layer_name: str, analyzer: LayerAnalyzer) -> Tuple[Optional[gpd.GeoDataFrame], Dict[str, Any]]:
    """Load layer and perform comprehensive analysis."""
    file_path = staging_dir / f"osm_{layer_name}.parquet"

    if not file_path.exists():
        analysis = analyzer.analyze_layer(None, layer_name)
        analysis.setdefault("issues", []).append(f"File not found: {file_path}")
        return None, analysis

    try:
        gdf = gpd.read_parquet(file_path)

        if gdf.empty:
            analysis = analyzer.analyze_layer(gdf, layer_name)
            analysis.setdefault("issues", []).append("Layer loaded but contains no features")
            return gdf, analysis

        # Ensure CRS is EPSG:4326
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif str(gdf.crs) != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        # Perform comprehensive analysis
        analysis = analyzer.analyze_layer(gdf, layer_name)

        return gdf, analysis

    except Exception as e:
        analysis = analyzer.analyze_layer(None, layer_name)
        analysis.setdefault("issues", []).append(f"Error loading layer: {str(e)}")
        return None, analysis


def generate_layer_report(analysis: Dict[str, Any]) -> str:
    """Generate a human-readable report for a layer."""
    layer_name = analysis.get("layer_name", "unknown")
    status = analysis.get("status", "UNKNOWN")

    # Status emoji
    status_emoji = {
        "GOOD": "✅",
        "OK": "⚠️",
        "ISSUES": "🔶",
        "CRITICAL": "❌",
        "EMPTY": "⭕",
    }.get(status, "❓")

    report_lines: List[str] = [
        f"\n{'='*60}",
        f"{status_emoji} LAYER REPORT: {layer_name.upper()}",
        f"{'='*60}",
        f"Status: {status_emoji} {status}",
        f"Features: {analysis.get('total_features', 0):,}",
    ]

    if analysis.get("total_features", 0) == 0:
        issues = analysis.get("issues", [])
        if issues:
            report_lines.append("\n🚨 ISSUES:")
            report_lines.extend([f"  • {issue}" for issue in issues])
        return "\n".join(report_lines)

    # Statistics
    stats = analysis.get("statistics", {})
    report_lines.extend(
        [
            f"CRS: {stats.get('crs', 'Unknown')}",
            f"Memory: {stats.get('memory_usage_mb', 0):.1f} MB",
            f"Columns: {len(stats.get('columns', []))}",
        ]
    )

    # Geometry analysis
    geom_analysis = analysis.get("geometry_analysis", {})
    if geom_analysis:
        report_lines.append(f"\n📐 GEOMETRY ANALYSIS:")
        geom_types = geom_analysis.get("geometry_types", {})
        for geom_type, count in geom_types.items():
            report_lines.append(f"  • {geom_type}: {count:,}")
        invalid_count = geom_analysis.get("invalid_geometries", 0)
        if isinstance(invalid_count, int) and invalid_count > 0:
            report_lines.append(f"  ⚠️ Invalid geometries: {invalid_count}")
            topology_issues = geom_analysis.get("topology_issues", [])
            if topology_issues:
                report_lines.append("  📍 Sample topology issues:")
                for issue in topology_issues[:3]:
                    report_lines.append(f"    - {issue}")

    # Spatial analysis
    spatial_analysis = analysis.get("spatial_analysis", {})
    if spatial_analysis:
        report_lines.append(f"\n🗺️ SPATIAL ANALYSIS:")
        bbox = spatial_analysis.get("bounding_box", [])
        if bbox and len(bbox) == 4:
            report_lines.append(
                f"  • Bounds: {bbox[0]:.3f}, {bbox[1]:.3f}, {bbox[2]:.3f}, {bbox[3]:.3f}"
            )
        extent_analysis = spatial_analysis.get("extent_analysis", {})
        within_stuttgart = bool(extent_analysis.get("within_stuttgart", False))
        report_lines.append(
            f"  • Within Stuttgart: {'✅ Yes' if within_stuttgart else '⚠️ No'}"
        )
        density = spatial_analysis.get("density_analysis", {}).get("features_per_km2", 0)
        if isinstance(density, (int, float)):
            report_lines.append(f"  • Density: {float(density):.1f} features/km²")
        size_analysis = spatial_analysis.get("size_analysis", {})
        if "polygons" in size_analysis:
            poly_info = size_analysis["polygons"]
            report_lines.append(
                f"  • Polygon areas: {poly_info.get('min_area_m2', 0.0):.1f} - {poly_info.get('max_area_m2', 0.0):.1f} m²"
            )
            tiny_poly = poly_info.get("tiny_features", 0)
            if isinstance(tiny_poly, int) and tiny_poly > 0:
                report_lines.append(f"    ⚠️ Tiny polygons (< 1m²): {tiny_poly}")
        if "lines" in size_analysis:
            line_info = size_analysis["lines"]
            report_lines.append(
                f"  • Line lengths: {line_info.get('min_length_m', 0.0):.1f} - {line_info.get('max_length_m', 0.0):.1f} m"
            )
            tiny_lines = line_info.get("tiny_features", 0)
            if isinstance(tiny_lines, int) and tiny_lines > 0:
                report_lines.append(f"    ⚠️ Tiny lines (< 1m): {tiny_lines}")

    # Attribute analysis
    attr_analysis = analysis.get("attribute_analysis", {})
    if attr_analysis:
        report_lines.append(f"\n📊 ATTRIBUTE ANALYSIS:")
        null_analysis = attr_analysis.get("null_analysis", {})
        high_null_cols = [
            (col, info.get("null_percentage", 0))
            for col, info in null_analysis.items()
            if isinstance(info.get("null_percentage", 0), (int, float)) and info.get("null_percentage", 0) > 50
        ]
        if high_null_cols:
            report_lines.append("  ⚠️ High null percentages:")
            for col, pct in high_null_cols:
                report_lines.append(f"    - {col}: {pct:.1f}% null")

    # Issues and warnings
    issues = analysis.get("issues", [])
    if issues:
        report_lines.append(f"\n🚨 ISSUES:")
        report_lines.extend([f"  • {issue}" for issue in issues])
    warns = analysis.get("warnings", [])
    if warns:
        report_lines.append(f"\n⚠️ WARNINGS:")
        report_lines.extend([f"  • {w}" for w in warns])
    recs = analysis.get("recommendations", [])
    if recs:
        report_lines.append(f"\n💡 RECOMMENDATIONS:")
        report_lines.extend([f"  • {r}" for r in recs])

    return "\n".join(report_lines)


def create_summary_report(all_analyses: Dict[str, Dict[str, Any]], validation_results: Optional[Dict[str, Any]] = None) -> str:
    """Generate overall summary report."""
    total_features = sum(int(a.get("total_features", 0)) for a in all_analyses.values())

    status_counts: Dict[str, int] = {}
    for analysis in all_analyses.values():
        status = analysis.get("status", "UNKNOWN")
        status_counts[status] = status_counts.get(status, 0) + 1

    lines: List[str] = [
        f"\n{'='*80}",
        f"🎯 STUTTGART LAYERS SUMMARY REPORT",
        f"{'='*80}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Total Layers: {len(all_analyses)}",
        f"Total Features: {total_features:,}",
        f"\n📊 LAYER STATUS OVERVIEW:",
    ]

    for status, count in sorted(status_counts.items()):
        emoji = {"GOOD": "✅", "OK": "⚠️", "ISSUES": "🔶", "CRITICAL": "❌", "EMPTY": "⭕"}.get(status, "❓")
        lines.append(f"  {emoji} {status}: {count} layers")

    # Layer summary table
    lines.append(f"\n📋 DETAILED LAYER SUMMARY:")
    lines.append(f"{'Layer':<15} {'Status':<10} {'Features':<12} {'Issues':<8} {'Warnings':<8}")
    lines.append("-" * 60)

    for layer_name, analysis in sorted(all_analyses.items()):
        status_emoji = {"GOOD": "✅", "OK": "⚠️", "ISSUES": "🔶", "CRITICAL": "❌", "EMPTY": "⭕"}.get(
            analysis.get("status", "UNKNOWN"), "❓"
        )
        lines.append(
            f"{layer_name:<15} {status_emoji} {analysis.get('status','UNKNOWN'):<9} {int(analysis.get('total_features',0)):<12,} "
            f"{len(analysis.get('issues', [])):<8} {len(analysis.get('warnings', [])):<8}"
        )

    # Validation results integration
    if validation_results:
        lines.append(f"\n🔍 VALIDATION RESULTS:")
        summary = validation_results.get("summary", {})
        lines.append(
            f"  • Validation passed: {int(summary.get('passed_layers', 0))}/{int(summary.get('total_layers', 0))} layers"
        )
        lines.append(f"  • Total features validated: {int(summary.get('total_features', 0)):,}")

    # Recommendations
    lines.append(f"\n💡 OVERALL RECOMMENDATIONS:")

    critical_layers = [name for name, analysis in all_analyses.items() if analysis.get("status") == "CRITICAL"]
    if critical_layers:
        lines.append(f"  🚨 CRITICAL: Fix these layers immediately: {', '.join(critical_layers)}")

    issue_layers = [name for name, analysis in all_analyses.items() if analysis.get("status") == "ISSUES"]
    if issue_layers:
        lines.append(f"  🔶 ISSUES: Address problems in: {', '.join(issue_layers)}")

    empty_layers = [name for name, analysis in all_analyses.items() if analysis.get("status") == "EMPTY"]
    if empty_layers:
        lines.append(f"  ⭕ EMPTY: Re-extract these layers: {', '.join(empty_layers)}")

    if not critical_layers and not issue_layers and not empty_layers:
        lines.append(f"  ✅ All layers are in good condition!")

    return "\n".join(lines)


def _project_and_clip(gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, Tuple[float, float, float, float]]:
    """Project data to plotting CRS and clip to Stuttgart bbox for clean rendering.

    Returns projected GeoDataFrame and extent (minx, miny, maxx, maxy).
    Falls back to EPSG:4326 if projection fails.
    """
    try:
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        bbox_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_bbox(STUTTGART_BBOX), crs="EPSG:4326")
        gdf_proj = gdf.to_crs(PLOT_CRS)
        bbox_proj = bbox_gdf.to_crs(PLOT_CRS)
        # Clip to bbox polygon to avoid long diagonal artifacts
        gdf_proj = gpd.clip(gdf_proj, bbox_proj.geometry.iloc[0])
        extent = tuple(bbox_proj.total_bounds)  # type: ignore[assignment]
        return gdf_proj, extent  # type: ignore[return-value]
    except Exception:
        # Fallback: no projection
        return gdf, STUTTGART_BBOX


def create_individual_maps(layers: Dict[str, gpd.GeoDataFrame], analyses: Dict[str, Dict[str, Any]], output_dir: Path) -> None:
    """Create individual maps for each layer with quality indicators."""
    print("\n📊 Creating individual layer maps with quality indicators...")

    for layer_name, gdf in layers.items():
        if gdf is None or gdf.empty:
            continue

        analysis = analyses.get(layer_name, {})
        status = analysis.get("status", "UNKNOWN")

        fig, ax = plt.subplots(1, 1, figsize=(14, 11))

        # Project to metric CRS and clip
        gdf_plot, extent = _project_and_clip(gdf)

        # Set map extent to projected Stuttgart bbox
        ax.set_xlim(extent[0], extent[2])
        ax.set_ylim(extent[1], extent[3])

        # Get layer style
        style = LAYER_STYLES.get(layer_name, {"color": "blue", "alpha": 0.7})

        # Plot based on geometry type
        geom_types = list(gdf_plot.geometry.geom_type.unique())

        if any(gt in geom_types for gt in ["Point", "MultiPoint"]):
            gdf_plot.plot(
                ax=ax,
                color=style.get("color", "blue"),
                markersize=style.get("markersize", 1.0),
                alpha=style.get("alpha", 0.7),
            )
        elif any(gt in geom_types for gt in ["LineString", "MultiLineString"]):
            gdf_plot.plot(
                ax=ax,
                color=style.get("color", "blue"),
                linewidth=style.get("linewidth", 0.5),
                alpha=style.get("alpha", 0.7),
            )
        else:
            gdf_plot.plot(
                ax=ax,
                facecolor=style.get("facecolor", "lightblue"),
                edgecolor=style.get("edgecolor", "blue"),
                linewidth=style.get("linewidth", 0.1),
                alpha=style.get("alpha", 0.7),
            )

        # Status indicator
        status_emoji = {
            "GOOD": "✅",
            "OK": "⚠️",
            "ISSUES": "🔶",
            "CRITICAL": "❌",
            "EMPTY": "⭕",
        }.get(status, "❓")
        status_color = {
            "GOOD": "green",
            "OK": "orange",
            "ISSUES": "red",
            "CRITICAL": "darkred",
            "EMPTY": "gray",
        }.get(status, "blue")

        # Title with status
        ax.set_title(
            f"Stuttgart - {layer_name.title()} Layer {status_emoji}\n{len(gdf):,} features - Status: {status}",
            fontsize=14,
            fontweight='bold',
        )
        ax.set_xlabel("Easting (m) — EPSG:25832", fontsize=12)
        ax.set_ylabel("Northing (m)", fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        # Quality info box
        info_lines: List[str] = [f"Features: {len(gdf):,}", f"Status: {status}"]

        # Add key statistics
        geom_analysis = analysis.get("geometry_analysis", {})
        invalid_count = geom_analysis.get("invalid_geometries", 0)
        if isinstance(invalid_count, int) and invalid_count > 0:
            info_lines.append(f"Invalid: {invalid_count}")

        spatial_analysis = analysis.get("spatial_analysis", {})
        density_val = spatial_analysis.get("density_analysis", {}).get("features_per_km2", 0)
        if isinstance(density_val, (int, float)) and density_val > 0:
            info_lines.append(f"Density: {float(density_val):.0f}/km²")

        info_text = "\n".join(info_lines)
        ax.text(
            0.02,
            0.98,
            info_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor=status_color, linewidth=2),
        )

        # Issues indicator
        issues_list = analysis.get("issues", [])
        warnings_list = analysis.get("warnings", [])
        if issues_list or warnings_list:
            issue_text = f"Issues: {len(issues_list)}\nWarnings: {len(warnings_list)}"
            ax.text(
                0.98,
                0.98,
                issue_text,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.8),
            )

        # Save map
        output_file = output_dir / f"stuttgart_{layer_name}_map_with_report.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"   💾 Saved: {output_file}")


def create_overview_map(layers: Dict[str, gpd.GeoDataFrame], output_dir: Path) -> None:
    """Create combined overview map with all layers."""
    print("\n🗺️ Creating combined overview map...")

    fig, ax = plt.subplots(1, 1, figsize=(16, 12))

    # Set map extent (projected)
    try:
        bbox_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_bbox(STUTTGART_BBOX), crs="EPSG:4326").to_crs(PLOT_CRS)
        extent = tuple(bbox_gdf.total_bounds)
    except Exception:
        extent = STUTTGART_BBOX
    ax.set_xlim(extent[0], extent[2])
    ax.set_ylim(extent[1], extent[3])

    # Plot layers in order (background to foreground)
    layer_order = ["boundaries", "landuse", "buildings", "roads", "cycle", "amenities", "pt_stops"]

    legend_elements: List[Any] = []

    for layer_name in layer_order:
        if layer_name not in layers or layers[layer_name] is None:
            continue

        gdf = layers[layer_name]
        if gdf.empty:
            continue

        # Project and clip for clean rendering
        gdf_plot, _extent = _project_and_clip(gdf)
        style = LAYER_STYLES.get(layer_name, {"color": "blue", "alpha": 0.7})
        geom_types = list(gdf_plot.geometry.geom_type.unique())

        # Plot layer
        if any(gt in geom_types for gt in ["Point", "MultiPoint"]):
            gdf_plot.plot(
                ax=ax,
                color=style.get("color", "blue"),
                markersize=style.get("markersize", 1.0),
                alpha=style.get("alpha", 0.7),
                label=f"{layer_name.title()} ({len(gdf):,})",
            )
            legend_elements.append(
                plt.Line2D(
                    [0],
                    [0],
                    marker='o',
                    color='w',
                    markerfacecolor=style.get("color", "blue"),
                    markersize=8,
                    label=f"{layer_name.title()} ({len(gdf):,})",
                )
            )
        elif any(gt in geom_types for gt in ["LineString", "MultiLineString"]):
            gdf_plot.plot(
                ax=ax,
                color=style.get("color", "blue"),
                linewidth=style.get("linewidth", 0.5),
                alpha=style.get("alpha", 0.7),
                label=f"{layer_name.title()} ({len(gdf):,})",
            )
            legend_elements.append(
                plt.Line2D(
                    [0],
                    [0],
                    color=style.get("color", "blue"),
                    linewidth=2,
                    label=f"{layer_name.title()} ({len(gdf):,})",
                )
            )
        else:
            gdf_plot.plot(
                ax=ax,
                facecolor=style.get("facecolor", "lightblue"),
                edgecolor=style.get("edgecolor", "blue"),
                linewidth=style.get("linewidth", 0.1),
                alpha=style.get("alpha", 0.7),
                label=f"{layer_name.title()} ({len(gdf):,})",
            )
            legend_elements.append(
                patches.Patch(
                    facecolor=style.get("facecolor", "lightblue"),
                    edgecolor=style.get("edgecolor", "blue"),
                    label=f"{layer_name.title()} ({len(gdf):,})",
                )
            )

    # Styling
    ax.set_title("Stuttgart - All Layers Overview", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel("Easting (m) — EPSG:25832", fontsize=12)
    ax.set_ylabel("Northing (m)", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')

    # Add legend
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=10)

    # Add total features count
    total_features = sum(len(gdf) for gdf in layers.values() if gdf is not None and not gdf.empty)
    ax.text(
        0.02,
        0.02,
        f"Total Features: {total_features:,}",
        transform=ax.transAxes,
        fontsize=12,
        fontweight='bold',
        verticalalignment='bottom',
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9),
    )

    # Save overview map
    output_file = output_dir / "stuttgart_overview_map.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"   💾 Saved: {output_file}")


def visualize_stuttgart_with_reports() -> bool:
    """Main function with comprehensive reporting."""
    print("🗺️ STUTTGART LAYERS VISUALIZATION + REPORTING")
    print("=" * 60)

    staging_dir = Path("data/staging")
    output_dir = Path("data/maps")
    reports_dir = Path("data/reports")
    validation_dir = Path("data/validation")

    ensure_directory(output_dir)
    ensure_directory(reports_dir)

    # Initialize analyzer
    analyzer = LayerAnalyzer()

    # Available layers
    layer_names = [
        "roads",
        "buildings",
        "landuse",
        "cycle",
        "pt_stops",
        "boundaries",
        "amenities",
    ]

    print(f"📁 Loading layers from: {staging_dir}")
    print(f"💾 Saving maps to: {output_dir}")
    print(f"📄 Saving reports to: {reports_dir}")

    # Load all layers with analysis
    layers: Dict[str, Optional[gpd.GeoDataFrame]] = {}
    all_analyses: Dict[str, Dict[str, Any]] = {}

    for layer_name in layer_names:
        print(f"\n📖 Analyzing {layer_name}...")
        gdf, analysis = load_layer_with_analysis(staging_dir, layer_name, analyzer)
        layers[layer_name] = gdf
        all_analyses[layer_name] = analysis

        status_emoji = {"GOOD": "✅", "OK": "⚠️", "ISSUES": "🔶", "CRITICAL": "❌", "EMPTY": "⭕"}.get(
            analysis.get("status", "UNKNOWN"), "❓"
        )
        print(f"   {status_emoji} {analysis.get('status','UNKNOWN')}: {int(analysis.get('total_features',0)):,} features")

    # Load validation results if available
    validation_results: Optional[Dict[str, Any]] = None
    validation_file = validation_dir / "spatial_validation_report.json"
    if validation_file.exists():
        try:
            with open(validation_file, "r", encoding="utf-8") as f:
                validation_results = json.load(f)
            print(f"\n📋 Loaded validation results from: {validation_file}")
        except Exception as e:
            print(f"⚠️ Could not load validation results: {str(e)}")

    # Filter valid layers for mapping
    valid_layers: Dict[str, gpd.GeoDataFrame] = {
        name: g for name, g in layers.items() if g is not None and not g.empty
    }

    if valid_layers:
        print(f"\n✅ Found {len(valid_layers)} valid layers for mapping")

        # Create individual maps with quality indicators
        create_individual_maps(valid_layers, all_analyses, output_dir)

        # Create overview map
        create_overview_map(valid_layers, output_dir)
    else:
        print("\n❌ No valid layers found for mapping!")

    # Generate detailed reports
    print(f"\n📄 Generating detailed reports...")

    # Individual layer reports
    for layer_name, analysis in all_analyses.items():
        layer_report = generate_layer_report(analysis)
        report_file = reports_dir / f"{layer_name}_detailed_report.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(layer_report)
        print(f"   📄 Saved: {report_file}")

    # Summary report
    summary_report = create_summary_report(all_analyses, validation_results)
    summary_file = reports_dir / "stuttgart_summary_report.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary_report)

    # JSON report for programmatic use
    json_report: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_layers": len(all_analyses),
            "total_features": sum(int(a.get("total_features", 0)) for a in all_analyses.values()),
            "status_counts": {},
        },
        "layers": all_analyses,
        "validation_results": validation_results,
    }

    # Count statuses
    for analysis in all_analyses.values():
        status = analysis.get("status", "UNKNOWN")
        json_report["summary"]["status_counts"][status] = json_report["summary"]["status_counts"].get(status, 0) + 1

    json_file = reports_dir / "stuttgart_comprehensive_report.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False, default=str)

    # Print summary to console
    print(summary_report)

    print(f"\n📁 Reports saved to: {reports_dir}")
    print(f"  📄 Summary: {summary_file}")
    print(f"  📊 JSON: {json_file}")
    print(f"  📋 Individual: {len(all_analyses)} layer reports")

    return True


if __name__ == "__main__":
    try:
        success = visualize_stuttgart_with_reports()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


