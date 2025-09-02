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
try:
    from src.light_pollution_analyzer import LightPollutionAnalyzer
except ImportError:
    from light_pollution_analyzer import LightPollutionAnalyzer

@dataclass
class Location:
    """统一的地点数据类，支持山峰、天文台、观景台等多种类型"""
    # 基础必需字段
    name: str  # 地点名称
    latitude: float  # 纬度
    longitude: float  # 经度
    elevation: float  # 海拔高度（米）
    distance_to_nearest_town: float  # 到最近城镇的距离（公里）
    nearest_town_name: str  # 最近城镇名称
    location_type: str  # 地点类型："mountain_peak", "observatory", "viewpoint"
    
    # 可选字段，根据不同类型使用
    description: Optional[str] = None  # 描述信息
    prominence: Optional[float] = None  # 相对高度（米）- 主要用于山峰
    height_difference: Optional[float] = None  # 与最近城镇的高度差（米）- 主要用于山峰
    observatory_type: Optional[str] = None  # 天文台类型 - 仅用于天文台
    viewpoint_type: Optional[str] = None  # 观景台类型 - 仅用于观景台
    light_pollution_level: Optional[str] = None  # 光污染等级
    scenic_value: Optional[str] = None  # 景观价值等级 - 主要用于观景台
    
    def is_mountain_peak(self) -> bool:
        """判断是否为山峰"""
        return self.location_type == "mountain_peak"
    
    def is_observatory(self) -> bool:
        """判断是否为天文台"""
        return self.location_type == "observatory"
    
    def is_viewpoint(self) -> bool:
        """判断是否为观景台"""
        return self.location_type == "viewpoint"

# 为了向后兼容，保留原有类名作为别名
Peak = Location
Observatory = Location
Viewpoint = Location

class MountainPeakFinder:
    """
    山峰查找器类
    用于查找指定范围内符合条件的山峰
    """
    
    def __init__(self, min_height_difference: float = 100.0, light_pollution_analyzer: Optional[LightPollutionAnalyzer] = None):
        """
        初始化山峰查找器
        
        Args:
            min_height_difference: 与周围城镇的最小高度差（米），默认100米
        """
        self.min_height_difference = min_height_difference
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.light_pollution_analyzer = light_pollution_analyzer
        
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
        
        return self._make_overpass_request(query, "山峰")
    
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
        
        return self._make_overpass_request(query, "天文台")
    
    def get_viewpoints_from_overpass(self, bbox: Tuple[float, float, float, float]) -> List[Dict]:
        """
        从Overpass API获取指定边界框内的观景台数据
        
        Args:
            bbox: 边界框 (south, west, north, east)
            
        Returns:
            观景台数据列表
        """
        south, west, north, east = bbox
        
        # Overpass QL查询语句 - 获取观景台、观景点等
        query = f"""
        [out:json][timeout:25];
        (
          node["tourism"="viewpoint"]({south},{west},{north},{east});
          way["tourism"="viewpoint"]({south},{west},{north},{east});
          relation["tourism"="viewpoint"]({south},{west},{north},{east});
          node["man_made"="tower"]["tower:type"="observation"]({south},{west},{north},{east});
          way["man_made"="tower"]["tower:type"="observation"]({south},{west},{north},{east});
          node["amenity"="observation_deck"]({south},{west},{north},{east});
          way["amenity"="observation_deck"]({south},{west},{north},{east});
          node["leisure"="viewing_platform"]({south},{west},{north},{east});
          way["leisure"="viewing_platform"]({south},{west},{north},{east});
        );
        out center geom;
        """
        
        return self._make_overpass_request(query, "观景台")
    
    def _make_overpass_request(self, query: str, data_type: str = "数据", max_retries: int = 3, debug: bool = False) -> List[Dict]:
        """
        向Overpass API发送请求，包含重试机制和错误处理
        
        Args:
            query: Overpass查询语句
            data_type: 数据类型描述（用于错误信息）
            max_retries: 最大重试次数
            debug: 是否显示调试信息
            
        Returns:
            API返回的元素列表
        """
        if debug:
            print(f"查询语句:\n{query}")
            print("-" * 50)
        
        for attempt in range(max_retries):
            try:
                # 添加随机延迟以避免API限制
                if attempt > 0:
                    delay = random.uniform(1, 3) * (attempt + 1)
                    print(f"第{attempt + 1}次重试，等待{delay:.1f}秒...")
                    time.sleep(delay)
                
                print(f"正在获取{data_type}数据...")
                response = requests.post(self.overpass_url, data=query, timeout=45)
                
                if debug:
                    print(f"响应状态码: {response.status_code}")
                    if response.status_code != 200:
                        print(f"响应内容: {response.text[:500]}")
                
                response.raise_for_status()
                data = response.json()
                elements = data.get('elements', [])
                print(f"找到 {len(elements)} 个{data_type}")
                return elements
                
            except requests.exceptions.Timeout:
                print(f"获取{data_type}数据超时 (尝试 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print(f"⚠️ 经过{max_retries}次尝试后仍然超时，可能是网络问题或Overpass API服务器繁忙")
                    print("建议稍后重试或检查网络连接")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 504:
                    print(f"Overpass API网关超时 (尝试 {attempt + 1}/{max_retries})")
                    if attempt == max_retries - 1:
                        print("⚠️ Overpass API服务器当前繁忙，请稍后重试")
                elif e.response.status_code == 429:
                    print(f"API请求频率限制 (尝试 {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(60)  # 等待更长时间
                elif e.response.status_code == 400:
                    print(f"查询语句错误 (400 Bad Request)")
                    if debug:
                        print(f"错误响应: {e.response.text[:500]}")
                    print("⚠️ 请检查查询语句格式")
                    break  # 400错误通常不需要重试
                else:
                    print(f"HTTP错误: {e}")
                    if debug and hasattr(e, 'response'):
                        print(f"错误响应: {e.response.text[:500]}")
                    break
            except requests.exceptions.RequestException as e:
                print(f"网络请求错误: {e} (尝试 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print("⚠️ 网络连接问题，请检查网络设置")
            except json.JSONDecodeError:
                print(f"API返回数据格式错误 (尝试 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print("⚠️ API返回的数据格式不正确")
            except Exception as e:
                print(f"获取{data_type}数据时出错: {e} (尝试 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    print("⚠️ 发生未知错误，请检查查询参数或稍后重试")
        
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
            try:
                if town['type'] == 'node':
                    town_lat = town['lat']
                    town_lon = town['lon']
                elif 'center' in town:
                    town_lat = town['center']['lat']
                    town_lon = town['center']['lon']
                else:
                    continue
            except KeyError:
                # 跳过缺少坐标信息的城镇数据
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

    def _sort_places_by_lightpollution(self, places: List[Dict]) -> List[Dict]: 
        """
        根据光污染程度对地点进行排序
        
        Args:
            places: 地点列表，每个地点包含lat和lon字段
            
        Returns:
            按光污染程度排序的地点列表（光污染越低排在前面，适合观星）
        """
        # 如果没有光污染分析器或列表为空，直接返回原列表
        if not self.light_pollution_analyzer or not places:
            return places
             
        # 安全地获取坐标信息
        places_coord = []
        valid_places = []
        for place in places:
            try:
                if place['type'] == 'node':
                    lat = place['lat']
                    lon = place['lon']
                elif 'center' in place:
                    lat = place['center']['lat']
                    lon = place['center']['lon']
                else:
                    continue  # 跳过无法获取坐标的地点
                places_coord.append([lat, lon])
                valid_places.append(place)
            except KeyError:
                # 跳过缺少坐标信息的地点
                continue
        
        # 如果没有有效的地点，返回空列表
        if not places_coord:
            return []
        places_light_pollutions = self.light_pollution_analyzer.batch_analyze_coordinates(places_coord)
        # 按光污染程度排序，光污染越低越适合观星，所以reverse=False
        places_light_pollutions = sorted(places_light_pollutions, key=lambda x: x['pollution_info']["brightness"], reverse=False)
        # 根据排序后的索引重新排列places列表
        sorted_places = [valid_places[place_light_pollution['index']] for place_light_pollution in places_light_pollutions]
        # 添加光污染信息
        for place, light_pollution in zip(sorted_places, places_light_pollutions):
            place['light_pollution'] = light_pollution['pollution_info']
        print(f"排序后的地点: {sorted_places[:3]}")
        return sorted_places
    
    def _extract_coordinates(self, data: Dict) -> Tuple[Optional[float], Optional[float]]:
        """
        从地点数据中提取坐标
        
        Args:
            data: 地点数据字典
            
        Returns:
            (latitude, longitude) 或 (None, None) 如果提取失败
        """
        try:
            if data['type'] == 'node':
                return data['lat'], data['lon']
            elif 'center' in data:
                return data['center']['lat'], data['center']['lon']
            else:
                return None, None
        except KeyError:
            return None, None
    
    def _find_locations_in_area(self, 
                               bbox: Tuple[float, float, float, float],
                               location_type: str,
                               max_locations: int,
                               data_getter_func,
                               location_processor_func) -> List[Location]:
        """
        通用的地点查找函数，用于减少代码重复
        
        Args:
            bbox: 边界框 (south, west, north, east)
            location_type: 地点类型 ('mountain_peak', 'observatory', 'viewpoint')
            max_locations: 最大返回地点数量
            data_getter_func: 获取特定类型数据的函数
            location_processor_func: 处理特定类型地点的函数
            
        Returns:
            地点列表
        """
        print(f"正在搜索{location_type}区域: {bbox}")
        
        # 获取特定类型数据
        print(f"正在获取{location_type}数据...")
        locations_data = data_getter_func(bbox)
        locations_data = self._sort_places_by_lightpollution(locations_data)
        print(f"找到 {len(locations_data)} 个{location_type}")
        
        # 获取城镇数据
        print("正在获取城镇数据...")
        towns_data = self.get_towns_from_overpass(bbox)
        print(f"找到 {len(towns_data)} 个城镇")
        
        if not locations_data:
            print(f"未找到{location_type}数据")
            return []
        
        locations = []
        
        for i, location_data in enumerate(locations_data[:max_locations]):
            if i % 5 == 0:
                print(f"处理进度: {i+1}/{min(len(locations_data), max_locations)}")
            
            # 提取坐标
            lat, lon = self._extract_coordinates(location_data)
            if lat is None or lon is None:
                print(f"警告: {location_type}数据缺少坐标信息，跳过: {location_data.get('id', 'unknown')}")
                continue
            
            # 获取基本信息
            tags = location_data.get('tags', {})
            name = tags.get('name', f'{location_type}_{i+1}')
            
            # 获取海拔
            elevation = None
            if 'ele' in tags:
                try:
                    elevation = float(tags['ele'])
                except ValueError:
                    pass
            
            if elevation is None:
                elevation = self.get_elevation_from_api(lat, lon)
                time.sleep(0.1)  # 避免API请求过于频繁
            
            if elevation is None:
                elevation = 0.0  # 默认海拔
            
            # 查找最近的城镇
            nearest_town = "未知"
            distance_to_town = 0.0
            town_elevation = None
            
            if towns_data:
                nearest_town, distance_to_town, town_elevation = self.find_nearest_town(
                    lat, lon, towns_data
                )
            
            # 获取光污染信息
            light_pollution_level = None
            if 'light_pollution' in location_data:
                light_pollution_level = location_data['light_pollution'].get('pollution_level', '未知污染等级')
            
            # 使用特定的处理函数创建Location对象
            location = location_processor_func(
                name, lat, lon, elevation, tags, 
                nearest_town, distance_to_town, town_elevation,
                light_pollution_level, i
            )
            
            if location:
                locations.append(location)
        
        print(f"\n总共找到 {len(locations)} 个{location_type}")
        return locations
    
    def _process_peak_data(self, name: str, lat: float, lon: float, elevation: float, 
                          tags: Dict, nearest_town: str, distance_to_town: float, 
                          town_elevation: Optional[float], light_pollution_level: Optional[str], 
                          index: int) -> Optional[Peak]:
        """
        处理山峰数据并创建Peak对象
        """
        # 计算高度差
        height_difference = None
        if town_elevation is not None:
            height_difference = elevation - town_elevation
            
            # 检查是否满足高度差要求
            if height_difference < self.min_height_difference:
                print(f"山峰 {name} 高度差不足 ({height_difference:.1f}m < {self.min_height_difference}m)，跳过")
                return None
        
        return Peak(
            name=name,
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            nearest_town_name=nearest_town,
            distance_to_nearest_town=distance_to_town,
            location_type="mountain_peak",
            height_difference=height_difference,
            light_pollution_level=light_pollution_level
        )
    
    def _process_observatory_data(self, name: str, lat: float, lon: float, elevation: float, 
                                 tags: Dict, nearest_town: str, distance_to_town: float, 
                                 town_elevation: Optional[float], light_pollution_level: Optional[str], 
                                 index: int) -> Optional[Observatory]:
        """
        处理天文台数据并创建Observatory对象
        """
        # 确定天文台类型
        observatory_type = "未知类型"
        if tags.get('man_made') == 'observatory':
            observatory_type = "天文观测台"
        elif tags.get('amenity') == 'planetarium':
            observatory_type = "天象馆"
        elif tags.get('building') == 'observatory':
            observatory_type = "天文台建筑"
        elif tags.get('man_made') == 'telescope':
            observatory_type = "望远镜"
        
        # 获取描述信息
        description = tags.get('description', '')
        if not description:
            description = tags.get('note', '')
        
        return Observatory(
            name=name,
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            nearest_town_name=nearest_town,
            distance_to_nearest_town=distance_to_town,
            location_type="observatory",
            observatory_type=observatory_type,
            description=description,
            light_pollution_level=light_pollution_level
        )
    
    def _process_viewpoint_data(self, name: str, lat: float, lon: float, elevation: float, 
                               tags: Dict, nearest_town: str, distance_to_town: float, 
                               town_elevation: Optional[float], light_pollution_level: Optional[str], 
                               index: int) -> Optional[Viewpoint]:
        """
        处理观景台数据并创建Viewpoint对象
        """
        # 确定观景台类型
        viewpoint_type = "观景台"
        if 'tourism' in tags:
            if tags['tourism'] == 'viewpoint':
                viewpoint_type = "观景台"
        elif 'natural' in tags:
            if tags['natural'] == 'peak':
                viewpoint_type = "山峰观景点"
        
        # 获取描述信息
        description = tags.get('description', '')
        if not description:
            description = tags.get('note', '')
        
        # 评估景观价值
        scenic_value = "中等"
        if elevation > 1000:
            scenic_value = "高"
        elif elevation > 500:
            scenic_value = "中等"
        else:
            scenic_value = "一般"
        
        return Viewpoint(
            name=name,
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            nearest_town_name=nearest_town,
            distance_to_nearest_town=distance_to_town,
            location_type="viewpoint",
            viewpoint_type=viewpoint_type,
            description=description,
            scenic_value=scenic_value,
            light_pollution_level=light_pollution_level
        )
     
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
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="山峰",
            max_locations=max_peaks,
            data_getter_func=self.get_peaks_from_overpass,
            location_processor_func=self._process_peak_data
        )
    
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
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="天文台",
            max_locations=max_observatories,
            data_getter_func=self.get_observatories_from_overpass,
            location_processor_func=self._process_observatory_data
        )
    
    def find_viewpoints_in_area(self, bbox: Tuple[float, float, float, float], 
                               max_viewpoints: int = 50) -> List[Viewpoint]:
        """
        在指定区域内查找观景台
        
        Args:
            bbox: 边界框 (south, west, north, east)
            max_viewpoints: 最大返回观景台数量
            
        Returns:
            观景台列表
        """
        return self._find_locations_in_area(
            bbox=bbox,
            location_type="观景台",
            max_locations=max_viewpoints,
            data_getter_func=self.get_viewpoints_from_overpass,
            location_processor_func=self._process_viewpoint_data
        )
    
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
    finder = MountainPeakFinder(min_height_difference=min_height_diff, light_pollution_analyzer=LightPollutionAnalyzer("world_atlas/doc.xml"))
    return finder.find_peaks_in_area((south, west, north, east), max_peaks)

def find_viewpoints(south: float, west: float, north: float, east: float,
                   max_viewpoints: int = 50) -> List[Viewpoint]:
    """
    在指定区域查找观景台
    
    Args:
        south, west, north, east: 边界框坐标
        max_viewpoints: 最大搜索观景台数量
        
    Returns:
        观景台列表，按海拔高度排序
    """
    finder = MountainPeakFinder(min_height_difference=100.0, light_pollution_analyzer=LightPollutionAnalyzer("world_atlas/doc.xml"))
    return finder.find_viewpoints_in_area((south, west, north, east), max_viewpoints)

if __name__ == "__main__":
    # 示例：搜索北京周边的山峰
    print("=== 山峰查找器示例 ===")
    
    # 定义搜索区域（北京周边）
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    
    # 创建查找器
    finder = MountainPeakFinder(min_height_difference=100.0, light_pollution_analyzer=LightPollutionAnalyzer("world_atlas/doc.xml"))
    
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