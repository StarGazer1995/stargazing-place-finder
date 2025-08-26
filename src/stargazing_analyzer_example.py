#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
观星地点综合分析器使用示例

展示如何使用StargazingLocationAnalyzer进行全面的观星地点分析，
包括山峰查找、光污染分析和道路连通性检测。
"""

import os
from stargazing_location_analyzer import StargazingLocationAnalyzer, analyze_stargazing_area

def example_1_basic_analysis():
    """
    示例1：基础分析（不包含光污染数据）
    """
    print("\n=== 示例1：基础观星地点分析 ===")
    print("分析北京周边地区的观星地点（不包含光污染分析）")
    
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
        max_peaks=15,
        network_type='drive',
        include_light_pollution=False,
        include_road_connectivity=True
    )
    
    # 保存结果
    if locations:
        analyzer.save_results_to_json(locations, "beijing_stargazing_basic.json")
        print(f"\n找到 {len(locations)} 个观星地点")
        
        # 显示前3个推荐
        top_3 = analyzer.get_top_recommendations(locations, 3)
        print("\n=== 前3个推荐地点 ===")
        for i, loc in enumerate(top_3, 1):
            print(f"{i}. {loc.name} (评分: {loc.stargazing_score}/100)")
            print(f"   {loc.recommendation_level}")
            print(f"   海拔: {loc.elevation:.1f}m, 高度差: {loc.height_difference:.1f}m")
            road_status = "可达" if loc.road_accessible else "不可达" if loc.road_accessible is False else "未知"
            print(f"   道路: {road_status}")
            print(f"   备注: {loc.analysis_notes}")
            print()
    else:
        print("未找到符合条件的观星地点")

def example_2_with_light_pollution():
    """
    示例2：包含光污染分析（需要KML文件）
    """
    print("\n=== 示例2：包含光污染分析 ===")
    
    # 检查是否有光污染KML文件
    kml_file = "light_pollution.kml"  # 替换为实际的KML文件路径
    
    if not os.path.exists(kml_file):
        print(f"光污染KML文件不存在: {kml_file}")
        print("跳过光污染分析示例")
        return
    
    print(f"使用光污染数据文件: {kml_file}")
    
    # 分析华山地区
    bbox = (34.3, 109.8, 34.7, 110.2)  # 华山地区
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=kml_file,
        min_height_difference=150.0,
        road_search_radius_km=15.0
    )
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_peaks=10,
        network_type='drive',
        include_light_pollution=True,
        include_road_connectivity=True
    )
    
    if locations:
        analyzer.save_results_to_json(locations, "huashan_stargazing_full.json")
        analyzer.print_analysis_summary(locations)
    else:
        print("未找到符合条件的观星地点")

def example_3_multiple_areas():
    """
    示例3：批量分析多个地区
    """
    print("\n=== 示例3：批量分析多个地区 ===")
    
    # 定义多个分析区域
    areas = {
        "张家界": (29.0, 110.0, 29.5, 110.5),
        "黄山": (30.0, 118.0, 30.3, 118.3),
        "泰山": (36.1, 117.0, 36.4, 117.3),
        "峨眉山": (29.4, 103.2, 29.7, 103.5)
    }
    
    all_results = {}
    
    for area_name, bbox in areas.items():
        print(f"\n正在分析 {area_name} 地区...")
        
        analyzer = StargazingLocationAnalyzer(
            kml_file_path=None,
            min_height_difference=120.0,
            road_search_radius_km=12.0
        )
        
        locations = analyzer.analyze_area(
            bbox=bbox,
            max_peaks=8,
            network_type='drive',
            include_light_pollution=False,
            include_road_connectivity=True
        )
        
        all_results[area_name] = locations
        
        if locations:
            print(f"{area_name}: 找到 {len(locations)} 个观星地点")
            top_1 = analyzer.get_top_recommendations(locations, 1)
            if top_1:
                best = top_1[0]
                print(f"最佳推荐: {best.name} (评分: {best.stargazing_score}/100)")
        else:
            print(f"{area_name}: 未找到符合条件的观星地点")
    
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
    
    print("\n批量分析结果已保存到: batch_stargazing_analysis.json")

def example_4_custom_parameters():
    """
    示例4：自定义参数分析
    """
    print("\n=== 示例4：自定义参数分析 ===")
    print("使用严格的筛选条件分析庐山地区")
    
    # 庐山地区，使用更严格的条件
    bbox = (29.4, 115.8, 29.8, 116.2)
    
    analyzer = StargazingLocationAnalyzer(
        kml_file_path=None,
        min_height_difference=200.0,  # 更高的高度差要求
        road_search_radius_km=20.0    # 更大的道路搜索范围
    )
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_peaks=12,
        network_type='all',  # 检查所有类型的道路网络
        include_light_pollution=False,
        include_road_connectivity=True
    )
    
    if locations:
        print(f"\n严格条件下找到 {len(locations)} 个观星地点")
        
        # 按不同标准排序显示
        print("\n=== 按海拔高度排序 ===")
        by_elevation = sorted(locations, key=lambda x: x.elevation, reverse=True)[:3]
        for i, loc in enumerate(by_elevation, 1):
            print(f"{i}. {loc.name} - 海拔 {loc.elevation:.1f}m")
        
        print("\n=== 按高度差排序 ===")
        by_height_diff = sorted(locations, key=lambda x: x.height_difference, reverse=True)[:3]
        for i, loc in enumerate(by_height_diff, 1):
            print(f"{i}. {loc.name} - 高度差 {loc.height_difference:.1f}m")
        
        print("\n=== 按综合评分排序 ===")
        by_score = sorted(locations, key=lambda x: x.stargazing_score or 0, reverse=True)[:3]
        for i, loc in enumerate(by_score, 1):
            print(f"{i}. {loc.name} - 评分 {loc.stargazing_score}/100")
        
        analyzer.save_results_to_json(locations, "lushan_stargazing_strict.json")
    else:
        print("严格条件下未找到符合条件的观星地点")

def example_5_convenience_function():
    """
    示例5：使用便捷函数
    """
    print("\n=== 示例5：使用便捷函数 ===")
    print("快速分析天山地区")
    
    # 使用便捷函数进行快速分析
    locations = analyze_stargazing_area(
        south=43.0, west=86.5, north=43.5, east=87.0,  # 天山地区
        kml_file_path=None,
        max_peaks=10,
        min_height_diff=150.0
    )
    
    if locations:
        print(f"\n便捷函数分析完成，找到 {len(locations)} 个观星地点")
        
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
        
        print("结果已保存到: tianshan_stargazing_quick.json")
    else:
        print("未找到符合条件的观星地点")

def main():
    """
    主函数：运行所有示例
    """
    print("观星地点综合分析器 - 使用示例")
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
        
        print("\n=== 所有示例运行完成 ===")
        print("生成的文件:")
        print("- beijing_stargazing_basic.json")
        print("- batch_stargazing_analysis.json")
        print("- lushan_stargazing_strict.json")
        print("- tianshan_stargazing_quick.json")
        print("- huashan_stargazing_full.json (如果有光污染数据)")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()