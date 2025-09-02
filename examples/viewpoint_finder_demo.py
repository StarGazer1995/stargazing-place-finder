#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观景台查找器演示脚本

这个脚本演示如何使用mountain_peak_finder模块中的观景台查找功能。
它会在指定区域内搜索观景台，并显示详细信息。
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mountain_peak_finder import find_viewpoints, StarGazingPlaceFinder, Location

def main():
    """
    主函数：演示观景台查找功能
    """
    print("=== 观景台查找器演示 ===")
    print("正在搜索北京周边的观景台...")
    
    # 定义搜索区域（北京周边）
    # 格式：(south, west, north, east)
    bbox_coords = (39.5, 115.5, 40.5, 117.5)
    south, west, north, east = bbox_coords
    
    print(f"搜索区域：")
    print(f"  南纬: {south}°")
    print(f"  西经: {west}°")
    print(f"  北纬: {north}°")
    print(f"  东经: {east}°")
    print()
    
    try:
        # 使用便捷函数查找观景台
        print("使用便捷函数查找观景台...")
        viewpoints = find_viewpoints(south, west, north, east, max_viewpoints=20)
        
        # 显示结果
        if viewpoints:
            print(f"\n=== 找到 {len(viewpoints)} 个观景台 ===")
            for i, viewpoint in enumerate(viewpoints, 1):
                # 验证这是观景台类型的Location对象
                assert viewpoint.is_viewpoint(), f"期望观景台类型，但得到：{viewpoint.location_type}"
                
                print(f"{i}. {viewpoint.name}")
                print(f"   位置类型: {viewpoint.location_type}")
                print(f"   观景台类型: {viewpoint.viewpoint_type}")
                print(f"   坐标: ({viewpoint.latitude:.4f}, {viewpoint.longitude:.4f})")
                print(f"   海拔: {viewpoint.elevation:.1f}m")
                print(f"   距离最近城镇: {viewpoint.distance_to_nearest_town:.1f}km ({viewpoint.nearest_town_name})")
                if viewpoint.description:
                    print(f"   描述: {viewpoint.description}")
                if viewpoint.scenic_value:
                    print(f"   景观价值: {viewpoint.scenic_value}/10")
                print()
        else:
            print("\n未找到符合条件的观景台")
            
        # 演示使用类方法
        print("\n=== 使用MountainPeakFinder类方法 ===")
        finder = StarGazingPlaceFinder()
        viewpoints_class = finder.find_viewpoints_in_area(bbox_coords, max_viewpoints=10)
        
        if viewpoints_class:
            # 验证所有结果都是观景台类型
            viewpoint_count = sum(1 for vp in viewpoints_class if vp.is_viewpoint())
            print(f"通过类方法找到 {viewpoint_count} 个观景台")
            
            # 显示前3个结果
            for i, viewpoint in enumerate(viewpoints_class[:3], 1):
                assert viewpoint.is_viewpoint(), f"期望观景台类型，但得到：{viewpoint.location_type}"
                print(f"{i}. {viewpoint.name} - 海拔: {viewpoint.elevation:.1f}m - 类型: {viewpoint.location_type}")
        
    except Exception as e:
        print(f"搜索过程中发生错误: {e}")
        print("请检查网络连接和API可用性")

if __name__ == "__main__":
    main()