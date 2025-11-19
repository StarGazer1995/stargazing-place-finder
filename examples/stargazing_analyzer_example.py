#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观星地点综合分析器使用示例

展示如何使用StargazingLocationAnalyzer进行全面的观星地点分析，
包括山峰查找、光污染分析和道路连通性检测。
"""

import os
import sys
# 添加 src 目录到Python路径以加载顶层包
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, '..', 'src'))
from stargazing_analyzer.stargazing_location_analyzer import StargazingLocationAnalyzer, analyze_stargazing_area

def example_1_basic_analysis():
    """
    示例1：基础观星地点分析功能演示
    
    演示如何使用StargazingLocationAnalyzer进行基础的观星地点分析，
    不包含光污染数据分析，主要展示山峰查找和道路连通性检测功能。
    
    演示功能:
    - 创建不包含光污染数据的分析器实例
    - 在指定区域内搜索观星地点
    - 进行道路连通性检测
    - 生成观星评分和推荐等级
    - 保存分析结果为JSON格式
    - 显示前3个推荐地点的详细信息
    
    测试区域:
    - 北京周边地区 (39.5°N-40.5°N, 115.5°E-117.5°E)
    
    输出内容:
    - 控制台显示分析过程和结果统计
    - 前3个推荐地点的详细信息（名称、评分、海拔、道路状况等）
    - beijing_stargazing_basic.json 文件（包含所有找到的观星地点数据）
    
    注意事项:
    - 不进行光污染分析，适用于没有光污染数据的情况
    - 使用默认的评分算法（基于海拔和高度差）
    - 包含道路连通性检测，确保地点的可达性
    """
    print("\n=== Example 1: Basic Stargazing Location Analysis ===")
    print("Analyzing stargazing locations around Beijing (without light pollution analysis)")
    
    # 定义分析区域（北京周边）
    bbox = (39.5, 115.5, 40.5, 117.5)  # (south, west, north, east)
    
    # 创建分析器
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=None,  # 不提供光污染数据
        min_height_difference=100.0,
        road_search_radius_km=10.0
    )
    
    # 执行分析
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=15,
        network_type='drive',
        include_light_pollution=False,
        include_road_connectivity=True
    )
    
    # 保存结果
    if locations:
        analyzer.save_results_to_json(locations, "beijing_stargazing_basic.json")
        print(f"\nFound {len(locations)} stargazing locations")
        
        # 显示前3个推荐
        top_3 = analyzer.get_top_recommendations(locations, 3)
        print("\n=== Top 3 Recommended Locations ===")
        for i, loc in enumerate(top_3, 1):
            print(f"{i}. {loc.name} (Score: {loc.stargazing_score}/100)")
            print(f"   {loc.recommendation_level}")
            print(f"   Elevation: {loc.elevation:.1f}m, Height difference: {loc.height_difference:.1f}m")
            road_status = "Accessible" if loc.road_accessible else "Not accessible" if loc.road_accessible is False else "Unknown"
            print(f"   Road: {road_status}")
            print(f"   Notes: {loc.analysis_notes}")
            print()
    else:
        print("No suitable stargazing locations found")

def example_2_with_light_pollution():
    """
    示例2：包含光污染分析的完整观星地点分析功能演示
    
    演示如何使用StargazingLocationAnalyzer进行包含光污染数据的完整分析，
    展示山峰查找、光污染分析和道路连通性检测的综合功能。
    
    演示功能:
    - 检查光污染KML文件的存在性
    - 创建包含光污染数据的分析器实例
    - 在指定区域内搜索观星地点
    - 进行光污染等级分析
    - 进行道路连通性检测
    - 生成综合观星评分和推荐等级
    - 保存完整分析结果
    - 打印详细的分析摘要
    
    测试区域:
    - 华山地区 (34.3°N-34.7°N, 109.8°E-110.2°E)
    
    输出内容:
    - 控制台显示分析过程和结果统计
    - 详细的分析摘要（包括光污染分布统计）
    - huashan_stargazing_full.json 文件（包含完整的观星地点数据）
    
    前置条件:
    - 需要存在有效的光污染KML数据文件
    - KML文件应包含光污染等级的地理数据
    
    注意事项:
    - 如果KML文件不存在，将跳过此示例
    - 使用更严格的筛选条件（最小高度差150m）
    - 包含完整的光污染等级评估
    """
    print("\n=== Example 2: Analysis with Light Pollution ===")
    
    # 检查是否有光污染KML文件
    kml_file = "light_pollution.kml"  # 替换为实际的KML文件路径
    
    if not os.path.exists(kml_file):
        print(f"Light pollution KML file does not exist: {kml_file}")
        print("Skipping light pollution analysis example")
        return
    
    print(f"Using light pollution data file: {kml_file}")
    
    # 分析华山地区
    bbox = (34.3, 109.8, 34.7, 110.2)  # 华山地区
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file,
        min_height_difference=150.0,
        road_search_radius_km=15.0
    )
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=10,
        network_type='drive',
        include_light_pollution=True,
        include_road_connectivity=True
    )
    
    if locations:
        analyzer.save_results_to_json(locations, "huashan_stargazing_full.json")
        analyzer.print_analysis_summary(locations)
    else:
        print("No suitable stargazing locations found")

def example_3_multiple_areas():
    """
    示例3：多地区批量观星地点分析功能演示
    
    演示如何使用StargazingLocationAnalyzer对多个不同地区进行批量分析，
    展示大规模地理区域的观星地点搜索和比较功能。
    
    演示功能:
    - 定义多个分析区域的地理边界
    - 对每个区域独立进行观星地点分析
    - 收集和汇总所有区域的分析结果
    - 为每个区域找出最佳推荐地点
    - 生成批量分析的统计报告
    - 保存结构化的批量分析结果
    
    测试区域:
    - 张家界地区 (29.0°N-29.5°N, 110.0°E-110.5°E)
    - 黄山地区 (30.0°N-30.3°N, 118.0°E-118.3°E)
    - 泰山地区 (36.1°N-36.4°N, 117.0°E-117.3°E)
    - 峨眉山地区 (29.4°N-29.7°N, 103.2°E-103.5°E)
    
    输出内容:
    - 控制台显示每个区域的分析进度和结果
    - 每个区域的观星地点数量统计
    - 每个区域的最佳推荐地点信息
    - batch_stargazing_analysis.json 文件（包含所有区域的汇总结果）
    
    应用场景:
    - 旅游规划中的多目的地观星地点比较
    - 区域性观星资源调查
    - 观星地点数据库的批量构建
    
    注意事项:
    - 不包含光污染分析，适用于快速批量评估
    - 使用统一的筛选标准确保结果可比性
    - 生成的JSON文件包含时间戳和统计信息
    """
    print("\n=== Example 3: Batch Analysis of Multiple Areas ===")
    
    # 定义多个分析区域
    areas = {
        "张家界": (29.0, 110.0, 29.5, 110.5),
        "黄山": (30.0, 118.0, 30.3, 118.3),
        "泰山": (36.1, 117.0, 36.4, 117.3),
        "峨眉山": (29.4, 103.2, 29.7, 103.5)
    }
    
    all_results = {}
    
    for area_name, bbox in areas.items():
        print(f"\nAnalyzing {area_name} area...")
        
        analyzer = StargazingLocationAnalyzer(
            kml_file_path=None,
            min_height_difference=120.0,
            road_search_radius_km=12.0
        )
        
        locations = analyzer.analyze_area(
            bbox=bbox,
            max_locations=8,
            network_type='drive',
            include_light_pollution=False,
            include_road_connectivity=True
        )
        
        all_results[area_name] = locations
        
        if locations:
            print(f"{area_name}: Found {len(locations)} stargazing locations")
            top_1 = analyzer.get_top_recommendations(locations, 1)
            if top_1:
                best = top_1[0]
                print(f"Best recommendation: {best.name} (Score: {best.stargazing_score}/100)")
        else:
            print(f"{area_name}: No suitable stargazing locations found")
    
    # 保存批量分析结果
    import json
    from datetime import datetime
    
    batch_results = {
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "areas_analyzed": len(areas),
        "results": {}
    }
    
    for area_name, locations in all_results.items():
        batch_results["results"][area_name] = {
            "total_locations": len(locations),
            "top_recommendation": None
        }
        
        if locations:
            best = max(locations, key=lambda x: x.stargazing_score or 0)
            batch_results["results"][area_name]["top_recommendation"] = {
                "name": best.name,
                "score": best.stargazing_score,
                "coordinates": [best.latitude, best.longitude],
                "elevation": best.elevation,
                "recommendation_level": best.recommendation_level
            }
    
    with open("batch_stargazing_analysis.json", 'w', encoding='utf-8') as f:
        json.dump(batch_results, f, ensure_ascii=False, indent=2)
    
    print("\nBatch analysis results saved to: batch_stargazing_analysis.json")

def example_4_custom_parameters():
    """
    示例4：自定义参数的高级观星地点分析功能演示
    
    演示如何使用StargazingLocationAnalyzer的高级配置选项进行定制化分析，
    展示严格筛选条件下的观星地点搜索和多维度结果排序功能。
    
    演示功能:
    - 使用严格的自定义筛选参数
    - 扩大道路搜索范围以提高可达性检测准确性
    - 检查所有类型的道路网络连通性
    - 按多个维度对结果进行排序和展示
    - 生成高质量观星地点的精选列表
    
    自定义参数:
    - 最小高度差: 200m（比默认值更严格）
    - 道路搜索半径: 20km（比默认值更大）
    - 网络类型: 'all'（检查所有道路类型）
    - 最大山峰数: 12个
    
    测试区域:
    - 庐山地区 (29.4°N-29.8°N, 115.8°E-116.2°E)
    
    输出内容:
    - 控制台显示严格条件下的分析结果
    - 按海拔高度排序的前3个地点
    - 按高度差排序的前3个地点
    - 按综合评分排序的前3个地点
    - lushan_stargazing_strict.json 文件（包含高质量观星地点数据）
    
    应用场景:
    - 专业观星活动的地点选择
    - 天文摄影的最佳位置筛选
    - 高标准观星体验的地点推荐
    
    注意事项:
    - 严格的筛选条件可能导致找到的地点较少
    - 适用于对观星条件要求较高的用户
    - 多维度排序有助于不同需求的地点选择
    """
    print("\n=== Example 4: Custom Parameter Analysis ===")
    print("Analyzing Lushan area with strict filtering conditions")
    
    # 庐山地区，使用更严格的条件
    bbox = (29.4, 115.8, 29.8, 116.2)
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=None,
        min_height_difference=200.0,  # 更高的高度差要求
        road_search_radius_km=20.0    # 更大的道路搜索范围
    )
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=12,
        network_type='all',  # 检查所有类型的道路网络
        include_light_pollution=False,
        include_road_connectivity=True
    )
    
    if locations:
        print(f"\nFound {len(locations)} stargazing locations under strict conditions")
        
        # 按不同标准排序显示
        print("\n=== Sorted by Elevation ===")
        by_elevation = sorted(locations, key=lambda x: x.elevation, reverse=True)[:3]
        for i, loc in enumerate(by_elevation, 1):
            print(f"{i}. {loc.name} - Elevation {loc.elevation:.1f}m")
        
        print("\n=== Sorted by Height Difference ===")
        by_height_diff = sorted(locations, key=lambda x: x.height_difference, reverse=True)[:3]
        for i, loc in enumerate(by_height_diff, 1):
            print(f"{i}. {loc.name} - Height difference {loc.height_difference:.1f}m")
        
        print("\n=== Sorted by Overall Score ===")
        by_score = sorted(locations, key=lambda x: x.stargazing_score or 0, reverse=True)[:3]
        for i, loc in enumerate(by_score, 1):
            print(f"{i}. {loc.name} - Score {loc.stargazing_score}/100")
        
        analyzer.save_results_to_json(locations, "lushan_stargazing_strict.json")
    else:
        print("No suitable stargazing locations found under strict conditions")

def example_5_convenience_function():
    """
    示例5：便捷函数快速观星地点分析功能演示
    
    演示如何使用analyze_stargazing_area便捷函数进行快速的观星地点分析，
    展示简化的API接口和快速分析流程。
    
    演示功能:
    - 使用简化的便捷函数接口
    - 通过地理坐标直接指定分析区域
    - 快速获取观星地点分析结果
    - 自动生成带时间戳的分析报告
    - 保存结构化的分析结果
    
    便捷函数特点:
    - 简化的参数接口，减少配置复杂度
    - 内置默认的合理参数设置
    - 适合快速原型开发和简单应用场景
    - 自动处理分析器的创建和配置
    
    测试区域:
    - 天山地区 (43.0°N-43.5°N, 86.5°E-87.0°E)
    
    输出内容:
    - 控制台显示快速分析的进度和结果
    - 找到的观星地点数量统计
    - tianshan_stargazing_quick.json 文件（包含完整的分析结果和元数据）
    
    应用场景:
    - 快速的观星地点评估
    - 原型开发和概念验证
    - 简单的观星地点查询需求
    - 教学和演示用途
    
    注意事项:
    - 使用默认参数，可能不适合特殊需求
    - 不包含光污染分析
    - 适合对分析精度要求不高的场景
    """
    print("\n=== Example 5: Using Convenience Function ===")
    print("Quick analysis of Tianshan area")
    
    # 使用便捷函数进行快速分析
    locations = analyze_stargazing_area(
        south=43.0, west=86.5, north=43.5, east=87.0,  # 天山地区
        kml_file_path=None,
        max_locations=10,
        min_height_diff=150.0
    )
    
    if locations:
        print(f"\nConvenience function analysis completed, found {len(locations)} stargazing locations")
        
        # 保存结果
        import json
        from dataclasses import asdict
        from datetime import datetime
        
        results = {
            "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "area": "天山地区",
            "total_locations": len(locations),
            "locations": [asdict(loc) for loc in locations]
        }
        
        with open("tianshan_stargazing_quick.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print("Results saved to: tianshan_stargazing_quick.json")
    else:
        print("No suitable stargazing locations found")

def main():
    """
    观星地点综合分析器示例程序主函数
    
    按顺序运行所有观星地点分析示例，展示StargazingLocationAnalyzer
    的完整功能集合和不同应用场景。
    
    执行流程:
    1. 基础观星地点分析（不含光污染数据）
    2. 完整观星地点分析（含光污染数据，如果可用）
    3. 多地区批量分析
    4. 自定义参数的高级分析
    5. 便捷函数快速分析
    
    生成文件:
    - beijing_stargazing_basic.json: 北京地区基础分析结果
    - huashan_stargazing_full.json: 华山地区完整分析结果（如果有光污染数据）
    - batch_stargazing_analysis.json: 多地区批量分析汇总结果
    - lushan_stargazing_strict.json: 庐山地区严格条件分析结果
    - tianshan_stargazing_quick.json: 天山地区快速分析结果
    
    异常处理:
    - 捕获并显示运行过程中的所有异常
    - 提供详细的错误堆栈信息用于调试
    - 确保程序在出错时能够优雅退出
    
    使用说明:
    - 直接运行此函数可体验所有功能
    - 各示例相互独立，可单独运行
    - 建议在有网络连接的环境下运行（用于道路数据获取）
    
    注意事项:
    - 某些示例需要外部数据文件（如光污染KML文件）
    - 分析过程可能需要较长时间，特别是批量分析
    - 生成的JSON文件可用于后续的数据分析和可视化
    """
    print("Stargazing Location Comprehensive Analyzer - Usage Examples")
    print("=" * 50)
    
    try:
        # 运行示例1：基础分析
        example_1_basic_analysis()
        
        # 运行示例2：光污染分析（如果有KML文件）
        example_2_with_light_pollution()
        
        # 运行示例3：批量分析
        example_3_multiple_areas()
        
        # 运行示例4：自定义参数
        example_4_custom_parameters()
        
        # 运行示例5：便捷函数
        example_5_convenience_function()
        
        print("\n=== All Examples Completed ===")
        print("Generated files:")
        print("- beijing_stargazing_basic.json")
        print("- batch_stargazing_analysis.json")
        print("- lushan_stargazing_strict.json")
        print("- tianshan_stargazing_quick.json")
        print("- huashan_stargazing_full.json (if light pollution data available)")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()