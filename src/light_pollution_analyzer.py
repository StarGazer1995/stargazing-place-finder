#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染分析器

这个模块提供了一个光污染分析器类，用于根据地理坐标获取光污染颜色数值。
该类使用LocationFinder的解析结果进行初始化，并提供根据坐标获取光污染信息的功能。
"""

import os
import sys
from typing import Optional, Tuple, Dict, Any
from PIL import Image
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from .location_finder import LocationFinder
    from .kml_parser import GroundOverlay
    from .cache_config import get_cache_dir
except ImportError:
    from location_finder import LocationFinder
    from kml_parser import GroundOverlay
    from cache_config import get_cache_dir


class LightPollutionAnalyzer:
    """光污染分析器
    
    这个类使用LocationFinder的解析结果进行初始化，提供根据地理坐标
    获取光污染颜色数值的功能。通过分析对应的图像文件来获取精确的
    光污染强度信息。
    """
    
    def __init__(self, kml_file_path: str, images_base_path: Optional[str] = None):
        """初始化光污染分析器
        
        Args:
            kml_file_path: KML文件路径
            images_base_path: 图像文件基础路径，如果为None则自动推断
            
        Raises:
            FileNotFoundError: 当KML文件不存在时
            ValueError: 当KML文件格式错误时
        """
        self.location_finder = LocationFinder(kml_file_path)
        
        # 设置图像文件基础路径
        if images_base_path is None:
            # 自动推断图像路径（假设在KML文件同目录下的files文件夹）
            kml_dir = os.path.dirname(kml_file_path)
            self.images_base_path = os.path.join(kml_dir, 'files')
        else:
            self.images_base_path = images_base_path
            
        # 缓存已加载的图像以提高性能
        self._image_cache = {}
        # 设置图像缓存目录
        self._image_cache_dir = get_cache_dir('images')
        
        print(f"光污染分析器初始化完成")
        print(f"图像基础路径: {self.images_base_path}")
    
    def get_light_pollution_color(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """根据坐标获取光污染颜色数值
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            包含光污染信息的字典，如果未找到则返回None
            字典包含以下键：
            - 'rgb': RGB颜色值元组 (r, g, b)
            - 'hex': 十六进制颜色值
            - 'brightness': 亮度值 (0-255)
            - 'pollution_level': 污染等级描述
            - 'overlay_name': 对应的覆盖层名称
            - 'coordinates': 输入的坐标信息
        
        Raises:
            ValueError: 当坐标无效时
        """
        # 验证坐标有效性
        if not (-90 <= latitude <= 90):
            raise ValueError(f"纬度必须在-90到90之间，当前值: {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"经度必须在-180到180之间，当前值: {longitude}")
        
        # 查找对应的GroundOverlay
        overlay = self.location_finder.find_overlay_by_coordinates(latitude, longitude)
        if overlay is None:
            return None
        
        # 从图像中提取颜色信息
        color_info = self._extract_color_from_image(overlay, latitude, longitude)
        if color_info is None:
            return None
        
        # 添加额外信息
        color_info['overlay_name'] = overlay.name
        color_info['coordinates'] = {'latitude': latitude, 'longitude': longitude}
        
        return color_info
    
    def _extract_color_from_image(self, overlay: GroundOverlay, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """从图像文件中提取指定坐标的颜色信息
        
        Args:
            overlay: GroundOverlay对象
            latitude: 纬度
            longitude: 经度
            
        Returns:
            颜色信息字典或None
        """
        try:
            # 获取图像文件路径
            image_filename = os.path.basename(overlay.icon.href)
            image_path = os.path.join(self.images_base_path, image_filename)
            
            # 检查图像文件是否存在
            if not os.path.exists(image_path):
                print(f"警告: 图像文件不存在: {image_path}")
                return self._get_default_color_info()
            
            # 加载图像（使用缓存）
            image = self._load_image_cached(image_path)
            if image is None:
                return self._get_default_color_info()
            
            # 计算图像中对应的像素坐标
            pixel_x, pixel_y = self._geo_to_pixel_coordinates(
                latitude, longitude, overlay, image.size
            )
            
            # 确保像素坐标在图像范围内
            if not (0 <= pixel_x < image.size[0] and 0 <= pixel_y < image.size[1]):
                print(f"警告: 计算的像素坐标超出图像范围: ({pixel_x}, {pixel_y})")
                return self._get_default_color_info()
            
            # 使用双线性插值获取sub-pixel颜色
            pixel_color = self._get_interpolated_color(image, pixel_x, pixel_y)
            
            # 处理不同的图像模式
            if image.mode == 'RGB':
                r, g, b = pixel_color
            elif image.mode == 'RGBA':
                r, g, b, a = pixel_color
            elif image.mode == 'L':  # 灰度图像
                r = g = b = pixel_color
            else:
                # 转换为RGB模式
                rgb_image = image.convert('RGB')
                r, g, b = rgb_image.getpixel((int(pixel_x), int(pixel_y)))
            
            # 计算亮度和污染等级
            brightness = int(0.299 * r + 0.587 * g + 0.114 * b)
            pollution_level = self._calculate_pollution_level(brightness)
            
            return {
                'rgb': (r, g, b),
                'hex': f"#{r:02x}{g:02x}{b:02x}",
                'brightness': brightness,
                'pollution_level': pollution_level
            }
            
        except Exception as e:
            print(f"提取颜色信息时出错: {e}")
            return self._get_default_color_info()
    
    def _load_image_cached(self, image_path: str) -> Optional[Image.Image]:
        """缓存加载图像文件
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            PIL Image对象或None
        """
        # 首先检查内存缓存
        if image_path in self._image_cache:
            return self._image_cache[image_path]
        
        # 生成缓存文件名
        import hashlib
        cache_filename = hashlib.md5(image_path.encode()).hexdigest() + ".pkl"
        cache_file_path = self._image_cache_dir / cache_filename
        
        # 检查磁盘缓存
        if cache_file_path.exists():
            try:
                import pickle
                with open(cache_file_path, 'rb') as f:
                    image = pickle.load(f)
                self._image_cache[image_path] = image
                return image
            except Exception as e:
                print(f"从磁盘缓存加载图像失败 {cache_file_path}: {e}")
                # 删除损坏的缓存文件
                try:
                    cache_file_path.unlink()
                except:
                    pass
        
        # 从原始文件加载图像
        try:
            image = Image.open(image_path)
            # 保存到内存缓存
            self._image_cache[image_path] = image
            
            # 保存到磁盘缓存
            try:
                import pickle
                with open(cache_file_path, 'wb') as f:
                    pickle.dump(image, f)
            except Exception as e:
                print(f"保存图像到磁盘缓存失败 {cache_file_path}: {e}")
            
            return image
        except Exception as e:
            print(f"加载图像失败 {image_path}: {e}")
            return None
    
    def _geo_to_pixel_coordinates(self, latitude: float, longitude: float, 
                                overlay: GroundOverlay, image_size: Tuple[int, int]) -> Tuple[float, float]:
        """将地理坐标转换为图像像素坐标
        
        Args:
            latitude: 纬度
            longitude: 经度
            overlay: GroundOverlay对象
            image_size: 图像尺寸 (width, height)
            
        Returns:
            像素坐标 (x, y)
        """
        box = overlay.lat_lon_box
        
        # 计算相对位置（0-1之间）
        lat_ratio = (latitude - box.south) / (box.north - box.south)
        lon_ratio = (longitude - box.west) / (box.east - box.west)
        
        # 转换为像素坐标
        # 注意：图像的Y轴是从上到下的，所以需要翻转纬度
        pixel_x = lon_ratio * image_size[0]
        pixel_y = (1 - lat_ratio) * image_size[1]
        
        return pixel_x, pixel_y
    
    def _calculate_pollution_level(self, brightness: int) -> str:
        """根据亮度值计算光污染等级
        
        Args:
            brightness: 亮度值 (0-255)
            
        Returns:
            污染等级描述字符串
        """
        if brightness < 32:
            return "极低污染 (Class 1 - 优秀观星条件)"
        elif brightness < 64:
            return "低污染 (Class 2 - 良好观星条件)"
        elif brightness < 96:
            return "轻度污染 (Class 3 - 一般观星条件)"
        elif brightness < 128:
            return "中度污染 (Class 4 - 较差观星条件)"
        elif brightness < 160:
            return "重度污染 (Class 5 - 差观星条件)"
        elif brightness < 192:
            return "严重污染 (Class 6 - 很差观星条件)"
        else:
            return "极重污染 (Class 7+ - 极差观星条件)"
    
    def _get_default_color_info(self) -> Dict[str, Any]:
        """获取默认的颜色信息（当无法从图像中提取时）
        
        Returns:
            默认颜色信息字典
        """
        return {
            'rgb': (128, 128, 128),  # 灰色
            'hex': '#808080',
            'brightness': 128,
            'pollution_level': '未知污染等级'
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取分析器统计信息
        
        Returns:
            统计信息字典
        """
        base_stats = self.location_finder.get_statistics()
        
        return {
            **base_stats,
            'images_base_path': self.images_base_path,
            'cached_images': len(self._image_cache),
            'images_directory_exists': os.path.exists(self.images_base_path)
        }
    
    def clear_image_cache(self) -> None:
        """清除图像缓存
        
        用于释放内存，特别是在处理大量图像后。
        同时清除内存缓存和磁盘缓存。
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
            print("图像缓存已清除（包括磁盘缓存）")
        except Exception as e:
            print(f"清除磁盘缓存时出错: {e}")
            print("内存缓存已清除")
    
    def batch_analyze_coordinates(self, coordinates_list: list) -> list:
        """批量分析多个坐标的光污染信息
        
        Args:
            coordinates_list: 坐标列表，每个元素为 (latitude, longitude) 元组
            
        Returns:
            分析结果列表，每个元素包含坐标和对应的光污染信息
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
        """获取指定地理边界内的光污染图片数据
        
        Args:
            north: 北边界纬度
            south: 南边界纬度  
            east: 东边界经度
            west: 西边界经度
            
        Returns:
            包含图片信息的列表，每个元素包含:
            - 'overlay': GroundOverlay对象
            - 'image_path': 图片文件路径
            - 'image_data': 图片的base64编码数据
            - 'bounds': 图片的地理边界
            - 'exists': 图片文件是否存在
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
                        print(f"读取图片文件失败 {image_path}: {e}")
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
                print(f"处理覆盖层时出错 {overlay.name}: {e}")
                continue
        
        print(f"在指定边界内找到 {len(results)} 个光污染图片")
        return results
    
    def _get_interpolated_color(self, image: Image.Image, x: float, y: float) -> Tuple[int, ...]:
        """使用双线性插值获取sub-pixel位置的颜色值
        
        Args:
            image: PIL图像对象
            x: X坐标（可以是小数）
            y: Y坐标（可以是小数）
            
        Returns:
            插值后的像素颜色值
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
            print(f"双线性插值计算出错: {e}，回退到最近邻插值")
            # 回退到最近邻插值
            return image.getpixel((int(round(x)), int(round(y))))