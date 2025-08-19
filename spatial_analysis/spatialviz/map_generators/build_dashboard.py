#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64
import json

# Paths
MAPS_DIR = Path("outputs/maps")
OUT_DIR = Path("outputs/dashboard"); OUT_DIR.mkdir(parents=True, exist_ok=True)

def encode_image_as_base64(image_path: Path) -> str:
    """Convert image to base64 for embedding in HTML"""
    if not image_path.exists():
        return ""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def build_dashboard():
    """Build the complete HTML dashboard"""
    
    # Get all map images
    map_files = {
        "01_macro_green_pt": "Macro Green Access & PT",
        "02_h3_population_surface": "H3 Population Surface",
        "03_green_space_distribution": "Green Space Distribution", 
        "04_bivariate_green_vs_pt": "Bivariate: PT vs Green",
        "05_pt_stop_density": "PT Stop Density",
        "06_area_vs_population": "Area vs Population",
        "07_h3_hexbin_visualization": "H3 Hexbin Population",
        "08_combined_accessibility_score": "Combined Accessibility"
    }
    
    # Encode images
    encoded_images = {}
    for filename, title in map_files.items():
        image_path = MAPS_DIR / f"{filename}.png"
        if image_path.exists():
            encoded_images[filename] = encode_image_as_base64(image_path)
            print(f"✅ Encoded: {filename}")
        else:
            print(f"⚠️  Missing: {filename}")
    
    # HTML template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stuttgart H3 Spatial Analysis Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white; 
            padding: 40px; 
            text-align: center;
        }}
        .header h1 {{ 
            font-size: 2.5em; 
            margin-bottom: 10px; 
            font-weight: 300;
        }}
        .header p {{ 
            font-size: 1.2em; 
            opacity: 0.9; 
            font-weight: 300;
        }}
        .content {{ padding: 40px; }}
        .section {{ 
            margin-bottom: 50px; 
            background: #f8f9fa; 
            padding: 30px; 
            border-radius: 15px;
            border-left: 5px solid #667eea;
        }}
        .section h2 {{ 
            color: #2c3e50; 
            margin-bottom: 20px; 
            font-size: 1.8em;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section h2::before {{
            content: "🗺️";
            font-size: 0.8em;
        }}
        .maps-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); 
            gap: 30px; 
            margin-top: 20px;
        }}
        .map-item {{ 
            background: white; 
            padding: 20px; 
            border-radius: 15px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .map-item:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }}
        .map-item h3 {{ 
            color: #34495e; 
            margin-bottom: 15px; 
            font-size: 1.3em;
            text-align: center;
        }}
        .map-item img {{ 
            width: 100%; 
            height: auto; 
            border-radius: 10px; 
            border: 2px solid #e9ecef;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .stat-label {{
            color: #6c757d;
            font-size: 0.9em;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-top: 20px;
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
            opacity: 0.8;
        }}
        @media (max-width: 768px) {{
            .maps-grid {{ grid-template-columns: 1fr; }}
            .header h1 {{ font-size: 2em; }}
            .content {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Stuttgart H3 Spatial Analysis</h1>
            <p>Comprehensive spatial analysis using H3 hexagonal grid system</p>
            <p><em>Umfassende räumliche Analyse mit H3-Hexagon-Raster</em></p>
        </div>
        
        <div class="content">
            <!-- Overview Section -->
            <div class="section">
                <h2>Overview & Key Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">23</div>
                        <div class="stat-label">Districts</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">610K</div>
                        <div class="stat-label">Population</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">116.5</div>
                        <div class="stat-label">Green Area (km²)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">3,367</div>
                        <div class="stat-label">PT Stops</div>
                    </div>
                </div>
            </div>

            <!-- Maps Section -->
            <div class="section">
                <h2>Spatial Analysis Maps</h2>
                <div class="maps-grid">
"""

    # Add map items
    for filename, title in map_files.items():
        if filename in encoded_images:
            html_content += f"""
                    <div class="map-item">
                        <h3>{title}</h3>
                        <img src="data:image/png;base64,{encoded_images[filename]}" alt="{title}">
                    </div>"""

    # Complete HTML
    html_content += """
                </div>
            </div>

            <!-- Interactive Charts Section -->
            <div class="section">
                <h2>Interactive Analysis</h2>
                <div class="chart-container">
                    <div id="accessibilityChart" style="height: 400px;"></div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated with Python, GeoPandas, and H3 | Data: Stuttgart Open Data</p>
        </div>
    </div>

    <script>
        // Sample interactive chart (you can enhance this with real data)
        const data = [
            {{
                x: ['District 1', 'District 2', 'District 3', 'District 4', 'District 5'],
                y: [85, 72, 91, 68, 79],
                type: 'bar',
                name: 'Green Access Score',
                marker: {{
                    color: ['#2e7d32', '#43a047', '#66bb6a', '#81c784', '#a5d6a7']
                }}
            }}
        ];

        const layout = {{
            title: 'Sample District Accessibility Scores',
            xaxis: {{ title: 'Districts' }},
            yaxis: {{ title: 'Accessibility Score (0-100)' }},
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)'
        }};

        Plotly.newPlot('accessibilityChart', data, layout);
    </script>
</body>
</html>"""

    # Write dashboard
    dashboard_path = OUT_DIR / "stuttgart_dashboard.html"
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"🎉 Dashboard created: {dashboard_path}")
    print("📁 Open in your browser to view the complete analysis!")

if __name__ == "__main__":
    build_dashboard()
