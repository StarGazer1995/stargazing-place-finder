#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观星地点综合分析器使用示例

展示如何使用StargazingLocationAnalyzer进行观星地点分析，
包括山峰查找、光污染分析和道路连通性检测的综合评估。
"""

import sys
import os
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.stargazing_location_analyzer import (
    StargazingLocationAnalyzer,
    analyze_stargazing_area
)

def example_basic_analysis():
    """
    示例1: 基础分析（含光污染数据）
    """
    print("\n=== 示例1: 基础观星地点分析 ===")
    print("分析区域: 北京香山地区")
    print("功能: 山峰查找 + 光污染分析 + 道路连通性检测")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"错误: 光污染数据文件 {kml_file} 不存在")
        print("请从光污染地图网站下载KML文件后再运行此示例")
        return
    
    # 创建分析器（使用光污染数据）
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file,  # 使用光污染数据
        min_height_difference=100.0,  # 最小高度差100米
        road_search_radius_km=10.0    # 道路搜索半径10公里
    )
    
    # 定义香山地区边界框
    bbox = (39.98, 116.18, 40.02, 116.22)  # (south, west, north, east)
    
    # 执行分析
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=5,
        network_type='drive',
        include_light_pollution=True,  # 强制包含光污染分析
        include_road_connectivity=True
    )
    
    # 显示结果
    if locations:
        print(f"\n找到 {len(locations)} 个观星地点:")
        analyzer.print_analysis_summary(locations)
        
        # 保存结果
        output_file = "xiangshan_stargazing_analysis.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"\n结果已保存到: {output_file}")
        
        # 获取前3个推荐
        top_3 = analyzer.get_top_recommendations(locations, 3)
        print(f"\n前3个推荐地点:")
        for i, loc in enumerate(top_3, 1):
            print(f"{i}. {loc.name} (评分: {loc.stargazing_score:.1f})")
    else:
        print("未找到符合条件的观星地点")

def example_advanced_analysis():
    """
    示例2: 高级光污染分析（扩大搜索范围）
    """
    print("\n=== 示例2: 高级光污染分析 ===")
    print("分析更大区域以获得更多候选地点")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"错误: 光污染数据文件 {kml_file} 不存在")
        print("请从光污染地图网站下载KML文件后再运行此示例")
        return
    
    print(f"使用光污染数据文件: {kml_file}")
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file,
        min_height_difference=150.0,
        road_search_radius_km=15.0
    )
    
    # 分析更大的区域
    bbox = (39.9, 116.0, 40.1, 116.3)
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=8,
        network_type='drive',
        include_light_pollution=True,  # 强制包含光污染分析
        include_road_connectivity=True
    )
    
    if locations:
        print(f"\n找到 {len(locations)} 个观星地点（含光污染分析）:")
        analyzer.print_analysis_summary(locations)
        
        output_file = "beijing_stargazing_with_light_pollution.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"\n结果已保存到: {output_file}")
    else:
        print("未找到符合条件的观星地点")

def example_batch_analysis():
    """
    示例3: 批量分析多个地区
    """
    print("\n=== 示例3: 批量分析多个地区 ===")
    
    # 定义多个分析区域
    regions = {
        "怀柔地区": (40.3, 116.6, 40.4, 116.7),
        "密云地区": (40.35, 116.8, 40.45, 116.9),
        "延庆地区": (40.45, 115.9, 40.55, 116.0)
    }
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"错误: 光污染数据文件 {kml_file} 不存在")
        print("批量分析需要光污染数据，请先准备KML文件")
        return
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file,  # 强制使用光污染数据
        min_height_difference=120.0,
        road_search_radius_km=12.0
    )
    
    all_results = {}
    
    for region_name, bbox in regions.items():
        print(f"\n正在分析: {region_name}")
        
        locations = analyzer.analyze_area(
            bbox=bbox,
            max_locations=3,
            network_type='drive',
            include_light_pollution=True,  # 强制包含光污染分析
            include_road_connectivity=True
        )
        
        all_results[region_name] = locations
        
        if locations:
            print(f"  找到 {len(locations)} 个地点")
            top_location = max(locations, key=lambda x: x.stargazing_score)
            print(f"  最佳地点: {top_location.name} (评分: {top_location.stargazing_score:.1f})")
        else:
            print("  未找到符合条件的地点")
    
    # 汇总所有结果
    all_locations = []
    for region_locations in all_results.values():
        all_locations.extend(region_locations)
    
    if all_locations:
        print(f"\n=== 批量分析汇总 ===")
        print(f"总共找到 {len(all_locations)} 个观星地点")
        
        # 获取全局前5个推荐
        top_5_global = analyzer.get_top_recommendations(all_locations, 5)
        print(f"\n全局前5个推荐:")
        for i, loc in enumerate(top_5_global, 1):
            print(f"{i}. {loc.name} (评分: {loc.stargazing_score:.1f}, 海拔: {loc.elevation:.1f}m)")
        
        # 保存汇总结果
        output_file = "batch_stargazing_analysis.json"
        analyzer.save_results_to_json(all_locations, output_file)
        print(f"\n汇总结果已保存到: {output_file}")

def example_custom_parameters():
    """
    示例4: 自定义参数分析
    """
    print("\n=== 示例4: 自定义参数分析 ===")
    print("使用严格的筛选条件")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"错误: 光污染数据文件 {kml_file} 不存在")
        print("自定义参数分析需要光污染数据，请先准备KML文件")
        return
    
    # 创建严格条件的分析器
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file,  # 强制使用光污染数据
        min_height_difference=200.0,  # 更高的高度差要求
        road_search_radius_km=20.0    # 更大的道路搜索范围
    )
    
    # 分析更大的区域
    bbox = (39.8, 115.8, 40.3, 116.5)
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=10,
        network_type='drive',
        include_light_pollution=True,  # 强制包含光污染分析
        include_road_connectivity=True
    )
    
    if locations:
        print(f"\n严格条件下找到 {len(locations)} 个观星地点:")
        
        # 按不同标准排序显示
        print("\n按海拔排序:")
        by_elevation = sorted(locations, key=lambda x: x.elevation, reverse=True)[:3]
        for i, loc in enumerate(by_elevation, 1):
            print(f"{i}. {loc.name} - 海拔: {loc.elevation:.1f}m")
        
        print("\n按高度差排序:")
        by_height_diff = sorted(locations, key=lambda x: x.height_difference, reverse=True)[:3]
        for i, loc in enumerate(by_height_diff, 1):
            print(f"{i}. {loc.name} - 高度差: {loc.height_difference:.1f}m")
        
        print("\n按综合评分排序:")
        by_score = sorted(locations, key=lambda x: x.stargazing_score, reverse=True)[:3]
        for i, loc in enumerate(by_score, 1):
            print(f"{i}. {loc.name} - 评分: {loc.stargazing_score:.1f}")
        
        output_file = "custom_parameters_analysis.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"\n结果已保存到: {output_file}")
    else:
        print("严格条件下未找到符合要求的观星地点")
        print("建议降低筛选标准或扩大搜索范围")

def example_convenience_function():
    """
    示例5: 使用便捷函数进行快速分析
    """
    print("\n=== 示例5: 便捷函数快速分析 ===")
    print("使用 analyze_stargazing_area() 函数")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"错误: 光污染数据文件 {kml_file} 不存在")
        print("便捷函数分析需要光污染数据，请先准备KML文件")
        return
    
    # 使用便捷函数进行快速分析
    locations = analyze_stargazing_area(
        south=40.0, west=116.2, north=40.1, east=116.3,
        kml_file_path=kml_file,  # 强制使用光污染数据
        max_locations=5,
        min_height_diff=80.0,
        road_radius_km=8.0,
        network_type='drive'
    )
    
    if locations:
        print(f"\n便捷函数找到 {len(locations)} 个观星地点:")
        
        for i, loc in enumerate(locations, 1):
            print(f"{i}. {loc.name}")
            print(f"   坐标: ({loc.latitude:.4f}, {loc.longitude:.4f})")
            print(f"   海拔: {loc.elevation:.1f}m")
            print(f"   评分: {loc.stargazing_score:.1f}/100")
            print(f"   推荐: {loc.recommendation_level}")
            print(f"   道路: {'可达' if loc.road_accessible else '不可达'}")
            print()
        
        # 保存便捷函数结果
        analyzer = StargazingLocationAnalyzer()
        output_file = "convenience_function_analysis.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"结果已保存到: {output_file}")
    else:
        print("便捷函数未找到符合条件的观星地点")

def main():
    """
    主函数 - 运行所有示例
    """
    print("观星地点综合分析器 - 使用示例")
    print("=" * 60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 检查光污染数据文件是否存在
        kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
        if not os.path.exists(kml_file):
            print(f"\n⚠️  警告: 光污染数据文件 {kml_file} 不存在")
            print("光污染数据是观星地点分析的强制要求")
            print("请从以下网站下载光污染地图KML文件:")
            print("- Light Pollution Map: https://www.lightpollutionmap.info/")
            print("- Dark Site Finder: https://darksitefinder.com/")
            print("\n下载后请将文件重命名为 'light_pollution_map.kml' 并放在项目根目录")
            return
        
        # 运行各个示例
        example_basic_analysis()
        example_advanced_analysis()
        example_batch_analysis()
        example_custom_parameters()
        example_convenience_function()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n生成的文件:")
        output_files = [
            "xiangshan_stargazing_analysis.json",
            "beijing_stargazing_with_light_pollution.json",
            "batch_stargazing_analysis.json",
            "custom_parameters_analysis.json",
            "convenience_function_analysis.json"
        ]
        
        for filename in output_files:
            if os.path.exists(filename):
                print(f"✓ {filename}")
            else:
                print(f"- {filename} (未生成)")
        
        print("\n使用提示:")
        print("1. 根据实际需求调整搜索范围和参数")
        print("2. 有光污染KML文件时可获得更准确的评估")
        print("3. 可以集成到现有的观星项目中")
        print("4. 支持批量分析和结果比较")
        
    except Exception as e:
        print(f"\n运行示例时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()