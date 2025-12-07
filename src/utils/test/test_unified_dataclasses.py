#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据类测试脚本
测试Peak、Observatory和Viewpoint统一为Location类后的功能
"""

import sys
import os

# 添加 src 目录到Python路径以加载顶层包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from stargazing_analyzer.stargazing_place_finder import Location, Peak, Observatory, Viewpoint

def test_unified_location_class():
    """测试统一的Location类"""
    print("=== Testing Unified Location Class ===")
    
    # 测试直接使用Location类创建山峰
    peak_location = Location(
        name="测试山峰",
        latitude=40.0,
        longitude=116.0,
        elevation=1500.0,
        distance_to_nearest_town=15.0,
        nearest_town_name="测试城镇",
        location_type="mountain_peak",
        prominence=500.0,
        height_difference=800.0
    )
    
    print(f"Peak: {peak_location.name}")
    print(f"Type: {peak_location.location_type}")
    print(f"Is mountain peak: {peak_location.is_mountain_peak()}")
    print(f"Is observatory: {peak_location.is_observatory()}")
    print(f"Is viewpoint: {peak_location.is_viewpoint()}")
    print(f"Elevation: {peak_location.elevation}m")
    print(f"Prominence: {peak_location.prominence}m")
    print()
    
    # 测试直接使用Location类创建天文台
    observatory_location = Location(
        name="测试天文台",
        latitude=39.0,
        longitude=115.0,
        elevation=1200.0,
        distance_to_nearest_town=20.0,
        nearest_town_name="天文城",
        location_type="observatory",
        observatory_type="Optical observatory",
        description="用于深空观测的光学天文台",
        light_pollution_level="极低"
    )
    
    print(f"Observatory: {observatory_location.name}")
    print(f"Type: {observatory_location.location_type}")
    print(f"Is mountain peak: {observatory_location.is_mountain_peak()}")
    print(f"Is observatory: {observatory_location.is_observatory()}")
    print(f"Is viewpoint: {observatory_location.is_viewpoint()}")
    print(f"Observatory type: {observatory_location.observatory_type}")
    print(f"Light pollution level: {observatory_location.light_pollution_level}")
    print()
    
    # 测试直接使用Location类创建观景台
    viewpoint_location = Location(
        name="测试观景台",
        latitude=38.0,
        longitude=114.0,
        elevation=800.0,
        distance_to_nearest_town=5.0,
        nearest_town_name="观景镇",
        location_type="viewpoint",
        viewpoint_type="山顶观景台",
        description="可以俯瞰整个山谷的观景台",
        scenic_value="优秀"
    )
    
    print(f"Viewpoint: {viewpoint_location.name}")
    print(f"Type: {viewpoint_location.location_type}")
    print(f"Is mountain peak: {viewpoint_location.is_mountain_peak()}")
    print(f"Is observatory: {viewpoint_location.is_observatory()}")
    print(f"Is viewpoint: {viewpoint_location.is_viewpoint()}")
    print(f"Viewpoint type: {viewpoint_location.viewpoint_type}")
    print(f"Scenic value: {viewpoint_location.scenic_value}")
    print()

def test_backward_compatibility():
    """测试向后兼容性"""
    print("=== Testing Backward Compatibility ===")
    
    # 测试Peak别名
    peak = Peak(
        name="兼容性山峰",
        latitude=41.0,
        longitude=117.0,
        elevation=2000.0,
        distance_to_nearest_town=25.0,
        nearest_town_name="兼容城镇",
        location_type="mountain_peak",
        prominence=600.0
    )
    
    print(f"Object created with Peak alias: {peak.name}")
    print(f"Type: {type(peak).__name__}")
    print(f"Is Location instance: {isinstance(peak, Location)}")
    print()
    
    # 测试Observatory别名
    observatory = Observatory(
        name="兼容性天文台",
        latitude=42.0,
        longitude=118.0,
        elevation=1800.0,
        distance_to_nearest_town=30.0,
        nearest_town_name="兼容天文城",
        location_type="observatory",
        observatory_type="Radio observatory"
    )
    
    print(f"Object created with Observatory alias: {observatory.name}")
    print(f"Type: {type(observatory).__name__}")
    print(f"Is Location instance: {isinstance(observatory, Location)}")
    print()
    
    # 测试Viewpoint别名
    viewpoint = Viewpoint(
        name="兼容性观景台",
        latitude=43.0,
        longitude=119.0,
        elevation=1000.0,
        distance_to_nearest_town=8.0,
        nearest_town_name="兼容观景镇",
        location_type="viewpoint",
        viewpoint_type="湖边观景台"
    )
    
    print(f"Object created with Viewpoint alias: {viewpoint.name}")
    print(f"Type: {type(viewpoint).__name__}")
    print(f"Is Location instance: {isinstance(viewpoint, Location)}")
    print()

def test_type_checking_methods():
    """测试类型检查方法"""
    print("=== Testing Type Checking Methods ===")
    
    locations = [
        Location("山峰", 40.0, 116.0, 1500.0, 10.0, "城镇A", "mountain_peak"),
        Location("天文台", 39.0, 115.0, 1200.0, 15.0, "城镇B", "observatory"),
        Location("观景台", 38.0, 114.0, 800.0, 5.0, "城镇C", "viewpoint")
    ]
    
    for location in locations:
        print(f"{location.name} ({location.location_type}):")
        print(f"  Is mountain peak: {location.is_mountain_peak()}")
        print(f"  Is observatory: {location.is_observatory()}")
        print(f"  Is viewpoint: {location.is_viewpoint()}")
        print()

if __name__ == "__main__":
    test_unified_location_class()
    test_backward_compatibility()
    test_type_checking_methods()
    print("All tests completed!")