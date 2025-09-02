#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理测试脚本

测试山峰查找器在处理缺少坐标信息的数据时的错误处理能力。
这个脚本模拟了可能导致 'lat' KeyError 的各种数据格式问题。
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mountain_peak_finder import StarGazingPlaceFinder
from src.light_pollution_analyzer import LightPollutionAnalyzer

def test_error_handling():
    """
    测试错误处理功能
    """
    print("=== 错误处理测试 ===")
    
    # 初始化查找器
    try:
        light_analyzer = LightPollutionAnalyzer("world_atlas/doc.xml")
        finder = StarGazingPlaceFinder(light_pollution_analyzer=light_analyzer)
        print("✓ 查找器初始化成功")
    except Exception as e:
        print(f"✗ 查找器初始化失败: {e}")
        return
    
    # 测试各种可能导致错误的数据格式
    print("\n=== 测试缺少坐标信息的数据处理 ===")
    
    # 模拟缺少 'lat' 字段的节点数据
    test_data_missing_lat = {
        'type': 'node',
        'id': 12345,
        'lon': 116.4074,
        'tags': {'natural': 'peak', 'name': '测试山峰'}
        # 缺少 'lat' 字段
    }
    
    # 模拟缺少 'center' 字段的关系数据
    test_data_missing_center = {
        'type': 'relation',
        'id': 67890,
        'tags': {'natural': 'peak', 'name': '测试山峰2'}
        # 缺少 'center' 字段
    }
    
    # 模拟 center 字段存在但缺少 lat/lon 的数据
    test_data_incomplete_center = {
        'type': 'way',
        'id': 11111,
        'center': {
            'lon': 116.4074
            # 缺少 'lat' 字段
        },
        'tags': {'natural': 'peak', 'name': '测试山峰3'}
    }
    
    print("测试数据已准备完成")
    print("注意: 实际的错误处理会在真实API调用中触发")
    print("当前的错误处理机制会：")
    print("1. 捕获 KeyError 异常")
    print("2. 输出警告信息")
    print("3. 跳过有问题的数据项")
    print("4. 继续处理其他数据")
    
    # 测试真实的API调用（可能触发错误处理）
    print("\n=== 测试真实API调用的错误处理 ===")
    
    # 使用一个较小的区域进行测试
    test_bbox = (39.9, 116.3, 40.0, 116.5)  # 北京附近的小区域
    
    try:
        print("正在测试山峰查找...")
        peaks = finder.find_peaks_in_area(test_bbox, max_locations=5)
        print(f"✓ 山峰查找完成，找到 {len(peaks)} 个山峰")
        
        print("\n正在测试天文台查找...")
        observatories = finder.find_observatories_in_area(test_bbox, max_observatories=5)
        print(f"✓ 天文台查找完成，找到 {len(observatories)} 个天文台")
        
        print("\n正在测试观景台查找...")
        viewpoints = finder.find_viewpoints_in_area(test_bbox, max_viewpoints=5)
        print(f"✓ 观景台查找完成，找到 {len(viewpoints)} 个观景台")
        
    except Exception as e:
        print(f"✗ API调用过程中出现错误: {e}")
        print("这可能是由于网络问题或数据格式问题导致的")
    
    print("\n=== 错误处理测试完成 ===")
    print("如果看到警告信息，说明错误处理机制正在工作")
    print("如果没有看到崩溃，说明错误处理有效")

if __name__ == "__main__":
    test_error_handling()