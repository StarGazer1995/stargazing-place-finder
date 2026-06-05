#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Light Pollution Analyzer

Provides light pollution analysis using either:
1. VIIRS DNB GeoTIFF (default) — direct radiance values from satellite data
2. KML + image tiles (legacy) — Falchi World Atlas JPEG tiles

The GeoTIFF backend is the recommended data source for new deployments.
"""

import os
import sys
from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path

import numpy as np

try:
    import rasterio
except ImportError:
    rasterio = None  # type: ignore

# Legacy KML backend imports (optional)
try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

try:
    from location_finder.location_finder import LocationFinder
    from utils.kml_parser import KMLParser, GroundOverlay
    from cache.cache_config import get_cache_dir
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    from location_finder.location_finder import LocationFinder
    from utils.kml_parser import KMLParser, GroundOverlay
    from cache.cache_config import get_cache_dir


# ---------------------------------------------------------------------------
# Radiance → Bortle scale conversion
# Based on standard VIIRS DNB radiance thresholds used in light pollution science
# ---------------------------------------------------------------------------

def radiance_to_bortle(radiance: float) -> int:
    """Convert VIIRS DNB radiance (nW/cm²/sr) to Bortle class (1-9).
    
    Thresholds derived from peer-reviewed literature correlating VIIRS DNB
    radiance with Sky Quality Meter (SQM) measurements.
    """
    if radiance <= 0.0:
        return 1   # Excellent dark sky
    elif radiance <= 0.5:
        return 2   # Typical dark sky
    elif radiance <= 1.5:
        return 3   # Rural sky
    elif radiance <= 4.0:
        return 4   # Rural/suburban transition
    elif radiance <= 10.0:
        return 5   # Suburban sky
    elif radiance <= 25.0:
        return 6   # Bright suburban
    elif radiance <= 60.0:
        return 7   # Suburban/urban transition
    elif radiance <= 150.0:
        return 8   # City sky
    else:
        return 9   # Inner city sky


def radiance_to_brightness(radiance: float) -> int:
    """Map radiance (nW/cm²/sr) to a 0-255 brightness value for backward compatibility."""
    # Apply log-like scaling: 0→0, ~0.5→~30, ~100→~200, 1000+→255
    if radiance <= 0:
        return 0
    b = int(255.0 * (1.0 - 1.0 / (1.0 + radiance * 0.1)))
    return min(255, b)


def radiance_to_pollution_level(radiance: float) -> str:
    """Get a human-readable pollution level string from radiance."""
    bortle = radiance_to_bortle(radiance)
    descriptions = {
        1: "极低污染 (Class 1 - 优秀观星条件)",
        2: "低度污染 (Class 2 - 良好观星条件)",
        3: "轻度污染 (Class 3 - 一般观星条件)",
        4: "中度污染 (Class 4 - 较差观星条件)",
        5: "重度污染 (Class 5 - 差观星条件)",
        6: "严重污染 (Class 6 - 很差观星条件)",
        7: "严重污染 (Class 7 - 极差观星条件)",
        8: "极端污染 (Class 8 - 不适合观星)",
        9: "极端污染 (Class 9 - 完全不适合观星)",
    }
    return descriptions.get(bortle, "未知污染等级")


class LightPollutionAnalyzer:
    """Light Pollution Analyzer
    
    Supports two backends:
    1. **VIIRS GeoTIFF** (default): Reads radiance directly from a clipped
       VIIRS DNB GeoTIFF file. Returns nW/cm²/sr values.
    2. **KML + image tiles** (legacy): Uses Falchi World Atlas JPEG tiles
       via LocationFinder to extract color information.
    
    The GeoTIFF backend is used automatically when `geotiff_path` is provided
    or when no KML path is given. It is the recommended data source.
    """
    
    def __init__(
        self,
        kml_file_path: Optional[str] = None,
        images_base_path: Optional[str] = None,
        geotiff_path: Optional[Union[str, Path]] = None,
    ):
        """Initialize light pollution analyzer
        
        Args:
            kml_file_path: Path to KML file (legacy backend). If None and no
                geotiff_path given, defaults to the bundled VIIRS China GeoTIFF.
            images_base_path: Base path for image files (legacy backend).
                Auto-inferred from KML path if None.
            geotiff_path: Path to VIIRS GeoTIFF file. If provided, uses the
                GeoTIFF backend instead of KML.
                
        Raises:
            FileNotFoundError: When the specified data file does not exist
            ValueError: When required dependencies are missing
        """
        # Determine which backend to use
        if geotiff_path is not None:
            # ---- GeoTIFF backend ----
            if rasterio is None:
                raise ImportError(
                    "rasterio is required for GeoTIFF backend. "
                    "Install with: uv add rasterio"
                )
            self._backend = 'geotiff'
            self._geotiff_path = str(geotiff_path)
            self._src = None  # Lazy open
            self.location_finder = None
            self.images_base_path = None
            self._image_cache = {}
            self._image_cache_dir = None
            print(f"Light pollution analyzer (GeoTIFF backend)")
            print(f"  Data: {self._geotiff_path}")
            
        else:
            # ---- Legacy KML backend ----
            if kml_file_path is None:
                # No path specified at all — will be set later via init()
                self._backend = None
                self.location_finder = None
                self.images_base_path = None
                self._image_cache = {}
                self._image_cache_dir = None
                return
                
            if not os.path.exists(kml_file_path) and kml_file_path.endswith('.xml'):
                alt = kml_file_path[:-4] + '.kml'
                if os.path.exists(alt):
                    kml_file_path = alt
                    
            self._backend = 'kml'
            self.location_finder = LocationFinder(kml_file_path)
            
            if images_base_path is None:
                kml_dir = os.path.dirname(kml_file_path)
                self.images_base_path = os.path.join(kml_dir, 'files')
            else:
                self.images_base_path = images_base_path
                
            self._image_cache = {}
            self._image_cache_dir = get_cache_dir('images')
            
            print(f"Light pollution analyzer (legacy KML backend)")
            print(f"Images base path: {self.images_base_path}")
    
    # ------------------------------------------------------------------
    # GeoTIFF backend helpers
    # ------------------------------------------------------------------
    
    def _ensure_geotiff_open(self):
        """Lazy-open the GeoTIFF file on first access."""
        if self._src is None and self._backend == 'geotiff':
            self._src = rasterio.open(self._geotiff_path)
    
    def get_radiance(self, latitude: float, longitude: float) -> Optional[float]:
        """Get VIIRS DNB radiance (nW/cm²/sr) at the given coordinates.
        
        Only available with the GeoTIFF backend.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Radiance value in nW/cm²/sr, or None if outside data coverage
        """
        self._ensure_geotiff_open()
        if self._src is None:
            return None
        
        try:
            row, col = self._src.index(longitude, latitude)
            if row < 0 or row >= self._src.height or col < 0 or col >= self._src.width:
                return None
            val = float(self._src.read(1, window=((row, row+1), (col, col+1)))[0, 0])
            return val
        except Exception:
            return None
    
    # ------------------------------------------------------------------
    # Main public API — dispatches to the active backend
    # ------------------------------------------------------------------
    
    def get_light_pollution_color(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Get light pollution information at the given coordinates.
        
        With the GeoTIFF backend, returns radiance-based results.
        With the KML backend (legacy), returns color-based results.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Dictionary containing light pollution information, None if not found.
            Keys:
            - 'radiance' (GeoTIFF only): VIIRS DNB radiance in nW/cm²/sr
            - 'rgb', 'hex': Color representation
            - 'brightness': Brightness value (0-255)
            - 'pollution_level': Human-readable pollution description
            - 'overlay_name': Source name
            - 'coordinates': Input coordinate information
        
        Raises:
            ValueError: When coordinates are invalid
        """
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, current value: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, current value: {longitude}")
        
        if self._backend == 'geotiff':
            return self._get_pollution_geotiff(latitude, longitude)
        elif self._backend == 'kml':
            return self._get_pollution_kml(latitude, longitude)
        else:
            return None
    
    def _get_pollution_geotiff(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """GeoTIFF backend: read radiance and convert to pollution info."""
        self._ensure_geotiff_open()
        if self._src is None:
            return None
        
        try:
            row, col = self._src.index(longitude, latitude)
            if row < 0 or row >= self._src.height or col < 0 or col >= self._src.width:
                return None
            
            radiance = float(self._src.read(1, window=((row, row+1), (col, col+1)))[0, 0])
            brightness = radiance_to_brightness(radiance)
            bortle = radiance_to_bortle(radiance)
            pollution_level = radiance_to_pollution_level(radiance)
            
            # Build a color representation (false-color heat)
            r, g, b = self._radiance_to_false_color(radiance)
            
            return {
                'radiance': radiance,
                'rgb': (r, g, b),
                'hex': f"#{r:02x}{g:02x}{b:02x}",
                'brightness': brightness,
                'pollution_level': pollution_level,
                'bortle': bortle,
                'overlay_name': 'VIIRS-DNB-2025',
                'coordinates': {'latitude': latitude, 'longitude': longitude},
            }
        except Exception:
            return None
    
    @staticmethod
    def _radiance_to_false_color(radiance: float) -> Tuple[int, int, int]:
        """Map radiance to a false-color RGB for visualization.
        
        Dark (low radiance) → blue-black
        Medium → green-yellow
        High (urban) → red-white
        """
        if radiance <= 0:
            return (10, 10, 40)  # Very dark blue
        # Use log-scale for better visual range
        import math as _m
        v = _m.log10(max(radiance, 0.01) + 1) / _m.log10(1001)  # 0-1 scale
        v = min(1.0, v)
        if v < 0.33:
            t = v / 0.33
            r, g, b = int(10 + 50 * t), int(30 + 150 * t), int(80 + 80 * (1 - t))
        elif v < 0.66:
            t = (v - 0.33) / 0.33
            r, g, b = int(60 + 150 * t), int(180 - 100 * t), int(80 - 60 * t)
        else:
            t = (v - 0.66) / 0.34
            r, g, b = int(210 + 45 * t), int(80 + 120 * t), int(20 + 20 * t)
        return (min(255, r), min(255, g), min(255, b))
    
    def _get_pollution_kml(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """KML backend: use LocationFinder + image extraction (legacy)."""
        overlay = self.location_finder.find_overlay_by_coordinates(latitude, longitude)
        if overlay is None:
            return None
        
        color_info = self._extract_color_from_image(overlay, latitude, longitude)
        if color_info is None:
            return None
        
        color_info['overlay_name'] = overlay.name
        color_info['coordinates'] = {'latitude': latitude, 'longitude': longitude}
        return color_info
    
    def _extract_color_from_image(self, overlay: GroundOverlay, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Extract color information from image file at specified coordinates
        
        Args:
            overlay: GroundOverlay object
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Color information dictionary or None
        """
        try:
            # Get image file path
            image_filename = os.path.basename(overlay.icon.href)
            image_path = os.path.join(self.images_base_path, image_filename)
            
            # Check if image file exists
            if not os.path.exists(image_path):
                print(f"Warning: Image file does not exist: {image_path}")
                return self._get_default_color_info()
            
            # Load image (using cache)
            image = self._load_image_cached(image_path)
            if image is None:
                return self._get_default_color_info()
            
            # Calculate corresponding pixel coordinates in image
            pixel_x, pixel_y = self._geo_to_pixel_coordinates(
                latitude, longitude, overlay, image.size
            )
            
            # Ensure pixel coordinates are within image bounds
            if not (0 <= pixel_x < image.size[0] and 0 <= pixel_y < image.size[1]):
                print(f"Warning: Calculated pixel coordinates out of image bounds: ({pixel_x}, {pixel_y})")
                return self._get_default_color_info()
            
            # Use bilinear interpolation to get sub-pixel color
            pixel_color = self._get_interpolated_color(image, pixel_x, pixel_y)
            
            # Handle different image modes
            if image.mode == 'RGB':
                r, g, b = pixel_color
            elif image.mode == 'RGBA':
                r, g, b, a = pixel_color
            elif image.mode == 'L':  # Grayscale image
                r = g = b = pixel_color
            else:
                # Convert to RGB mode
                rgb_image = image.convert('RGB')
                r, g, b = rgb_image.getpixel((int(pixel_x), int(pixel_y)))
            
            # Calculate brightness and pollution level
            brightness = int(0.299 * r + 0.587 * g + 0.114 * b)
            pollution_level = self._calculate_pollution_level(brightness)
            
            return {
                'rgb': (r, g, b),
                'hex': f"#{r:02x}{g:02x}{b:02x}",
                'brightness': brightness,
                'pollution_level': pollution_level
            }
            
        except Exception as e:
            print(f"Error extracting color information: {e}")
            return self._get_default_color_info()
    
    def _load_image_cached(self, image_path: str) -> Optional[Image.Image]:
        """Load image file with caching
        
        Args:
            image_path: Image file path
            
        Returns:
            PIL Image object or None
        """
        # First check memory cache
        if image_path in self._image_cache:
            return self._image_cache[image_path]
        
        # Generate cache filename
        import hashlib
        cache_filename = hashlib.md5(image_path.encode()).hexdigest() + ".pkl"
        cache_file_path = self._image_cache_dir / cache_filename
        
        # Check disk cache
        if cache_file_path.exists():
            try:
                import pickle
                with open(cache_file_path, 'rb') as f:
                    image = pickle.load(f)
                self._image_cache[image_path] = image
                return image
            except Exception as e:
                print(f"Failed to load image from disk cache {cache_file_path}: {e}")
                # Delete corrupted cache file
                try:
                    cache_file_path.unlink()
                except:
                    pass
        
        # Load image from original file
        try:
            image = Image.open(image_path)
            # Save to memory cache
            self._image_cache[image_path] = image
            
            # Save to disk cache
            try:
                import pickle
                with open(cache_file_path, 'wb') as f:
                    pickle.dump(image, f)
            except Exception as e:
                print(f"Failed to save image to disk cache {cache_file_path}: {e}")
            
            return image
        except Exception as e:
            print(f"Failed to load image {image_path}: {e}")
            return None
    
    def _geo_to_pixel_coordinates(self, latitude: float, longitude: float, 
                                overlay: GroundOverlay, image_size: Tuple[int, int]) -> Tuple[float, float]:
        """Convert geographic coordinates to image pixel coordinates
        
        Args:
            latitude: Latitude
            longitude: Longitude
            overlay: GroundOverlay object
            image_size: Image size (width, height)
            
        Returns:
            Pixel coordinates (x, y)
        """
        box = overlay.lat_lon_box
        
        # Calculate relative position (between 0-1)
        lat_ratio = (latitude - box.south) / (box.north - box.south)
        lon_ratio = (longitude - box.west) / (box.east - box.west)
        
        # Convert to pixel coordinates
        # Note: Image Y-axis is top-to-bottom, so need to flip latitude
        pixel_x = lon_ratio * image_size[0]
        pixel_y = (1 - lat_ratio) * image_size[1]
        
        return pixel_x, pixel_y
    
    def _calculate_pollution_level(self, brightness: int) -> str:
        """Calculate light pollution level based on brightness value
        
        Args:
            brightness: Brightness value (0-255)
            
        Returns:
            Pollution level description string
        """
        if brightness < 32:
            return "Very Low Pollution (Class 1 - Excellent stargazing conditions)"
        elif brightness < 64:
            return "Low Pollution (Class 2 - Good stargazing conditions)"
        elif brightness < 96:
            return "Light Pollution (Class 3 - Fair stargazing conditions)"
        elif brightness < 128:
            return "Moderate Pollution (Class 4 - Poor stargazing conditions)"
        elif brightness < 160:
            return "Heavy Pollution (Class 5 - Bad stargazing conditions)"
        elif brightness < 192:
            return "Severe Pollution (Class 6 - Very bad stargazing conditions)"
        else:
            return "Extreme Pollution (Class 7+ - Extremely poor stargazing conditions)"
    
    def _get_default_color_info(self) -> Dict[str, Any]:
        """Get default color information (used when unable to extract from image)
        
        Returns:
            Default color information dictionary
        """
        return {
            'rgb': (128, 128, 128),  # 灰色
            'hex': '#808080',
            'brightness': 128,
            'pollution_level': 'Unknown pollution level'
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics
        
        Returns:
            Statistics information dictionary
        """
        if self._backend == 'geotiff':
            self._ensure_geotiff_open()
            if self._src is not None:
                return {
                    'backend': 'geotiff',
                    'data_path': self._geotiff_path,
                    'width': self._src.width,
                    'height': self._src.height,
                    'crs': str(self._src.crs),
                    'bounds': {
                        'north': self._src.bounds.top,
                        'south': self._src.bounds.bottom,
                        'east': self._src.bounds.right,
                        'west': self._src.bounds.left,
                    },
                    'count': self._src.count,
                    'dtype': self._src.dtypes[0],
                }
            return {'backend': 'geotiff', 'error': 'not opened'}
        
        # KML backend
        base_stats = self.location_finder.get_statistics()
        return {
            **base_stats,
            'backend': 'kml',
            'images_base_path': self.images_base_path,
            'cached_images': len(self._image_cache),
            'images_directory_exists': os.path.exists(self.images_base_path)
        }
    
    def clear_image_cache(self) -> None:
        """Clear cache (image cache for KML backend, no-op for GeoTIFF)."""
        if self._backend == 'kml':
            for image in self._image_cache.values():
                if hasattr(image, 'close'):
                    image.close()
            self._image_cache.clear()
            try:
                import shutil
                if self._image_cache_dir.exists():
                    shutil.rmtree(self._image_cache_dir)
                    self._image_cache_dir.mkdir(exist_ok=True)
                print("Image cache cleared (including disk cache)")
            except Exception as e:
                print(f"Error clearing disk cache: {e}")
                print("Memory cache cleared")
        else:
            print("GeoTIFF backend has no image cache to clear")
    
    def batch_analyze_coordinates(self, coordinates_list: list) -> list:
        """Batch analyze light pollution information for multiple coordinates
        
        For GeoTIFF backend, this is optimized to read rows in bulk.
        
        Args:
            coordinates_list: List of (latitude, longitude) tuples
            
        Returns:
            List of analysis results
        """
        if self._backend == 'geotiff':
            return self._batch_analyze_geotiff(coordinates_list)
        
        # KML backend — sequential
        results = []
        for i, (lat, lon) in enumerate(coordinates_list):
            try:
                pollution_info = self.get_light_pollution_color(lat, lon)
                results.append({
                    'index': i,
                    'coordinates': (lat, lon),
                    'pollution_info': pollution_info,
                    'success': pollution_info is not None
                })
            except Exception as e:
                results.append({
                    'index': i,
                    'coordinates': (lat, lon),
                    'pollution_info': None,
                    'success': False,
                    'error': str(e)
                })
        return results
    
    def _batch_analyze_geotiff(self, coordinates_list: list) -> list:
        """Batch analysis optimized for GeoTIFF: group by row for efficient reads."""
        self._ensure_geotiff_open()
        if self._src is None:
            return [{'index': i, 'success': False, 'error': 'GeoTIFF not open'}
                    for i in range(len(coordinates_list))]
        
        # Group points by row
        row_groups = {}
        for i, (lat, lon) in enumerate(coordinates_list):
            try:
                row, col = self._src.index(lon, lat)
                if 0 <= row < self._src.height and 0 <= col < self._src.width:
                    row_groups.setdefault(row, []).append((i, col, lat, lon))
            except Exception:
                pass
        
        results = [None] * len(coordinates_list)
        for row, items in row_groups.items():
            row_data = self._src.read(1, window=((row, row+1), (0, self._src.width)))
            for idx, col, lat, lon in items:
                radiance = float(row_data[0, col])
                pollution_info = {
                    'radiance': radiance,
                    'brightness': radiance_to_brightness(radiance),
                    'pollution_level': radiance_to_pollution_level(radiance),
                    'bortle': radiance_to_bortle(radiance),
                    'coordinates': {'latitude': lat, 'longitude': lon},
                }
                results[idx] = {
                    'index': idx,
                    'coordinates': (lat, lon),
                    'pollution_info': pollution_info,
                    'success': True,
                }
        
        # Fill in missing
        for i, r in enumerate(results):
            if r is None:
                results[i] = {
                    'index': i,
                    'coordinates': coordinates_list[i],
                    'pollution_info': None,
                    'success': False,
                    'error': 'Outside data coverage',
                }
        return results
    
    def get_light_pollution_images_in_bounds(self, north: float, south: float, 
                                           east: float, west: float) -> list:
        """Get light pollution image data within specified geographic bounds.
        
        Note: Only works with KML backend. For GeoTIFF, use get_radiance().
        """
        if self._backend == 'geotiff':
            print("Warning: get_light_pollution_images_in_bounds is not available "
                  "with GeoTIFF backend. Use get_radiance() or batch_analyze_coordinates() instead.")
            return []
        
        results = []
        overlapping_overlays = self.location_finder.find_overlays_in_bounds(
            north, south, east, west
        )
        
        for overlay in overlapping_overlays:
            try:
                image_filename = os.path.basename(overlay.icon.href)
                image_path = os.path.join(self.images_base_path, image_filename)
                file_exists = os.path.exists(image_path)
                
                image_data = None
                if file_exists:
                    try:
                        import base64
                        with open(image_path, 'rb') as img_file:
                            image_data = base64.b64encode(img_file.read()).decode('utf-8')
                    except Exception as e:
                        print(f"Failed to read image file {image_path}: {e}")
                
                results.append({
                    'overlay': overlay,
                    'image_path': image_path,
                    'image_data': image_data,
                    'bounds': {
                        'north': overlay.lat_lon_box.north,
                        'south': overlay.lat_lon_box.south,
                        'east': overlay.lat_lon_box.east,
                        'west': overlay.lat_lon_box.west,
                    },
                    'exists': file_exists,
                    'name': overlay.name,
                })
            except Exception as e:
                print(f"Error processing overlay {overlay.name}: {e}")
                continue
        
        print(f"Found {len(results)} light pollution images within specified boundaries")
        return results
    
    def _get_interpolated_color(self, image: Image.Image, x: float, y: float) -> Tuple[int, ...]:
        """Get color value at sub-pixel position using bilinear interpolation
        
        Args:
            image: PIL image object
            x: X coordinate (can be decimal)
            y: Y coordinate (can be decimal)
            
        Returns:
            Interpolated pixel color value
        """
        # 获取图像尺寸
        width, height = image.size
        
        # 边界检查
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        
        # 获取四个相邻像素的坐标
        x1 = int(x)
        y1 = int(y)
        x2 = min(x1 + 1, width - 1)
        y2 = min(y1 + 1, height - 1)
        
        # 计算插值权重
        dx = x - x1
        dy = y - y1
        
        # 获取四个角的像素值
        try:
            p11 = image.getpixel((x1, y1))  # 左上
            p12 = image.getpixel((x1, y2))  # 左下
            p21 = image.getpixel((x2, y1))  # 右上
            p22 = image.getpixel((x2, y2))  # 右下
            
            # 确保像素值是元组格式
            if not isinstance(p11, tuple):
                p11 = (p11,)
            if not isinstance(p12, tuple):
                p12 = (p12,)
            if not isinstance(p21, tuple):
                p21 = (p21,)
            if not isinstance(p22, tuple):
                p22 = (p22,)
            
            # 对每个颜色通道进行双线性插值
            channels = len(p11)
            result = []
            
            for i in range(channels):
                # 双线性插值公式
                interpolated = (
                    p11[i] * (1 - dx) * (1 - dy) +
                    p21[i] * dx * (1 - dy) +
                    p12[i] * (1 - dx) * dy +
                    p22[i] * dx * dy
                )
                result.append(int(round(interpolated)))
            
            return tuple(result)
            
        except Exception as e:
            print(f"Bilinear interpolation calculation error: {e}, falling back to nearest neighbor interpolation")
            # 回退到最近邻插值
            return image.getpixel((int(round(x)), int(round(y))))