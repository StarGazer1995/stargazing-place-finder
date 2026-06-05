#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试统一后的Peak、Observatory、Viewpoint数据类

这个脚本验证三个数据类的统一结构是否正常工作。
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.models import Peak, Observatory, Viewpoint

def test_unified_dataclasses():
    """
    测试统一后的数据类结构
    """
    print("=== 测试统一后的数据类结构 ===")
    
    # 测试Peak数据类
    print("\n1. 测试Peak数据类:")
    peak = Peak(
        name="珠穆朗玛峰",
        latitude=27.9881,
        longitude=86.9250,
        elevation=8848.86,
        location_type="mountain_peak",
        prominence=8848.86,
        height_difference=1000.0,
        distance_to_nearest_town=50.0,
        nearest_town_name="定日县"
    )
    print(f"  名称: {peak.name}")
    print(f"  位置类型: {peak.location_type}")
    print(f"  海拔: {peak.elevation}m")
    print(f"  突起度: {peak.prominence}m")
    print(f"  高度差: {peak.height_difference}m")
    print(f"  距离最近城镇: {peak.distance_to_nearest_town}km")
    print(f"  最近城镇: {peak.nearest_town_name}")
    
    # 测试Observatory数据类
    print("\n2. 测试Observatory数据类:")
    observatory = Observatory(
        name="北京天文馆",
        latitude=39.9388,
        longitude=116.3374,
        elevation=50.0,
        location_type="observatory",
        observatory_type="天象馆",
        description="北京市重要的天文科普场所",
        light_pollution_level="高",
        distance_to_nearest_town=0.0,
        nearest_town_name="北京市"
    )
    print(f"  名称: {observatory.name}")
    print(f"  位置类型: {observatory.location_type}")
    print(f"  天文台类型: {observatory.observatory_type}")
    print(f"  描述: {observatory.description}")
    print(f"  光污染等级: {observatory.light_pollution_level}")
    print(f"  距离最近城镇: {observatory.distance_to_nearest_town}km")
    print(f"  最近城镇: {observatory.nearest_town_name}")
    
    # 测试Viewpoint数据类
    print("\n3. 测试Viewpoint数据类:")
    viewpoint = Viewpoint(
        name="八达岭长城观景台",
        latitude=40.3584,
        longitude=116.0138,
        elevation=1000.0,
        location_type="viewpoint",
        viewpoint_type="观景台",
        description="可以俯瞰长城全景的绝佳观景点",
        scenic_value="优秀",
        distance_to_nearest_town=15.0,
        nearest_town_name="延庆区"
    )
    print(f"  名称: {viewpoint.name}")
    print(f"  位置类型: {viewpoint.location_type}")
    print(f"  观景台类型: {viewpoint.viewpoint_type}")
    print(f"  描述: {viewpoint.description}")
    print(f"  景观价值: {viewpoint.scenic_value}")
    print(f"  距离最近城镇: {viewpoint.distance_to_nearest_town}km")
    print(f"  最近城镇: {viewpoint.nearest_town_name}")
    
    # 测试通用字段
    print("\n4. 验证通用字段:")
    locations = [peak, observatory, viewpoint]
    for i, location in enumerate(locations, 1):
        print(f"  位置 {i}: {location.name}")
        print(f"    - 经纬度: ({location.latitude}, {location.longitude})")
        print(f"    - 海拔: {location.elevation}m")
        print(f"    - 位置类型: {location.location_type}")
        print(f"    - 距离最近城镇: {location.distance_to_nearest_town}km")
        print(f"    - 最近城镇: {location.nearest_town_name}")
        print()
    
    print("✅ 所有数据类测试通过！统一结构工作正常。")

if __name__ == "__main__":
    test_unified_dataclasses()