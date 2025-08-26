# Spatial Analysis Core - Shared Analysis Components

## 🔺 **Overview**

The **Spatial Analysis Core** provides shared, reusable components for city-specific spatial analysis. This module contains base classes and utilities that all city analysis scripts inherit from, ensuring consistency while allowing customization for unique city characteristics.

## 🏗️ **Architecture**

### **Inheritance Structure**
```
BaseCityAnalysis (Abstract Base Class)
├── StuttgartAnalysis
├── CuritibaAnalysis
├── FutureCityAnalysis
└── ... (other cities)
```

### **Shared Components**
- **Base Analysis Class**: Common analysis framework
- **KPI Calculator**: Generic indicator calculations
- **Data Loader**: Standardized data loading utilities
- **Visualization Base**: Common visualization methods

## 📁 **Module Structure**

```
spatial_analysis_core/
├── __init__.py                    # Module initialization and exports
├── base_analysis.py               # Base analysis class (abstract)
├── kpi_calculator.py              # Generic KPI calculations
├── data_loader.py                 # Generic data loading utilities
├── visualization_base.py          # Base visualization class
└── README.md                      # This documentation
```

## 🔧 **Core Components**

### **1. BaseCityAnalysis (Abstract Base Class)**

**Purpose**: Foundation class that all city analysis scripts inherit from

**Key Features**:
- **Common data loading** methods
- **Standard KPI calculation** framework
- **Basic visualization** capabilities
- **Error handling** and logging
- **Result saving** and management

**Abstract Methods**:
- `run_city_analysis()`: Each city must implement this for custom logic

**Concrete Methods**:
- `load_city_data()`: Load all city data using shared logic
- `calculate_basic_kpis()`: Calculate standard KPIs
- `generate_base_maps()`: Create basic visualizations
- `run_full_analysis()`: Orchestrate complete analysis pipeline

### **2. KPICalculator**

**Purpose**: Generic KPI calculations that work for any city

**Key Features**:
- **Population access** calculations
- **Network density** analysis
- **Service coverage** metrics
- **Accessibility scoring**

**Methods**:
- `calculate_population_access()`: Generic population access to facilities
- `calculate_network_density()`: Network density analysis
- `calculate_service_coverage()`: Service coverage metrics
- `normalize_scores()`: Score normalization methods

### **3. DataLoader**

**Purpose**: Standardized data loading for all cities

**Key Features**:
- **Multi-format support** (GeoJSON, Parquet, Shapefile)
- **Coordinate system** handling
- **Data validation** and quality checks
- **Caching** for performance

**Methods**:
- `load_all_layers()`: Load all required data layers
- `load_geodata()`: Load geospatial data with validation
- `validate_data_quality()`: Check data quality metrics
- `get_cached_data()`: Retrieve cached data if available

### **4. VisualizationBase**

**Purpose**: Common visualization methods for all cities

**Key Features**:
- **Map generation** templates
- **Chart creation** utilities
- **Report formatting** helpers
- **Output management**

**Methods**:
- `create_base_maps()`: Generate standard map types
- `create_charts()`: Generate standard charts
- `format_reports()`: Format analysis reports
- `manage_outputs()`: Handle output file management

## 🚀 **Usage Examples**

### **Creating a New City Analysis**

```python
# cities/your_city/spatial_analysis/scripts/your_city_analysis.py
from spatial_analysis_core.base_analysis import BaseCityAnalysis

class YourCityAnalysis(BaseCityAnalysis):
    """Your city-specific analysis"""
    
    def run_city_analysis(self):
        """Implement your city-specific analysis logic"""
        # Your custom analysis here
        results = {
            'custom_metric': self.calculate_custom_metric(),
            'local_kpi': self.calculate_local_kpi()
        }
        return results
    
    def calculate_custom_metric(self):
        """City-specific calculation"""
        # Your custom logic here
        pass
    
    def calculate_local_kpi(self):
        """City-specific KPI"""
        # Your custom logic here
        pass

# Usage
if __name__ == "__main__":
    analysis = YourCityAnalysis("your_city", load_city_config())
    results = analysis.run_full_analysis()
    print(f"Analysis completed: {results}")
```

### **Using Shared KPI Calculations**

```python
from spatial_analysis_core.kpi_calculator import KPICalculator

# Create calculator instance
kpi_calc = KPICalculator(city_config)

# Calculate standard KPIs
population_access = kpi_calc.calculate_population_access(
    population=population_data,
    facilities=amenity_data,
    max_distance=500
)

network_density = kpi_calc.calculate_network_density(
    network_data=road_network
)
```

### **Using Shared Data Loading**

```python
from spatial_analysis_core.data_loader import DataLoader

# Create data loader instance
data_loader = DataLoader(city_config)

# Load all city data
city_data = data_loader.load_all_layers()

# Load specific layer
amenities = data_loader.load_geodata("amenities")
```

## 🔄 **Data Flow**

### **Standard Analysis Pipeline**

```
1. Initialize Analysis
   ├── Load city configuration
   ├── Setup logging
   └── Initialize shared components

2. Load City Data
   ├── Use shared DataLoader
   ├── Validate data quality
   └── Cache for performance

3. Calculate Basic KPIs
   ├── Use shared KPICalculator
   ├── Apply standard metrics
   └── Normalize scores

4. Run City-Specific Analysis
   ├── Call abstract method
   ├── Execute custom logic
   └── Return custom results

5. Generate Visualizations
   ├── Use shared VisualizationBase
   ├── Create standard maps
   └── Apply city-specific styling

6. Save Results
   ├── Save to city-specific outputs
   ├── Include metadata
   └── Generate reports
```

## 🎯 **Benefits**

### **✅ Consistency**
- **Same methodology** across all cities
- **Comparable results** for urban planning
- **Standardized outputs** for stakeholders

### **✅ Maintainability**
- **Fix once, applies everywhere** for shared logic
- **Centralized updates** for common functionality
- **Easier testing** of shared components

### **✅ Extensibility**
- **Easy to add new cities** using template
- **Simple to add new analysis types**
- **Flexible for city-specific customization**

### **✅ Professional Quality**
- **Industry-standard** analysis methods
- **Robust error handling** and logging
- **Comprehensive documentation**

## 🔧 **Customization Points**

### **City-Specific Configuration**
- **Analysis parameters** in city config files
- **KPI weights** for different priorities
- **Data sources** for local data
- **Output preferences** for local stakeholders

### **Custom Analysis Logic**
- **Abstract method implementation** for unique analysis
- **City-specific data processing** for local characteristics
- **Custom visualization** for local requirements
- **Specialized reporting** for local audiences

### **Local Data Integration**
- **Local data sources** (municipal data, local APIs)
- **Local coordinate systems** and projections
- **Local administrative boundaries** and divisions
- **Local population data** and demographics

## 🧪 **Testing**

### **Unit Testing**
- **Test shared components** independently
- **Mock city configurations** for testing
- **Validate data handling** with test data
- **Check error handling** with edge cases

### **Integration Testing**
- **Test complete analysis pipeline** with sample cities
- **Validate output consistency** across cities
- **Check performance** with different data sizes
- **Verify error handling** in real scenarios

## 📚 **Documentation**

### **API Reference**
- **Class documentation** with examples
- **Method signatures** and parameters
- **Return value** descriptions
- **Error handling** documentation

### **Usage Guides**
- **Quick start** examples for new cities
- **Best practices** for customization
- **Troubleshooting** common issues
- **Performance optimization** tips

## 🔮 **Future Enhancements**

### **Planned Features**
- **Machine learning** integration for advanced analysis
- **Real-time data** processing capabilities
- **Cloud deployment** optimization
- **Interactive visualization** components

### **Extension Points**
- **Plugin system** for custom analysis types
- **API endpoints** for web integration
- **Database integration** for large-scale analysis
- **Parallel processing** for performance optimization

---

## 📞 **Support & Contributing**

### **Getting Help**
- **Check documentation** for usage examples
- **Review existing city implementations** for patterns
- **Report issues** through project issue tracker
- **Ask questions** through project discussions

### **Contributing**
- **Follow existing patterns** for consistency
- **Add tests** for new functionality
- **Update documentation** for changes
- **Review pull requests** for quality

---

*Last Updated: 2024-12-19 - Version 1.0.0*

