#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据类测试脚本
测试Peak、Observatory和Viewpoint统一为Location类后的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stargazing_place_finder import Location, Peak, Observatory, Viewpoint

def test_unified_location_class():
    """测试统一的Location类"""
    print("=== 测试统一的Location类 ===")
    
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
    
    print(f"山峰: {peak_location.name}")
    print(f"类型: {peak_location.location_type}")
    print(f"是山峰: {peak_location.is_mountain_peak()}")
    print(f"是天文台: {peak_location.is_observatory()}")
    print(f"是观景台: {peak_location.is_viewpoint()}")
    print(f"海拔: {peak_location.elevation}m")
    print(f"相对高度: {peak_location.prominence}m")
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
        observatory_type="光学天文台",
        description="用于深空观测的光学天文台",
        light_pollution_level="极低"
    )
    
    print(f"天文台: {observatory_location.name}")
    print(f"类型: {observatory_location.location_type}")
    print(f"是山峰: {observatory_location.is_mountain_peak()}")
    print(f"是天文台: {observatory_location.is_observatory()}")
    print(f"是观景台: {observatory_location.is_viewpoint()}")
    print(f"天文台类型: {observatory_location.observatory_type}")
    print(f"光污染等级: {observatory_location.light_pollution_level}")
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
    
    print(f"观景台: {viewpoint_location.name}")
    print(f"类型: {viewpoint_location.location_type}")
    print(f"是山峰: {viewpoint_location.is_mountain_peak()}")
    print(f"是天文台: {viewpoint_location.is_observatory()}")
    print(f"是观景台: {viewpoint_location.is_viewpoint()}")
    print(f"观景台类型: {viewpoint_location.viewpoint_type}")
    print(f"景观价值: {viewpoint_location.scenic_value}")
    print()

def test_backward_compatibility():
    """测试向后兼容性"""
    print("=== 测试向后兼容性 ===")
    
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
    
    print(f"Peak别名创建的对象: {peak.name}")
    print(f"类型: {type(peak).__name__}")
    print(f"是否为Location实例: {isinstance(peak, Location)}")
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
        observatory_type="射电天文台"
    )
    
    print(f"Observatory别名创建的对象: {observatory.name}")
    print(f"类型: {type(observatory).__name__}")
    print(f"是否为Location实例: {isinstance(observatory, Location)}")
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
    
    print(f"Viewpoint别名创建的对象: {viewpoint.name}")
    print(f"类型: {type(viewpoint).__name__}")
    print(f"是否为Location实例: {isinstance(viewpoint, Location)}")
    print()

def test_type_checking_methods():
    """测试类型检查方法"""
    print("=== 测试类型检查方法 ===")
    
    locations = [
        Location("山峰", 40.0, 116.0, 1500.0, 10.0, "城镇A", "mountain_peak"),
        Location("天文台", 39.0, 115.0, 1200.0, 15.0, "城镇B", "observatory"),
        Location("观景台", 38.0, 114.0, 800.0, 5.0, "城镇C", "viewpoint")
    ]
    
    for location in locations:
        print(f"{location.name} ({location.location_type}):")
        print(f"  是山峰: {location.is_mountain_peak()}")
        print(f"  是天文台: {location.is_observatory()}")
        print(f"  是观景台: {location.is_viewpoint()}")
        print()

if __name__ == "__main__":
    test_unified_location_class()
    test_backward_compatibility()
    test_type_checking_methods()
    print("所有测试完成！")