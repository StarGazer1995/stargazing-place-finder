# Light Pollution Analyzer System Design

## Overview

The Light Pollution Analyzer is a core component of the Stargazing Place Finder project that provides precise light pollution analysis based on geographic coordinates. This system extracts light pollution data from KML files and associated image overlays, offering detailed color analysis and pollution level assessment for astronomical observation site evaluation.

## System Architecture

### Core Components

```
LightPollutionAnalyzer
├── LocationFinder Integration
├── Image Processing Engine
├── Coordinate Transformation
├── Cache Management System
└── Pollution Level Classification
```

### Dependencies

- **LocationFinder**: Geographic overlay location services
- **KML Parser**: Ground overlay data extraction
- **PIL (Pillow)**: Image processing and manipulation
- **NumPy**: Numerical computations
- **Cache Config**: Performance optimization through caching

## Functional Requirements

### 1. Geographic Light Pollution Analysis

**Primary Function**: Extract light pollution data from geographic coordinates

**Key Features**:
- Coordinate-based pollution level detection
- RGB color value extraction from satellite imagery
- Brightness calculation and classification
- Multi-format image support (RGB, RGBA, Grayscale)

### 2. Advanced Image Processing

**Sub-pixel Accuracy**: Bilinear interpolation for precise color extraction

**Image Format Support**:
- RGB color images
- RGBA images with transparency
- Grayscale images
- Automatic format conversion

### 3. Performance Optimization

**Multi-level Caching**:
- Memory cache for frequently accessed images
- Disk cache for persistent storage
- Automatic cache management and cleanup

## Data Models

### LightPollutionResult

```python
{
    'rgb': Tuple[int, int, int],           # RGB color values (0-255)
    'hex': str,                           # Hexadecimal color representation
    'brightness': int,                    # Calculated brightness (0-255)
    'pollution_level': str,               # Human-readable pollution classification
    'overlay_name': str,                  # Source overlay identifier
    'coordinates': {
        'latitude': float,
        'longitude': float
    }
}
```

### BatchAnalysisResult

```python
{
    'index': int,                         # Coordinate index in batch
    'coordinates': Tuple[float, float],   # (latitude, longitude)
    'pollution_info': LightPollutionResult, # Analysis result
    'success': bool,                      # Analysis success status
    'error': Optional[str]                # Error message if failed
}
```

### ImageBoundsResult

```python
{
    'overlay': GroundOverlay,             # KML overlay object
    'image_path': str,                    # Local image file path
    'image_data': Optional[str],          # Base64 encoded image data
    'bounds': {
        'north': float, 'south': float,
        'east': float, 'west': float
    },
    'exists': bool,                       # File existence status
    'name': str                           # Overlay name
}
```

## Algorithm Implementations

### 1. Coordinate-to-Pixel Transformation

**Purpose**: Convert geographic coordinates to image pixel coordinates

**Algorithm**:
```python
def _geo_to_pixel_coordinates(latitude, longitude, overlay, image_size):
    box = overlay.lat_lon_box
    
    # Calculate relative position (0-1 range)
    lat_ratio = (latitude - box.south) / (box.north - box.south)
    lon_ratio = (longitude - box.west) / (box.east - box.west)
    
    # Convert to pixel coordinates (Y-axis flipped for image coordinates)
    pixel_x = lon_ratio * image_size[0]
    pixel_y = (1 - lat_ratio) * image_size[1]
    
    return pixel_x, pixel_y
```

**Key Considerations**:
- Y-axis inversion for image coordinate system
- Boundary validation and clipping
- Sub-pixel precision support

### 2. Bilinear Interpolation

**Purpose**: Achieve sub-pixel accuracy in color extraction

**Implementation**:
- Four-point sampling around target coordinates
- Weighted average calculation based on distance
- Fallback to nearest-neighbor for edge cases

**Benefits**:
- Improved accuracy for coordinate-based queries
- Smooth color transitions
- Reduced aliasing artifacts

### 3. Light Pollution Classification

**Brightness Calculation**: Luminance formula (ITU-R BT.709)
```python
brightness = int(0.299 * r + 0.587 * g + 0.114 * b)
```

**Classification Scale**:
- **Class 1** (0-31): Excellent dark sky conditions
- **Class 2** (32-63): Good observing conditions
- **Class 3** (64-95): Moderate light pollution
- **Class 4** (96-127): Poor observing conditions
- **Class 5** (128-159): Heavy light pollution
- **Class 6** (160-191): Severe light pollution
- **Class 7+** (192-255): Extreme light pollution

## Use Case Implementations

### 1. Single Coordinate Analysis

**Scenario**: Evaluate light pollution at a specific location

**Implementation**:
```python
analyzer = LightPollutionAnalyzer('pollution_data.kml')
result = analyzer.get_light_pollution_color(39.9042, 116.4074)  # Beijing

if result:
    print(f"Pollution Level: {result['pollution_level']}")
    print(f"RGB Values: {result['rgb']}")
    print(f"Brightness: {result['brightness']}")
```

### 2. Batch Coordinate Processing

**Scenario**: Analyze multiple locations efficiently

**Implementation**:
```python
coordinates = [(39.9042, 116.4074), (40.7128, -74.0060), (51.5074, -0.1278)]
results = analyzer.batch_analyze_coordinates(coordinates)

for result in results:
    if result['success']:
        pollution_info = result['pollution_info']
        print(f"Location {result['index']}: {pollution_info['pollution_level']}")
    else:
        print(f"Location {result['index']}: Analysis failed - {result['error']}")
```

### 3. Regional Image Data Extraction

**Scenario**: Extract all light pollution images within geographic bounds

**Implementation**:
```python
# Define bounding box (North, South, East, West)
images = analyzer.get_light_pollution_images_in_bounds(40.0, 39.0, 117.0, 116.0)

for image_info in images:
    if image_info['exists']:
        print(f"Found image: {image_info['name']}")
        print(f"Bounds: {image_info['bounds']}")
        # Process base64 image data if needed
```

## Performance Optimization

### 1. Multi-level Caching Strategy

**Memory Cache**:
- In-memory storage of frequently accessed images
- Automatic cleanup on system shutdown
- Configurable cache size limits

**Disk Cache**:
- Persistent storage using pickle serialization
- MD5-based cache key generation
- Automatic corruption detection and recovery

**Cache Management**:
```python
# Manual cache clearing
analyzer.clear_image_cache()  # Clears both memory and disk cache

# Automatic cache directory management
cache_dir = get_cache_dir('images')  # Centralized cache configuration
```

### 2. Image Loading Optimization

**Lazy Loading**: Images loaded only when needed
**Format Optimization**: Automatic conversion to optimal formats
**Memory Management**: Proper image disposal and garbage collection

### 3. Batch Processing Efficiency

**Error Isolation**: Individual coordinate failures don't affect batch
**Progress Tracking**: Index-based result correlation
**Resource Reuse**: Shared image cache across batch operations

## Error Handling and Resilience

### 1. Input Validation

**Coordinate Validation**:
```python
if not (-90 <= latitude <= 90):
    raise ValueError(f"Invalid latitude: {latitude}")
if not (-180 <= longitude <= 180):
    raise ValueError(f"Invalid longitude: {longitude}")
```

### 2. File System Resilience

**Missing Image Handling**:
- Graceful degradation to default values
- Warning messages for missing files
- Automatic fallback mechanisms

**Cache Corruption Recovery**:
- Automatic detection of corrupted cache files
- Safe cache file deletion and regeneration
- Fallback to original file loading

### 3. Image Processing Error Handling

**Format Compatibility**:
- Automatic format detection and conversion
- Support for various image modes (RGB, RGBA, L)
- Graceful handling of unsupported formats

**Interpolation Fallbacks**:
- Bilinear interpolation with nearest-neighbor fallback
- Boundary condition handling
- Robust error recovery

## Integration Interfaces

### 1. Stargazing Location Analyzer Integration

**Purpose**: Provide light pollution data for comprehensive site analysis

**Interface**:
```python
class StargazingLocationAnalyzer:
    def __init__(self, light_pollution_kml_path):
        self.light_pollution_analyzer = LightPollutionAnalyzer(light_pollution_kml_path)
    
    def analyze_location(self, latitude, longitude):
        pollution_data = self.light_pollution_analyzer.get_light_pollution_color(
            latitude, longitude
        )
        # Integrate with other analysis components
```

### 2. Visualization System Integration

**Map Overlay Generation**:
```python
# Generate pollution overlay for interactive maps
images_in_bounds = analyzer.get_light_pollution_images_in_bounds(
    north, south, east, west
)

for image_info in images_in_bounds:
    if image_info['image_data']:
        # Add image overlay to map visualization
        add_image_overlay_to_map(image_info)
```

### 3. API Service Integration

**RESTful API Endpoints**:
```python
@app.route('/api/light-pollution')
def get_light_pollution():
    lat = float(request.args.get('lat'))
    lon = float(request.args.get('lon'))
    
    result = analyzer.get_light_pollution_color(lat, lon)
    return jsonify(result)

@app.route('/api/light-pollution/batch', methods=['POST'])
def batch_light_pollution():
    coordinates = request.json['coordinates']
    results = analyzer.batch_analyze_coordinates(coordinates)
    return jsonify(results)
```

## Output Formats and Visualization

### 1. Structured Data Output

**JSON Format**:
```json
{
    "rgb": [45, 23, 12],
    "hex": "#2d170c",
    "brightness": 28,
    "pollution_level": "极低污染 (Class 1 - 优秀观星条件)",
    "overlay_name": "Beijing_Light_Pollution",
    "coordinates": {
        "latitude": 39.9042,
        "longitude": 116.4074
    }
}
```

### 2. Statistical Reporting

**System Statistics**:
```python
stats = analyzer.get_statistics()
# Returns: overlay count, cache status, file system info
```

### 3. Base64 Image Data

**Image Export**: Direct base64 encoding for web applications
**Boundary-based Extraction**: Regional image data retrieval
**Metadata Inclusion**: Complete overlay information with image data

## Technical Dependencies

### Core Libraries

```python
# Image processing
PIL>=8.0.0
numpy>=1.20.0

# File system and caching
os, sys, hashlib, pickle, shutil

# Type hints
typing>=3.7.0
```

### System Requirements

**Python Version**: 3.7+
**Memory**: Minimum 512MB for image caching
**Storage**: Variable based on KML and image data size
**Network**: Not required for local analysis

### Installation Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install python3-pil python3-numpy

# macOS
brew install pillow numpy

# Windows
pip install Pillow numpy
```

## Future Enhancements

### 1. Advanced Image Processing

**Multi-spectral Analysis**: Support for infrared and other spectral bands
**Temporal Analysis**: Time-series light pollution tracking
**Machine Learning Integration**: Automated pollution pattern recognition

### 2. Performance Improvements

**Parallel Processing**: Multi-threaded batch analysis
**GPU Acceleration**: CUDA support for large-scale processing
**Streaming Processing**: Real-time analysis for large datasets

### 3. Data Source Expansion

**Multiple Data Sources**: Integration with various light pollution databases
**Real-time Data**: Live satellite feed integration
**Crowdsourced Data**: Community-contributed measurements

### 4. Advanced Visualization

**3D Pollution Mapping**: Height-aware pollution visualization
**Interactive Overlays**: Dynamic map layer management
**Comparative Analysis**: Multi-temporal comparison tools

## Security and Privacy Considerations

### 1. Data Privacy

**Local Processing**: No external data transmission required
**Cache Security**: Secure local cache storage
**Input Sanitization**: Robust coordinate validation

### 2. File System Security

**Path Validation**: Prevention of directory traversal attacks
**Permission Checks**: Appropriate file access controls
**Error Information**: Limited error disclosure

### 3. Resource Management

**Memory Limits**: Configurable cache size restrictions
**CPU Usage**: Efficient algorithm implementations
**Disk Space**: Automatic cache cleanup mechanisms

This comprehensive design document provides the foundation for understanding, maintaining, and extending the Light Pollution Analyzer system within the Stargazing Place Finder project.