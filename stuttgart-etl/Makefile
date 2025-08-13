.PHONY: install extract-osm

install:
	pip install -e .

extract-osm:
	python -m etl.cli extract-osm --area stuttgart --layers roads buildings landuse cycle pt_stops boundaries amenities
