#!/usr/bin/env python3
"""
Stuttgart Urban Analysis Dashboard Generator
Creates a beautiful HTML dashboard with all exported GeoJSON layers
"""

import json
import os
from pathlib import Path
from datetime import datetime
import webbrowser

def generate_dashboard_html(output_dir, output_series):
    """Generate the dashboard HTML with the exact same beautiful structure"""
    
    # Get the path to the GeoJSON layers
    geojson_dir = output_dir / "geojson_layers"
    
    # Check if the directory exists
    if not geojson_dir.exists():
        print(f"❌ GeoJSON layers directory not found: {geojson_dir}")
        return None
    
    # Get all GeoJSON files
    geojson_files = list(geojson_dir.glob("*.geojson"))
    if not geojson_files:
        print(f"❌ No GeoJSON files found in: {geojson_dir}")
        return None
    
    print(f"✅ Found {len(geojson_files)} GeoJSON layers")
    
    # Create the HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stuttgart Urban Analysis Dashboard - {output_series}</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            overflow: hidden;
        }}
        
        .header {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 15px 20px;
            z-index: 1000;
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 300;
        }}
        
        .header p {{
            margin: 5px 0 0 0;
            opacity: 0.8;
            font-size: 14px;
        }}
        
        .map-container {{
            position: absolute;
            top: 80px;
            left: 0;
            right: 0;
            bottom: 0;
            background: #000;
        }}
        
        #map {{
            width: 100%;
            height: 100%;
        }}
        
        .layer-controls {{
            position: absolute;
            top: 100px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            padding: 20px;
            max-width: 300px;
            max-height: 70vh;
            overflow-y: auto;
            z-index: 1001;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .layer-controls h3 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 18px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 8px;
        }}
        
        .layer-group {{
            margin-bottom: 20px;
        }}
        
        .layer-group h4 {{
            margin: 0 0 10px 0;
            color: #555;
            font-size: 14px;
            font-weight: 600;
        }}
        
        .layer-item {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            padding: 8px;
            border-radius: 5px;
            background: #f8f9fa;
            transition: all 0.2s ease;
        }}
        
        .layer-item:hover {{
            background: #e9ecef;
            transform: translateX(5px);
        }}
        
        .layer-item input[type="checkbox"] {{
            margin-right: 10px;
            transform: scale(1.2);
        }}
        
        .layer-item label {{
            font-size: 13px;
            color: #495057;
            cursor: pointer;
            flex: 1;
        }}
        
        .layer-item .layer-info {{
            font-size: 11px;
            color: #6c757d;
            margin-top: 2px;
        }}
        
        .legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            padding: 15px;
            max-width: 250px;
            z-index: 1001;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .legend h4 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 14px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 3px;
            margin-right: 10px;
            border: 1px solid #ddd;
        }}
        
        .legend-text {{
            font-size: 12px;
            color: #555;
        }}
        
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 18px;
            z-index: 1002;
        }}
        
        .spinner {{
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top: 3px solid white;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .info-panel {{
            position: absolute;
            top: 100px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            padding: 15px;
            max-width: 250px;
            z-index: 1001;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .info-panel h4 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 14px;
        }}
        
        .info-panel p {{
            margin: 5px 0;
            font-size: 12px;
            color: #555;
        }}
    </style>
    
    <!-- Load Leaflet CSS and JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
</head>
<body>
    <div class="header">
        <h1>🏗️ Stuttgart Urban Analysis Dashboard</h1>
        <p>Comprehensive spatial analysis with H3 hexagons, choropleth maps, and urban indicators</p>
    </div>
    
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div>Loading Stuttgart Urban Analysis Dashboard...</div>
    </div>
    
    <div class="map-container">
        <div id="map"></div>
    </div>
    
    <div class="info-panel">
        <h4>📊 Data Info</h4>
        <p><strong>Output Series:</strong> {output_series}</p>
        <p><strong>Layers Loaded:</strong> <span id="layers-count">0</span></p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <div class="layer-controls">
        <h3>🗺️ Layer Controls</h3>
        
        <div class="layer-group">
            <h4>🏛️ Base Layers</h4>
            <div class="layer-item">
                <input type="checkbox" id="city-boundary" checked>
                <label for="city-boundary">City Boundary</label>
                <div class="layer-info">Municipal limits</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="districts" checked>
                <label for="districts">Districts</label>
                <div class="layer-info">Administrative divisions</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="roads">
                <label for="roads">Road Network</label>
                <div class="layer-info">Street infrastructure</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="pt-stops">
                <label for="pt-stops">PT Stops</label>
                <div class="layer-info">Public transport stations</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="landuse">
                <label for="landuse">Land Use</label>
                <div class="layer-info">Urban land classification</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="green-areas">
                <label for="green-areas">Green Areas</label>
                <div class="layer-info">Parks and natural spaces</div>
            </div>
        </div>
        
        <div class="layer-group">
            <h4>🔷 H3 Analysis Layers</h4>
            <div class="layer-item">
                <input type="checkbox" id="pt-gravity" checked>
                <label for="pt-gravity">PT Modal Gravity</label>
                <div class="layer-info">H3 hexagon analysis</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="essentials-access">
                <label for="essentials-access">Essentials Access</label>
                <div class="layer-info">H3 hexagon analysis</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="service-diversity">
                <label for="service-diversity">Service Diversity</label>
                <div class="layer-info">H3 hexagon analysis</div>
            </div>
        </div>
        
        <div class="layer-group">
            <h4>📊 Composite Scores</h4>
            <div class="layer-item">
                <input type="checkbox" id="mobility-score">
                <label for="mobility-score">Mobility Score</label>
                <div class="layer-info">PT + essentials combined</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="walkability-score">
                <label for="walkability-score">Walkability Score</label>
                <div class="layer-info">Essentials + diversity</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="overall-score">
                <label for="overall-score">Overall Score</label>
                <div class="layer-info">All metrics combined</div>
            </div>
        </div>
        
        <div class="layer-group">
            <h4>📈 Additional Metrics</h4>
            <div class="layer-item">
                <input type="checkbox" id="pt-density">
                <label for="pt-density">PT Density</label>
                <div class="layer-info">Transport accessibility</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="amenity-density">
                <label for="amenity-density">Amenity Density</label>
                <div class="layer-info">Service concentration</div>
            </div>
            <div class="layer-item">
                <input type="checkbox" id="green-ratio">
                <label for="green-ratio">Green Space Ratio</label>
                <div class="layer-info">Environmental quality</div>
            </div>
        </div>
    </div>
    
    <div class="legend">
        <h4>🎨 Map Legend</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #ff6b6b;"></div>
            <div class="legend-text">High Values</div>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #4ecdc4;"></div>
            <div class="legend-text">Medium Values</div>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #45b7d1;"></div>
            <div class="legend-text">Low Values</div>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #96ceb4;"></div>
            <div class="legend-text">H3 Hexagons</div>
        </div>
    </div>

    <script>
        // Map configuration
        let map;
        let layers = {{}};
        let layerGroups = {{}};
        
        // Initialize map
        function initMap() {{
            // Create map centered on Stuttgart
            map = L.map('map', {{
                center: [48.7758, 9.1829],
                zoom: 10,
                zoomControl: true,
                attributionControl: true
            }});
            
            // Add OpenStreetMap tiles
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }}).addTo(map);
            
            // Load all layers
            loadAllLayers();
        }}
        
        // Load all GeoJSON layers
        async function loadAllLayers() {{
            const layerFiles = {get_layer_files_list(geojson_files, output_series)};
            let loadedCount = 0;
            
            for (const layer of layerFiles) {{
                try {{
                    const response = await fetch(layer.file);
                    if (response.ok) {{
                        const geojson = await response.json();
                        addLayerToMap(layer.id, geojson, layer.type);
                        loadedCount++;
                        document.getElementById('layers-count').textContent = loadedCount;
                    }}
                }} catch (error) {{
                    console.error(`Error loading layer ${{layer.id}}:`, error);
                }}
            }}
            
            // Hide loading screen
            document.getElementById('loading').style.display = 'none';
            
            // Set up layer controls
            setupLayerControls();
        }}
        
        // Add layer to map
        function addLayerToMap(layerId, geojson, layerType) {{
            const layerGroup = L.layerGroup();
            
            if (layerType === 'point') {{
                // Handle point layers (PT stops)
                L.geoJSON(geojson, {{
                    pointToLayer: function(feature, latlng) {{
                        return L.circleMarker(latlng, {{
                            radius: 6,
                            fillColor: '#c3423f',
                            color: '#fff',
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8
                        }});
                    }},
                    onEachFeature: function(feature, layer) {{
                        if (feature.properties) {{
                            layer.bindPopup(createPopupContent(feature.properties, layerId));
                        }}
                    }}
                }}).addTo(layerGroup);
            }} else {{
                // Handle polygon/line layers
                L.geoJSON(geojson, {{
                    style: function(feature) {{
                        return getLayerStyle(layerId, feature);
                    }},
                    onEachFeature: function(feature, layer) {{
                        if (feature.properties) {{
                            layer.bindPopup(createPopupContent(feature.properties, layerId));
                        }}
                    }}
                }}).addTo(layerGroup);
            }}
            
            // Store the layer group
            layerGroups[layerId] = layerGroup;
            
            // Add to map if it should be visible by default
            if (document.getElementById(layerId) && document.getElementById(layerId).checked) {{
                layerGroup.addTo(map);
            }}
        }}
        
        // Get layer styling
        function getLayerStyle(layerId, feature) {{
            const baseStyle = {{
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.6
            }};
            
            switch(layerId) {{
                case 'city-boundary':
                    return {{
                        ...baseStyle,
                        color: '#000',
                        weight: 3,
                        fillColor: 'transparent',
                        fillOpacity: 0
                    }};
                case 'districts':
                    return {{
                        ...baseStyle,
                        color: '#666',
                        fillColor: '#4ecdc4',
                        fillOpacity: 0.3
                    }};
                case 'roads':
                    return {{
                        ...baseStyle,
                        color: '#8b7355',
                        weight: 2,
                        fillColor: 'transparent',
                        fillOpacity: 0
                    }};
                case 'landuse':
                    return {{
                        ...baseStyle,
                        color: '#fff',
                        fillColor: '#96ceb4'
                    }};
                case 'green-areas':
                    return {{
                        ...baseStyle,
                        color: '#4c5d4a',
                        fillColor: '#4c5d4a'
                    }};
                case 'pt-gravity':
                case 'essentials-access':
                case 'service-diversity':
                case 'mobility-score':
                case 'walkability-score':
                case 'overall-score':
                    return {{
                        ...baseStyle,
                        color: '#fff',
                        fillColor: getChoroplethColor(feature.properties, layerId)
                    }};
                default:
                    return baseStyle;
            }}
        }}
        
        // Get choropleth color based on data values
        function getChoroplethColor(properties, layerId) {{
            let value = 0;
            
            switch(layerId) {{
                case 'pt-gravity':
                    value = properties.pt_gravity || 0;
                    break;
                case 'essentials-access':
                    value = properties.ess_types || 0;
                    break;
                case 'service-diversity':
                    value = properties.amen_entropy || 0;
                    break;
                case 'mobility-score':
                    value = properties.mobility_score || 0;
                    break;
                case 'walkability-score':
                    value = properties.walkability_score || 0;
                    break;
                case 'overall-score':
                    value = properties.overall_score || 0;
                    break;
            }}
            
            // Simple color scale
            if (value > 0.7) return '#ff6b6b';
            if (value > 0.4) return '#4ecdc4';
            return '#45b7d1';
        }}
        
        // Create popup content
        function createPopupContent(properties, layerId) {{
            let content = '<div style="min-width: 200px;">';
            content += `<h4>${{layerId.replace('-', ' ').toUpperCase()}}</h4>`;
            
            for (const [key, value] of Object.entries(properties)) {{
                if (key !== 'geometry') {{
                    content += `<p><strong>${{key}}:</strong> ${{value}}</p>`;
                }}
            }}
            
            content += '</div>';
            return content;
        }}
        
        // Set up layer controls
        function setupLayerControls() {{
            const checkboxes = document.querySelectorAll('.layer-controls input[type="checkbox"]');
            checkboxes.forEach(checkbox => {{
                checkbox.addEventListener('change', function() {{
                    const layerId = this.id;
                    const isVisible = this.checked;
                    
                    if (layerGroups[layerId]) {{
                        if (isVisible) {{
                            layerGroups[layerId].addTo(map);
                        }} else {{
                            map.removeLayer(layerGroups[layerId]);
                        }}
                    }}
                }});
            }});
        }}
        
        // Initialize when page loads
        window.addEventListener('load', initMap);
    </script>
</body>
</html>"""
    
    return html_content

def get_layer_files_list(geojson_files, output_series):
    """Create the JavaScript array of layer files"""
    layers = []
    
    # Define layer types and their corresponding files
    layer_mapping = {
        'city-boundary': '01_city_boundary.geojson',
        'districts': '02_districts.geojson',
        'roads': '03_roads.geojson',
        'pt-stops': '04_pt_stops.geojson',
        'landuse': '05_landuse.geojson',
        'green-areas': '06_green_areas.geojson',
        'pt-gravity': '13_pt_modal_gravity_h3.geojson',
        'essentials-access': '14_access_essentials_h3.geojson',
        'service-diversity': '16_service_diversity_h3.geojson',
        'mobility-score': '21_mobility_score.geojson',
        'walkability-score': '23_walkability_score.geojson',
        'overall-score': '24_overall_score.geojson',
        'pt-density': '22_pt_density.geojson',
        'amenity-density': '18_amenity_density.geojson',
        'green-ratio': '20_green_space_ratio.geojson'
    }
    
    for layer_id, filename in layer_mapping.items():
        file_path = next((f for f in geojson_files if f.name == filename), None)
        if file_path:
            # Determine layer type
            layer_type = 'point' if layer_id == 'pt-stops' else 'polygon'
            
            layers.append({
                'id': layer_id,
                'file': f'outputs/{output_series}/geojson_layers/{filename}',
                'type': layer_type
            })
    
    return json.dumps(layers, indent=8)

def find_latest_output():
    """Find the latest output directory"""
    outputs_dir = Path("outputs")
    if not outputs_dir.exists():
        return None
    
    # Find all stuttgart_maps_* directories
    map_dirs = [d for d in outputs_dir.iterdir() if d.is_dir() and d.name.startswith('stuttgart_maps_')]
    
    if not map_dirs:
        return None
    
    # Sort by name and get the latest
    latest_dir = sorted(map_dirs, key=lambda x: x.name)[-1]
    return latest_dir

def main():
    """Main function to generate the dashboard"""
    print("🏗️ Stuttgart Urban Analysis Dashboard Generator")
    print("=" * 50)
    
    # Find the latest output directory
    latest_output = find_latest_output()
    if not latest_output:
        print("❌ No output directories found. Run the analysis script first.")
        return
    
    print(f"✅ Found latest output: {latest_output.name}")
    
    # Generate the dashboard HTML
    html_content = generate_dashboard_html(latest_output, latest_output.name)
    if not html_content:
        return
    
    # Create the dashboard file
    dashboard_file = Path(f"dashboard_{latest_output.name}.html")
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Dashboard generated: {dashboard_file}")
    print(f"📁 Location: {dashboard_file.absolute()}")
    
    # Ask if user wants to open the dashboard
    try:
        response = input("\n🚀 Open dashboard in browser? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            webbrowser.open(f'file://{dashboard_file.absolute()}')
            print("✅ Dashboard opened in browser!")
    except KeyboardInterrupt:
        print("\n👋 Dashboard generation completed!")
    
    print(f"\n💡 To open manually: {dashboard_file.absolute()}")

if __name__ == "__main__":
    main()
