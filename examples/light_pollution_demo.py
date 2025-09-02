#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染信息演示脚本

本脚本演示如何使用MountainPeakFinder类查找包含光污染信息的地点，
包括山峰、天文台和观景台。

功能特点：
1. 集成光污染分析器
2. 显示每个地点的光污染等级
3. 按光污染程度排序地点
4. 提供详细的地点信息展示
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mountain_peak_finder import MountainPeakFinder
from src.light_pollution_analyzer import LightPollutionAnalyzer

def display_location_info(location, index):
    """
    显示地点详细信息
    
    Args:
        location: Location对象
        index: 序号
    """
    print(f"{index}. {location.name}")
    print(f"   类型: {location.location_type}")
    print(f"   坐标: ({location.latitude:.4f}, {location.longitude:.4f})")
    print(f"   海拔: {location.elevation:.1f}m")
    print(f"   距离最近城镇: {location.distance_to_nearest_town:.1f}km ({location.nearest_town_name})")
    
    # 显示光污染信息
    if location.light_pollution_level:
        print(f"   光污染等级: {location.light_pollution_level}")
    else:
        print(f"   光污染等级: 未知")
    
    # 显示特定类型的额外信息
    if location.is_mountain_peak() and location.height_difference:
        print(f"   与{location.nearest_town_name}的高度差: {location.height_difference:.1f}m")
        if location.prominence:
            print(f"   相对高度: {location.prominence:.1f}m")
    elif location.is_observatory() and location.observatory_type:
        print(f"   天文台类型: {location.observatory_type}")
    elif location.is_viewpoint():
        if location.viewpoint_type:
            print(f"   观景台类型: {location.viewpoint_type}")
        if location.scenic_value:
            print(f"   景观价值: {location.scenic_value}")
    
    if location.description:
        print(f"   描述: {location.description}")
    print()

def test_light_pollution_integration():
    """
    测试光污染信息集成功能
    """
    print("=== 光污染信息集成演示 ===")
    print()
    
    # 初始化光污染分析器（如果有KML文件的话）
    try:
        light_analyzer = LightPollutionAnalyzer("world_atlas/doc.xml")
        print("✓ 光污染分析器初始化成功")
    except Exception as e:
        print(f"⚠ 光污染分析器初始化失败: {e}")
        print("继续使用默认设置...")
        light_analyzer = None
    
    # 初始化山峰查找器
    finder = MountainPeakFinder(
        min_height_difference=100.0,
        light_pollution_analyzer=light_analyzer
    )
    
    # 测试区域：北京周边
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    print(f"搜索区域: {bbox}")
    print()
    
    # 1. 测试山峰查找（包含光污染信息）
    print("1. 查找山峰（包含光污染信息）")
    print("=" * 50)
    try:
        peaks = finder.find_peaks_in_area(bbox, max_peaks=5)
        if peaks:
            print(f"\n找到 {len(peaks)} 个山峰:")
            print()
            for i, peak in enumerate(peaks, 1):
                display_location_info(peak, i)
        else:
            print("未找到符合条件的山峰")
    except Exception as e:
        print(f"山峰查找出错: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # 2. 测试天文台查找（包含光污染信息）
    print("2. 查找天文台（包含光污染信息）")
    print("=" * 50)
    try:
        observatories = finder.find_observatories_in_area(bbox, max_observatories=5)
        if observatories:
            print(f"\n找到 {len(observatories)} 个天文台:")
            print()
            for i, observatory in enumerate(observatories, 1):
                display_location_info(observatory, i)
        else:
            print("未找到天文台")
    except Exception as e:
        print(f"天文台查找出错: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # 3. 测试观景台查找（包含光污染信息）
    print("3. 查找观景台（包含光污染信息）")
    print("=" * 50)
    try:
        viewpoints = finder.find_viewpoints_in_area(bbox, max_viewpoints=5)
        if viewpoints:
            print(f"\n找到 {len(viewpoints)} 个观景台:")
            print()
            for i, viewpoint in enumerate(viewpoints, 1):
                display_location_info(viewpoint, i)
        else:
            print("未找到观景台")
    except Exception as e:
        print(f"观景台查找出错: {e}")

def test_different_regions():
    """
    测试不同区域的光污染情况
    """
    print("\n\n=== 不同区域光污染对比 ===")
    print()
    
    # 初始化查找器
    try:
        light_analyzer = LightPollutionAnalyzer("world_atlas/doc.xml")
        finder = MountainPeakFinder(light_pollution_analyzer=light_analyzer)
    except:
        finder = MountainPeakFinder()
    
    # 测试区域列表
    regions = [
        {"name": "北京周边", "bbox": (39.5, 115.5, 40.5, 117.5)},
        {"name": "张家口地区", "bbox": (40.5, 114.5, 41.5, 115.5)},
        {"name": "承德地区", "bbox": (40.5, 117.0, 41.5, 118.0)}
    ]
    
    for region in regions:
        print(f"区域: {region['name']}")
        print("-" * 30)
        
        try:
            # 只查找少量观景台作为示例
            viewpoints = finder.find_viewpoints_in_area(region['bbox'], max_viewpoints=3)
            
            if viewpoints:
                for i, vp in enumerate(viewpoints, 1):
                    pollution_info = vp.light_pollution_level or "未知"
                    print(f"{i}. {vp.name} - 光污染: {pollution_info}")
            else:
                print("未找到观景台")
        except Exception as e:
            print(f"查找出错: {e}")
        
        print()

if __name__ == "__main__":
    print("光污染信息集成演示")
    print("=" * 60)
    print()
    
    # 运行主要演示
    test_light_pollution_integration()
    
    # 运行区域对比演示
    test_different_regions()
    
    print("\n演示完成！")
    print("\n说明:")
    print("- 所有地点类型（山峰、天文台、观景台）现在都包含光污染信息")
    print("- 光污染等级有助于评估观星条件")
    print("- 数据按光污染程度排序，优先显示污染较轻的地点")