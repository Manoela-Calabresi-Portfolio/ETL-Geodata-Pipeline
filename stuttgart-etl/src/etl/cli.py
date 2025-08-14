from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.table import Table

from .utils import ensure_directory, load_yaml, parse_bbox
from .extract_osm import extract_osm_bulk
from .validation import validate_pipeline_data
from .data_cleaner import clean_staging_data

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command("extract-osm")
def extract_osm(
	area: str = typer.Option("stuttgart", help="Area key from config/areas.yaml"),
	layers: List[str] = typer.Argument(
		..., help="Layers to extract (e.g., roads buildings landuse cycle pt_stops boundaries amenities)"
	),
	pbf_path: Optional[str] = typer.Option(None, help="Local path to .osm.pbf"),
	pbf_url: Optional[str] = typer.Option(None, help="Remote URL to .osm.pbf"),
	geofabrik_region: Optional[str] = typer.Option(None, help="Geofabrik region like 'europe/germany/baden-wuerttemberg'"),
	bbox: Optional[str] = typer.Option(None, help="minx,miny,maxx,maxy in EPSG:4326"),
	data_dir: Path = typer.Option(Path("data"), help="Project data directory"),
):
	project_cfg = load_yaml(Path("config/project.yaml"))
	areas_cfg = load_yaml(Path("config/areas.yaml"))

	area_cfg = (areas_cfg.get("areas") or {}).get(area)
	if area_cfg is None:
		typer.echo(f"Area '{area}' not found in config/areas.yaml", err=True)
		typer.Exit(code=1)

	download_dir = Path(project_cfg.get("paths", {}).get("raw_dir", data_dir / "raw"))
	staging_dir = Path(project_cfg.get("paths", {}).get("staging_dir", data_dir / "staging"))
	ensure_directory(download_dir)
	ensure_directory(staging_dir)

	# Effective parameters with area defaults
	effective_region = geofabrik_region or area_cfg.get("geofabrik_region")
	effective_bbox = parse_bbox(bbox, None)
	if effective_bbox is None:
		cfg_bbox = area_cfg.get("bbox")
		if cfg_bbox:
			effective_bbox = parse_bbox(cfg_bbox, None)

	print(f"[bold]Extracting OSM[/bold] area={area} layers={layers} region={effective_region} bbox={effective_bbox}")

	extract_osm_bulk(
		layers=layers,
		pbf_path=pbf_path,
		pbf_url=pbf_url,
		geofabrik_region=effective_region,
		download_dir=download_dir,
		staging_dir=staging_dir,
		bbox=effective_bbox,
	)

	print("[green]Done.[/green]")


@app.command("validate")
def validate(
	staging_dir: Path = typer.Option(Path("data/staging"), help="Directory containing GeoParquet staging files"),
	output_dir: Path = typer.Option(Path("data/validation"), help="Directory to write validation reports"),
    include_tests: bool = typer.Option(False, help="Also validate test_*.parquet files"),
):
	"""Validate spatial data quality for all layers in staging."""
	print("[bold]Validating spatial data[/bold]")
	ensure_directory(output_dir)

	results = validate_pipeline_data(
		staging_dir=staging_dir,
		output_dir=output_dir,
		include_tests=include_tests,
	)

	# Summarize results
	total_layers = len(results)
	passed_layers = sum(1 for r in results.values() if r.is_valid)
	failed_layers = total_layers - passed_layers

	table = Table(title="Spatial Validation Summary")
	table.add_column("Layer", style="cyan")
	table.add_column("Status", style="magenta")
	table.add_column("Success %", justify="right")
	table.add_column("Features", justify="right")

	for name, res in sorted(results.items()):
		status = "[green]PASS[/green]" if res.is_valid else "[red]FAIL[/red]"
		table.add_row(name, status, f"{res.success_rate:.1f}", f"{res.total_features}")

	print(table)
	print(f"[bold]Report:[/bold] {output_dir / 'spatial_validation_report.json'}")

	if failed_layers > 0:
		raise typer.Exit(code=1)

	print("[green]Validation complete.[/green]")


@app.command("clean")
def clean(
	staging_dir: Path = typer.Option(Path("data/staging"), help="Directory containing GeoParquet staging files"),
	layers: Optional[List[str]] = typer.Option(None, help="Specific layers to clean (default: all)"),
	backup: bool = typer.Option(True, help="Create backup of original files"),
	dry_run: bool = typer.Option(False, help="Show what would be cleaned without making changes"),
):
	"""Clean spatial data by fixing geometries, removing duplicates, and filtering tiny features."""
	print("[bold]Cleaning spatial data[/bold]")
	
	if dry_run:
		print("[yellow]DRY RUN MODE - No files will be modified[/yellow]")
		# TODO: Implement dry run functionality
		print("Dry run functionality not yet implemented")
		return
	
	# Run cleaning
	results = clean_staging_data(
		staging_dir=staging_dir,
		layers=layers,
		backup=backup
	)
	
	if "error" in results:
		print(f"[red]Error: {results['error']}[/red]")
		raise typer.Exit(code=1)
	
	# Display results table
	table = Table(title="Data Cleaning Results")
	table.add_column("Layer", style="cyan")
	table.add_column("Original", justify="right")
	table.add_column("Final", justify="right") 
	table.add_column("Removed", justify="right")
	table.add_column("Repaired", justify="right")
	table.add_column("Status", style="magenta")
	
	for layer_name, layer_result in results.get("layers", {}).items():
		if layer_result.get("success", False):
			status = "[green]✓[/green]"
			original = str(layer_result["original_features"])
			final = str(layer_result["final_features"])
			removed = str(layer_result.get("features_removed_total", 0))
			repaired = str(layer_result.get("repaired_features", 0))
		else:
			status = "[red]✗[/red]"
			original = final = removed = repaired = "N/A"
		
		table.add_row(layer_name, original, final, removed, repaired, status)
	
	print(table)
	
	# Summary
	if "summary" in results:
		summary = results["summary"]
		print(f"[bold]Summary:[/bold] {summary['files_processed']} files processed, "
			  f"{summary['features_removed']:,} features removed ({summary['removal_rate']}%)")
	
	print("[green]Cleaning complete.[/green]")


if __name__ == "__main__":
	app()
