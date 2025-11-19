#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Overpass API重试机制

这个脚本用于测试新的Overpass API重试机制是否能够正确处理网络超时和服务器错误。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from stargazing_analyzer.stargazing_place_finder import StarGazingPlaceFinder

def test_overpass_retry():
    """
    测试Overpass API的重试机制
    """
    print("=== 测试Overpass API重试机制 ===")
    print()
    
    # 创建查找器实例
    finder = StarGazingPlaceFinder()
    
    # 测试一个小范围的查询，减少超时概率
    print("1. 测试观景台查询（小范围，带调试信息）...")
    bbox = (39.9, 116.3, 40.0, 116.4)  # 北京小范围 (south, west, north, east)
    print(f"   查询范围: {bbox}")
    
    # 手动调用带调试的方法
    viewpoints_data = finder.get_viewpoints_from_overpass(bbox)
    print(f"   结果: 找到 {len(viewpoints_data)} 个观景台原始数据")
    print()
    
    # 如果有数据，显示前几个
    if viewpoints_data:
        print("   前3个观景台数据:")
        for i, vp in enumerate(viewpoints_data[:3]):
            print(f"   {i+1}. {vp.get('tags', {}).get('name', '未命名')}")
            print(f"      坐标: ({vp.get('lat', 'N/A')}, {vp.get('lon', 'N/A')})")
            print(f"      标签: {vp.get('tags', {})}")
    print()
    
    print("2. 测试完整的观景台查找流程...")
    try:
        viewpoints = finder.find_viewpoints_in_area(bbox, max_viewpoints=10)
        print(f"   结果: 找到 {len(viewpoints)} 个处理后的观景台")
        
        if viewpoints:
            print("   观景台列表:")
            for i, vp in enumerate(viewpoints[:3]):
                print(f"   {i+1}. {vp.name}")
                print(f"      坐标: ({vp.latitude:.4f}, {vp.longitude:.4f})")
                print(f"      海拔: {vp.elevation}m")
                print(f"      类型: {vp.location_type}")
    except Exception as e:
        print(f"   错误: {e}")
    print()
    
    print("=== 测试完成 ===")
    print("如果看到重试信息，说明重试机制正在工作")
    print("如果没有错误信息，说明API调用成功")

def test_simple_query():
    """
    测试简单的Overpass查询
    """
    print("\n=== 测试简单查询 ===")
    
    finder = StarGazingPlaceFinder()
    
    # 构建一个简单的查询
    simple_query = """
    [out:json][timeout:25];
    (
      node["tourism"="viewpoint"](39.9,116.3,40.0,116.4);
    );
    out geom;
    """
    
    print("使用简化查询语句:")
    result = finder._make_overpass_request(simple_query, "观景台", debug=True)
    print(f"结果: {len(result)} 个观景台")

if __name__ == "__main__":
    test_overpass_retry()
    test_simple_query()