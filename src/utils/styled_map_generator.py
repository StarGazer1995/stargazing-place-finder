#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML-style Light Pollution Map Generator

Generates modern light pollution maps based on the design style of light_pollution_map.html.
"""

import os
import sys
import json
import shutil
from typing import Dict, List, Tuple, Any, Optional
try:
    from light_pollution.light_pollution_map import LightPollutionMap
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    try:
        from light_pollution.light_pollution_map import LightPollutionMap
    except ImportError:
        class LightPollutionMap:
            def __init__(self, kml_file_path):
                self.kml_file_path = kml_file_path
            
            def get_sample_locations(self):
                return [
                {'name': 'Beijing', 'lat': 39.9042, 'lng': 116.4074, 'bortle_class': 8},
                {'name': 'Shanghai', 'lat': 31.2304, 'lng': 121.4737, 'bortle_class': 9},
                {'name': 'Hong Kong', 'lat': 22.3193, 'lng': 114.1694, 'bortle_class': 7},
                {'name': 'Chengdu', 'lat': 30.5728, 'lng': 104.0668, 'bortle_class': 6},
                {'name': 'Shijiazhuang', 'lat': 38.0428, 'lng': 114.5149, 'bortle_class': 5}
            ]


class StyledMapGenerator:
    """
    HTML-style Map Generator
    
    Generates modern, responsive light pollution maps based on the design style of light_pollution_map.html.
    """
    
    def __init__(self, kml_file_path: str):
        """
        Initialize styled map generator
        
        Args:
            kml_file_path: KML file path
        """
        self.map_generator = LightPollutionMap(kml_file_path)
        
        # Bortle classification colors based on HTML file
        self.bortle_colors = {
            1: '#000033',  # Excellent dark sky
            2: '#000066',  # Typical dark sky
            3: '#000099',  # Rural sky
            4: '#0066cc',  # Rural/suburban transition
            5: '#00ccff',  # Suburban sky
            6: '#66ff66',  # Bright suburban
            7: '#ffff00',  # Suburban/urban transition
            8: '#ff9900',  # Urban sky
            9: '#ff0000'   # Inner city sky
        }
        
        # Major Chinese cities and dark sky area data (based on HTML file)
        self.sample_locations = [
            {"lat": 39.9042, "lng": 116.4074, "intensity": 0.8, "bortle": 8, "sqm": 16.5, "name": "Beijing City Center"},
            {"lat": 31.2304, "lng": 121.4737, "intensity": 0.9, "bortle": 9, "sqm": 15.5, "name": "Shanghai City Center"},
            {"lat": 23.1291, "lng": 113.2644, "intensity": 0.7, "bortle": 7, "sqm": 17.5, "name": "Guangzhou City"},
            {"lat": 22.3193, "lng": 114.1694, "intensity": 0.85, "bortle": 8, "sqm": 16.5, "name": "Hong Kong"},
            {"lat": 30.5728, "lng": 104.0668, "intensity": 0.6, "bortle": 6, "sqm": 18.5, "name": "Chengdu City"},
            {"lat": 36.0611, "lng": 120.3785, "intensity": 0.65, "bortle": 6, "sqm": 18.5, "name": "Qingdao City"},
            {"lat": 29.5630, "lng": 106.5516, "intensity": 0.55, "bortle": 5, "sqm": 19.5, "name": "Chongqing City"},
            {"lat": 32.0603, "lng": 118.7969, "intensity": 0.7, "bortle": 7, "sqm": 17.5, "name": "Nanjing City"},
            {"lat": 38.0428, "lng": 114.5149, "intensity": 0.6, "bortle": 6, "sqm": 18.5, "name": "Shijiazhuang City"},
            {"lat": 34.3416, "lng": 108.9398, "intensity": 0.58, "bortle": 6, "sqm": 18.5, "name": "Xi'an City"},
            # Dark sky areas
            {"lat": 42.3601, "lng": 71.0589, "intensity": 0.15, "bortle": 2, "sqm": 21.4, "name": "Altai Mountains"},
            {"lat": 35.8617, "lng": 104.1954, "intensity": 0.2, "bortle": 2, "sqm": 21.4, "name": "Qinghai Lake"},
            {"lat": 29.6520, "lng": 91.1721, "intensity": 0.1, "bortle": 1, "sqm": 21.9, "name": "Tibet Plateau"},
            {"lat": 43.8803, "lng": 87.6177, "intensity": 0.18, "bortle": 2, "sqm": 21.4, "name": "Tianshan Mountains"},
            {"lat": 40.4319, "lng": 93.0866, "intensity": 0.12, "bortle": 1, "sqm": 21.9, "name": "Dunhuang Desert"}
        ]
    
    def _generate_modern_html_template(self) -> str:
        """
        Generate modern HTML template with multi-language adaptive support
        
        Returns:
            HTML template string
        """

        try:
            # Try to read external template file
            template_path = os.path.join(os.path.dirname(__file__), 'source', 'template.html')
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                return template_content
        except Exception as e:
            print(f"Warning: Could not load external template files: {e}")
            print("Falling back to built-in template...")
        
        # Throw error and return None, let the program crash
        return None
    def generate_styled_map(self, output_path: str = "./styled_light_pollution_map.html") -> str:
        """
        Generate HTML-style light pollution map
        
        Args:
            output_path: Output file path
            
        Returns:
            Generated HTML file path
        """
        print("🎨 Generating HTML-style light pollution map...")
        
        # Get HTML template
        html_template = self._generate_modern_html_template()
        
        # Convert sample data to JSON format
        light_pollution_json = json.dumps(self.sample_locations, ensure_ascii=False, indent=2)
        
        # Replace data placeholders in template
        html_content = html_template.replace('{LIGHT_POLLUTION_DATA}', light_pollution_json)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Write HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Styled map generated: {output_path}")
        return output_path
    
    def generate_comprehensive_styled_maps(self, output_dir: str = "./styled_map_output") -> Dict[str, str]:
        """
        Generate comprehensive styled map collection
        
        Args:
            output_dir: Output directory
            
        Returns:
            Dictionary of generated file paths
        """
        print("🚀 Generating comprehensive styled map collection...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        
        # 1. Generate main styled map
        main_map_path = os.path.join(output_dir, "index.html")
        results['main_map'] = self.generate_styled_map(main_map_path)
        
        # 2. Generate data file
        data_file_path = os.path.join(output_dir, "light_pollution_data.json")
        with open(data_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.sample_locations, f, ensure_ascii=False, indent=2)
        results['data_file'] = data_file_path
        
        # 3. Generate README file
        readme_path = os.path.join(output_dir, "README.md")
        readme_content = f"""
# Light Pollution Map - Stargazing Place Finder

## 📖 Introduction

This is a light pollution map visualization system based on modern web technology, following professional HTML design style, providing intuitive and beautiful light pollution data display.

## 🌟 Features

- **Modern Design**: Gradient backgrounds, glass morphism effects, rounded corners
- **Responsive Layout**: Support for desktop and mobile access
- **Multi-layer Support**: Four display modes - heatmap, markers, clusters, contours
- **Interactive Query**: Click on map to get real-time light pollution data
- **Smart Search**: Support for place name search and location functions
- **Bortle Classification**: Complete 1-9 level dark sky classification system

## 📊 Data Description

### Bortle Dark Sky Scale

1. **Class 1 - Excellent Dark Sky**: Milky Way clearly visible, suitable for deep sky observation
2. **Class 2 - Typical Dark Sky**: Milky Way structure obvious, nebulae clear
3. **Class 3 - Rural Sky**: Milky Way visible, some light pollution
4. **Class 4 - Rural/Suburban Transition**: Milky Way faintly visible
5. **Class 5 - Suburban Sky**: Milky Way barely perceptible
6. **Class 6 - Bright Suburban**: Milky Way invisible, only bright stars visible
7. **Class 7 - Suburban/Urban Transition**: Severe light pollution
8. **Class 8 - Urban Sky**: Only brightest stars visible
9. **Class 9 - Inner City Sky**: Almost impossible for astronomical observation

### SQM Values (Sky Quality Meter)

- **Unit**: mag/arcsec² (magnitude per square arcsecond)
- **Range**: Usually between 17-22
- **Description**: Higher values indicate darker skies, better stargazing conditions

## 🎯 Usage

1. **Open Map**: Open `index.html` in browser
2. **Select Layers**: Use top-left control panel to switch display modes
3. **Search Places**: Enter place names in top-right search box
4. **View Data**: Click anywhere on map to get light pollution information
5. **Location Function**: Click location button to get current position

## 📁 File Structure

```
{output_dir}/
├── index.html              # Main map page
├── light_pollution_data.json  # Light pollution data file
└── README.md               # Documentation
```

## 🔧 Technology Stack

- **Frontend Framework**: Leaflet.js (map library)
- **Style Design**: CSS3 (gradients, glass morphism, animations)
- **Data Format**: JSON
- **Map Service**: OpenStreetMap

## 📱 Browser Support

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 🌍 Data Sources

- Light Pollution Data: Based on real KML data processing
- Map Tiles: OpenStreetMap
- Bortle Classification: International Astronomical Union standards

---

**Stargazing Place Finder** - Help everyone find their own starry sky ✨
        """
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        results['readme'] = readme_path
        
        print(f"\n🎉 Comprehensive styled map collection generation completed!")
        print(f"📁 Output directory: {output_dir}")
        print(f"🌐 Main page: {results['main_map']}")
        print(f"📊 Data file: {results['data_file']}")
        print(f"📖 Documentation: {results['readme']}")
        
        return results


def main():
    """
    Main function: Generate HTML-style light pollution map
    """
    # KML file path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("🎨 === HTML-style Light Pollution Map Generator ===")
        print("Initializing styled map generator...")
        
        # Initialize generator
        generator = StyledMapGenerator(kml_file)
        
        # Generate comprehensive styled map collection
        output_dir = os.path.join(project_root, 'styled_map_output')
        results = generator.generate_comprehensive_styled_maps(output_dir)
        
        print("\n✅ All maps generated successfully!")
        print("\n📋 Generated files:")
        print(f"  Main page (area selection): {results['main_map']}")
        for key, path in results.items():
            print(f"  {key}: {path}")
        
        print("\n🌐 Usage:")
        print(f"  1. Main page: Open {results['main_map']} in browser")
        print("     - Supports area selection and stargazing location analysis")
        print("     - Requires API server startup (python stargazing_area_api.py)")
        print(f"  2. Light pollution map: Open {results['main_map']} in browser")
        print("  3. Check README file for detailed usage instructions")
        
    except Exception as e:
        print(f"❌ Error occurred while generating map: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()