#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观星地点综合分析器

这个模块整合了山峰查找、光污染分析和道路连通性检测功能，
为用户提供一站式的观星地点评估服务。
"""

import json
import os
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import time
from datetime import datetime

# 导入相关模块
try:
    from .stargazing_place_finder import StarGazingPlaceFinder, Peak
    from .light_pollution_analyzer import LightPollutionAnalyzer
    from .road_connectivity_checker import RoadConnectivityChecker
except ImportError:
    from stargazing_place_finder import StarGazingPlaceFinder, Peak
    from light_pollution_analyzer import LightPollutionAnalyzer
    from road_connectivity_checker import RoadConnectivityChecker


@dataclass
class StargazingLocation:
    """
    观星地点数据类
    支持山峰、天文台、观景台等多种类型的观星地点
    包含基本地点信息、光污染数据和道路连通性信息
    """
    # 基本地点信息（适配统一的Location类）
    name: str
    latitude: float
    longitude: float
    elevation: float
    distance_to_nearest_town: float
    nearest_town_name: str
    
    # 地点类型和描述
    location_type: str = "mountain_peak"  # "mountain_peak", "observatory", "viewpoint"
    description: Optional[str] = None
    
    # 山峰特有信息
    prominence: Optional[float] = None
    height_difference: Optional[float] = None
    
    # 光污染信息
    light_pollution_rgb: Optional[Tuple[int, int, int]] = None
    light_pollution_hex: Optional[str] = None
    light_pollution_brightness: Optional[int] = None
    light_pollution_level: Optional[str] = None
    light_pollution_overlay: Optional[str] = None
    
    # 道路连通性信息
    road_accessible: Optional[bool] = None
    distance_to_road_km: Optional[float] = None
    road_network_type: Optional[str] = None
    road_check_error: Optional[str] = None
    
    # 综合评分
    stargazing_score: Optional[float] = None
    recommendation_level: Optional[str] = None
    analysis_notes: Optional[str] = None
    
    def is_mountain_peak(self) -> bool:
        """判断是否为山峰"""
        return self.location_type == "mountain_peak"
    
    def is_observatory(self) -> bool:
        """判断是否为天文台"""
        return self.location_type == "observatory"
    
    def is_viewpoint(self) -> bool:
        """判断是否为观景台"""
        return self.location_type == "viewpoint"


class StargazingLocationAnalyzer:
    """
    观星地点综合分析器
    
    整合山峰查找、光污染分析和道路连通性检测功能，
    为指定坐标范围内的山峰提供全面的观星适宜性分析。
    """
    
    def __init__(self, 
                 kml_file_path: Optional[str] = None,
                 images_base_path: Optional[str] = None,
                 min_height_difference: float = 100.0,
                 road_search_radius_km: float = 10.0):
        """
        初始化观星地点分析器
        
        Args:
            kml_file_path: 光污染KML文件路径，如果为None则跳过光污染分析（强烈推荐提供）
            images_base_path: 光污染图像文件基础路径
            min_height_difference: 山峰与周围城镇的最小高度差（米）
            road_search_radius_km: 道路连通性检测的搜索半径（公里）
        """
        # 初始化山峰查找器
        
        
        # 初始化光污染分析器（如果提供了KML文件）
        self.light_pollution_analyzer = None
        if kml_file_path and os.path.exists(kml_file_path):
            try:
                self.light_pollution_analyzer = LightPollutionAnalyzer(
                    kml_file_path=kml_file_path,
                    images_base_path=images_base_path
                )
                print("光污染分析器初始化成功")
            except Exception as e:
                print(f"光污染分析器初始化失败: {e}")
                self.light_pollution_analyzer = None
            self.mountain_finder = StarGazingPlaceFinder(min_height_difference=min_height_difference, light_pollution_analyzer=self.light_pollution_analyzer)
        else:
            if kml_file_path:
                print(f"⚠️  警告: KML文件 {kml_file_path} 不存在")
            else:
                print("⚠️  警告: 未提供光污染数据文件")
            print("⚠️  光污染数据是观星地点分析的重要组成部分")
            print("⚠️  建议从以下网站下载光污染地图KML文件:")
            print("   - Light Pollution Map: https://www.lightpollutionmap.info/")
            print("   - Dark Site Finder: https://darksitefinder.com/")
            self.mountain_finder = StarGazingPlaceFinder(min_height_difference=min_height_difference)
        
        # 初始化道路连通性检测器
        self.road_checker = RoadConnectivityChecker(search_radius_km=road_search_radius_km)
        
        print("观星地点分析器初始化完成")
    
    def analyze_area(self, 
                    bbox: Tuple[float, float, float, float],
                    max_locations: int = 50,
                    location_types: List[str] = None,
                    network_type: str = 'drive',
                    include_light_pollution: bool = True,
                    include_road_connectivity: bool = True) -> List[StargazingLocation]:
        """
        分析指定区域内的观星地点（支持山峰、天文台、观景台等多种类型）
        
        Args:
            bbox: 边界框 (south, west, north, east)
            max_locations: 最大地点数量
            location_types: 地点类型列表，可选值：['mountain_peak', 'observatory', 'viewpoint']
                          如果为None，则默认查找所有类型
            network_type: 道路网络类型 ('drive', 'walk', 'bike', 'all')
            include_light_pollution: 是否包含光污染分析
            include_road_connectivity: 是否包含道路连通性分析
            
        Returns:
            观星地点列表
        """
        print(f"开始分析区域: {bbox}")
        
        # 默认查找所有类型的地点
        if location_types is None:
            location_types = ['mountain_peak', 'observatory', 'viewpoint']
        
        all_locations = []
        
        # 1. 根据指定类型查找地点
        for location_type in location_types:
            print(f"正在查找{location_type}...")
            
            if location_type == 'mountain_peak':
                locations = self.mountain_finder.find_peaks_in_area(bbox, max_locations=max_locations)
            elif location_type == 'observatory':
                locations = self.mountain_finder.find_observatories_in_area(bbox, max_observatories=max_locations)
            elif location_type == 'viewpoint':
                locations = self.mountain_finder.find_viewpoints_in_area(bbox, max_viewpoints=max_locations)
            else:
                print(f"  警告: 不支持的地点类型 {location_type}")
                continue
            
            if locations:
                print(f"找到 {len(locations)} 个 {location_type}")
                all_locations.extend(locations)
            else:
                print(f"未找到符合条件的 {location_type}")
        
        if not all_locations:
            print("未找到符合条件的观星地点")
            return []
        
        # 限制总数量
        if len(all_locations) > max_locations:
            all_locations = all_locations[:max_locations]
        
        print(f"总共找到 {len(all_locations)} 个地点，开始详细分析...")
        
        # 2. 为每个地点进行综合分析
        stargazing_locations = []
        for i, location in enumerate(all_locations, 1):
            print(f"分析第 {i}/{len(all_locations)} 个地点: {location.name} ({location.location_type})")
            
            # 创建观星地点对象，适配统一的Location类
            stargazing_location = StargazingLocation(
                name=location.name,
                latitude=location.latitude,
                longitude=location.longitude,
                elevation=location.elevation,
                prominence=location.prominence if hasattr(location, 'prominence') and location.prominence else 0.0,
                distance_to_nearest_town=location.distance_to_nearest_town,
                nearest_town_name=location.nearest_town_name,
                height_difference=location.height_difference if hasattr(location, 'height_difference') and location.height_difference else 0.0,
                location_type=location.location_type,
                description=location.description if hasattr(location, 'description') else None
            )
            
            # 3. 光污染分析
            if include_light_pollution:
                if self.light_pollution_analyzer:
                    try:
                        light_info = self.light_pollution_analyzer.get_light_pollution_color(
                            location.latitude, location.longitude
                        )
                        if light_info:
                            stargazing_location.light_pollution_rgb = light_info['rgb']
                            stargazing_location.light_pollution_hex = light_info['hex']
                            stargazing_location.light_pollution_brightness = light_info['brightness']
                            stargazing_location.light_pollution_level = light_info['pollution_level']
                            stargazing_location.light_pollution_overlay = light_info.get('overlay_name')
                    except Exception as e:
                        print(f"  光污染分析失败: {e}")
                else:
                    print(f"  ⚠️  警告: 无法获取 {location.name} 的光污染数据 - 未提供光污染数据文件")
            
            # 4. 道路连通性分析
            if include_road_connectivity:
                try:
                    road_info = self.road_checker.get_accessibility_info(
                        location.latitude, location.longitude, network_type=network_type
                    )
                    stargazing_location.road_accessible = road_info['accessible']
                    stargazing_location.distance_to_road_km = road_info['distance_to_road_km']
                    stargazing_location.road_network_type = network_type
                    stargazing_location.road_check_error = road_info.get('error')
                except Exception as e:
                    print(f"  道路连通性分析失败: {e}")
                    stargazing_location.road_check_error = str(e)
            
            # 5. 计算综合评分
            stargazing_location.stargazing_score = self._calculate_stargazing_score(stargazing_location)
            stargazing_location.recommendation_level = self._get_recommendation_level_with_warning(stargazing_location)
            stargazing_location.analysis_notes = self._generate_analysis_notes(stargazing_location)
            
            stargazing_locations.append(stargazing_location)
            
            # 添加延迟以避免API限制
            time.sleep(0.5)
        
        # 按评分排序
        stargazing_locations.sort(key=lambda x: x.stargazing_score or 0, reverse=True)
        
        print(f"分析完成，共 {len(stargazing_locations)} 个观星地点")
        return stargazing_locations
    
    def _calculate_stargazing_score(self, location: StargazingLocation) -> float:
        """
        计算观星地点的综合评分（适配多种地点类型）
        
        评分标准:
        - 海拔高度 (0-30分): 海拔越高越好
        - 地点类型特有评分 (0-25分): 根据不同类型计算
        - 光污染等级 (0-25分): 光污染越少越好
        - 道路可达性 (0-20分): 可达且距离适中最好
        
        Args:
            location: 观星地点对象
            
        Returns:
            综合评分 (0-100分)
        """
        score = 0.0
        
        # 1. 海拔高度评分 (0-30分)
        if location.elevation:
            # 海拔每100米得1分，最高30分
            elevation_score = min(location.elevation / 100 * 1, 30)
            score += elevation_score
        
        # 2. 地点类型特有评分 (0-25分)
        if location.is_mountain_peak():
            # 山峰：相对高度评分
            if location.prominence:
                # 相对高度每50米得1分，最高25分
                prominence_score = min(location.prominence / 50 * 1, 25)
                score += prominence_score
        elif location.is_observatory():
            # 天文台：固定高分（因为是专业观测设施）
            score += 25
        elif location.is_viewpoint():
            # 观景台：根据高度差评分
            if location.height_difference:
                # 高度差每40米得1分，最高25分
                height_diff_score = min(location.height_difference / 40 * 1, 25)
                score += height_diff_score
            else:
                score += 15  # 默认中等评分
        
        # 3. 光污染评分 (0-25分)
        if location.light_pollution_level:
            pollution_scores = {
                '极低': 25, '很低': 20, '低': 15, '中等': 10, 
                '高': 5, '很高': 2, '极高': 0
            }
            score += pollution_scores.get(location.light_pollution_level, 0)
        elif location.light_pollution_brightness is not None:
            # 如果没有等级但有亮度数据，根据亮度计算
            light_score = max(0, (255 - location.light_pollution_brightness) / 255.0 * 25)
            score += light_score
        else:
            # 如果没有光污染数据，给予警告并使用默认评分
            print(f"⚠️  警告: {location.name} 缺少光污染数据，评分准确性受影响")
            score += 12  # 25分权重的一半
        
        # 4. 道路可达性评分 (0-20分)
        if location.road_accessible is not None:
            if location.road_accessible:
                # 可达的情况下，距离道路越近越好（但不能太近）
                if location.distance_to_road_km is not None:
                    if 0.5 <= location.distance_to_road_km <= 5:
                        # 理想距离：0.5-5公里
                        score += 20
                    elif location.distance_to_road_km <= 10:
                        # 可接受距离：5-10公里
                        score += 15
                    elif location.distance_to_road_km <= 20:
                        # 较远距离：10-20公里
                        score += 10
                    else:
                        # 很远距离：>20公里
                        score += 5
                else:
                    score += 10  # 可达但距离未知
            else:
                score += 0  # 不可达
        else:
            score += 10  # 未知状态给予中等分数
        
        return round(score, 1)
    
    def _get_recommendation_level_with_warning(self, location: StargazingLocation) -> str:
        """
        根据评分获取推荐等级，并在缺少光污染数据时添加警告
        
        Args:
            location: 观星地点对象
            
        Returns:
            推荐等级描述（包含警告信息）
        """
        base_level = self._get_recommendation_level(location.stargazing_score)
        
        # 检查是否缺少光污染数据
        if location.light_pollution_brightness is None:
            return base_level + " (⚠️缺少光污染数据)"
        
        return base_level
    
    def _get_recommendation_level(self, score: Optional[float]) -> str:
        """
        根据评分获取推荐等级
        
        Args:
            score: 综合评分
            
        Returns:
            推荐等级描述
        """
        if score is None:
            return "未评级"
        
        if score >= 80:
            return "强烈推荐 ⭐⭐⭐⭐⭐"
        elif score >= 70:
            return "推荐 ⭐⭐⭐⭐"
        elif score >= 60:
            return "一般推荐 ⭐⭐⭐"
        elif score >= 50:
            return "可考虑 ⭐⭐"
        else:
            return "不推荐 ⭐"
    
    def _generate_analysis_notes(self, location: StargazingLocation) -> str:
        """
        生成分析备注
        
        Args:
            location: 观星地点对象
            
        Returns:
            分析备注字符串
        """
        notes = []
        
        # 高度优势
        if location.height_difference > 300:
            notes.append(f"海拔优势显著，比{location.nearest_town_name}高{location.height_difference:.0f}米")
        elif location.height_difference > 150:
            notes.append(f"有一定海拔优势，比{location.nearest_town_name}高{location.height_difference:.0f}米")
        
        # 光污染状况
        if location.light_pollution_brightness is not None:
            if location.light_pollution_brightness < 64:
                notes.append("光污染水平较低，观星条件良好")
            elif location.light_pollution_brightness < 128:
                notes.append("光污染水平中等，观星条件一般")
            else:
                notes.append("光污染较严重，可能影响观星效果")
        else:
            notes.append("⚠️ 缺少光污染数据，无法准确评估观星条件")
        
        # 道路可达性
        if location.road_accessible is True:
            if location.distance_to_road_km and location.distance_to_road_km < 1:
                notes.append("交通便利，距离道路很近")
            else:
                notes.append("有道路可达")
        elif location.road_accessible is False:
            notes.append("道路不可达，需要徒步前往")
        
        # 距离城镇
        if location.distance_to_nearest_town > 50:
            notes.append("远离城镇，环境安静")
        elif location.distance_to_nearest_town < 10:
            notes.append("距离城镇较近，可能有光污染影响")
        
        return "; ".join(notes) if notes else "无特殊备注"
    
    def save_results_to_json(self, locations: List[StargazingLocation], filename: str) -> None:
        """
        将分析结果保存到JSON文件
        
        Args:
            locations: 观星地点列表
            filename: 输出文件名
        """
        # 转换为可序列化的格式
        results = {
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_locations": len(locations),
            "analysis_parameters": {
                "min_height_difference": self.mountain_finder.min_height_difference,
                "road_search_radius_km": self.road_checker.search_radius_km,
                "has_light_pollution_analyzer": self.light_pollution_analyzer is not None
            },
            "locations": [asdict(location) for location in locations]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"分析结果已保存到: {filename}")
    
    def get_top_recommendations(self, locations: List[StargazingLocation], top_n: int = 5) -> List[StargazingLocation]:
        """
        获取评分最高的推荐地点
        
        Args:
            locations: 观星地点列表
            top_n: 返回的推荐数量
            
        Returns:
            评分最高的观星地点列表
        """
        # 按评分排序并返回前N个
        sorted_locations = sorted(locations, key=lambda x: x.stargazing_score or 0, reverse=True)
        return sorted_locations[:top_n]
    
    def print_analysis_summary(self, locations: List[StargazingLocation]) -> None:
        """
        打印分析结果摘要
        
        Args:
            locations: 观星地点列表
        """
        if not locations:
            print("没有找到观星地点")
            return
        
        print("\n=== 观星地点分析摘要 ===")
        print(f"总计找到 {len(locations)} 个观星地点")
        
        # 检查光污染数据完整性
        locations_with_light_data = sum(1 for loc in locations if loc.light_pollution_brightness is not None)
        locations_without_light_data = len(locations) - locations_with_light_data
        
        if locations_without_light_data > 0:
            print(f"\n⚠️  数据完整性提醒:")
            print(f"   - {locations_with_light_data} 个地点有完整的光污染数据")
            print(f"   - {locations_without_light_data} 个地点缺少光污染数据")
            print(f"   - 建议提供光污染KML文件以获得更准确的评估")
        
        # 统计推荐等级分布
        recommendation_counts = {}
        for location in locations:
            level = location.recommendation_level
            recommendation_counts[level] = recommendation_counts.get(level, 0) + 1
        
        print("\n推荐等级分布:")
        for level, count in recommendation_counts.items():
            print(f"  {level}: {count} 个地点")
        
        # 显示前5个推荐地点
        top_locations = self.get_top_recommendations(locations, 5)
        print("\n=== 前5个推荐地点 ===")
        for i, location in enumerate(top_locations, 1):
            print(f"\n{i}. {location.name}")
            print(f"   坐标: ({location.latitude:.4f}, {location.longitude:.4f})")
            print(f"   海拔: {location.elevation:.1f}m")
            print(f"   综合评分: {location.stargazing_score}/100")
            print(f"   推荐等级: {location.recommendation_level}")
            if location.light_pollution_brightness is not None:
                print(f"   光污染: {location.light_pollution_level}")
            else:
                print(f"   光污染: ⚠️ 数据缺失")
            if location.road_accessible is not None:
                accessibility = "可达" if location.road_accessible else "不可达"
                print(f"   道路: {accessibility}")
            print(f"   备注: {location.analysis_notes}")


def analyze_stargazing_area(south: float, west: float, north: float, east: float,
                           kml_file_path: Optional[str] = None,
                           max_locations: int = 30,
                           location_types: List[str] = None,
                           min_height_diff: float = 100.0,
                           road_radius_km: float = 10.0,
                           network_type: str = 'drive') -> List[StargazingLocation]:
    """
    便捷函数：分析指定区域的观星地点
    
    Args:
        south, west, north, east: 边界框坐标
        kml_file_path: 光污染KML文件路径（强烈推荐提供）
        max_locations: 最大地点数量
        location_types: 地点类型列表，可选值：['mountain_peak', 'observatory', 'viewpoint']
        min_height_diff: 最小高度差（仅对山峰有效）
        road_radius_km: 道路搜索半径
        network_type: 网络类型
        
    Returns:
        观星地点列表
        
    Note:
        光污染数据对于准确的观星地点评估至关重要。
        如果未提供kml_file_path，分析结果的准确性将受到影响。
    """
    if kml_file_path is None:
        print("⚠️  警告: 便捷函数未提供光污染数据文件")
        print("⚠️  这将影响观星地点评估的准确性")
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file_path,
        min_height_difference=min_height_diff,
        road_search_radius_km=road_radius_km
    )
    
    bbox = (south, west, north, east)
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=max_locations,
        location_types=location_types,
        network_type=network_type,
        include_light_pollution=(kml_file_path is not None),
        include_road_connectivity=True
    )
    
    # 打印摘要
    analyzer.print_analysis_summary(locations)
    
    return locations


if __name__ == "__main__":
    # 示例：分析北京周边地区的观星地点
    print("=== 观星地点综合分析器示例 ===")
    
    # 定义分析区域（北京周边）
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    
    # 创建分析器（这里没有提供KML文件，所以跳过光污染分析）
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=None,  # 如果有光污染KML文件，在这里提供路径
        min_height_difference=100.0,
        road_search_radius_km=10.0
    )
    
    # 分析区域
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=20,
        location_types=['mountain_peak', 'observatory', 'viewpoint'],
        network_type='drive',
        include_light_pollution=False,  # 没有KML文件时设为False
        include_road_connectivity=True
    )
    
    # 保存结果
    if locations:
        analyzer.save_results_to_json(locations, "stargazing_analysis_results.json")
        
        # 打印摘要
        analyzer.print_analysis_summary(locations)
    else:
        print("未找到符合条件的观星地点")