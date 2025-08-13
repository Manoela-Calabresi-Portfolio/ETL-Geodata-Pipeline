from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.table import Table

from .utils import ensure_directory, load_yaml, parse_bbox
from .extract_osm import extract_osm_bulk

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


if __name__ == "__main__":
	app()
