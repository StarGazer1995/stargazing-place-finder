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
    print("\n=== Example 1: Basic Stargazing Location Analysis ===")
    print("Analysis area: Beijing Xiangshan area")
    print("Features: Peak finding + Light pollution analysis + Road connectivity detection")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"Error: Light pollution data file {kml_file} does not exist")
        print("Please download KML file from light pollution map website before running this example")
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
        print(f"\nFound {len(locations)} stargazing locations:")
        analyzer.print_analysis_summary(locations)
        
        # 保存结果
        output_file = "xiangshan_stargazing_analysis.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"\nResults saved to: {output_file}")
        
        # 获取前3个推荐
        top_3 = analyzer.get_top_recommendations(locations, 3)
        print(f"\nTop 3 recommended locations:")
        for i, loc in enumerate(top_3, 1):
            print(f"{i}. {loc.name} (Score: {loc.stargazing_score:.1f})")
    else:
        print("No suitable stargazing locations found")

def example_advanced_analysis():
    """
    示例2: 高级光污染分析（扩大搜索范围）
    """
    print("\n=== Example 2: Advanced Light Pollution Analysis ===")
    print("Analyzing larger area to get more candidate locations")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"Error: Light pollution data file {kml_file} does not exist")
        print("Please download the KML file from the light pollution map website before running this example")
        return
    
    print(f"Using light pollution data file: {kml_file}")
    
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
        print(f"\nFound {len(locations)} stargazing locations (with light pollution analysis):")
        analyzer.print_analysis_summary(locations)
        
        output_file = "beijing_stargazing_with_light_pollution.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"\nResults saved to: {output_file}")
    else:
        print("No suitable stargazing locations found")

def example_batch_analysis():
    """
    示例3: 批量分析多个地区
    """
    print("\n=== Example 3: Batch Analysis of Multiple Areas ===")
    
    # 定义多个分析区域
    regions = {
        "怀柔地区": (40.3, 116.6, 40.4, 116.7),
        "密云地区": (40.35, 116.8, 40.45, 116.9),
        "延庆地区": (40.45, 115.9, 40.55, 116.0)
    }
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"Error: Light pollution data file {kml_file} does not exist")
        print("Batch analysis requires light pollution data, please prepare KML file first")
        return
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file,  # 强制使用光污染数据
        min_height_difference=120.0,
        road_search_radius_km=12.0
    )
    
    all_results = {}
    
    for region_name, bbox in regions.items():
        print(f"\nAnalyzing: {region_name}")
        
        locations = analyzer.analyze_area(
            bbox=bbox,
            max_locations=3,
            network_type='drive',
            include_light_pollution=True,  # 强制包含光污染分析
            include_road_connectivity=True
        )
        
        all_results[region_name] = locations
        
        if locations:
            print(f"  Found {len(locations)} locations")
            top_location = max(locations, key=lambda x: x.stargazing_score)
            print(f"  Best location: {top_location.name} (Score: {top_location.stargazing_score:.1f})")
        else:
            print("  No suitable locations found")
    
    # 汇总所有结果
    all_locations = []
    for region_locations in all_results.values():
        all_locations.extend(region_locations)
    
    if all_locations:
        print(f"\n=== Batch Analysis Summary ===")
        print(f"Total found {len(all_locations)} stargazing locations")
        
        # 获取全局前5个推荐
        top_5_global = analyzer.get_top_recommendations(all_locations, 5)
        print(f"\nGlobal top 5 recommendations:")
        for i, loc in enumerate(top_5_global, 1):
            print(f"{i}. {loc.name} (Score: {loc.stargazing_score:.1f}, Elevation: {loc.elevation:.1f}m)")
        
        # 保存汇总结果
        output_file = "batch_stargazing_analysis.json"
        analyzer.save_results_to_json(all_locations, output_file)
        print(f"\nSummary results saved to: {output_file}")

def example_custom_parameters():
    """
    示例4: 自定义参数分析
    """
    print("\n=== Example 4: Custom Parameters Analysis ===")
    print("Using strict filtering criteria")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"Error: Light pollution data file {kml_file} does not exist")
        print("Custom parameter analysis requires light pollution data, please prepare KML file first")
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
        print(f"\nFound {len(locations)} stargazing locations under strict conditions:")
        
        # 按不同标准排序显示
        print("\nSorted by elevation:")
        by_elevation = sorted(locations, key=lambda x: x.elevation, reverse=True)[:3]
        for i, loc in enumerate(by_elevation, 1):
            print(f"{i}. {loc.name} - Elevation: {loc.elevation:.1f}m")
        
        print("\nSorted by height difference:")
        by_height_diff = sorted(locations, key=lambda x: x.height_difference, reverse=True)[:3]
        for i, loc in enumerate(by_height_diff, 1):
            print(f"{i}. {loc.name} - Height difference: {loc.height_difference:.1f}m")
        
        print("\nSorted by comprehensive score:")
        by_score = sorted(locations, key=lambda x: x.stargazing_score, reverse=True)[:3]
        for i, loc in enumerate(by_score, 1):
            print(f"{i}. {loc.name} - Score: {loc.stargazing_score:.1f}")
        
        output_file = "custom_parameters_analysis.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"\nResults saved to: {output_file}")
    else:
        print("No suitable stargazing locations found under strict conditions")
        print("Suggest lowering filtering criteria or expanding search range")

def example_convenience_function():
    """
    示例5: 使用便捷函数进行快速分析
    """
    print("\n=== Example 5: Quick Analysis with Convenience Function ===")
    print("Using analyze_stargazing_area() function")
    
    # 检查光污染数据文件
    kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
    if not os.path.exists(kml_file):
        print(f"Error: Light pollution data file {kml_file} does not exist")
        print("Convenience function analysis requires light pollution data, please prepare KML file first")
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
        print(f"\nConvenience function found {len(locations)} stargazing locations:")
        
        for i, loc in enumerate(locations, 1):
            print(f"{i}. {loc.name}")
            print(f"   Coordinates: ({loc.latitude:.4f}, {loc.longitude:.4f})")
            print(f"   Elevation: {loc.elevation:.1f}m")
            print(f"   Score: {loc.stargazing_score:.1f}/100")
            print(f"   Recommendation: {loc.recommendation_level}")
            print(f"   Road: {'Accessible' if loc.road_accessible else 'Not accessible'}")
            print()
        
        # 保存便捷函数结果
        analyzer = StargazingLocationAnalyzer()
        output_file = "convenience_function_analysis.json"
        analyzer.save_results_to_json(locations, output_file)
        print(f"Results saved to: {output_file}")
    else:
        print("Convenience function found no suitable stargazing locations")

def main():
    """
    主函数 - 运行所有示例
    """
    print("Stargazing Location Comprehensive Analyzer - Usage Examples")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 检查光污染数据文件是否存在
        kml_file = "/Users/gongzhao/workspace/stargazing-place-finder/world_atlas/doc.kml"
        if not os.path.exists(kml_file):
            print(f"\n⚠️  Warning: Light pollution data file {kml_file} does not exist")
            print("Light pollution data is a mandatory requirement for stargazing location analysis")
            print("Please download light pollution map KML file from the following websites:")
            print("- Light Pollution Map: https://www.lightpollutionmap.info/")
            print("- Dark Site Finder: https://darksitefinder.com/")
            print("\nAfter downloading, please rename the file to 'light_pollution_map.kml' and place it in the project root directory")
            return
        
        # 运行各个示例
        example_basic_analysis()
        example_advanced_analysis()
        example_batch_analysis()
        example_custom_parameters()
        example_convenience_function()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\nGenerated files:")
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
                print(f"- {filename} (not generated)")
        
        print("\nUsage tips:")
        print("1. Adjust search range and parameters according to actual needs")
        print("2. More accurate assessment can be obtained with light pollution KML file")
        print("3. Can be integrated into existing stargazing projects")
        print("4. Supports batch analysis and result comparison")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()