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
    from .mountain_peak_finder import MountainPeakFinder, Peak
    from .light_pollution_analyzer import LightPollutionAnalyzer
    from .road_connectivity_checker import RoadConnectivityChecker
except ImportError:
    from mountain_peak_finder import MountainPeakFinder, Peak
    from light_pollution_analyzer import LightPollutionAnalyzer
    from road_connectivity_checker import RoadConnectivityChecker


@dataclass
class StargazingLocation:
    """
    观星地点数据类
    包含山峰信息、光污染数据和道路连通性信息
    """
    # 基本山峰信息
    name: str
    latitude: float
    longitude: float
    elevation: float
    prominence: float
    distance_to_nearest_town: float
    nearest_town_name: str
    height_difference: float
    
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
        self.mountain_finder = MountainPeakFinder(min_height_difference=min_height_difference)
        
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
        else:
            if kml_file_path:
                print(f"⚠️  警告: KML文件 {kml_file_path} 不存在")
            else:
                print("⚠️  警告: 未提供光污染数据文件")
            print("⚠️  光污染数据是观星地点分析的重要组成部分")
            print("⚠️  建议从以下网站下载光污染地图KML文件:")
            print("   - Light Pollution Map: https://www.lightpollutionmap.info/")
            print("   - Dark Site Finder: https://darksitefinder.com/")
        
        # 初始化道路连通性检测器
        self.road_checker = RoadConnectivityChecker(search_radius_km=road_search_radius_km)
        
        print("观星地点分析器初始化完成")
    
    def analyze_area(self, 
                    bbox: Tuple[float, float, float, float],
                    max_peaks: int = 50,
                    network_type: str = 'drive',
                    include_light_pollution: bool = True,
                    include_road_connectivity: bool = True) -> List[StargazingLocation]:
        """
        分析指定区域内的观星地点
        
        Args:
            bbox: 边界框 (south, west, north, east)
            max_peaks: 最大山峰数量
            network_type: 道路网络类型 ('drive', 'walk', 'bike', 'all')
            include_light_pollution: 是否包含光污染分析
            include_road_connectivity: 是否包含道路连通性分析
            
        Returns:
            观星地点列表
        """
        print(f"开始分析区域: {bbox}")
        
        # 1. 查找山峰
        print("正在查找山峰...")
        peaks = self.mountain_finder.find_peaks_in_area(bbox, max_peaks=max_peaks)
        
        if not peaks:
            print("未找到符合条件的山峰")
            return []
        
        print(f"找到 {len(peaks)} 座山峰，开始详细分析...")
        
        # 2. 为每个山峰进行综合分析
        stargazing_locations = []
        for i, peak in enumerate(peaks, 1):
            print(f"分析第 {i}/{len(peaks)} 座山峰: {peak.name}")
            
            # 创建观星地点对象
            location = StargazingLocation(
                name=peak.name,
                latitude=peak.latitude,
                longitude=peak.longitude,
                elevation=peak.elevation,
                prominence=peak.prominence,
                distance_to_nearest_town=peak.distance_to_nearest_town,
                nearest_town_name=peak.nearest_town_name,
                height_difference=peak.height_difference
            )
            
            # 3. 光污染分析
            if include_light_pollution:
                if self.light_pollution_analyzer:
                    try:
                        light_info = self.light_pollution_analyzer.get_light_pollution_color(
                            peak.latitude, peak.longitude
                        )
                        if light_info:
                            location.light_pollution_rgb = light_info['rgb']
                            location.light_pollution_hex = light_info['hex']
                            location.light_pollution_brightness = light_info['brightness']
                            location.light_pollution_level = light_info['pollution_level']
                            location.light_pollution_overlay = light_info.get('overlay_name')
                    except Exception as e:
                        print(f"  光污染分析失败: {e}")
                else:
                    print(f"  ⚠️  警告: 无法获取 {peak.name} 的光污染数据 - 未提供光污染数据文件")
            
            # 4. 道路连通性分析
            if include_road_connectivity:
                try:
                    road_info = self.road_checker.get_accessibility_info(
                        peak.latitude, peak.longitude, network_type=network_type
                    )
                    location.road_accessible = road_info['accessible']
                    location.distance_to_road_km = road_info['distance_to_road_km']
                    location.road_network_type = network_type
                    location.road_check_error = road_info.get('error')
                except Exception as e:
                    print(f"  道路连通性分析失败: {e}")
                    location.road_check_error = str(e)
            
            # 5. 计算综合评分
            location.stargazing_score = self._calculate_stargazing_score(location)
            location.recommendation_level = self._get_recommendation_level_with_warning(location)
            location.analysis_notes = self._generate_analysis_notes(location)
            
            stargazing_locations.append(location)
            
            # 添加延迟以避免API限制
            time.sleep(0.5)
        
        # 按评分排序
        stargazing_locations.sort(key=lambda x: x.stargazing_score or 0, reverse=True)
        
        print(f"分析完成，共 {len(stargazing_locations)} 个观星地点")
        return stargazing_locations
    
    def _calculate_stargazing_score(self, location: StargazingLocation) -> float:
        """
        计算观星地点的综合评分（0-100分）
        
        Args:
            location: 观星地点对象
            
        Returns:
            综合评分
        """
        score = 0.0
        
        # 1. 高度差评分（30分）
        height_score = min(location.height_difference / 500.0 * 30, 30)
        score += height_score
        
        # 2. 光污染评分（40分）
        if location.light_pollution_brightness is not None:
            # 亮度越低，评分越高
            light_score = max(0, (255 - location.light_pollution_brightness) / 255.0 * 40)
            score += light_score
        else:
            # 如果没有光污染数据，给予警告并使用默认评分
            print(f"⚠️  警告: {location.name} 缺少光污染数据，评分准确性受影响")
            # 给予中等评分，但标记为不完整
            score += 20  # 40分权重的一半
        
        # 3. 道路可达性评分（20分）
        if location.road_accessible is True:
            score += 20
        elif location.road_accessible is False:
            score += 5  # 不可达但给予少量分数
        else:
            score += 10  # 未知状态给予中等分数
        
        # 4. 距离城镇评分（10分）
        if location.distance_to_nearest_town > 50:
            score += 10
        elif location.distance_to_nearest_town > 20:
            score += 7
        elif location.distance_to_nearest_town > 10:
            score += 5
        else:
            score += 2
        
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
                           max_peaks: int = 30,
                           min_height_diff: float = 100.0,
                           road_radius_km: float = 10.0,
                           network_type: str = 'drive') -> List[StargazingLocation]:
    """
    便捷函数：分析指定区域的观星地点
    
    Args:
        south, west, north, east: 边界框坐标
        kml_file_path: 光污染KML文件路径（强烈推荐提供）
        max_peaks: 最大山峰数量
        min_height_diff: 最小高度差
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
        max_peaks=max_peaks,
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
        max_peaks=20,
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