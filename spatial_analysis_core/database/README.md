# 🗄️ Database Module

This module provides comprehensive database management functionality for the ETL Geodata Pipeline system, including PostgreSQL setup, PostGIS management, and spatial data handling.

## 🏗️ **Module Structure**

```
spatial_analysis_core/database/
├── __init__.py              # Module exports
├── database_manager.py      # PostgreSQL database management
├── postgis_manager.py       # PostGIS extension management
├── manage_database.py       # Command-line interface
└── README.md                # This documentation
```

## 🔧 **Core Components**

### **DatabaseManager** (`database_manager.py`)
- **Purpose**: Manages PostgreSQL database setup and connections
- **Features**:
  - Database creation and connection management
  - Schema creation and management
  - Credentials loading and validation
  - Context manager support for safe connections

### **PostGISManager** (`postgis_manager.py`)
- **Purpose**: Manages PostGIS extension and spatial functionality
- **Features**:
  - PostGIS extension enabling/disabling
  - Spatial function testing and validation
  - PostGIS file copying utilities
  - Connection management for spatial operations

### **CLI Interface** (`manage_database.py`)
- **Purpose**: Command-line interface for database operations
- **Commands**:
  - `setup` - Setup database and schemas
  - `enable-postgis` - Enable PostGIS extension
  - `copy-postgis` - Copy PostGIS files
  - `check-postgis` - Check PostGIS status
  - `test-connection` - Test database connection

## 🚀 **Quick Start**

### **1. Setup Database**
```bash
# Setup database and schemas
python spatial_analysis_core/database/manage_database.py setup

# Setup specific database
python spatial_analysis_core/database/manage_database.py setup --database my_city_db
```

### **2. Enable PostGIS**
```bash
# Enable PostGIS extension
python spatial_analysis_core/database/manage_database.py enable-postgis

# Enable in specific database
python spatial_analysis_core/database/manage_database.py enable-postgis --database my_city_db
```

### **3. Copy PostGIS Files** (if needed)
```bash
# Copy PostGIS files to PostgreSQL extension directory
python spatial_analysis_core/database/manage_database.py copy-postgis
```

### **4. Check Status**
```bash
# Check PostGIS status
python spatial_analysis_core/database/manage_database.py check-postgis

# Test database connection
python spatial_analysis_core/database/manage_database.py test-connection
```

## 🐍 **Python API Usage**

### **Database Setup**
```python
from spatial_analysis_core.database import DatabaseManager

# Setup database
db_manager = DatabaseManager()
if db_manager.load_credentials():
    if db_manager.create_database("my_city_db"):
        if db_manager.connect("my_city_db"):
            db_manager.create_schemas()
            print("Database setup complete!")
```

### **PostGIS Management**
```python
from spatial_analysis_core.database import PostGISManager

# Enable PostGIS
postgis_manager = PostGISManager()
if postgis_manager.load_credentials():
    if postgis_manager.connect("my_city_db"):
        if postgis_manager.enable_postgis():
            print("PostGIS enabled!")
```

### **Context Manager Usage**
```python
from spatial_analysis_core.database import DatabaseManager

# Safe connection handling
with DatabaseManager() as db:
    if db.connect("my_city_db"):
        # Database operations here
        pass
# Connection automatically closed
```

## 🔐 **Credentials Configuration**

The module expects credentials in `credentials/database_credentials.yaml`:

```yaml
database:
  postgres:
    user: postgres
    password: your_password
  
  etl_pipeline:
    host: localhost
    port: 5432
    database: etl_pipeline
```

## 🎯 **Use Cases**

### **Multi-City Database Setup**
- Create separate databases for each city
- Manage city-specific schemas
- Enable PostGIS for spatial operations

### **Development Environment**
- Quick database setup for testing
- PostGIS validation for spatial development
- Connection testing for debugging

### **Production Deployment**
- Automated database provisioning
- PostGIS extension management
- Schema standardization across cities

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Credentials Not Found**
```bash
# Check credentials file exists
ls credentials/database_credentials.yaml

# Verify file permissions
chmod 600 credentials/database_credentials.yaml
```

**2. PostGIS Not Working**
```bash
# Check if PostGIS files are copied
python manage_database.py copy-postgis

# Restart PostgreSQL service
sudo systemctl restart postgresql
```

**3. Connection Failed**
```bash
# Test connection
python manage_database.py test-connection

# Check PostgreSQL service status
sudo systemctl status postgresql
```

### **Debug Mode**
```bash
# Enable verbose logging
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from spatial_analysis_core.database import DatabaseManager
db = DatabaseManager()
db.load_credentials()
"
```

## 🔄 **Integration with Pipeline**

This database module integrates with the main ETL pipeline:

- **Data Storage**: Provides PostgreSQL + PostGIS backend
- **Spatial Operations**: Enables geospatial data processing
- **Multi-City Support**: Scalable database architecture
- **Professional Standards**: Industry-standard spatial database

## 📚 **Dependencies**

- **psycopg2**: PostgreSQL adapter for Python
- **PyYAML**: YAML configuration file handling
- **pathlib**: Path manipulation utilities
- **logging**: Structured logging support

## 🎉 **Success Indicators**

- ✅ Database connection successful
- ✅ PostGIS extension enabled
- ✅ Spatial functions working
- ✅ Schemas created successfully
- ✅ Multi-city support ready

---

**This module provides the foundation for professional-grade spatial data management in the ETL Geodata Pipeline system.**
