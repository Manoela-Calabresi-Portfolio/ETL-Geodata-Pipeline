-- Initialize DuckDB with Spatial
INSTALL spatial;
LOAD spatial;

-- Optionally create schemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS marts;
