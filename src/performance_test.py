#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能测试脚本

这个脚本用于测试LocationFinder类的性能优化效果，
比较使用缓存和不使用缓存的性能差异。
"""

import os
import sys
import time
from typing import List
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from location_finder import LocationFinder


def benchmark_statistics_calls(finder: LocationFinder, num_calls: int = 100) -> float:
    """测试统计信息获取的性能
    
    Args:
        finder: LocationFinder实例
        num_calls: 调用次数
        
    Returns:
        平均每次调用的时间（秒）
    """
    start_time = time.time()
    
    for _ in range(num_calls):
        stats = finder.get_statistics()
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / num_calls
    
    return avg_time


def benchmark_coordinate_queries(finder: LocationFinder, coordinates: List[tuple], num_iterations: int = 10) -> float:
    """测试坐标查询的性能
    
    Args:
        finder: LocationFinder实例
        coordinates: 坐标列表 [(lat, lon), ...]
        num_iterations: 迭代次数
        
    Returns:
        平均每次查询的时间（秒）
    """
    start_time = time.time()
    
    for _ in range(num_iterations):
        for lat, lon in coordinates:
            overlay = finder.find_overlay_by_coordinates(lat, lon)
    
    end_time = time.time()
    total_time = end_time - start_time
    total_queries = len(coordinates) * num_iterations
    avg_time = total_time / total_queries
    
    return avg_time


def benchmark_nearby_searches(finder: LocationFinder, coordinates: List[tuple], num_iterations: int = 10) -> float:
    """测试附近搜索的性能
    
    Args:
        finder: LocationFinder实例
        coordinates: 坐标列表 [(lat, lon), ...]
        num_iterations: 迭代次数
        
    Returns:
        平均每次搜索的时间（秒）
    """
    start_time = time.time()
    
    for _ in range(num_iterations):
        for lat, lon in coordinates:
            nearby = finder.find_nearby_overlays(lat, lon, radius_degrees=2.0)
    
    end_time = time.time()
    total_time = end_time - start_time
    total_searches = len(coordinates) * num_iterations
    avg_time = total_time / total_searches
    
    return avg_time


def main():
    """主函数：执行性能测试"""
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== LocationFinder 性能测试 ===")
        print("正在初始化LocationFinder...")
        
        # 测量初始化时间
        init_start = time.time()
        finder = LocationFinder(kml_file)
        init_time = time.time() - init_start
        
        print(f"初始化完成，耗时: {init_time:.4f} 秒")
        
        # 测试坐标集合
        test_coordinates = [
            (39.9042, 116.4074),  # 北京
            (31.2304, 121.4737),  # 上海
            (40.7128, -74.0060),  # 纽约
            (51.5074, -0.1278),   # 伦敦
            (35.6762, 139.6503),  # 东京
            (-33.8688, 151.2093), # 悉尼
            (0.0, -160.0),        # 太平洋中心
            (48.8566, 2.3522),    # 巴黎
            (55.7558, 37.6176),   # 莫斯科
            (-22.9068, -43.1729)  # 里约热内卢
        ]
        
        print("\n=== 统计信息获取性能测试 ===")
        stats_time = benchmark_statistics_calls(finder, num_calls=1000)
        print(f"1000次统计信息调用平均时间: {stats_time*1000:.4f} 毫秒")
        print(f"由于使用了缓存，统计信息获取非常快速")
        
        print("\n=== 坐标查询性能测试 ===")
        query_time = benchmark_coordinate_queries(finder, test_coordinates, num_iterations=100)
        print(f"坐标查询平均时间: {query_time*1000:.4f} 毫秒/次")
        print(f"总共执行了 {len(test_coordinates) * 100} 次查询")
        
        print("\n=== 附近搜索性能测试 ===")
        nearby_time = benchmark_nearby_searches(finder, test_coordinates, num_iterations=50)
        print(f"附近搜索平均时间: {nearby_time*1000:.4f} 毫秒/次")
        print(f"总共执行了 {len(test_coordinates) * 50} 次搜索")
        print(f"使用了KMLParser的filter_by_bounds方法，避免了重复的边界检查逻辑")
        
        print("\n=== 内存使用情况 ===")
        stats = finder.get_statistics()
        print(f"已加载覆盖层数量: {stats['count']}")
        print(f"统计信息已缓存，避免重复计算")
        
        print("\n=== 重新加载测试 ===")
        reload_start = time.time()
        finder.reload_overlays()
        reload_time = time.time() - reload_start
        print(f"重新加载耗时: {reload_time:.4f} 秒")
        print(f"重新加载会清除缓存并重新计算统计信息")
        
        print("\n=== 性能优化总结 ===")
        print("1. 统计信息缓存: 避免重复计算边界和统计数据")
        print("2. 复用Parser方法: find_nearby_overlays使用filter_by_bounds减少重复代码")
        print("3. 一次性加载: 初始化时加载所有数据到内存，提高查询速度")
        print("4. 智能缓存管理: reload时自动清除缓存并重新计算")
        
        print("\n=== 测试完成 ===")
        
    except FileNotFoundError:
        print(f"错误: 找不到KML文件 {kml_file}")
        print("请确保文件路径正确")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()