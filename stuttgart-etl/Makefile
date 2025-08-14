.PHONY: install extract-osm validate clean clean-problematic test-quick test-smoke test-full

install:
	pip install -e .

extract-osm:
	python -m etl.cli extract-osm --area stuttgart --layers roads buildings landuse cycle pt_stops boundaries amenities

validate:
	python -m etl.cli validate --include-tests

clean:
	python -m etl.cli clean

clean-problematic:
	python scripts/clean_problematic_layers.py

test-quick:
	python scripts/smoke_test_quick.py

test-smoke:
	python scripts/smoke_export.py

test-full:
	python scripts/smoke_test_main_pipeline.py
