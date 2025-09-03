#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
道路连通性检测模块
用于检测指定坐标点是否有道路可以到达
"""

import os
import pickle
import osmnx as ox
import networkx as nx
from typing import Tuple, Optional
from typing import List, Dict, Tuple, Optional
import logging
from geopy.distance import geodesic
from dataclasses import dataclass
try:
    from .cache_config import get_cache_dir, setup_osmnx_cache
    from .stargazing_place_finder import LocationCache, Location
except ImportError:
    from cache_config import get_cache_dir, setup_osmnx_cache
    from stargazing_place_finder import LocationCache, Location

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RoadAccessInfo:
    """道路连通性信息"""
    latitude: float = 0.0
    longitude: float = 0.0
    is_road_accessible: bool = False #  是否有到最近道路的路径
    network_nodes_count: int = 0 # 最近道路网络节点数量
    nearest_road_type: Optional[str] = None # 最近道路类型
    distance_to_road_km: Optional[float] = None # 到最近道路的距离（公里）
    error: Optional[str] = None # 错误信息

class RoadAccessInfoCache(LocationCache):
    def __init__(self,  cache_expiry_hours: int = 24):
        super().__init__(cache_expiry_hours)

    def save_road_access_info_to_cache(self, location_type: str, data: List[RoadAccessInfo]):
        """
        将查询结果保存到缓存
        
        Args:
            location_type: 地点类型
            data: 查询结果数据
        """
        cache_key = self._generate_cache_key(location_type)
        cache_file = self._get_cache_file_path(cache_key)
        cached_data = self.get_cached_result(location_type)
        if cached_data is None or not isinstance(cached_data, list):
            cached_data = data
        else:
            for item in data:
                if item not in cached_data:
                    cached_data.append(item)
        self.cache_mem_data[location_type] = cached_data
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(cached_data, f)
            logger.info(f"💾 查询结果已缓存: {len(data)} 条记录")
        except Exception as e:
            logger.error(f"⚠️ 保存缓存失败: {e}")

    def get_cached_result(self, location_type: str) -> Optional[List[RoadAccessInfo]]:
        """
        从缓存中获取查询结果
        
        Args:
            location_type: 地点类型
            
        Returns:
            缓存的查询结果，如果没有有效缓存则返回None
        """
        if location_type in self.cache_mem_data:
            return self.cache_mem_data[location_type]
        
        cache_key = self._generate_cache_key(location_type)
        cache_file = self._get_cache_file_path(cache_key)
        
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    logger.info(f"✅ 从缓存加载数据: {len(cached_data)} 条记录")
                    return cached_data
            except Exception as e:
                logger.error(f"⚠️ 读取缓存文件失败: {e}")
                # 删除损坏的缓存文件
                try:
                    cache_file.unlink()
                except:
                    pass
        
        return None
    
    def get_location_by_coordinates(self, cache_data: List[RoadAccessInfo], latitude: float, longitude: float, tolerance: float = 0.001) -> Optional[RoadAccessInfo]:
        """
        根据地点类型和经纬度坐标从缓存中查找特定地点
        
        Args:
            cache_data: 缓存数据
            latitude: 纬度
            longitude: 经度
            tolerance: 坐标匹配容差，默认0.001度（约100米）
            
        Returns:
            匹配的地点对象，如果未找到则返回None
        """
        if cache_data is None:
            return None
        for location in cache_data:
            if abs(location.latitude - latitude) <= tolerance and abs(location.longitude - longitude) <= tolerance:
                return location
        return None
class RoadConnectivityChecker:
    """
    道路连通性检测器
    用于检测指定坐标是否有道路网络连接
    """
    
    def __init__(self, search_radius_km: float = 10.0):
        """
        初始化道路连通性检测器
        
        Args:
            search_radius_km: 搜索半径（公里），默认10公里
        """
        self.search_radius_km = search_radius_km
        self.graph_cache = {}  # 缓存已下载的道路网络
        
        # 设置OSMnx缓存目录
        setup_osmnx_cache()
        
        # 设置道路网络缓存目录
        self._road_cache_dir = get_cache_dir('road_networks')
        self.location_cache = RoadAccessInfoCache()
    
    def is_road_accessible(self, lat: float, lon: float, 
                          network_type: str = 'drive') -> bool:
        """
        检测指定坐标是否有道路可以到达
        
        Args:
            lat: 纬度
            lon: 经度
            network_type: 网络类型 ('drive', 'walk', 'bike', 'all')
            
        Returns:
            bool: True表示可达，False表示不可达
        """
        def process_and_return(res):
            # 不再使用Location对象保存道路连通性信息，因为RoadAccessInfo更适合
            road_info = RoadAccessInfo(latitude=lat, longitude=lon, is_road_accessible=res)
            self.location_cache.save_road_access_info_to_cache(f"accessible_{network_type}", [road_info])
            return res
        try:
            # 尝试获取该点周围的道路网络
            cached_results = self.location_cache.get_cached_result(f"accessible_{network_type}")
            if cached_results is not None:
                logger.info("Read road accessible from cache")
                cache = self.location_cache.get_location_by_coordinates(cached_results, lat, lon)
                if cache is not None:
                    return cache.is_road_accessible


            logger.info("Not found in cache, try to download")
            graph = self._get_road_network(lat, lon, network_type)
            
            if graph is None or len(graph.nodes()) == 0:
                logger.warning(f"坐标 ({lat}, {lon}) 周围没有找到道路网络")
                return process_and_return(False)
            
            # 查找最近的道路节点
            nearest_node = ox.distance.nearest_nodes(graph, lon, lat)
            
            if nearest_node is None:
                logger.warning(f"坐标 ({lat}, {lon}) 附近没有找到道路节点")
                return process_and_return(False)
            
            # 检查最近节点的距离
            node_data = graph.nodes[nearest_node]
            node_lat, node_lon = node_data['y'], node_data['x']
            distance_km = geodesic((lat, lon), (node_lat, node_lon)).kilometers
            
            # 如果最近的道路节点距离过远，认为不可达
            max_distance_km = min(self.search_radius_km / 2, 5.0)  # 最大距离不超过5公里
            if distance_km > max_distance_km:
                logger.info(f"坐标 ({lat}, {lon}) 距离最近道路 {distance_km:.2f}km，超过阈值 {max_distance_km}km")
                return process_and_return(False)
            
            logger.info(f"坐标 ({lat}, {lon}) 可达，距离最近道路 {distance_km:.2f}km")
            self.location_cache.save_to_cache(network_type, True)
            return process_and_return(True)
            
        except Exception as e:
            logger.error(f"检测坐标 ({lat}, {lon}) 可达性时出错: {str(e)}")
            return False
    
    def _get_road_network(self, lat: float, lon: float, 
                         network_type: str) -> Optional[nx.MultiDiGraph]:
        """
        获取指定坐标周围的道路网络
        
        Args:
            lat: 纬度
            lon: 经度
            network_type: 网络类型
            
        Returns:
            道路网络图，如果获取失败返回None
        """
        cache_key = f"{lat:.4f}_{lon:.4f}_{network_type}_{self.search_radius_km}"
        
        # 检查缓存
        if cache_key in self.graph_cache:
            logger.debug(f"使用缓存的道路网络: {cache_key}")
            return self.graph_cache[cache_key]
        
        try:
            logger.info(f"下载坐标 ({lat}, {lon}) 周围 {self.search_radius_km}km 的道路网络")
            
            # 下载道路网络
            graph = ox.graph_from_point(
                (lat, lon), 
                dist=self.search_radius_km * 1000,  # 转换为米
                network_type=network_type,
                simplify=True
            )
            
            # 缓存结果
            self.graph_cache[cache_key] = graph
            logger.info(f"成功下载道路网络，包含 {len(graph.nodes())} 个节点")
            
            return graph
            
        except Exception as e:
            logger.error(f"下载道路网络失败: {str(e)}")
            return None
    
    def batch_check_accessibility(self, coordinates: list, 
                                 network_type: str = 'drive') -> list:
        """
        批量检测多个坐标的道路可达性
        
        Args:
            coordinates: 坐标列表，格式为 [(lat1, lon1), (lat2, lon2), ...]
            network_type: 网络类型
            
        Returns:
            list: 可达性结果列表，对应输入坐标的顺序
        """
        results = []
        
        for i, (lat, lon) in enumerate(coordinates):
            logger.info(f"检测第 {i+1}/{len(coordinates)} 个坐标: ({lat}, {lon})")
            accessible = self.is_road_accessible(lat, lon, network_type)
            results.append(accessible)
        
        accessible_count = sum(results)
        logger.info(f"批量检测完成: {accessible_count}/{len(coordinates)} 个坐标可达")
        
        return results
    
    def get_accessibility_info(self, lat: float, lon: float, 
                              network_type: str = 'drive') -> dict:
        """
        获取详细的可达性信息
        
        Args:
            lat: 纬度
            lon: 经度
            network_type: 网络类型
            
        Returns:
            dict: 包含可达性和详细信息的字典
        """
        result = {
            'accessible': False,
            'distance_to_road_km': None,
            'nearest_road_type': None,
            'network_nodes_count': 0,
            'error': None
        }
        
        try:
            cached_res = self.location_cache.get_cached_result(f"access_info_{network_type}")
            cache = self.location_cache.get_location_by_coordinates(cached_res, lat, lon)
            if cache is not None:
                result['accessible'] = cache.is_road_accessible
                result['distance_to_road_km'] = cache.distance_to_road_km
                result['nearest_road_type'] = cache.nearest_road_type
                result['network_nodes_count'] = cache.network_nodes_count
                result['error'] = cache.error
                print("Read road accessible info from cache")
                return result
            else:
                print("No road accessible info in cache")
            
            graph = self._get_road_network(lat, lon, network_type)
            
            if graph is None or len(graph.nodes()) == 0:
                result['error'] = '无法获取道路网络数据'
                return result
            
            result['network_nodes_count'] = len(graph.nodes())
            
            # 查找最近的道路节点
            nearest_node = ox.distance.nearest_nodes(graph, lon, lat)
            
            if nearest_node is not None:
                node_data = graph.nodes[nearest_node]
                node_lat, node_lon = node_data['y'], node_data['x']
                distance_km = geodesic((lat, lon), (node_lat, node_lon)).kilometers
                
                result['distance_to_road_km'] = distance_km
                result['accessible'] = distance_km <= min(self.search_radius_km / 2, 5.0)
                
                # 尝试获取道路类型信息
                edges = graph.edges(nearest_node, data=True)
                if edges:
                    edge_data = list(edges)[0][2]
                    result['nearest_road_type'] = edge_data.get('highway', 'unknown')
                    result['error'] = None

            cache = RoadAccessInfo(is_road_accessible=result['accessible'], 
                                   distance_to_road_km=result['distance_to_road_km'],
                     nearest_road_type=result['nearest_road_type'],
                     network_nodes_count=result['network_nodes_count'],
                     error=result['error'],
                     latitude=lat,
                     longitude=lon)
            self.location_cache.save_road_access_info_to_cache(f"access_info_{network_type}", [cache])
            
        except Exception as e:
            result['error'] = str(e)
        
        return result


def simple_road_check(lat: float, lon: float) -> bool:
    """
    简单的道路连通性检测函数
    
    Args:
        lat: 纬度
        lon: 经度
        
    Returns:
        bool: True表示可达，False表示不可达
    """
    checker = RoadConnectivityChecker(search_radius_km=5.0)
    return checker.is_road_accessible(lat, lon)


if __name__ == "__main__":
    # 示例用法
    checker = RoadConnectivityChecker(search_radius_km=10.0)
    
    # 测试一些坐标
    test_coordinates = [
        (39.9042, 116.4074),  # 北京天安门
        (31.2304, 121.4737),  # 上海外滩
        (90.0, 0.0),          # 北极点（应该不可达）
    ]
    
    for lat, lon in test_coordinates:
        print(f"\n检测坐标 ({lat}, {lon}):")
        info = checker.get_accessibility_info(lat, lon)
        print(f"可达性: {info['accessible']}")
        if info['distance_to_road_km'] is not None:
            print(f"距离最近道路: {info['distance_to_road_km']:.2f} km")
        if info['error']:
            print(f"错误: {info['error']}")