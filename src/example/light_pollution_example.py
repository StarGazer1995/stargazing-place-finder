#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染分析器使用示例

这个脚本演示了如何使用LightPollutionAnalyzer类来分析指定坐标的光污染情况。
"""

import os
import sys
# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from light_pollution_analyzer import LightPollutionAnalyzer


def main():
    """
    光污染分析器功能演示主函数
    
    展示LightPollutionAnalyzer类的完整使用流程
    包括初始化、单点分析、批量分析、统计分析和错误处理
    
    演示功能：
    1. 分析器初始化和统计信息获取
    2. 单个坐标的光污染分析
    3. 批量坐标的光污染分析
    4. 光污染等级分布统计
    5. 亮度值统计分析
    6. 缓存管理操作
    7. 错误处理和边界条件测试
    
    测试坐标：
    - 包含全球主要城市和偏远地区
    - 覆盖不同光污染等级的区域
    - 验证分析器的准确性和稳定性
    
    输出内容：
    - 每个测试点的详细光污染信息
    - 批量分析的统计摘要
    - 光污染等级分布图
    - 亮度值统计数据
    - 使用说明和注意事项
    """
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== Light Pollution Analysis Example ===")
        print("Initializing light pollution analyzer...")
        
        # 初始化分析器
        analyzer = LightPollutionAnalyzer(kml_file)
        
        # 显示统计信息
        stats = analyzer.get_statistics()
        print(f"\n=== Analyzer Statistics ===")
        print(f"Number of overlays: {stats['count']}")
        print(f"Images base path: {stats['images_base_path']}")
        print(f"Images directory exists: {stats['images_directory_exists']}")
        print(f"Cached images count: {stats['cached_images']}")
        
        # 测试坐标列表
        test_locations = [
            (39.9042, 116.4074, "北京"),
            (31.2304, 121.4737, "上海"),
            (40.7128, -74.0060, "纽约"),
            (51.5074, -0.1278, "伦敦"),
            (35.6762, 139.6503, "东京"),
            (-33.8688, 151.2093, "悉尼"),
            (0.0, -160.0, "太平洋中心"),
            (48.8566, 2.3522, "巴黎"),
            (55.7558, 37.6176, "莫斯科"),
            (-22.9068, -43.1729, "里约热内卢"),
            (30.212929, 119.121289, "浙西大峡谷"),
            (31.7504, 110.3741, "神农架")
        ]
        
        print("\n=== Single Point Light Pollution Analysis ===")
        
        for lat, lon, location_name in test_locations:
            print(f"\n--- {location_name} ({lat}°, {lon}°) ---")
            
            try:
                pollution_info = analyzer.get_light_pollution_color(lat, lon)
                
                if pollution_info:
                    print(f"Overlay: {pollution_info['overlay_name']}")
                    print(f"RGB color: {pollution_info['rgb']}")
                    print(f"Hex color: {pollution_info['hex']}")
                    print(f"Brightness value: {pollution_info['brightness']}/255")
                    print(f"Pollution level: {pollution_info['pollution_level']}")
                else:
                    print("No corresponding light pollution data found")
                    
            except ValueError as e:
                print(f"Coordinate error: {e}")
            except Exception as e:
                print(f"Analysis error: {e}")
        
        # 批量分析示例
        print("\n=== Batch Light Pollution Analysis ===")
        
        # 准备批量分析的坐标
        batch_coordinates = [(lat, lon) for lat, lon, _ in test_locations]
        
        print(f"Batch analyzing {len(batch_coordinates)} coordinates...")
        batch_results = analyzer.batch_analyze_coordinates(batch_coordinates)
        
        successful_analyses = sum(1 for result in batch_results if result['success'])
        print(f"Successfully analyzed: {successful_analyses}/{len(batch_results)} coordinates")
        
        # 显示批量分析结果摘要
        print("\nBatch analysis results summary:")
        for result in batch_results:
            lat, lon = result['coordinates']
            if result['success'] and result['pollution_info']:
                pollution_level = result['pollution_info']['pollution_level']
                brightness = result['pollution_info']['brightness']
                print(f"  Coordinates ({lat}, {lon}): Brightness {brightness}, {pollution_level}")
            else:
                error_msg = result.get('error', '未找到数据')
                print(f"  Coordinates ({lat}, {lon}): Analysis failed - {error_msg}")
        
        # 光污染等级分布统计
        print("\n=== Light Pollution Level Distribution ===")
        
        pollution_levels = {}
        brightness_values = []
        
        for result in batch_results:
            if result['success'] and result['pollution_info']:
                level = result['pollution_info']['pollution_level']
                brightness = result['pollution_info']['brightness']
                
                # 提取等级类别（Class 1, Class 2等）
                if 'Class' in level:
                    class_num = level.split('Class')[1].split()[0]
                    pollution_levels[f"Class {class_num}"] = pollution_levels.get(f"Class {class_num}", 0) + 1
                
                brightness_values.append(brightness)
        
        if pollution_levels:
            print("Pollution level distribution:")
            for level, count in sorted(pollution_levels.items()):
                print(f"  {level}: {count} locations")
        
        if brightness_values:
            avg_brightness = sum(brightness_values) / len(brightness_values)
            min_brightness = min(brightness_values)
            max_brightness = max(brightness_values)
            
            print(f"\nBrightness statistics:")
            print(f"  Average brightness: {avg_brightness:.1f}/255")
            print(f"  Minimum brightness: {min_brightness}/255 (Best stargazing conditions)")
            print(f"  Maximum brightness: {max_brightness}/255 (Worst stargazing conditions)")
        
        # 缓存管理示例
        print("\n=== Cache Management ===")
        cache_stats = analyzer.get_statistics()
        print(f"Current cached images count: {cache_stats['cached_images']}")
        
        if cache_stats['cached_images'] > 0:
            print("Clearing image cache...")
            analyzer.clear_image_cache()
            
            updated_stats = analyzer.get_statistics()
            print(f"Cached images count after clearing: {updated_stats['cached_images']}")
        
        # 错误处理示例
        print("\n=== Error Handling Examples ===")
        
        try:
            # 测试无效坐标
            analyzer.get_light_pollution_color(100, 200)
        except ValueError as e:
            print(f"Caught expected coordinate error: {e}")
        
        try:
            # 测试边界坐标
            result = analyzer.get_light_pollution_color(90, 180)
            if result:
                print(f"Boundary coordinate analysis successful: Pollution level {result['pollution_level']}")
            else:
                print("No corresponding data found for boundary coordinates")
        except Exception as e:
            print(f"Boundary coordinate analysis error: {e}")
        
        print("\n=== Analysis Complete ===")
        print("\nUsage Instructions:")
        print("1. Brightness value range: 0-255, lower values indicate less light pollution and better stargazing conditions")
        print("2. Class 1-2: Excellent to good stargazing conditions")
        print("3. Class 3-4: Average to poor stargazing conditions")
        print("4. Class 5+: Poor to extremely poor stargazing conditions")
        print("5. If image files do not exist, default gray values will be returned")
        
    except FileNotFoundError:
        print(f"Error: Cannot find KML file {kml_file}")
        print("Please ensure the file path is correct")
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()