# 🗄️ Database Integration

## 🔺 **PostgreSQL + PostGIS Setup**

### **System Requirements**
- **PostgreSQL**: Version 17+ (recommended)
- **PostGIS**: Version 3.5+ extension
- **Python**: 3.8+ with required packages
- **Memory**: Minimum 4GB RAM, 8GB+ recommended
- **Storage**: 10GB+ free space for city data

### **Installation Steps**

#### **1. PostgreSQL Installation**
```bash
# Windows (using installer)
# Download from: https://www.postgresql.org/download/windows/
# Install with default settings, remember the password

# macOS (using Homebrew)
brew install postgresql@17
brew services start postgresql@17

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql-17 postgresql-17-postgis-3
sudo systemctl start postgresql
```

#### **2. PostGIS Extension**
```bash
# Enable PostGIS extension
python spatial_analysis_core/database/manage_database.py enable-postgis

# Verify PostGIS installation
python spatial_analysis_core/database/manage_database.py check-postgis
```

#### **3. Database Setup**
```bash
# Setup database and schemas
python spatial_analysis_core/database/manage_database.py setup

# Test connection
python spatial_analysis_core/database/manage_database.py test-connection
```

## 🖥️ **CLI Commands**

### **Database Management Commands**

#### **Connection Testing**
```bash
# Test database connection
python spatial_analysis_core/database/manage_database.py test-connection

# Test with specific database
python spatial_analysis_core/database/manage_database.py test-connection --database my_city_db
```

#### **Database Setup**
```bash
# Setup complete database environment
python spatial_analysis_core/database/manage_database.py setup

# Setup specific database
python spatial_analysis_core/database/manage_database.py setup --database my_city_db

# Create schemas only
python spatial_analysis_core/database/manage_database.py setup --schemas-only
```

#### **PostGIS Management**
```bash
# Enable PostGIS extension
python spatial_analysis_core/database/manage_database.py enable-postgis

# Check PostGIS status
python spatial_analysis_core/database/manage_database.py check-postgis

# Verify spatial functions
python spatial_analysis_core/database/manage_database.py test-spatial
```

#### **PostGIS File Management**
```bash
# Copy PostGIS files (if needed)
python spatial_analysis_core/database/manage_database.py copy-postgis

# Find PostGIS control files
python spatial_analysis_core/database/manage_database.py find-postgis
```

### **Command Options**
```bash
# Help for any command
python spatial_analysis_core/database/manage_database.py --help

# Verbose output
python spatial_analysis_core/database/manage_database.py setup --verbose

# Dry run (show what would be done)
python spatial_analysis_core/database/manage_database.py setup --dry-run
```

## 🐍 **Python API Examples**

### **Basic Database Operations**

#### **Database Connection**
```python
from spatial_analysis_core.database import DatabaseManager

# Initialize database manager
db_manager = DatabaseManager()

# Load credentials
if db_manager.load_credentials():
    # Create database
    if db_manager.create_database("curitiba_db"):
        # Connect to database
        if db_manager.connect("curitiba_db"):
            print("✅ Connected to database successfully!")
            
            # Create schemas
            db_manager.create_schemas()
            
            # Close connection
            db_manager.close()
```

#### **PostGIS Operations**
```python
from spatial_analysis_core.database import PostGISManager

# Initialize PostGIS manager
postgis_manager = PostGISManager()

# Load credentials and connect
if postgis_manager.load_credentials():
    if postgis_manager.connect("curitiba_db"):
        # Enable PostGIS extension
        if postgis_manager.enable_postgis():
            print("✅ PostGIS enabled successfully!")
            
            # Test spatial functions
            if postgis_manager.test_spatial_functions():
                print("✅ Spatial functions working!")
```

### **Advanced Database Operations**

#### **Schema Management**
```python
from spatial_analysis_core.database import DatabaseManager

db_manager = DatabaseManager()

if db_manager.connect("curitiba_db"):
    # Create city-specific schema
    with db_manager.connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS curitiba;")
        
        # Create spatial table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS curitiba.amenities (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                category VARCHAR(100),
                geom GEOMETRY(POINT, 4326)
            );
        """)
        
        # Create spatial index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_amenities_geom 
            ON curitiba.amenities USING GIST (geom);
        """)
        
        db_manager.connection.commit()
        print("✅ Curitiba schema and tables created!")
```

#### **Spatial Data Operations**
```python
from spatial_analysis_core.database import DatabaseManager
import geopandas as gpd

db_manager = DatabaseManager()

if db_manager.connect("curitiba_db"):
    # Insert spatial data
    with db_manager.connection.cursor() as cursor:
        # Insert a point
        cursor.execute("""
            INSERT INTO curitiba.amenities (name, category, geom)
            VALUES (%s, %s, ST_GeomFromText(%s, 4326))
        """, ("Central Market", "commercial", "POINT(-49.3 -25.5)"))
        
        # Query spatial data
        cursor.execute("""
            SELECT name, category, ST_AsText(geom) as geometry
            FROM curitiba.amenities
            WHERE ST_DWithin(geom, ST_GeomFromText('POINT(-49.3 -25.5)', 4326), 0.01)
        """)
        
        results = cursor.fetchall()
        for row in results:
            print(f"Name: {row[0]}, Category: {row[1]}, Geometry: {row[2]}")
    
    db_manager.connection.commit()
```

### **Data Loading Integration**
```python
from spatial_analysis_core import DataLoader, DatabaseManager
import geopandas as gpd

# Initialize components
loader = DataLoader()
db_manager = DatabaseManager()

# Load OSM data
gdf = loader.extract_osm_data(
    pbf_file="path/to/curitiba.osm.pbf",
    bbox=(-49.4, -25.6, -49.2, -25.4),
    output_name="amenities"
)

if gdf is not None and db_manager.connect("curitiba_db"):
    # Convert to WKT for database insertion
    gdf['geom_wkt'] = gdf.geometry.apply(lambda x: x.wkt)
    
    with db_manager.connection.cursor() as cursor:
        for idx, row in gdf.iterrows():
            cursor.execute("""
                INSERT INTO curitiba.amenities (name, category, geom)
                VALUES (%s, %s, ST_GeomFromText(%s, 4326))
            """, (row.get('name', ''), row.get('amenity', 'unknown'), row['geom_wkt']))
    
    db_manager.connection.commit()
    print(f"✅ Inserted {len(gdf)} amenities into database!")
```

## 🔐 **Secure Credentials Management**

### **Credentials File Structure**
```yaml
# credentials/database_credentials.yaml
database:
  host: "localhost"
  port: 5432
  username: "postgres"
  password: "your_secure_password"
  default_database: "postgres"
  ssl_mode: "prefer"
  
# Optional: Environment-specific credentials
production:
  host: "prod-db.example.com"
  port: 5432
  username: "app_user"
  password: "prod_password"
  default_database: "urban_analysis"
  ssl_mode: "require"
```

### **Environment Variables**
```bash
# Set environment variables for sensitive data
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_USERNAME="postgres"
export DB_PASSWORD="your_password"
export DB_NAME="postgres"
```

### **Security Best Practices**
- **Never commit credentials** to version control
- **Use environment variables** for production deployments
- **Implement connection pooling** for high-traffic applications
- **Regular password rotation** and access review
- **SSL encryption** for production databases

## 🗃️ **Database Schema Design**

### **Standard Schemas**
```sql
-- Public schema (default)
-- Contains system tables and extensions

-- City-specific schemas
CREATE SCHEMA IF NOT EXISTS curitiba;
CREATE SCHEMA IF NOT EXISTS stuttgart;
CREATE SCHEMA IF NOT EXISTS paris;

-- Analysis schemas
CREATE SCHEMA IF NOT EXISTS analysis;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS results;
```

### **Spatial Table Structure**
```sql
-- Example: Amenities table
CREATE TABLE curitiba.amenities (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    name VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    tags JSONB,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Spatial index for performance
CREATE INDEX idx_amenities_geom ON curitiba.amenities USING GIST (geom);

-- Regular indexes for common queries
CREATE INDEX idx_amenities_category ON curitiba.amenities (category);
CREATE INDEX idx_amenities_osm_id ON curitiba.amenities (osm_id);
```

### **Metadata Tables**
```sql
-- Data lineage tracking
CREATE TABLE analysis.data_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(255),
    source_type VARCHAR(100),
    file_path VARCHAR(500),
    file_size BIGINT,
    extraction_date TIMESTAMP,
    bbox GEOMETRY(POLYGON, 4326),
    feature_count INTEGER,
    processing_status VARCHAR(50)
);

-- Analysis runs tracking
CREATE TABLE analysis.run_log (
    id SERIAL PRIMARY KEY,
    run_id UUID DEFAULT gen_random_uuid(),
    city_name VARCHAR(100),
    analysis_type VARCHAR(100),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50),
    features_processed INTEGER,
    error_message TEXT
);
```

## 📊 **Performance Optimization**

### **Database Tuning**
```sql
-- Increase shared buffers for better performance
ALTER SYSTEM SET shared_buffers = '256MB';

-- Optimize work memory for complex queries
ALTER SYSTEM SET work_mem = '64MB';

-- Enable parallel query execution
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;

-- Reload configuration
SELECT pg_reload_conf();
```

### **Spatial Index Optimization**
```sql
-- Analyze tables for better query planning
ANALYZE curitiba.amenities;
ANALYZE curitiba.roads;
ANALYZE curitiba.buildings;

-- Update statistics
VACUUM ANALYZE curitiba.amenities;
```

### **Query Optimization Examples**
```sql
-- Efficient spatial queries
SELECT name, category, ST_Distance(geom, ST_Point(-49.3, -25.5)) as distance
FROM curitiba.amenities
WHERE ST_DWithin(geom, ST_Point(-49.3, -25.5), 0.01)
ORDER BY distance
LIMIT 10;

-- Use spatial functions efficiently
SELECT category, COUNT(*) as count
FROM curitiba.amenities
WHERE ST_Intersects(geom, ST_GeomFromText('POLYGON((-49.4 -25.6, -49.2 -25.6, -49.2 -25.4, -49.4 -25.4, -49.4 -25.6))', 4326))
GROUP BY category
ORDER BY count DESC;
```

## 🔍 **Monitoring & Maintenance**

### **Database Health Checks**
```sql
-- Check database size
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check PostGIS version and extensions
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name LIKE 'postgis%';

-- Monitor active connections
SELECT 
    datname,
    usename,
    application_name,
    state,
    query_start
FROM pg_stat_activity
WHERE state = 'active';
```

### **Backup and Recovery**
```bash
# Create database backup
pg_dump -h localhost -U postgres -d curitiba_db > curitiba_backup.sql

# Restore database
psql -h localhost -U postgres -d curitiba_db < curitiba_backup.sql

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U postgres -d curitiba_db > "backup_curitiba_${DATE}.sql"
```

---

## 🔗 **Related Documentation**

- **[Architecture Overview](architecture.md)** - System design and structure
- **[Multi-City Support](multi_city.md)** - Pipeline execution and city management
- **[Data Layers](data_layers.md)** - Data processing and categorization
- **[Main Project](../README.md)** - Project overview and quick start

---

*Last Updated: 2025-08-27 - Database Documentation Version 1.0.0*
