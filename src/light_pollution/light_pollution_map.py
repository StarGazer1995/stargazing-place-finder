#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染地图可视化模块

这个模块提供了在真实地图上可视化光污染数据的功能，使用folium库生成交互式地图。
"""

import os
import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
import folium
from folium import plugins
from scipy.interpolate import griddata
from scipy import ndimage
from .light_pollution_analyzer import LightPollutionAnalyzer
from ..location_finder.location_finder import LocationFinder


class LightPollutionMap:
    """
    光污染地图可视化类
    
    使用folium库在真实地图上展示光污染数据，支持热力图、标记点、等高线等多种展示方式。
    """
    
    def __init__(self, kml_file_path: str):
        """
        初始化光污染地图可视化器
        
        Args:
            kml_file_path: KML文件路径
        """
        self.location_finder = LocationFinder(kml_file_path)
        self.analyzer = LightPollutionAnalyzer(kml_file_path)
        
        # 波特尔光污染分类颜色映射 - 降低饱和度的柔和色彩
        self.pollution_colors = {
            1: '#1a1a2e',  # 深蓝灰 - Class 1: 极佳暗夜天空
            2: '#16213e',  # 深蓝 - Class 2: 典型真正暗夜地点
            3: '#0f3460',  # 中蓝 - Class 3: 乡村天空
            4: '#0e4b99',  # 蓝色 - Class 4: 乡村/郊区过渡
            5: '#2e8b57',  # 海绿 - Class 5: 郊区天空
            6: '#8b7355',  # 棕褐 - Class 6: 明亮郊区天空
            7: '#cd853f',  # 秘鲁色 - Class 7: 郊区/城市过渡
            8: '#d2691e',  # 巧克力橙 - Class 8: 城市天空
            9: '#8b4513'   # 马鞍棕 - Class 9: 内城市天空
        }
    
    def _add_color_legend(self, m: folium.Map) -> None:
        """
        在地图右下角添加现代化颜色标尺
        """
        # 生成现代化颜色标尺HTML
        legend_items = []
        level_descriptions = {
            1: '极佳暗夜', 2: '真正暗夜', 3: '乡村天空', 4: '乡郊过渡', 5: '郊区天空',
            6: '明亮郊区', 7: '郊城过渡', 8: '城市天空', 9: '内城天空'
        }
        
        for level in sorted(self.pollution_colors.keys()):
            color = self.pollution_colors[level]
            desc = level_descriptions.get(level, f'等级{level}')
            legend_items.append(
                f'<div style="display: flex; align-items: center; margin: 8px 0; padding: 4px 0;">'
                f'<div style="width: 16px; height: 16px; background-color: {color}; '
                f'border-radius: 50%; margin-right: 10px; border: 1px solid rgba(0,0,0,0.2);"></div>'
                f'<span style="font-size: 13px; color: #333;">等级 {level} - {desc}</span></div>'
            )
        
        legend_html = f"""
        <div style="position: fixed; 
                    bottom: 20px; right: 20px; width: 200px; height: auto; 
                    background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,249,250,0.95) 100%);
                    border: 1px solid rgba(0,0,0,0.1); z-index:9999; 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 16px; border-radius: 12px; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08);
                    backdrop-filter: blur(10px);">
        <div style="margin: 0 0 12px 0; font-weight: 600; text-align: center; 
                    font-size: 16px; color: #2c3e50; border-bottom: 2px solid #3498db; 
                    padding-bottom: 8px;">波特尔暗夜分类</div>
        {''.join(legend_items)}
        <div style="margin-top: 12px; padding-top: 8px; border-top: 1px solid rgba(0,0,0,0.1); 
                    font-size: 11px; color: #7f8c8d; text-align: center;">数值越低观星条件越好</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两个地理坐标之间的距离（公里）
        
        Args:
            lat1, lon1: 第一个点的纬度和经度
            lat2, lon2: 第二个点的纬度和经度
            
        Returns:
            距离（公里）
        """
        R = 6371  # 地球半径（公里）
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _generate_grid_coordinates(self, center_lat: float, center_lon: float, 
                                 radius_km: float, grid_size: int) -> List[Tuple[float, float]]:
        """
        在指定半径内生成网格坐标
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 半径（公里）
            grid_size: 网格大小
            
        Returns:
            坐标列表
        """
        # 计算经纬度范围
        lat_range = radius_km / 111.0  # 1度纬度约等于111公里
        lon_range = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        
        coordinates = []
        
        for i in range(grid_size):
            for j in range(grid_size):
                # 计算网格点坐标
                lat_offset = (i - grid_size // 2) * (2 * lat_range / grid_size)
                lon_offset = (j - grid_size // 2) * (2 * lon_range / grid_size)
                
                lat = center_lat + lat_offset
                lon = center_lon + lon_offset
                
                # 检查是否在半径范围内
                distance = self._calculate_distance(center_lat, center_lon, lat, lon)
                if distance <= radius_km:
                    coordinates.append((lat, lon))
        
        return coordinates
    
    def _smooth_heat_data(self, heat_data: List[List[float]]) -> List[List[float]]:
        """
        对热力图数据进行平滑处理
        
        Args:
            heat_data: 原始热力图数据 [[lat, lon, intensity], ...]
            
        Returns:
            平滑处理后的热力图数据
        """
        if len(heat_data) < 10:
            return heat_data
            
        try:
            # 提取坐标和强度值
            lats = [point[0] for point in heat_data]
            lons = [point[1] for point in heat_data]
            intensities = [point[2] for point in heat_data]
            
            # 创建网格进行插值
            lat_min, lat_max = min(lats), max(lats)
            lon_min, lon_max = min(lons), max(lons)
            
            # 创建更密集的网格
            grid_resolution = 50
            lat_grid = np.linspace(lat_min, lat_max, grid_resolution)
            lon_grid = np.linspace(lon_min, lon_max, grid_resolution)
            lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)
            
            # 使用cubic插值方法进行数据插值
            points = np.array([[lat, lon] for lat, lon in zip(lats, lons)])
            values = np.array(intensities)
            
            interpolated = griddata(points, values, (lat_mesh, lon_mesh), method='cubic', fill_value=0)
            
            # 应用高斯滤波进行平滑
            smoothed = ndimage.gaussian_filter(interpolated, sigma=1.5)
            
            # 将平滑后的网格数据转换回点数据
            smoothed_data = []
            for i in range(grid_resolution):
                for j in range(grid_resolution):
                    if smoothed[i, j] > 0:  # 只保留有效值
                        smoothed_data.append([lat_mesh[i, j], lon_mesh[i, j], smoothed[i, j]])
            
            print(f"Data smoothing completed, expanded from {len(heat_data)} points to {len(smoothed_data)} smooth points")
            return smoothed_data
            
        except Exception as e:
            print(f"Data smoothing failed: {str(e)}, using original data")
            return heat_data
    
    def _add_heatmap_layer(self, m: folium.Map, heat_data: List[List[float]], 
                          center_lat: float, center_lon: float, radius_km: float) -> None:
        """
        添加热力图图层到地图
        
        Args:
            m: folium地图对象
            heat_data: 热力图数据 [[lat, lon, intensity], ...]
            center_lat: 中心纬度
            center_lon: 中心经度
            radius_km: 半径（公里）
        """
        try:
            if len(heat_data) < 1:  # 至少需要1个点才能生成热力图
                print("Insufficient data points, cannot generate heatmap")
                return
            
            print(f"Starting to generate heatmap, number of data points: {len(heat_data)}")
            
            # 对数据进行平滑处理
            smoothed_data = self._smooth_heat_data(heat_data)
            
            # 提取坐标和强度值
            intensities = np.array([point[2] for point in smoothed_data])
            print(f"Intensity range: {intensities.min():.2f} - {intensities.max():.2f}")
            
            # 准备热力图数据 - folium HeatMap需要 [lat, lon, weight] 格式
            heatmap_data = [[point[0], point[1], point[2]] for point in smoothed_data]
            
            # 添加热力图图层到地图 - 使用波特尔分类的低饱和度颜色
            heatmap = plugins.HeatMap(
                heatmap_data,
                min_opacity=0.05,  # 大幅降低透明度，确保在最小缩放下底图清晰
                max_zoom=20,       # 增加最大缩放级别
                radius=50,         # 增大半径以增强数据点之间的平滑过渡
                blur=15,           # 增加模糊度以实现更好的数据平滑效果
                gradient={
                    0.0: '#4a5568',  # 浅灰蓝 - 极佳暗夜（低光污染）
                    0.15: '#2d3748', # 深灰 - 真正暗夜
                    0.25: '#2c5282', # 浅蓝 - 乡村天空
                    0.35: '#3182ce', # 中蓝 - 乡郊过渡
                    0.45: '#38a169', # 浅绿 - 郊区天空
                    0.55: '#d69e2e', # 浅黄 - 明亮郊区
                    0.7: '#dd6b20',  # 浅橙 - 郊城过渡
                    0.85: '#e53e3e', # 浅红 - 城市天空
                    1.0: '#9c4221'   # 深棕 - 内城天空（高光污染）
                }
            )
            
            # 将热力图添加到地图
            heatmap.add_to(m)
            
            print(f"Heatmap layer added, containing {len(heatmap_data)} data points")
            
        except Exception as e:
            print(f"Error generating heatmap: {str(e)}")
    
    def _create_filled_contours_from_data(self, m: folium.Map, lon_mesh, lat_mesh, interpolated, levels, colors):
        """
        备用方案：基于插值数据创建平滑的等高线填充区域
        使用凸包算法创建更自然的等高线形状
        
        Args:
            m: folium地图对象
            lon_mesh: 经度网格
            lat_mesh: 纬度网格
            interpolated: 插值后的强度数据
            levels: 等高线级别
            colors: 颜色列表
        """
        print("Using backup solution: creating smooth contour fill areas based on data")
        
        try:
            from scipy.spatial import ConvexHull
            
            # 为每个级别创建平滑的填充区域
            for i in range(len(levels) - 1):
                if i < len(colors):
                    color = colors[i]
                    level_min = levels[i]
                    level_max = levels[i + 1] if i + 1 < len(levels) else levels[i] + 0.1
                    
                    # 找到在这个级别范围内的点
                    mask = (interpolated >= level_min) & (interpolated < level_max)
                    if np.any(mask):
                        # 获取这些点的坐标
                        lat_points = lat_mesh[mask]
                        lon_points = lon_mesh[mask]
                        
                        if len(lat_points) >= 3:  # 至少需要3个点才能形成凸包
                            try:
                                # 组合坐标点
                                points = np.column_stack((lon_points, lat_points))
                                
                                # 计算凸包
                                hull = ConvexHull(points)
                                
                                # 获取凸包的顶点坐标（注意folium需要[lat, lon]格式）
                                hull_coords = [[points[vertex][1], points[vertex][0]] for vertex in hull.vertices]
                                
                                # 创建多边形填充区域（无边框）
                                folium.Polygon(
                                    locations=hull_coords,
                                    color=color,
                                    weight=0,  # 设置边框宽度为0
                                    opacity=0,  # 设置边框透明度为0
                                    fillColor=color,
                                    fillOpacity=0.3,
                                    popup=f'光污染强度: {level_min:.2f} - {level_max:.2f}'
                                ).add_to(m)
                                print(f"Added convex hull fill area for level {i}, color: {color}, vertices: {len(hull_coords)}")
                                
                            except Exception as hull_error:
                                print(f"Convex hull calculation failed, using bounding box: {str(hull_error)}")
                                # 如果凸包计算失败，回退到边界框
                                self._create_bounding_box_contour(m, lat_points, lon_points, color, level_min, level_max, i)
                        else:
                            print(f"Insufficient points for level {i}, using bounding box")
                            # 点数不足时使用边界框
                            self._create_bounding_box_contour(m, lat_points, lon_points, color, level_min, level_max, i)
                            
        except ImportError:
            print("scipy.spatial.ConvexHull not available, using simplified solution")
            # 如果没有scipy，使用简化的边界框方案
            self._create_simplified_contours(m, lon_mesh, lat_mesh, interpolated, levels, colors)
        except Exception as e:
            print(f"Error creating fill areas with backup solution: {str(e)}")
    
    def _create_bounding_box_contour(self, m: folium.Map, lat_points, lon_points, color: str, 
                                   level_min: float, level_max: float, level_index: int) -> None:
        """
        创建边界框等高线填充区域（当凸包计算失败时的备用方案）
        
        Args:
            m: folium地图对象
            lat_points: 纬度点数组
            lon_points: 经度点数组
            color: 填充颜色
            level_min: 最小强度值
            level_max: 最大强度值
            level_index: 级别索引
        """
        if len(lat_points) > 0:
            # 计算边界框，但添加一些平滑处理
            lat_min, lat_max = lat_points.min(), lat_points.max()
            lon_min, lon_max = lon_points.min(), lon_points.max()
            
            # 添加小的边距使形状更自然
            lat_margin = (lat_max - lat_min) * 0.1
            lon_margin = (lon_max - lon_min) * 0.1
            
            # 创建稍微圆润的矩形（8个点而不是4个点）
            coords = [
                [lat_min - lat_margin, lon_min],
                [lat_min - lat_margin, lon_max],
                [lat_min, lon_max + lon_margin],
                [lat_max, lon_max + lon_margin],
                [lat_max + lat_margin, lon_max],
                [lat_max + lat_margin, lon_min],
                [lat_max, lon_min - lon_margin],
                [lat_min, lon_min - lon_margin]
            ]
            
            folium.Polygon(
                locations=coords,
                color=color,
                weight=0,  # 设置边框宽度为0
                opacity=0,  # 设置边框透明度为0
                fillColor=color,
                fillOpacity=0.3,
                popup=f'光污染强度: {level_min:.2f} - {level_max:.2f}'
            ).add_to(m)
            print(f"Added bounding box fill area for level {level_index}, color: {color}")
    
    def _create_simplified_contours(self, m: folium.Map, lon_mesh, lat_mesh, interpolated, levels, colors):
        """
        简化的等高线创建方案（当scipy不可用时）
        
        Args:
            m: folium地图对象
            lon_mesh: 经度网格
            lat_mesh: 纬度网格
            interpolated: 插值后的强度数据
            levels: 等高线级别
            colors: 颜色列表
        """
        print("Using simplified contour solution")
        
        for i in range(len(levels) - 1):
            if i < len(colors):
                color = colors[i]
                level_min = levels[i]
                level_max = levels[i + 1] if i + 1 < len(levels) else levels[i] + 0.1
                
                # 找到在这个级别范围内的点
                mask = (interpolated >= level_min) & (interpolated < level_max)
                if np.any(mask):
                    lat_points = lat_mesh[mask]
                    lon_points = lon_mesh[mask]
                    
                    self._create_bounding_box_contour(m, lat_points, lon_points, color, level_min, level_max, i)
    
    def _add_simple_filled_contours(self, m: folium.Map, heat_data: List[List[float]], 
                                   center_lat: float, center_lon: float, radius_km: float) -> None:
        """
        添加简单的填充圆形等高线作为备用方案
        
        Args:
            m: folium地图对象
            heat_data: 热力图数据 [[lat, lon, intensity], ...]
            center_lat: 中心纬度
            center_lon: 中心经度
            radius_km: 半径（公里）
        """
        try:
            # 提取强度值并计算等级
            intensities = [point[2] for point in heat_data]
            min_intensity = min(intensities)
            max_intensity = max(intensities)
            
            # 创建5个填充等高线级别
            levels = np.linspace(min_intensity, max_intensity, 5)
            colors = [self.pollution_colors[1], self.pollution_colors[2], self.pollution_colors[3], 
                     self.pollution_colors[4], self.pollution_colors[5]]
            
            # 为每个级别创建填充圆形等高线
            for i, level in enumerate(levels):
                if i < len(colors):
                    # 计算该级别对应的半径（基于强度比例）
                    intensity_ratio = (level - min_intensity) / (max_intensity - min_intensity) if max_intensity > min_intensity else 0.5
                    circle_radius = radius_km * 1000 * (0.3 + 0.7 * intensity_ratio)  # 转换为米
                    
                    folium.Circle(
                        location=[center_lat, center_lon],
                        radius=circle_radius,
                        color=colors[i],
                        weight=0,  # 设置边框宽度为0
                        opacity=0,  # 设置边框透明度为0
                        fill=True,
                        fillColor=colors[i],
                        fillOpacity=0.4,
                        popup=f'光污染强度等级: {level:.2f}'
                    ).add_to(m)
            
            print("Added simple filled circular contours")
            
        except Exception as e:
            print(f"Error adding simple filled contours: {str(e)}")
    
    def _add_simple_contours(self, m: folium.Map, heat_data: List[List[float]], 
                            center_lat: float, center_lon: float, radius_km: float) -> None:
        """
        添加简单的圆形等高线作为备用方案
        
        Args:
            m: folium地图对象
            heat_data: 热力图数据 [[lat, lon, intensity], ...]
            center_lat: 中心纬度
            center_lon: 中心经度
            radius_km: 半径（公里）
        """
        try:
            # 提取强度值并计算等级
            intensities = [point[2] for point in heat_data]
            min_intensity = min(intensities)
            max_intensity = max(intensities)
            
            # 创建8个等高线级别
            levels = np.linspace(min_intensity, max_intensity, 8)
            colors = [self.pollution_colors[1], self.pollution_colors[2], self.pollution_colors[3], 
                     self.pollution_colors[4], self.pollution_colors[5], self.pollution_colors[6],
                     self.pollution_colors[7], self.pollution_colors[8]]
            
            # 为每个级别创建同心圆等高线
            for i, level in enumerate(levels):
                if i < len(colors):
                    # 计算该级别对应的半径（基于强度比例）
                    intensity_ratio = (level - min_intensity) / (max_intensity - min_intensity) if max_intensity > min_intensity else 0.5
                    circle_radius = radius_km * 1000 * (0.3 + 0.7 * intensity_ratio)  # 转换为米
                    
                    folium.Circle(
                        location=[center_lat, center_lon],
                        radius=circle_radius,
                        color=colors[i],
                        weight=0,  # 设置边框宽度为0
                        opacity=0,  # 设置边框透明度为0
                        fill=False,
                        popup=f'光污染强度等级: {level:.2f}'
                    ).add_to(m)
            
            print("Added simple circular contours")
            
        except Exception as e:
            print(f"Error adding simple contours: {str(e)}")
    
    def _add_custom_styles(self, m: folium.Map) -> None:
        """
        添加自定义CSS样式以改善地图外观
        """
        custom_css = """
        <style>
        /* 全局样式 */
        .leaflet-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
            font-size: 14px !important;
        }
        
        /* 地图控件样式 */
        .leaflet-control-zoom a {
            background: rgba(255, 255, 255, 0.9) !important;
            border: 1px solid rgba(0, 0, 0, 0.1) !important;
            border-radius: 6px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
            transition: all 0.2s ease !important;
        }
        
        .leaflet-control-zoom a:hover {
            background: rgba(255, 255, 255, 1) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        }
        
        /* 弹出窗口样式 */
        .leaflet-popup-content-wrapper {
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 12px !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12) !important;
            backdrop-filter: blur(10px) !important;
        }
        
        .leaflet-popup-content {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
            font-size: 13px !important;
            line-height: 1.5 !important;
            color: #2c3e50 !important;
        }
        
        .leaflet-popup-tip {
            background: rgba(255, 255, 255, 0.95) !important;
        }
        
        /* 地图标题样式 */
        .map-title {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, rgba(52, 152, 219, 0.9) 0%, rgba(41, 128, 185, 0.9) 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 18px;
            font-weight: 600;
            z-index: 9999;
            box-shadow: 0 4px 20px rgba(52, 152, 219, 0.3);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .map-title {
                font-size: 16px;
                padding: 10px 20px;
            }
        }
        </style>
        """
        m.get_root().html.add_child(folium.Element(custom_css))
    
    def create_heatmap(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                      grid_size: int = 100, zoom_start: int = 10, save_path: Optional[str] = None) -> str:
        """
        创建光污染热力图地图
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 分析半径（公里）
            grid_size: 网格大小
            zoom_start: 初始缩放级别
            save_path: 保存路径
            
        Returns:
            地图HTML内容或保存路径
        """
        print(f"Generating heatmap, center point: ({center_lat}, {center_lon}), radius: {radius_km}km")
        
        # 创建基础地图
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles='OpenStreetMap'
        )
        
        # 生成网格坐标
        coordinates = self._generate_grid_coordinates(center_lat, center_lon, radius_km, grid_size)
        
        # 收集热力图数据
        heat_data = []
        valid_points = 0
        
        print(f"Collecting light pollution data for {len(coordinates)} points...")
        
        for i, (lat, lon) in enumerate(coordinates):
            if i % 100 == 0:
                progress = (i / len(coordinates)) * 100
                print(f"Progress: {progress:.1f}% ({i}/{len(coordinates)})")
            
            try:
                result = self.analyzer.get_light_pollution_color(lat, lon)
                if result and 'brightness' in result:
                    # 使用亮度值作为热力图强度
                    intensity = result['brightness'] / 255.0
                    heat_data.append([lat, lon, intensity])
                    valid_points += 1
            except Exception as e:
                continue
        
        print(f"Data collection completed, valid data points: {valid_points}")
        
        if heat_data:
            # 不再添加热力图层，只添加等高线填充
            print(f"Number of data points: {len(heat_data)}")
            print("Will generate contour fill areas")
            
            # 添加等高线填充图层
            self._add_heatmap_layer(m, heat_data, center_lat, center_lon, radius_km)
        else:
            print("Warning: No valid heatmap data points")
        
        # 添加中心点标记
        folium.Marker(
            [center_lat, center_lon],
            popup=f'中心点\n纬度: {center_lat}\n经度: {center_lon}',
            icon=folium.Icon(color='red', icon='star')
        ).add_to(m)
        
        # 添加半径圆圈
        folium.Circle(
            location=[center_lat, center_lon],
            radius=radius_km * 1000,  # 转换为米
            popup=f'分析范围: {radius_km}km',
            color='red',
            fill=False,
            weight=2
        ).add_to(m)
        
        # 添加自定义样式
        self._add_custom_styles(m)
        
        # 添加地图标题
        title_html = f'''
        <div class="map-title">
            光污染热力图 - 半径 {radius_km}km
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        # 添加颜色标尺
        self._add_color_legend(m)
        
        # 保存或返回地图
        if save_path:
            m.save(save_path)
            return f"热力图地图已保存到: {save_path}"
        else:
            return m._repr_html_()
    
    def create_marker_map(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                         sample_points: int = 100, zoom_start: int = 10, 
                         save_path: Optional[str] = None) -> str:
        """
        创建标记点地图，显示采样点的光污染等级
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 分析半径（公里）
            sample_points: 采样点数量
            zoom_start: 初始缩放级别
            save_path: 保存路径
            
        Returns:
            地图HTML内容或保存路径
        """
        print(f"Generating marker map, center point: ({center_lat}, {center_lon}), radius: {radius_km}km")
        
        # 创建基础地图
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles='OpenStreetMap'
        )
        
        # 生成随机采样点
        np.random.seed(42)  # 确保结果可重现
        sample_coords = []
        
        for _ in range(sample_points):
            # 在圆形区域内随机生成点
            angle = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, radius_km)
            
            # 转换为经纬度偏移
            lat_offset = r * np.cos(angle) / 111.0
            lon_offset = r * np.sin(angle) / (111.0 * np.cos(np.radians(center_lat)))
            
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset
            sample_coords.append((lat, lon))
        
        # 分析采样点并添加标记
        valid_points = 0
        pollution_stats = {}
        
        print(f"Analyzing {len(sample_coords)} sample points...")
        
        for i, (lat, lon) in enumerate(sample_coords):
            if i % 20 == 0:
                progress = (i / len(sample_coords)) * 100
                print(f"Progress: {progress:.1f}% ({i}/{len(sample_coords)})")
            
            try:
                result = self.analyzer.get_light_pollution_color(lat, lon)
                if result and 'pollution_level' in result:
                    level = result['pollution_level']
                    color_key = 'blue' if level <= 2 else 'green' if level <= 4 else 'orange' if level <= 6 else 'red'
                    
                    # 创建弹出信息
                    popup_text = f"""
                    <b>光污染信息</b><br>
                    坐标: ({lat:.4f}, {lon:.4f})<br>
                    污染等级: {level}<br>
                    RGB颜色: {result.get('rgb_color', 'N/A')}<br>
                    亮度值: {result.get('brightness', 'N/A')}<br>
                    覆盖层: {result.get('overlay_name', 'N/A')}
                    """
                    
                    # 标记已被移除，仅保留数据统计
                    # folium.CircleMarker(
                    #     location=[lat, lon],
                    #     radius=3,
                    #     popup=popup_text,
                    #     color=self.pollution_colors.get(level, '#808080'),
                    #     fill=True,
                    #     fillColor=self.pollution_colors.get(level, '#808080'),
                    #     fillOpacity=0.4,
                    #     weight=1
                    # ).add_to(m)
                    
                    # 统计
                    pollution_stats[level] = pollution_stats.get(level, 0) + 1
                    valid_points += 1
                    
            except Exception as e:
                continue
        
        print(f"Marker addition completed, valid markers: {valid_points}")
        
        # 添加中心点标记
        folium.Marker(
            [center_lat, center_lon],
            popup=f'中心点\n纬度: {center_lat}\n经度: {center_lon}',
            icon=folium.Icon(color='red', icon='star')
        ).add_to(m)
        
        # 添加半径圆圈
        folium.Circle(
            location=[center_lat, center_lon],
            radius=radius_km * 1000,
            popup=f'分析范围: {radius_km}km',
            color='red',
            fill=False,
            weight=2
        ).add_to(m)
        
        # 添加自定义样式
        self._add_custom_styles(m)
        
        # 添加地图标题
        title_html = f'''
        <div class="map-title">
            光污染标记点地图 - 半径 {radius_km}km
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        # 添加颜色标尺
        self._add_color_legend(m)
        
        # 保存或返回地图
        if save_path:
            m.save(save_path)
            return f"标记点地图已保存到: {save_path}，统计信息: {pollution_stats}"
        else:
            return m._repr_html_()
    
    def create_cluster_map(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                          sample_points: int = 200, zoom_start: int = 10,
                          save_path: Optional[str] = None) -> str:
        """
        创建聚类标记地图，自动聚合相近的标记点
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 分析半径（公里）
            sample_points: 采样点数量
            zoom_start: 初始缩放级别
            save_path: 保存路径
            
        Returns:
            地图HTML内容或保存路径
        """
        print(f"Generating cluster map, center point: ({center_lat}, {center_lon}), radius: {radius_km}km")
        
        # 创建基础地图
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles='OpenStreetMap'
        )
        
        # 创建标记聚类
        marker_cluster = plugins.MarkerCluster().add_to(m)
        
        # 生成随机采样点
        np.random.seed(42)
        sample_coords = []
        
        for _ in range(sample_points):
            angle = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, radius_km)
            
            lat_offset = r * np.cos(angle) / 111.0
            lon_offset = r * np.sin(angle) / (111.0 * np.cos(np.radians(center_lat)))
            
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset
            sample_coords.append((lat, lon))
        
        # 分析采样点并添加到聚类
        valid_points = 0
        pollution_stats = {}
        
        print(f"Analyzing {len(sample_coords)} sample points...")
        
        for i, (lat, lon) in enumerate(sample_coords):
            if i % 50 == 0:
                progress = (i / len(sample_coords)) * 100
                print(f"Progress: {progress:.1f}% ({i}/{len(sample_coords)})")
            
            try:
                result = self.analyzer.get_light_pollution_color(lat, lon)
                if result and 'pollution_level' in result:
                    level = result['pollution_level']
                    
                    # 根据污染等级选择图标颜色
                    if level <= 2:
                        icon_color = 'blue'
                        level_desc = '优秀'
                    elif level <= 4:
                        icon_color = 'green'
                        level_desc = '良好'
                    elif level <= 6:
                        icon_color = 'orange'
                        level_desc = '一般'
                    else:
                        icon_color = 'red'
                        level_desc = '较差'
                    
                    # 创建弹出信息
                    popup_text = f"""
                    <b>光污染分析结果</b><br>
                    坐标: ({lat:.4f}, {lon:.4f})<br>
                    污染等级: {level} ({level_desc})<br>
                    RGB颜色: {result.get('rgb_color', 'N/A')}<br>
                    十六进制: {result.get('hex_color', 'N/A')}<br>
                    亮度值: {result.get('brightness', 'N/A')}<br>
                    覆盖层: {result.get('overlay_name', 'N/A')}
                    """
                    
                    # 聚类标记已被移除，仅保留数据统计
                    # folium.CircleMarker(
                    #     location=[lat, lon],
                    #     radius=2,
                    #     popup=popup_text,
                    #     color=self.pollution_colors.get(level, '#808080'),
                    #     fill=True,
                    #     fillColor=self.pollution_colors.get(level, '#808080'),
                    #     fillOpacity=0.3,
                    #     weight=1
                    # ).add_to(marker_cluster)
                    
                    # 统计
                    pollution_stats[level] = pollution_stats.get(level, 0) + 1
                    valid_points += 1
                    
            except Exception as e:
                continue
        
        print(f"Cluster marker addition completed, valid markers: {valid_points}")
        
        # 添加中心点标记（不加入聚类）
        folium.Marker(
            [center_lat, center_lon],
            popup=f'分析中心点\n纬度: {center_lat}\n经度: {center_lon}\n有效数据点: {valid_points}',
            icon=folium.Icon(color='red', icon='star')
        ).add_to(m)
        
        # 添加半径圆圈
        folium.Circle(
            location=[center_lat, center_lon],
            radius=radius_km * 1000,
            popup=f'分析范围: {radius_km}km',
            color='red',
            fill=False,
            weight=2
        ).add_to(m)
        
        # 添加自定义样式
        self._add_custom_styles(m)
        
        # 添加地图标题
        title_html = f'''
        <div class="map-title">
            光污染聚类地图 - 半径 {radius_km}km
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        # 添加颜色标尺
        self._add_color_legend(m)
        
        # 保存或返回地图
        if save_path:
            m.save(save_path)
            return f"Cluster map saved to: {save_path}, statistics: {pollution_stats}"
        else:
            return m._repr_html_()
    
    def create_comprehensive_map(self, center_lat: float, center_lon: float, 
                               radius_km: float = 10.0, location_name: str = "Unknown Location",
                               output_dir: str = "./map_output") -> Dict[str, str]:
        """
        Create comprehensive map analysis report with multiple map types
        
        Args:
            center_lat: Center point latitude
            center_lon: Center point longitude
            radius_km: Analysis radius (kilometers)
            location_name: Location name
            output_dir: Output directory
            
        Returns:
            Dictionary of save paths for various maps
        """
        print(f"Generating comprehensive map analysis report for {location_name}...")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名前缀
        file_prefix = f"{location_name}_{center_lat}_{center_lon}_{radius_km}km"
        
        results = {}
        
        try:
            # 1. 热力图
            print("\n1. Generating heatmap...")
            heatmap_path = os.path.join(output_dir, f"{file_prefix}_heatmap.html")
            results['heatmap'] = self.create_heatmap(
                center_lat, center_lon, radius_km, 
                grid_size=40, save_path=heatmap_path
            )
            
            # 2. 标记点地图
            print("\n2. Generating marker map...")
            marker_path = os.path.join(output_dir, f"{file_prefix}_markers.html")
            results['markers'] = self.create_marker_map(
                center_lat, center_lon, radius_km,
                sample_points=150, save_path=marker_path
            )
            
            # 3. 聚类地图
            print("\n3. Generating cluster map...")
            cluster_path = os.path.join(output_dir, f"{file_prefix}_cluster.html")
            results['cluster'] = self.create_cluster_map(
                center_lat, center_lon, radius_km,
                sample_points=300, save_path=cluster_path
            )
            
        except Exception as e:
            print(f"Error occurred while generating maps: {e}")
            results['error'] = str(e)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics of the map visualizer
        
        Returns:
            Statistics dictionary
        """
        analyzer_stats = self.analyzer.get_statistics()
        
        return {
            'analyzer_stats': analyzer_stats,
            'available_colors': list(self.pollution_colors.keys()),
            'color_mapping': self.pollution_colors,
            'supported_map_types': ['heatmap', 'markers', 'cluster', 'comprehensive']
        }