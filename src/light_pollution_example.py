#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染分析器使用示例

这个脚本演示了如何使用LightPollutionAnalyzer类来分析指定坐标的光污染情况。
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from light_pollution_analyzer import LightPollutionAnalyzer


def main():
    """主函数：演示光污染分析器的使用"""
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        print("=== 光污染分析器示例 ===")
        print("正在初始化光污染分析器...")
        
        # 初始化分析器
        analyzer = LightPollutionAnalyzer(kml_file)
        
        # 显示统计信息
        stats = analyzer.get_statistics()
        print(f"\n=== 分析器统计信息 ===")
        print(f"覆盖层数量: {stats['count']}")
        print(f"图像基础路径: {stats['images_base_path']}")
        print(f"图像目录是否存在: {stats['images_directory_exists']}")
        print(f"已缓存图像数量: {stats['cached_images']}")
        
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
        
        print("\n=== 单点光污染分析 ===")
        
        for lat, lon, location_name in test_locations:
            print(f"\n--- {location_name} ({lat}°, {lon}°) ---")
            
            try:
                pollution_info = analyzer.get_light_pollution_color(lat, lon)
                
                if pollution_info:
                    print(f"覆盖层: {pollution_info['overlay_name']}")
                    print(f"RGB颜色: {pollution_info['rgb']}")
                    print(f"十六进制颜色: {pollution_info['hex']}")
                    print(f"亮度值: {pollution_info['brightness']}/255")
                    print(f"污染等级: {pollution_info['pollution_level']}")
                else:
                    print("未找到对应的光污染数据")
                    
            except ValueError as e:
                print(f"坐标错误: {e}")
            except Exception as e:
                print(f"分析出错: {e}")
        
        # 批量分析示例
        print("\n=== 批量光污染分析 ===")
        
        # 准备批量分析的坐标
        batch_coordinates = [(lat, lon) for lat, lon, _ in test_locations]
        
        print(f"正在批量分析 {len(batch_coordinates)} 个坐标...")
        batch_results = analyzer.batch_analyze_coordinates(batch_coordinates)
        
        successful_analyses = sum(1 for result in batch_results if result['success'])
        print(f"成功分析: {successful_analyses}/{len(batch_results)} 个坐标")
        
        # 显示批量分析结果摘要
        print("\n批量分析结果摘要:")
        for result in batch_results:
            lat, lon = result['coordinates']
            if result['success'] and result['pollution_info']:
                pollution_level = result['pollution_info']['pollution_level']
                brightness = result['pollution_info']['brightness']
                print(f"  坐标 ({lat}, {lon}): 亮度{brightness}, {pollution_level}")
            else:
                error_msg = result.get('error', '未找到数据')
                print(f"  坐标 ({lat}, {lon}): 分析失败 - {error_msg}")
        
        # 光污染等级分布统计
        print("\n=== 光污染等级分布 ===")
        
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
            print("污染等级分布:")
            for level, count in sorted(pollution_levels.items()):
                print(f"  {level}: {count} 个位置")
        
        if brightness_values:
            avg_brightness = sum(brightness_values) / len(brightness_values)
            min_brightness = min(brightness_values)
            max_brightness = max(brightness_values)
            
            print(f"\n亮度统计:")
            print(f"  平均亮度: {avg_brightness:.1f}/255")
            print(f"  最低亮度: {min_brightness}/255 (最佳观星条件)")
            print(f"  最高亮度: {max_brightness}/255 (最差观星条件)")
        
        # 缓存管理示例
        print("\n=== 缓存管理 ===")
        cache_stats = analyzer.get_statistics()
        print(f"当前缓存的图像数量: {cache_stats['cached_images']}")
        
        if cache_stats['cached_images'] > 0:
            print("清除图像缓存...")
            analyzer.clear_image_cache()
            
            updated_stats = analyzer.get_statistics()
            print(f"清除后缓存的图像数量: {updated_stats['cached_images']}")
        
        # 错误处理示例
        print("\n=== 错误处理示例 ===")
        
        try:
            # 测试无效坐标
            analyzer.get_light_pollution_color(100, 200)
        except ValueError as e:
            print(f"捕获到预期的坐标错误: {e}")
        
        try:
            # 测试边界坐标
            result = analyzer.get_light_pollution_color(90, 180)
            if result:
                print(f"边界坐标分析成功: 污染等级 {result['pollution_level']}")
            else:
                print("边界坐标未找到对应数据")
        except Exception as e:
            print(f"边界坐标分析出错: {e}")
        
        print("\n=== 分析完成 ===")
        print("\n使用说明:")
        print("1. 亮度值范围: 0-255，值越低表示光污染越少，观星条件越好")
        print("2. Class 1-2: 优秀到良好的观星条件")
        print("3. Class 3-4: 一般到较差的观星条件")
        print("4. Class 5+: 差到极差的观星条件")
        print("5. 如果图像文件不存在，将返回默认的灰色值")
        
    except FileNotFoundError:
        print(f"错误: 找不到KML文件 {kml_file}")
        print("请确保文件路径正确")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()