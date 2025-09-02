#!/usr/bin/env python3
"""
山峰查找器模块
用于在指定地理坐标范围内查找与周围城镇有足够高度差的山峰
"""

import requests
import json
from typing import List, Dict, Tuple, Optional
import math
from dataclasses import dataclass
import time

@dataclass
class Peak:
    """山峰数据类"""
    name: str
    latitude: float
    longitude: float
    elevation: float  # 海拔高度（米）
    prominence: float  # 相对高度（米）
    distance_to_nearest_town: float  # 到最近城镇的距离（公里）
    nearest_town_name: str  # 最近城镇名称
    height_difference: float  # 与最近城镇的高度差（米）

@dataclass
class Observatory:
    """天文台数据类"""
    name: str
    latitude: float
    longitude: float
    elevation: float  # 海拔高度（米）
    observatory_type: str  # 天文台类型
    description: str  # 描述信息
    distance_to_nearest_town: float  # 到最近城镇的距离（公里）
    nearest_town_name: str  # 最近城镇名称
    light_pollution_level: Optional[str] = None  # 光污染等级

class MountainPeakFinder:
    """
    山峰查找器类
    用于查找指定范围内符合条件的山峰
    """
    
    def __init__(self, min_height_difference: float = 100.0):
        """
        初始化山峰查找器
        
        Args:
            min_height_difference: 与周围城镇的最小高度差（米），默认100米
        """
        self.min_height_difference = min_height_difference
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        计算两个地理坐标之间的距离（公里）
        使用Haversine公式
        
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
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_peaks_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        从Overpass API获取指定边界框内的山峰数据
        
        Args:
            bbox: 边界框 (south, west, north, east)
            
        Returns:
            山峰数据列表
        """
        south, west, north, east = bbox
        
        # Overpass QL查询语句
        query = f"""
        [out:json][timeout:25];
        (
          node["natural"="peak"]({south},{west},{north},{east});
          node["natural"="volcano"]({south},{west},{north},{east});
        );
        out geom;
        """
        
        try:
            response = requests.post(self.overpass_url, data=query, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('elements', [])
        except Exception as e:
            print(f"获取山峰数据时出错: {e}")
            return []
    
    def get_towns_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        从Overpass API获取指定边界框内的城镇数据
        
        Args:
            bbox: 边界框 (south, west, north, east)
            
        Returns:
            城镇数据列表
        """
        south, west, north, east = bbox
        
        # Overpass QL查询语句 - 获取城镇、村庄等居住地
        query = f"""
        [out:json][timeout:25];
        (
          node["place"~"^(city|town|village|hamlet)$"]({south},{west},{north},{east});
          way["place"~"^(city|town|village|hamlet)$"]({south},{west},{north},{east});
          relation["place"~"^(city|town|village|hamlet)$"]({south},{west},{north},{east});
        );
        out center geom;
        """
        
        try:
            response = requests.post(self.overpass_url, data=query, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('elements', [])
        except Exception as e:
            print(f"获取城镇数据时出错: {e}")
            return []
    
    def get_observatories_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        从Overpass API获取指定边界框内的天文台数据
        
        Args:
            bbox: 边界框 (south, west, north, east)
            
        Returns:
            天文台数据列表
        """
        south, west, north, east = bbox
        
        # Overpass QL查询语句 - 获取天文台、观测站等
        query = f"""
        [out:json][timeout:25];
        (
          node["man_made"="observatory"]({south},{west},{north},{east});
          way["man_made"="observatory"]({south},{west},{north},{east});
          relation["man_made"="observatory"]({south},{west},{north},{east});
          node["amenity"="planetarium"]({south},{west},{north},{east});
          way["amenity"="planetarium"]({south},{west},{north},{east});
          node["building"="observatory"]({south},{west},{north},{east});
          way["building"="observatory"]({south},{west},{north},{east});
        );
        out center geom;
        """
        
        try:
            response = requests.post(self.overpass_url, data=query, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('elements', [])
        except Exception as e:
            print(f"获取天文台数据时出错: {e}")
            return []
    
    def get_elevation_from_api(self, lat: float, lon: float) -> Optional[float]:
        """
        从高程API获取指定坐标的海拔高度
        使用Open-Elevation API
        
        Args:
            lat: 纬度
            lon: 经度
            
        Returns:
            海拔高度（米），如果获取失败返回None
        """
        try:
            url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results'):
                return data['results'][0].get('elevation')
        except Exception as e:
            print(f"获取海拔数据时出错 ({lat}, {lon}): {e}")
        
        return None
    
    def find_nearest_town(self, peak_lat: float, peak_lon: float, towns: List[Dict]) -> Tuple[Optional[str], float, Optional[float]]:
        """
        查找距离山峰最近的城镇
        
        Args:
            peak_lat: 山峰纬度
            peak_lon: 山峰经度
            towns: 城镇数据列表
            
        Returns:
            (最近城镇名称, 距离(公里), 城镇海拔)
        """
        min_distance = float('inf')
        nearest_town = None
        nearest_town_elevation = None
        
        for town in towns:
            # 获取城镇坐标
            if town['type'] == 'node':
                town_lat = town['lat']
                town_lon = town['lon']
            elif 'center' in town:
                town_lat = town['center']['lat']
                town_lon = town['center']['lon']
            else:
                continue
            
            # 计算距离
            distance = self.calculate_distance(peak_lat, peak_lon, town_lat, town_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest_town = town.get('tags', {}).get('name', '未知城镇')
                # 获取城镇海拔
                nearest_town_elevation = self.get_elevation_from_api(town_lat, town_lon)
                time.sleep(0.1)  # 避免API请求过于频繁
        
        return nearest_town, min_distance, nearest_town_elevation
    
    def find_peaks_in_area(self, bbox: Tuple[float, float, float, float], 
                          max_peaks: int = 50) -> List[Peak]:
        """
        在指定区域内查找符合条件的山峰
        
        Args:
            bbox: 边界框 (south, west, north, east)
            max_peaks: 最大返回山峰数量
            
        Returns:
            符合条件的山峰列表
        """
        print(f"正在搜索区域: {bbox}")
        print(f"最小高度差要求: {self.min_height_difference}米")
        
        # 获取山峰数据
        print("正在获取山峰数据...")
        peaks_data = self.get_peaks_from_overpass(bbox)
        print(f"找到 {len(peaks_data)} 个山峰")
        
        # 获取城镇数据
        print("正在获取城镇数据...")
        towns_data = self.get_towns_from_overpass(bbox)
        print(f"找到 {len(towns_data)} 个城镇")
        
        if not peaks_data or not towns_data:
            print("未找到足够的山峰或城镇数据")
            return []
        
        qualified_peaks = []
        
        for i, peak_data in enumerate(peaks_data[:max_peaks]):
            if i % 10 == 0:
                print(f"处理进度: {i+1}/{min(len(peaks_data), max_peaks)}")
            
            peak_lat = peak_data['lat']
            peak_lon = peak_data['lon']
            peak_name = peak_data.get('tags', {}).get('name', f'山峰_{i+1}')
            
            # 获取山峰海拔
            peak_elevation = None
            if 'tags' in peak_data and 'ele' in peak_data['tags']:
                try:
                    peak_elevation = float(peak_data['tags']['ele'])
                except ValueError:
                    pass
            
            if peak_elevation is None:
                peak_elevation = self.get_elevation_from_api(peak_lat, peak_lon)
                time.sleep(0.1)  # 避免API请求过于频繁
            
            if peak_elevation is None:
                continue
            
            # 查找最近的城镇
            nearest_town, distance_to_town, town_elevation = self.find_nearest_town(
                peak_lat, peak_lon, towns_data
            )
            
            if nearest_town is None or town_elevation is None:
                continue
            
            # 计算高度差
            height_difference = peak_elevation - town_elevation
            
            # 检查是否满足高度差要求
            if height_difference >= self.min_height_difference:
                peak = Peak(
                    name=peak_name,
                    latitude=peak_lat,
                    longitude=peak_lon,
                    elevation=peak_elevation,
                    prominence=height_difference,  # 这里用高度差作为相对高度
                    distance_to_nearest_town=distance_to_town,
                    nearest_town_name=nearest_town,
                    height_difference=height_difference
                )
                qualified_peaks.append(peak)
                print(f"找到符合条件的山峰: {peak_name} (高度差: {height_difference:.1f}m)")
        
        # 按高度差排序
        qualified_peaks.sort(key=lambda p: p.height_difference, reverse=True)
        
        print(f"\n总共找到 {len(qualified_peaks)} 个符合条件的山峰")
        return qualified_peaks
    
    def find_observatories_in_area(self, bbox: Tuple[float, float, float, float], 
                                  max_observatories: int = 50) -> List[Observatory]:
        """
        在指定区域内查找天文台
        
        Args:
            bbox: 边界框 (south, west, north, east)
            max_observatories: 最大返回天文台数量
            
        Returns:
            天文台列表
        """
        print(f"正在搜索天文台区域: {bbox}")
        
        # 获取天文台数据
        print("正在获取天文台数据...")
        observatories_data = self.get_observatories_from_overpass(bbox)
        print(f"找到 {len(observatories_data)} 个天文台")
        
        # 获取城镇数据
        print("正在获取城镇数据...")
        towns_data = self.get_towns_from_overpass(bbox)
        print(f"找到 {len(towns_data)} 个城镇")
        
        if not observatories_data:
            print("未找到天文台数据")
            return []
        
        observatories = []
        
        for i, obs_data in enumerate(observatories_data[:max_observatories]):
            if i % 5 == 0:
                print(f"处理进度: {i+1}/{min(len(observatories_data), max_observatories)}")
            
            # 获取天文台坐标
            if obs_data['type'] == 'node':
                obs_lat = obs_data['lat']
                obs_lon = obs_data['lon']
            elif 'center' in obs_data:
                obs_lat = obs_data['center']['lat']
                obs_lon = obs_data['center']['lon']
            else:
                continue
            
            tags = obs_data.get('tags', {})
            obs_name = tags.get('name', f'天文台_{i+1}')
            
            # 确定天文台类型
            observatory_type = "未知类型"
            if tags.get('man_made') == 'observatory':
                observatory_type = "天文观测台"
            elif tags.get('amenity') == 'planetarium':
                observatory_type = "天象馆"
            elif tags.get('building') == 'observatory':
                observatory_type = "天文台建筑"
            
            # 获取描述信息
            description = tags.get('description', '')
            if not description:
                description = tags.get('note', '')
            if not description:
                description = f"{observatory_type}，位于({obs_lat:.4f}, {obs_lon:.4f})"
            
            # 获取天文台海拔
            obs_elevation = None
            if 'ele' in tags:
                try:
                    obs_elevation = float(tags['ele'])
                except ValueError:
                    pass
            
            if obs_elevation is None:
                obs_elevation = self.get_elevation_from_api(obs_lat, obs_lon)
                time.sleep(0.1)  # 避免API请求过于频繁
            
            if obs_elevation is None:
                obs_elevation = 0.0  # 默认海拔
            
            # 查找最近的城镇
            nearest_town = "未知"
            distance_to_town = 0.0
            
            if towns_data:
                nearest_town, distance_to_town, _ = self.find_nearest_town(
                    obs_lat, obs_lon, towns_data
                )
            
            observatory = Observatory(
                name=obs_name,
                latitude=obs_lat,
                longitude=obs_lon,
                elevation=obs_elevation,
                observatory_type=observatory_type,
                description=description,
                distance_to_nearest_town=distance_to_town,
                nearest_town_name=nearest_town or "未知"
            )
            observatories.append(observatory)
            print(f"找到天文台: {obs_name} ({observatory_type})")
        
        # 按海拔高度排序
        observatories.sort(key=lambda o: o.elevation, reverse=True)
        
        print(f"\n总共找到 {len(observatories)} 个天文台")
        return observatories
    
    def save_results_to_json(self, peaks: List[Peak], filename: str) -> None:
        """
        将结果保存到JSON文件
        
        Args:
            peaks: 山峰列表
            filename: 输出文件名
        """
        results = {
            "search_criteria": {
                "min_height_difference": self.min_height_difference
            },
            "total_peaks_found": len(peaks),
            "peaks": [
                {
                    "name": peak.name,
                    "latitude": peak.latitude,
                    "longitude": peak.longitude,
                    "elevation": peak.elevation,
                    "height_difference": peak.height_difference,
                    "distance_to_nearest_town": peak.distance_to_nearest_town,
                    "nearest_town_name": peak.nearest_town_name
                }
                for peak in peaks
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到: {filename}")

# 便捷函数
def find_peaks_with_height_difference(south: float, west: float, north: float, east: float,
                                     min_height_diff: float = 100.0,
                                     max_peaks: int = 50) -> List[Peak]:
    """
    在指定区域查找与周围城镇有足够高度差的山峰
    
    Args:
        south, west, north, east: 边界框坐标
        min_height_diff: 最小高度差（米）
        max_peaks: 最大搜索山峰数量
        
    Returns:
        符合条件的山峰列表
    """
    finder = MountainPeakFinder(min_height_difference=min_height_diff)
    return finder.find_peaks_in_area((south, west, north, east), max_peaks)

if __name__ == "__main__":
    # 示例：搜索北京周边的山峰
    print("=== 山峰查找器示例 ===")
    
    # 定义搜索区域（北京周边）
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    
    # 创建查找器
    finder = MountainPeakFinder(min_height_difference=100.0)
    
    # 查找山峰
    peaks = finder.find_peaks_in_area(bbox, max_peaks=20)
    
    # 显示结果
    if peaks:
        print("\n=== 符合条件的山峰 ===")
        for i, peak in enumerate(peaks, 1):
            print(f"{i}. {peak.name}")
            print(f"   坐标: ({peak.latitude:.4f}, {peak.longitude:.4f})")
            print(f"   海拔: {peak.elevation:.1f}m")
            print(f"   与{peak.nearest_town_name}的高度差: {peak.height_difference:.1f}m")
            print(f"   距离最近城镇: {peak.distance_to_nearest_town:.1f}km")
            print()
        
        # 保存结果
        finder.save_results_to_json(peaks, "mountain_peaks_results.json")
    else:
        print("未找到符合条件的山峰")