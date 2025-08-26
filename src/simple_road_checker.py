#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版道路连通性检测器
专门用于快速判断目的地是否有道路联通
"""

import osmnx as ox
import networkx as nx
from typing import Tuple, Optional
import logging
try:
    from .cache_config import setup_osmnx_cache
except ImportError:
    from cache_config import setup_osmnx_cache

# 配置日志
logging.basicConfig(level=logging.WARNING)
ox.settings.log_console = False

class SimpleRoadChecker:
    """
    简化版道路连通性检测器
    专注于快速判断指定坐标是否有道路可达
    """
    
    def __init__(self, search_radius_km: float = 5.0, max_distance_to_road_km: float = 2.0):
        """
        初始化道路连通性检测器
        
        Args:
            search_radius_km: 搜索半径（公里）
            max_distance_to_road_km: 到道路的最大可接受距离（公里）
        """
        self.search_radius_km = search_radius_km
        self.max_distance_to_road_km = max_distance_to_road_km
        
        # 设置OSMnx缓存目录
        setup_osmnx_cache()
    
    def is_connected(self, lat: float, lon: float) -> bool:
        """
        检测指定坐标是否有道路连通
        
        Args:
            lat: 纬度
            lon: 经度
            
        Returns:
            bool: True表示有道路连通，False表示无道路连通
        """
        try:
            # 下载指定区域的道路网络
            G = ox.graph_from_point(
                (lat, lon), 
                dist=self.search_radius_km * 1000,  # 转换为米
                network_type='drive',
                simplify=True
            )
            
            # 检查网络是否为空
            if len(G.nodes) == 0:
                return False
            
            # 查找最近的道路节点
            nearest_node = ox.nearest_nodes(G, lon, lat)
            
            # 计算到最近道路的距离
            node_data = G.nodes[nearest_node]
            node_lat = node_data['y']
            node_lon = node_data['x']
            
            # 使用简单的距离计算（近似）
            distance_km = self._calculate_distance(lat, lon, node_lat, node_lon)
            
            # 判断是否在可接受的距离范围内
            return distance_km <= self.max_distance_to_road_km
            
        except Exception as e:
            # 如果出现任何错误，认为不可达
            logging.warning(f"检测坐标 ({lat}, {lon}) 时出错: {e}")
            return False
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两点间的近似距离（公里）
        使用简化的球面距离公式
        
        Args:
            lat1, lon1: 第一个点的坐标
            lat2, lon2: 第二个点的坐标
            
        Returns:
            float: 距离（公里）
        """
        import math
        
        # 地球半径（公里）
        R = 6371.0
        
        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # 计算差值
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine公式
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def batch_check(self, coordinates: list) -> list:
        """
        批量检测多个坐标的道路连通性
        
        Args:
            coordinates: 坐标列表，格式为 [(lat1, lon1), (lat2, lon2), ...]
            
        Returns:
            list: 对应的连通性结果列表 [True, False, ...]
        """
        results = []
        for lat, lon in coordinates:
            results.append(self.is_connected(lat, lon))
        return results

# 便捷函数
def quick_road_check(lat: float, lon: float, search_radius_km: float = 5.0) -> bool:
    """
    快速检测指定坐标是否有道路连通的便捷函数
    
    Args:
        lat: 纬度
        lon: 经度
        search_radius_km: 搜索半径（公里），默认5公里
        
    Returns:
        bool: True表示有道路连通，False表示无道路连通
    """
    checker = SimpleRoadChecker(search_radius_km=search_radius_km)
    return checker.is_connected(lat, lon)

def batch_road_check(coordinates: list, search_radius_km: float = 5.0) -> list:
    """
    批量检测多个坐标的道路连通性的便捷函数
    
    Args:
        coordinates: 坐标列表，格式为 [(lat1, lon1), (lat2, lon2), ...]
        search_radius_km: 搜索半径（公里），默认5公里
        
    Returns:
        list: 对应的连通性结果列表 [True, False, ...]
    """
    checker = SimpleRoadChecker(search_radius_km=search_radius_km)
    return checker.batch_check(coordinates)

# 使用示例
if __name__ == "__main__":
    # 测试一些坐标
    test_locations = [
        (40.3242, 116.6312),  # 北京怀柔
        (31.6270, 121.3975),  # 上海崇明岛
        (30.0, 125.0),        # 海上某点（应该不可达）
    ]
    
    print("🛣️  简化版道路连通性检测")
    print("=" * 40)
    
    # 单个检测示例
    print("\n单个检测示例:")
    lat, lon = 40.3242, 116.6312
    result = quick_road_check(lat, lon)
    print(f"坐标 ({lat}, {lon}): {'✅ 可达' if result else '❌ 不可达'}")
    
    # 批量检测示例
    print("\n批量检测示例:")
    results = batch_road_check(test_locations)
    
    for (lat, lon), connected in zip(test_locations, results):
        status = "✅ 可达" if connected else "❌ 不可达"
        print(f"坐标 ({lat}, {lon}): {status}")
    
    print("\n✨ 检测完成！")