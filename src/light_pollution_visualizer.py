#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染可视化模块

该模块提供对指定地点周围光污染数据的可视化功能，包括热力图、等高线图等。
"""

import os
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Circle
from typing import List, Tuple, Dict, Optional, Any
from .light_pollution_analyzer import LightPollutionAnalyzer


class LightPollutionVisualizer:
    """
    光污染可视化器
    
    基于LightPollutionAnalyzer提供光污染数据的可视化功能，
    包括热力图、等高线图、散点图等多种可视化方式。
    """
    
    def __init__(self, kml_file_path: str):
        """
        初始化光污染可视化器
        
        Args:
            kml_file_path: KML文件路径
        """
        self.analyzer = LightPollutionAnalyzer(kml_file_path)
        
        # 光污染等级颜色映射 - 固定颜色标识：1为黑色，7为红色
        self.pollution_colors = {
            'Class 1': '#000000',  # 黑色 - 最佳观星条件
            'Class 2': '#0000FF',  # 蓝色 - 优秀观星条件
            'Class 3': '#00FF00',  # 绿色 - 良好观星条件
            'Class 4': '#FFFF00',  # 黄色 - 一般观星条件
            'Class 5': '#FFA500',  # 橙色 - 较差观星条件
            'Class 6': '#FF4500',  # 橙红色 - 差观星条件
            'Class 7+': '#FF0000', # 红色 - 极差观星条件
            'Unknown': '#AAAAAA'   # 灰色 - 无数据
        }
        
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两个地理坐标之间的距离（公里）
        
        Args:
            lat1, lon1: 第一个点的纬度和经度
            lat2, lon2: 第二个点的纬度和经度
            
        Returns:
            距离（公里）
        """
        # 使用Haversine公式计算球面距离
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
                                 radius_km: float, grid_size: int = 50) -> Tuple[np.ndarray, np.ndarray]:
        """
        生成指定范围内的网格坐标
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 半径（公里）
            grid_size: 网格大小
            
        Returns:
            经度网格和纬度网格
        """
        # 计算经纬度范围（粗略估算）
        lat_range = radius_km / 111.0  # 1度纬度约111公里
        lon_range = radius_km / (111.0 * math.cos(math.radians(center_lat)))  # 经度随纬度变化
        
        # 生成网格
        lats = np.linspace(center_lat - lat_range, center_lat + lat_range, grid_size)
        lons = np.linspace(center_lon - lon_range, center_lon + lon_range, grid_size)
        
        return np.meshgrid(lons, lats)
    
    def _collect_pollution_data(self, center_lat: float, center_lon: float, 
                              radius_km: float, grid_size: int = 50) -> Dict[str, Any]:
        """
        收集指定范围内的光污染数据
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 半径（公里）
            grid_size: 网格大小
            
        Returns:
            包含坐标、亮度值、污染等级等信息的字典
        """
        lon_grid, lat_grid = self._generate_grid_coordinates(center_lat, center_lon, radius_km, grid_size)
        
        brightness_grid = np.full_like(lat_grid, np.nan)
        pollution_levels = []
        valid_coordinates = []
        
        print(f"正在收集 {grid_size}x{grid_size} 网格内的光污染数据...")
        
        total_points = grid_size * grid_size
        processed_points = 0
        
        for i in range(grid_size):
            for j in range(grid_size):
                lat, lon = lat_grid[i, j], lon_grid[i, j]
                
                # 检查是否在指定半径内
                distance = self._calculate_distance(center_lat, center_lon, lat, lon)
                if distance <= radius_km:
                    try:
                        pollution_info = self.analyzer.get_light_pollution_color(lat, lon)
                        if pollution_info:
                            brightness_grid[i, j] = pollution_info['brightness']
                            pollution_levels.append(pollution_info['pollution_level'])
                            valid_coordinates.append((lat, lon, pollution_info))
                    except Exception as e:
                        # 忽略错误，继续处理其他点
                        pass
                
                processed_points += 1
                if processed_points % 500 == 0:
                    progress = (processed_points / total_points) * 100
                    print(f"进度: {progress:.1f}% ({processed_points}/{total_points})")
        
        print(f"数据收集完成，有效数据点: {len(valid_coordinates)}")
        
        return {
            'lon_grid': lon_grid,
            'lat_grid': lat_grid,
            'brightness_grid': brightness_grid,
            'pollution_levels': pollution_levels,
            'valid_coordinates': valid_coordinates,
            'center_lat': center_lat,
            'center_lon': center_lon,
            'radius_km': radius_km
        }
    
    def create_heatmap(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                      grid_size: int = 50, save_path: Optional[str] = None, 
                      show_plot: bool = True) -> str:
        """
        创建光污染热力图
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 半径（公里）
            grid_size: 网格大小
            save_path: 保存路径（可选）
            show_plot: 是否显示图表
            
        Returns:
            图表保存路径或状态信息
        """
        # 收集数据
        data = self._collect_pollution_data(center_lat, center_lon, radius_km, grid_size)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 绘制热力图
        im = ax.contourf(data['lon_grid'], data['lat_grid'], data['brightness_grid'], 
                        levels=20, cmap='YlOrRd', alpha=0.8)
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('光污染亮度值 (0-255)', fontsize=12)
        
        # 标记中心点
        ax.plot(center_lon, center_lat, 'ko', markersize=10, markerfacecolor='blue', 
               markeredgecolor='white', markeredgewidth=2, label='查询中心点')
        
        # 绘制半径圆圈
        # 将公里转换为经纬度（粗略估算）
        lat_radius = radius_km / 111.0
        lon_radius = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        circle = Circle((center_lon, center_lat), max(lat_radius, lon_radius), 
                       fill=False, color='blue', linestyle='--', linewidth=2, 
                       label=f'{radius_km}km 范围')
        ax.add_patch(circle)
        
        # 设置标题和标签
        ax.set_title(f'光污染热力图\n中心点: ({center_lat:.4f}°, {center_lon:.4f}°), 半径: {radius_km}km', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('经度', fontsize=12)
        ax.set_ylabel('纬度', fontsize=12)
        
        # 设置坐标轴
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # 设置坐标轴比例
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            result = f"热力图已保存到: {save_path}"
        else:
            result = "热力图已生成"
        
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return result
    
    def create_contour_map(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                          grid_size: int = 50, save_path: Optional[str] = None, 
                          show_plot: bool = True) -> str:
        """
        创建光污染等高线图
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 半径（公里）
            grid_size: 网格大小
            save_path: 保存路径（可选）
            show_plot: 是否显示图表
            
        Returns:
            图表保存路径或状态信息
        """
        # 收集数据
        data = self._collect_pollution_data(center_lat, center_lon, radius_km, grid_size)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 绘制等高线
        levels = [0, 50, 100, 150, 200, 255]
        contour = ax.contour(data['lon_grid'], data['lat_grid'], data['brightness_grid'], 
                           levels=levels, colors='black', linewidths=1)
        ax.clabel(contour, inline=True, fontsize=10, fmt='%d')
        
        # 绘制填充等高线
        contourf = ax.contourf(data['lon_grid'], data['lat_grid'], data['brightness_grid'], 
                             levels=levels, cmap='YlOrRd', alpha=0.6)
        
        # 添加颜色条
        cbar = plt.colorbar(contourf, ax=ax, shrink=0.8)
        cbar.set_label('光污染亮度值', fontsize=12)
        
        # 标记中心点
        ax.plot(center_lon, center_lat, 'ko', markersize=10, markerfacecolor='blue', 
               markeredgecolor='white', markeredgewidth=2, label='查询中心点')
        
        # 绘制半径圆圈
        lat_radius = radius_km / 111.0
        lon_radius = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        circle = Circle((center_lon, center_lat), max(lat_radius, lon_radius), 
                       fill=False, color='blue', linestyle='--', linewidth=2, 
                       label=f'{radius_km}km 范围')
        ax.add_patch(circle)
        
        # 设置标题和标签
        ax.set_title(f'光污染等高线图\n中心点: ({center_lat:.4f}°, {center_lon:.4f}°), 半径: {radius_km}km', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('经度', fontsize=12)
        ax.set_ylabel('纬度', fontsize=12)
        
        # 设置坐标轴
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            result = f"等高线图已保存到: {save_path}"
        else:
            result = "等高线图已生成"
        
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return result
    
    def create_scatter_plot(self, center_lat: float, center_lon: float, radius_km: float = 10.0,
                           sample_points: int = 200, save_path: Optional[str] = None, 
                           show_plot: bool = True) -> str:
        """
        创建光污染散点图
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 半径（公里）
            sample_points: 采样点数量
            save_path: 保存路径（可选）
            show_plot: 是否显示图表
            
        Returns:
            图表保存路径或状态信息
        """
        # 生成随机采样点
        coordinates = []
        pollution_data = []
        
        print(f"正在采样 {sample_points} 个随机点...")
        
        attempts = 0
        max_attempts = sample_points * 5  # 最多尝试5倍的点数
        
        while len(coordinates) < sample_points and attempts < max_attempts:
            # 在圆形区域内随机生成点
            angle = np.random.uniform(0, 2 * np.pi)
            r = np.random.uniform(0, radius_km)
            
            # 转换为经纬度偏移
            lat_offset = (r * np.cos(angle)) / 111.0
            lon_offset = (r * np.sin(angle)) / (111.0 * np.cos(math.radians(center_lat)))
            
            lat = center_lat + lat_offset
            lon = center_lon + lon_offset
            
            try:
                pollution_info = self.analyzer.get_light_pollution_color(lat, lon)
                if pollution_info:
                    coordinates.append((lat, lon))
                    pollution_data.append(pollution_info)
            except Exception:
                pass
            
            attempts += 1
            
            if len(coordinates) % 50 == 0 and len(coordinates) > 0:
                print(f"已采样: {len(coordinates)} 个有效点")
        
        if not coordinates:
            return "未找到有效的光污染数据点"
        
        print(f"采样完成，共获得 {len(coordinates)} 个有效数据点")
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 提取数据
        lats = [coord[0] for coord in coordinates]
        lons = [coord[1] for coord in coordinates]
        brightness_values = [data['brightness'] for data in pollution_data]
        
        # 绘制散点图
        scatter = ax.scatter(lons, lats, c=brightness_values, cmap='YlOrRd', 
                           s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
        
        # 添加颜色条
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
        cbar.set_label('光污染亮度值', fontsize=12)
        
        # 标记中心点
        ax.plot(center_lon, center_lat, 'ko', markersize=12, markerfacecolor='blue', 
               markeredgecolor='white', markeredgewidth=3, label='查询中心点')
        
        # 绘制半径圆圈
        lat_radius = radius_km / 111.0
        lon_radius = radius_km / (111.0 * math.cos(math.radians(center_lat)))
        circle = Circle((center_lon, center_lat), max(lat_radius, lon_radius), 
                       fill=False, color='blue', linestyle='--', linewidth=2, 
                       label=f'{radius_km}km 范围')
        ax.add_patch(circle)
        
        # 设置标题和标签
        ax.set_title(f'光污染散点图\n中心点: ({center_lat:.4f}°, {center_lon:.4f}°), 采样点: {len(coordinates)}个', 
                    fontsize=14, fontweight='bold')
        ax.set_xlabel('经度', fontsize=12)
        ax.set_ylabel('纬度', fontsize=12)
        
        # 设置坐标轴
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            result = f"散点图已保存到: {save_path}"
        else:
            result = "散点图已生成"
        
        if show_plot:
            plt.show()
        else:
            plt.close()
        
        return result
    
    def create_comprehensive_report(self, center_lat: float, center_lon: float, 
                                  radius_km: float = 10.0, location_name: str = "查询地点",
                                  output_dir: str = "visualization_output") -> Dict[str, str]:
        """
        创建综合光污染分析报告
        
        Args:
            center_lat: 中心点纬度
            center_lon: 中心点经度
            radius_km: 半径（公里）
            location_name: 地点名称
            output_dir: 输出目录
            
        Returns:
            包含各种图表路径的字典
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名前缀
        safe_name = location_name.replace(' ', '_').replace('/', '_')
        prefix = f"{safe_name}_{center_lat:.4f}_{center_lon:.4f}_{radius_km}km"
        
        results = {}
        
        print(f"正在为 {location_name} 生成综合光污染分析报告...")
        
        # 生成热力图
        print("1/3 生成热力图...")
        heatmap_path = os.path.join(output_dir, f"{prefix}_heatmap.png")
        results['heatmap'] = self.create_heatmap(center_lat, center_lon, radius_km, 
                                                save_path=heatmap_path, show_plot=False)
        
        # 生成等高线图
        print("2/3 生成等高线图...")
        contour_path = os.path.join(output_dir, f"{prefix}_contour.png")
        results['contour'] = self.create_contour_map(center_lat, center_lon, radius_km, 
                                                   save_path=contour_path, show_plot=False)
        
        # 生成散点图
        print("3/3 生成散点图...")
        scatter_path = os.path.join(output_dir, f"{prefix}_scatter.png")
        results['scatter'] = self.create_scatter_plot(center_lat, center_lon, radius_km, 
                                                    save_path=scatter_path, show_plot=False)
        
        print(f"综合报告生成完成！文件保存在: {output_dir}")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取可视化器统计信息
        
        Returns:
            统计信息字典
        """
        analyzer_stats = self.analyzer.get_statistics()
        
        return {
            'analyzer_stats': analyzer_stats,
            'available_colors': list(self.pollution_colors.keys()),
            'color_mapping': self.pollution_colors
        }