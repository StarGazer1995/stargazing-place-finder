#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Light Pollution Analyzer

This module provides a light pollution analyzer class for obtaining light pollution
color values based on geographic coordinates. The class is initialized using
LocationFinder parsing results and provides functionality to get light pollution
information based on coordinates.
"""

import os
import sys
from typing import Optional, Tuple, Dict, Any
from PIL import Image
import numpy as np
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


class LightPollutionAnalyzer:
    """Light Pollution Analyzer
    
    This class is initialized using LocationFinder parsing results and provides
    functionality to get light pollution color values based on geographic coordinates.
    It obtains precise light pollution intensity information by analyzing corresponding
    image files.
    """
    
    def __init__(self, kml_file_path: str, images_base_path: Optional[str] = None):
        """Initialize light pollution analyzer
        
        Args:
            kml_file_path: Path to KML file
            images_base_path: Base path for image files, auto-inferred if None
            
        Raises:
            FileNotFoundError: When KML file does not exist
            ValueError: When KML file format is invalid
        """
        if not os.path.exists(kml_file_path) and kml_file_path.endswith('.xml'):
            alt = kml_file_path[:-4] + '.kml'
            if os.path.exists(alt):
                kml_file_path = alt
        self.location_finder = LocationFinder(kml_file_path)
        
        # Set image files base path
        if images_base_path is None:
            # Auto-infer image path (assume files folder in same directory as KML file)
            kml_dir = os.path.dirname(kml_file_path)
            self.images_base_path = os.path.join(kml_dir, 'files')
        else:
            self.images_base_path = images_base_path
            
        # Cache loaded images to improve performance
        self._image_cache = {}
        # Set image cache directory
        self._image_cache_dir = get_cache_dir('images')
        
        print(f"Light pollution analyzer initialization completed")
        print(f"Images base path: {self.images_base_path}")
    
    def get_light_pollution_color(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Get light pollution color values based on coordinates
        
        Args:
            latitude: Latitude
            longitude: Longitude
            
        Returns:
            Dictionary containing light pollution information, None if not found
            Dictionary contains the following keys:
            - 'rgb': RGB color value tuple (r, g, b)
            - 'hex': Hexadecimal color value
            - 'brightness': Brightness value (0-255)
            - 'pollution_level': Pollution level description
            - 'overlay_name': Corresponding overlay name
            - 'coordinates': Input coordinate information
        
        Raises:
            ValueError: When coordinates are invalid
        """
        # Validate coordinate validity
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, current value: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, current value: {longitude}")
        
        # Find corresponding GroundOverlay
        overlay = self.location_finder.find_overlay_by_coordinates(latitude, longitude)
        if overlay is None:
            return None
        
        # Extract color information from image
        color_info = self._extract_color_from_image(overlay, latitude, longitude)
        if color_info is None:
            return None
        
        # Add additional information
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
        base_stats = self.location_finder.get_statistics()
        
        return {
            **base_stats,
            'images_base_path': self.images_base_path,
            'cached_images': len(self._image_cache),
            'images_directory_exists': os.path.exists(self.images_base_path)
        }
    
    def clear_image_cache(self) -> None:
        """Clear image cache
        
        Used to free memory, especially after processing large amounts of images.
        Clears both memory cache and disk cache.
        """
        # 清除内存缓存
        for image in self._image_cache.values():
            if hasattr(image, 'close'):
                image.close()
        
        self._image_cache.clear()
        
        # 清除磁盘缓存
        try:
            import shutil
            if self._image_cache_dir.exists():
                shutil.rmtree(self._image_cache_dir)
                self._image_cache_dir.mkdir(exist_ok=True)
            print("Image cache cleared (including disk cache)")
        except Exception as e:
            print(f"Error clearing disk cache: {e}")
            print("Memory cache cleared")
    
    def batch_analyze_coordinates(self, coordinates_list: list) -> list:
        """Batch analyze light pollution information for multiple coordinates
        
        Args:
            coordinates_list: List of coordinates, each element is a (latitude, longitude) tuple
            
        Returns:
            List of analysis results, each element contains coordinates and corresponding light pollution information
        """
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
    
    def get_light_pollution_images_in_bounds(self, north: float, south: float, 
                                           east: float, west: float) -> list:
        """Get light pollution image data within specified geographic boundaries
        
        Args:
            north: North boundary latitude
            south: South boundary latitude  
            east: East boundary longitude
            west: West boundary longitude
            
        Returns:
            List containing image information, each element contains:
            - 'overlay': GroundOverlay object
            - 'image_path': Image file path
            - 'image_data': Base64 encoded image data
            - 'bounds': Geographic boundaries of the image
            - 'exists': Whether the image file exists
        """
        results = []
        
        # 获取与指定边界相交的所有覆盖层
        overlapping_overlays = self.location_finder.find_overlays_in_bounds(
            north, south, east, west
        )
        
        for overlay in overlapping_overlays:
            try:
                # 获取图像文件路径
                image_filename = os.path.basename(overlay.icon.href)
                image_path = os.path.join(self.images_base_path, image_filename)
                
                # 检查文件是否存在
                file_exists = os.path.exists(image_path)
                
                image_data = None
                if file_exists:
                    # 读取图片并转换为base64
                    try:
                        import base64
                        with open(image_path, 'rb') as img_file:
                            image_data = base64.b64encode(img_file.read()).decode('utf-8')
                    except Exception as e:
                        print(f"Failed to read image file {image_path}: {e}")
                        image_data = None
                
                # 构建结果
                result = {
                    'overlay': overlay,
                    'image_path': image_path,
                    'image_data': image_data,
                    'bounds': {
                        'north': overlay.lat_lon_box.north,
                        'south': overlay.lat_lon_box.south,
                        'east': overlay.lat_lon_box.east,
                        'west': overlay.lat_lon_box.west
                    },
                    'exists': file_exists,
                    'name': overlay.name
                }
                
                results.append(result)
                
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