# 🛠️ Troubleshooting

## 🔺 **Common Issues & Solutions**

### **1. QuackOSM Installation Issues**

#### **Problem**: QuackOSM fails to install or import
```bash
# Error: ModuleNotFoundError: No module named 'quackosm'
# Error: ImportError: cannot import name 'QuackOSM' from 'quackosm'
```

#### **Solutions**:
```bash
# Update pip first
pip install --upgrade pip

# Install QuackOSM with no cache
pip install quackosm --no-cache-dir

# Verify installation
python -c "import quackosm; print('QuackOSM installed successfully')"

# If still having issues, try alternative installation
pip install quackosm[all]
```

#### **Alternative Installation Methods**:
```bash
# Using conda (if available)
conda install -c conda-forge quackosm

# From source (if pip fails)
git clone https://github.com/Wetransform/QuackOSM.git
cd QuackOSM
pip install -e .
```

### **2. Memory Issues with Large Cities**

#### **Problem**: Out of memory errors during processing
```bash
# Error: MemoryError: Unable to allocate array
# Error: Killed (process killed due to memory usage)
```

#### **Solutions**:
```bash
# Set memory limits for QuackOSM
export QUACKOSM_MAX_MEMORY=8GB

# For Windows PowerShell
$env:QUACKOSM_MAX_MEMORY="8GB"

# Process in smaller chunks
python -c "
from spatial_analysis_core import DataLoader
loader = DataLoader()
# Use smaller bounding box or process layers separately
"
```

#### **Memory Optimization Techniques**:
```python
# Process data in chunks
def process_large_city_in_chunks(city_data, chunk_size=10000):
    """Process large datasets in manageable chunks"""
    for i in range(0, len(city_data), chunk_size):
        chunk = city_data[i:i + chunk_size]
        process_chunk(chunk)
        
        # Force garbage collection
        import gc
        gc.collect()
```

### **3. Missing OSM Data**

#### **Problem**: No data extracted or empty results
```bash
# Warning: No features found in bounding box
# Error: Empty GeoDataFrame returned
```

#### **Solutions**:
```bash
# Check if PBF file exists
ls -la data/raw/
# or on Windows
dir data\raw

# Verify bounding box coordinates
python -c "
from spatial_analysis_core import DataLoader
loader = DataLoader()
bbox = [-49.4, -25.6, -49.2, -25.4]  # Curitiba example
print(f'Bounding box: {bbox}')
print(f'Format: [min_lon, min_lat, max_lon, max_lat]')
"

# Test with known working area
python -c "
# Use Stuttgart as test case
bbox = [9.0, 48.6, 9.4, 48.9]
print(f'Stuttgart bbox: {bbox}')
"
```

#### **Bounding Box Validation**:
```python
def validate_bbox(bbox):
    """Validate bounding box coordinates"""
    if len(bbox) != 4:
        return False, "Bounding box must have 4 coordinates"
    
    min_lon, min_lat, max_lon, max_lat = bbox
    
    if not (-180 <= min_lon <= 180) or not (-180 <= max_lon <= 180):
        return False, "Longitude must be between -180 and 180"
    
    if not (-90 <= min_lat <= 90) or not (-90 <= max_lat <= 90):
        return False, "Latitude must be between -90 and 90"
    
    if min_lon >= max_lon or min_lat >= max_lat:
        return False, "Invalid bounding box: min must be less than max"
    
    return True, "Valid bounding box"
```

### **4. Empty Maps**

#### **Problem**: Maps generated but no data visible
```bash
# Map file created but appears empty
# No features displayed on the map
```

#### **Solutions**:
```bash
# Check data processing pipeline
python cities/curitiba/spatial_analysis/test_curitiba_full_pipeline.py

# Verify data was extracted successfully
python -c "
import geopandas as gpd
from pathlib import Path

# Check staging data
staging_path = Path('cities/curitiba/data/staging')
if staging_path.exists():
    files = list(staging_path.glob('*.parquet'))
    print(f'Found {len(files)} staging files:')
    for f in files:
        print(f'  - {f.name}')
else:
    print('Staging directory not found')
"

# Check processed data
python -c "
processed_path = Path('cities/curitiba/data/processed')
if processed_path.exists():
    files = list(processed_path.glob('*.parquet'))
    print(f'Found {len(files)} processed files:')
    for f in files:
        gdf = gpd.read_parquet(f)
        print(f'  - {f.name}: {len(gdf)} features')
else:
    print('Processed directory not found')
"
```

#### **Data Pipeline Debugging**:
```python
def debug_data_pipeline(city_name):
    """Debug the complete data pipeline for a city"""
    
    # Check configuration
    config_path = f"cities/{city_name}/config/city.yaml"
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        return False
    
    # Check data directories
    data_dirs = ['raw', 'staging', 'processed', 'outputs']
    for dir_name in data_dirs:
        dir_path = f"cities/{city_name}/data/{dir_name}"
        if Path(dir_path).exists():
            files = list(Path(dir_path).glob('*'))
            print(f"✅ {dir_name}: {len(files)} files")
        else:
            print(f"❌ {dir_name}: directory not found")
    
    return True
```

### **5. Database Connection Issues**

#### **Problem**: Cannot connect to PostgreSQL/PostGIS
```bash
# Error: connection to server failed
# Error: PostGIS extension not available
```

#### **Solutions**:
```bash
# Test database connection
python spatial_analysis_core/database/manage_database.py test-connection

# Check PostGIS status
python spatial_analysis_core/database/manage_database.py check-postgis

# Verify credentials
cat credentials/database_credentials.yaml
# or check environment variables
echo $DB_HOST
echo $DB_PORT
echo $DB_USERNAME
```

#### **Database Troubleshooting**:
```bash
# Check if PostgreSQL is running
# Windows
net start postgresql-x64-17

# macOS
brew services list | grep postgresql

# Linux
sudo systemctl status postgresql

# Test direct connection
psql -h localhost -U postgres -d postgres
# Then run: SELECT version(); SELECT PostGIS_Version();
```

### **6. Import Errors**

#### **Problem**: Module import failures
```bash
# Error: ModuleNotFoundError: No module named 'spatial_analysis_core'
# Error: ImportError: cannot import name 'DataLoader'
```

#### **Solutions**:
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Add project root to path
export PYTHONPATH="${PYTHONPATH}:/path/to/ETL-Geodata-Pipeline"

# Verify module structure
ls -la spatial_analysis_core/
python -c "from spatial_analysis_core import DataLoader; print('Import successful')"
```

## 🔍 **Debug Mode Usage**

### **Enabling Debug Mode**
All scripts support the `--debug` flag for verbose logging:

```bash
# Test pipeline with debug output
python cities/curitiba/spatial_analysis/test_curitiba_full_pipeline.py --debug

# Database operations with debug
python spatial_analysis_core/database/manage_database.py setup --debug

# Data extraction with debug
python -c "
from spatial_analysis_core import DataLoader
import logging

# Set debug logging
logging.basicConfig(level=logging.DEBUG)
loader = DataLoader()
# Debug output will show detailed processing steps
"
```

### **Debug Configuration**
```python
# Enable debug logging in Python scripts
import logging

# Set debug level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create logger for specific module
logger = logging.getLogger(__name__)
logger.debug("Debug message with detailed information")
```

### **Debug Output Examples**
```bash
# Debug output shows:
2025-08-27 10:30:15 - spatial_analysis_core.data_loader - DEBUG - Loading OSM PBF file: parana-latest.osm.pbf
2025-08-27 10:30:15 - spatial_analysis_core.data_loader - DEBUG - Bounding box: [-49.4, -25.6, -49.2, -25.4]
2025-08-27 10:30:15 - spatial_analysis_core.data_loader - DEBUG - Extracting layer: amenities
2025-08-27 10:30:16 - spatial_analysis_core.data_loader - DEBUG - Found 15,432 amenity features
2025-08-27 10:30:16 - spatial_analysis_core.data_loader - DEBUG - Applying category rules
2025-08-27 10:30:17 - spatial_analysis_core.data_loader - DEBUG - Categorized 15,432 features into 21 categories
```

## 📋 **Log File Locations**

### **Application Logs**
```bash
# Main application logs
cities/curitiba/spatial_analysis/logs/curitiba_analysis.log
cities/stuttgart/spatial_analysis/logs/stuttgart_analysis.log

# Database operation logs
spatial_analysis_core/database/logs/database_operations.log

# Data processing logs
logs/data_processing.log
```

### **System Logs**
```bash
# PostgreSQL logs
# Windows: PostgreSQL installation directory
# macOS: /usr/local/var/log/postgres.log
# Linux: /var/log/postgresql/postgresql-17-main.log

# Python error logs
# Check console output or redirect to file
python script.py 2>&1 | tee error.log
```

### **Log Analysis Commands**
```bash
# View recent logs
tail -f cities/curitiba/spatial_analysis/logs/curitiba_analysis.log

# Search for errors
grep -i "error\|exception\|failed" cities/curitiba/spatial_analysis/logs/*.log

# Monitor database operations
tail -f spatial_analysis_core/database/logs/database_operations.log
```

## 🔧 **Performance Issues**

### **Slow Data Processing**
```bash
# Check system resources
# Windows: Task Manager
# macOS: Activity Monitor
# Linux: htop or top

# Monitor memory usage
python -c "
import psutil
process = psutil.Process()
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
print(f'CPU usage: {process.cpu_percent()}%')
"
```

### **Database Performance**
```sql
-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## 🚨 **Emergency Recovery**

### **Data Loss Prevention**
```bash
# Create backup before major changes
pg_dump -h localhost -U postgres -d curitiba_db > backup_curitiba_$(date +%Y%m%d_%H%M%S).sql

# Backup configuration files
cp -r cities/curitiba/config backup_config_$(date +%Y%m%d_%H%M%S)

# Backup processed data
cp -r cities/curitiba/data/processed backup_data_$(date +%Y%m%d_%H%M%S)
```

### **System Reset**
```bash
# Reset database (WARNING: This will delete all data)
python spatial_analysis_core/database/manage_database.py reset

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear cache and temporary files
rm -rf __pycache__/
rm -rf cities/*/spatial_analysis/__pycache__/
```

## **Getting Help**

### **Self-Diagnosis Steps**
1. **Check Logs**: Review application and system logs
2. **Verify Configuration**: Ensure all config files are correct
3. **Test Components**: Test individual components separately
4. **Check Dependencies**: Verify all required packages are installed
5. **Review Documentation**: Check relevant documentation sections

### **Reporting Issues**
When reporting issues, include:
- **Error Message**: Complete error text
- **Environment**: OS, Python version, package versions
- **Steps to Reproduce**: Detailed reproduction steps
- **Log Files**: Relevant log excerpts
- **Configuration**: Relevant configuration files

### **Useful Commands for Issue Reporting**
```bash
# System information
python --version
pip list | grep -E "(quackosm|geopandas|psycopg2)"

# Environment details
echo $PYTHONPATH
echo $PATH

# Check file permissions
ls -la spatial_analysis_core/
ls -la cities/curitiba/
```

---

## 🔗 **Related Documentation**

- **[Architecture Overview](architecture.md)** - System design and structure
- **[Database Integration](database.md)** - Database setup and storage
- **[Data Layers](data_layers.md)** - Data processing and categorization
- **[Main Project](../README.md)** - Project overview and quick start

---

*Last Updated: 2025-08-27 - Troubleshooting Documentation Version 1.0.0*
