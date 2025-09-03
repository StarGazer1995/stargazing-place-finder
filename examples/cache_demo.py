#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存功能演示脚本

本脚本演示了山峰查找器中的缓存功能，包括：
1. 启用缓存的查找器使用
2. 第一次查询（从网络获取并缓存）
3. 第二次查询（从缓存获取）
4. 缓存管理功能（清除缓存、查看缓存信息）
5. 禁用缓存的查找器对比
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.stargazing_place_finder import StarGazingPlaceFinder
    from src.light_pollution_analyzer import LightPollutionAnalyzer
except ImportError:
    from stargazing_place_finder import StarGazingPlaceFinder
    from light_pollution_analyzer import LightPollutionAnalyzer

def main():
    """
    主函数：演示缓存功能
    """
    print("=== 山峰查找器缓存功能演示 ===")
    
    # 定义测试区域（北京周边）
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    max_locations = 10
    
    print(f"\n测试区域: {bbox}")
    print(f"最大地点数量: {max_locations}")
    
    # 1. 创建启用缓存的查找器
    print("\n=== 1. 创建启用缓存的查找器 ===")
    finder_with_cache = StarGazingPlaceFinder(
        min_height_difference=100.0,
        light_pollution_analyzer=LightPollutionAnalyzer("world_atlas/doc.xml"),
        enable_cache=True,
        cache_expiry_hours=24
    )
    print("✓ 已创建启用缓存的查找器")
    
    # 2. 第一次查询（从网络获取并缓存）
    print("\n=== 2. 第一次查询山峰（从网络获取并缓存） ===")
    start_time = time.time()
    peaks_first = finder_with_cache.find_peaks_in_area(bbox, max_locations)
    first_query_time = time.time() - start_time
    
    print(f"第一次查询结果: 找到 {len(peaks_first)} 个山峰")
    print(f"第一次查询耗时: {first_query_time:.2f} 秒")
    
    if peaks_first:
        print("\n前3个山峰:")
        for i, peak in enumerate(peaks_first[:3], 1):
            print(f"  {i}. {peak.name} - 海拔: {peak.elevation:.1f}m")
    
    # 3. 第二次查询（从缓存获取）
    print("\n=== 3. 第二次查询山峰（从缓存获取） ===")
    start_time = time.time()
    peaks_second = finder_with_cache.find_peaks_in_area(bbox, max_locations)
    second_query_time = time.time() - start_time
    
    print(f"第二次查询结果: 找到 {len(peaks_second)} 个山峰")
    print(f"第二次查询耗时: {second_query_time:.2f} 秒")
    print(f"缓存加速比: {first_query_time/second_query_time:.1f}x")
    
    # 验证结果一致性
    if len(peaks_first) == len(peaks_second):
        print("✓ 缓存结果与原始结果一致")
    else:
        print("⚠️ 缓存结果与原始结果不一致")
    
    # 4. 缓存管理功能演示
    print("\n=== 4. 缓存管理功能演示 ===")
    
    # 查看缓存信息
    cache_info = finder_with_cache.get_cache_info()
    if cache_info:
        print(f"缓存总大小: {cache_info['total_size']}")
        print(f"缓存文件数量: {cache_info['file_count']}")
        print(f"缓存过期时间: {cache_info['expiry_hours']} 小时")
    
    # 测试其他类型的地点查询
    print("\n=== 5. 测试其他类型地点的缓存 ===")
    
    # 查询观景台
    print("\n查询观景台...")
    start_time = time.time()
    viewpoints_first = finder_with_cache.find_viewpoints_in_area(bbox, max_locations)
    viewpoints_time_1 = time.time() - start_time
    print(f"第一次查询观景台: 找到 {len(viewpoints_first)} 个，耗时 {viewpoints_time_1:.2f} 秒")
    
    start_time = time.time()
    viewpoints_second = finder_with_cache.find_viewpoints_in_area(bbox, max_locations)
    viewpoints_time_2 = time.time() - start_time
    print(f"第二次查询观景台: 找到 {len(viewpoints_second)} 个，耗时 {viewpoints_time_2:.2f} 秒")
    
    if viewpoints_time_1 > 0:
        print(f"观景台查询缓存加速比: {viewpoints_time_1/viewpoints_time_2:.1f}x")
    
    # 查询天文台
    print("\n查询天文台...")
    start_time = time.time()
    observatories_first = finder_with_cache.find_observatories_in_area(bbox, max_locations)
    observatories_time_1 = time.time() - start_time
    print(f"第一次查询天文台: 找到 {len(observatories_first)} 个，耗时 {observatories_time_1:.2f} 秒")
    
    start_time = time.time()
    observatories_second = finder_with_cache.find_observatories_in_area(bbox, max_locations)
    observatories_time_2 = time.time() - start_time
    print(f"第二次查询天文台: 找到 {len(observatories_second)} 个，耗时 {observatories_time_2:.2f} 秒")
    
    if observatories_time_1 > 0:
        print(f"天文台查询缓存加速比: {observatories_time_1/observatories_time_2:.1f}x")
    
    # 6. 清除缓存演示
    print("\n=== 6. 清除缓存演示 ===")
    print("清除缓存前的信息:")
    cache_info_before = finder_with_cache.get_cache_info()
    if cache_info_before:
        print(f"  缓存文件数量: {cache_info_before['file_count']}")
        print(f"  缓存总大小: {cache_info_before['total_size']}")
    
    finder_with_cache.clear_cache()
    print("✓ 已清除缓存")
    
    cache_info_after = finder_with_cache.get_cache_info()
    if cache_info_after:
        print(f"清除缓存后的信息:")
        print(f"  缓存文件数量: {cache_info_after['file_count']}")
        print(f"  缓存总大小: {cache_info_after['total_size']}")
    
    # 7. 禁用缓存的查找器对比
    print("\n=== 7. 禁用缓存的查找器对比 ===")
    finder_no_cache = StarGazingPlaceFinder(
        min_height_difference=100.0,
        light_pollution_analyzer=LightPollutionAnalyzer("world_atlas/doc.xml"),
        enable_cache=False
    )
    
    print("\n使用禁用缓存的查找器查询山峰...")
    start_time = time.time()
    peaks_no_cache = finder_no_cache.find_peaks_in_area(bbox, max_locations)
    no_cache_time = time.time() - start_time
    
    print(f"禁用缓存查询结果: 找到 {len(peaks_no_cache)} 个山峰")
    print(f"禁用缓存查询耗时: {no_cache_time:.2f} 秒")
    
    print("\n=== 演示完成 ===")
    print("\n总结:")
    print(f"- 启用缓存可以显著减少重复查询的时间")
    print(f"- 缓存功能支持山峰、观景台、天文台等所有类型的地点查询")
    print(f"- 可以通过缓存管理功能查看和清除缓存")
    print(f"- 缓存基于查询区域和参数，确保结果的准确性")

if __name__ == "__main__":
    main()