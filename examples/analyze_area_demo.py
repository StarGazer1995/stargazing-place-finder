#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观星地点区域分析示例

展示如何使用更新后的analyze_area函数来分析不同类型的观星地点，
包括山峰、天文台和观景台。

作者: StarGazing Place Finder
日期: 2024
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.stargazing_analyzer.stargazing_location_analyzer import StargazingLocationAnalyzer

def demo_analyze_area():
    """
    演示区域观星地点分析功能
    """
    print("=" * 60)
    print("观星地点区域分析示例")
    print("=" * 60)
    
    # 创建分析器
    analyzer = StargazingLocationAnalyzer()
    
    # 定义分析区域（北京周边）
    bbox = (39.8, 116.2, 40.0, 116.6)  # (south, west, north, east)
    print(f"\n分析区域: 北纬{bbox[0]}°-{bbox[2]}°, 东经{bbox[1]}°-{bbox[3]}°")
    
    # 示例1: 分析所有类型的观星地点
    print("\n" + "="*50)
    print("示例1: 分析所有类型的观星地点")
    print("="*50)
    
    locations_all = analyzer.analyze_area(
        bbox=bbox,
        max_locations=5,
        location_types=['mountain_peak', 'observatory', 'viewpoint'],
        include_light_pollution=False,  # 不使用光污染数据
        include_road_connectivity=True
    )
    
    print(f"\n找到 {len(locations_all)} 个观星地点:")
    for i, location in enumerate(locations_all, 1):
        print(f"{i}. {location.name} ({location.location_type})")
        print(f"   坐标: ({location.latitude:.4f}, {location.longitude:.4f})")
        print(f"   海拔: {location.elevation}m")
        print(f"   评分: {location.stargazing_score}分")
        print(f"   推荐等级: {location.recommendation_level}")
        if location.road_accessible is not None:
            accessible = "可达" if location.road_accessible else "不可达"
            print(f"   道路可达性: {accessible}")
        print()
    
    # 示例2: 只分析山峰
    print("\n" + "="*50)
    print("示例2: 只分析山峰")
    print("="*50)
    
    locations_peaks = analyzer.analyze_area(
        bbox=bbox,
        max_locations=3,
        location_types=['mountain_peak'],
        include_light_pollution=False,
        include_road_connectivity=True
    )
    
    print(f"\n找到 {len(locations_peaks)} 个山峰:")
    for i, location in enumerate(locations_peaks, 1):
        print(f"{i}. {location.name}")
        print(f"   海拔: {location.elevation}m")
        if location.prominence:
            print(f"   相对高度: {location.prominence}m")
        if location.height_difference:
            print(f"   高度差: {location.height_difference}m")
        print(f"   评分: {location.stargazing_score}分")
        print()
    
    # 示例3: 只分析天文台
    print("\n" + "="*50)
    print("示例3: 只分析天文台")
    print("="*50)
    
    locations_observatories = analyzer.analyze_area(
        bbox=bbox,
        max_locations=3,
        location_types=['observatory'],
        include_light_pollution=False,
        include_road_connectivity=True
    )
    
    print(f"\n找到 {len(locations_observatories)} 个天文台:")
    for i, location in enumerate(locations_observatories, 1):
        print(f"{i}. {location.name}")
        print(f"   坐标: ({location.latitude:.4f}, {location.longitude:.4f})")
        print(f"   海拔: {location.elevation}m")
        print(f"   评分: {location.stargazing_score}分")
        print(f"   推荐等级: {location.recommendation_level}")
        print()
    
    # 示例4: 只分析观景台
    print("\n" + "="*50)
    print("示例4: 只分析观景台")
    print("="*50)
    
    locations_viewpoints = analyzer.analyze_area(
        bbox=bbox,
        max_locations=3,
        location_types=['viewpoint'],
        include_light_pollution=False,
        include_road_connectivity=True
    )
    
    print(f"\n找到 {len(locations_viewpoints)} 个观景台:")
    for i, location in enumerate(locations_viewpoints, 1):
        print(f"{i}. {location.name}")
        print(f"   坐标: ({location.latitude:.4f}, {location.longitude:.4f})")
        print(f"   海拔: {location.elevation}m")
        if location.height_difference:
            print(f"   高度差: {location.height_difference}m")
        print(f"   评分: {location.stargazing_score}分")
        print(f"   推荐等级: {location.recommendation_level}")
        print()
    
    print("\n" + "="*60)
    print("分析完成！")
    print("="*60)
    print("\n提示:")
    print("- 可以通过修改bbox参数来分析不同的地理区域")
    print("- 可以通过location_types参数来选择特定类型的地点")
    print("- 建议提供光污染KML文件以获得更准确的评分")
    print("- 评分范围为0-100分，分数越高表示观星条件越好")

if __name__ == "__main__":
    demo_analyze_area()