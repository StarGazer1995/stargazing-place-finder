#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存坐标查询功能演示脚本

本脚本演示如何使用LocationCache类的新功能：
1. 根据坐标查找缓存中的特定地点
2. 根据中心坐标和半径查找范围内的所有地点

使用方法:
    python examples/cache_coordinate_demo.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder, LocationCache
    from src.light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
except ImportError:
    from stargazing_place_finder import StarGazingPlaceFinder, LocationCache
    from light_pollution_analyzer import LightPollutionAnalyzer

def main():
    """
    演示缓存坐标查询功能
    """
    print("=== 缓存坐标查询功能演示 ===")
    print()
    
    # 创建查找器实例（启用缓存）
    print("🔧 初始化查找器...")
    try:
        light_analyzer = LightPollutionAnalyzer("world_atlas/doc.xml")
        finder = StarGazingPlaceFinder(
            min_height_difference=100.0,
            light_pollution_analyzer=light_analyzer,
            enable_cache=True,
            cache_expiry_hours=24*365  # 缓存1年
        )
    except Exception as e:
        print(f"⚠️ 光污染分析器初始化失败: {e}")
        finder = StarGazingPlaceFinder(
            min_height_difference=100.0,
            enable_cache=True,
            cache_expiry_hours=24*365
        )
    
    print("✅ 查找器初始化完成")
    print()
    
    # 定义搜索区域（北京周边）
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    print(f"📍 搜索区域: {bbox}")
    print()
    
    # 1. 首先获取一些数据并缓存
    print("=== 步骤1: 获取并缓存地点数据 ===")
    
    print("🔍 查找山峰...")
    peaks = finder.find_peaks_in_area(bbox, max_locations=20)
    print(f"找到 {len(peaks)} 个山峰")
    
    print("🔍 查找观景台...")
    viewpoints = finder.find_viewpoints_in_area(bbox, max_viewpoints=10)
    print(f"找到 {len(viewpoints)} 个观景台")
    
    print()
    
    # 2. 演示根据坐标查找特定地点
    print("=== 步骤2: 根据坐标查找特定地点 ===")
    
    if peaks:
        # 使用第一个山峰的坐标进行演示
        target_peak = peaks[0]
        print(f"🎯 目标山峰: {target_peak.name}")
        print(f"   坐标: ({target_peak.latitude:.6f}, {target_peak.longitude:.6f})")
        print()
        
        # 精确匹配
        print("🔍 精确坐标匹配:")
        found_location = finder.cache.get_location_by_coordinates(
            "山峰", 
            target_peak.latitude, 
            target_peak.longitude,
            tolerance=0.0001  # 很小的容差
        )
        
        if found_location:
            print(f"   找到地点: {found_location.name}")
            print(f"   海拔: {found_location.elevation:.1f}m")
        print()
        
        # 模糊匹配（稍微偏移坐标）
        print("🔍 模糊坐标匹配（偏移0.0005度）:")
        offset_lat = target_peak.latitude + 0.0005
        offset_lon = target_peak.longitude + 0.0005
        
        found_location = finder.cache.get_location_by_coordinates(
            "山峰", 
            offset_lat, 
            offset_lon,
            tolerance=0.001  # 较大的容差
        )
        
        if found_location:
            print(f"   找到地点: {found_location.name}")
            print(f"   实际坐标: ({found_location.latitude:.6f}, {found_location.longitude:.6f})")
            print(f"   查询坐标: ({offset_lat:.6f}, {offset_lon:.6f})")
        print()
        
        # 测试找不到的情况
        print("🔍 测试找不到的情况（远离的坐标）:")
        finder.cache.get_location_by_coordinates(
            "山峰", 
            target_peak.latitude + 1.0,  # 偏移1度
            target_peak.longitude + 1.0,
            tolerance=0.001
        )
        print()
    
    # 3. 演示根据半径查找范围内地点
    print("=== 步骤3: 根据半径查找范围内地点 ===")
    
    if peaks:
        # 使用第一个山峰作为中心点
        center_peak = peaks[0]
        print(f"🎯 中心点: {center_peak.name}")
        print(f"   坐标: ({center_peak.latitude:.6f}, {center_peak.longitude:.6f})")
        print()
        
        # 查找5公里范围内的山峰
        print("🔍 查找5公里范围内的山峰:")
        nearby_peaks = finder.cache.get_locations_in_radius(
            "山峰",
            center_peak.latitude,
            center_peak.longitude,
            radius_km=5.0
        )
        
        for i, peak in enumerate(nearby_peaks[:5], 1):  # 只显示前5个
            # 计算实际距离
            distance = finder.calculate_distance(
                center_peak.latitude, center_peak.longitude,
                peak.latitude, peak.longitude
            )
            print(f"   {i}. {peak.name}")
            print(f"      坐标: ({peak.latitude:.6f}, {peak.longitude:.6f})")
            print(f"      距离: {distance:.2f}km")
            print(f"      海拔: {peak.elevation:.1f}m")
        print()
        
        # 查找10公里范围内的观景台
        if viewpoints:
            print("🔍 查找10公里范围内的观景台:")
            nearby_viewpoints = finder.cache.get_locations_in_radius(
                "观景台",
                center_peak.latitude,
                center_peak.longitude,
                radius_km=10.0
            )
            
            for i, viewpoint in enumerate(nearby_viewpoints[:3], 1):  # 只显示前3个
                distance = finder.calculate_distance(
                    center_peak.latitude, center_peak.longitude,
                    viewpoint.latitude, viewpoint.longitude
                )
                print(f"   {i}. {viewpoint.name}")
                print(f"      坐标: ({viewpoint.latitude:.6f}, {viewpoint.longitude:.6f})")
                print(f"      距离: {distance:.2f}km")
                print(f"      海拔: {viewpoint.elevation:.1f}m")
            print()
    
    # 4. 演示错误处理
    print("=== 步骤4: 错误处理演示 ===")
    
    # 查找不存在的地点类型
    print("🔍 查找不存在的地点类型:")
    finder.cache.get_location_by_coordinates(
        "不存在的类型",
        40.0, 116.0,
        tolerance=0.001
    )
    print()
    
    # 查找空缓存的地点类型
    print("🔍 查找空缓存的地点类型:")
    finder.cache.get_locations_in_radius(
        "天文台",  # 假设没有缓存天文台数据
        40.0, 116.0,
        radius_km=10.0
    )
    print()
    
    # 5. 显示缓存信息
    print("=== 缓存信息 ===")
    cache_info = finder.get_cache_info()
    if cache_info:
        print(f"📁 缓存目录: {cache_info['cache_dir']}")
        print(f"📄 缓存文件数: {cache_info['file_count']}")
        print(f"💾 总大小: {cache_info['total_size']}")
        print(f"⏰ 过期时间: {cache_info['expiry_hours']:.0f} 小时")
    print()
    
    print("=== 演示完成 ===")
    print("\n💡 新功能总结:")
    print("   ✅ get_location_by_coordinates(): 根据坐标精确查找地点")
    print("   ✅ get_locations_in_radius(): 根据半径查找范围内地点")
    print("   ✅ 支持容差匹配和距离排序")
    print("   ✅ 完善的错误处理和用户反馈")

if __name__ == "__main__":
    main()