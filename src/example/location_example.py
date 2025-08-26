#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理位置查找器使用示例

这个脚本演示了如何使用LocationFinder类根据地理坐标查找对应的GroundOverlay。
包含多个测试用例，展示不同地理位置的查找结果。
"""

import os
import sys
# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from location_finder import LocationFinder


def main():
    """
    地理位置查找器功能演示主函数
    
    展示LocationFinder类的完整使用流程
    包括覆盖层查找、统计信息获取、附近区域搜索和错误处理
    
    演示功能：
    1. 初始化LocationFinder并获取统计信息
    2. 单个坐标的覆盖层查找
    3. 多重覆盖层的查找和处理
    4. 附近覆盖层的范围搜索
    5. 详细信息的结构化获取
    6. 错误处理和边界条件测试
    
    测试坐标：
    - 全球主要城市的代表性坐标
    - 包含极地和海洋区域的边界测试
    - 验证查找器的覆盖范围和准确性
    
    输出内容：
    - 覆盖层统计信息和边界范围
    - 每个测试点的覆盖层详情
    - 重叠覆盖层的处理结果
    - 附近区域搜索的结果统计
    - 结构化的详细信息展示
    """
    # KML文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    kml_file = os.path.join(project_root, 'world_atlas', 'doc.kml')
    
    try:
        # 初始化LocationFinder
        print("正在初始化LocationFinder...")
        finder = LocationFinder(kml_file)
        
        # 显示统计信息
        stats = finder.get_statistics()
        print(f"\n=== 覆盖层统计信息 ===")
        print(f"总覆盖层数量: {stats['count']}")
        print(f"唯一名称数量: {stats['unique_names']}")
        bounds = stats['bounds']
        print(f"边界范围: 纬度 {bounds['south']['min']:.2f}° 到 {bounds['north']['max']:.2f}°")
        print(f"         经度 {bounds['west']['min']:.2f}° 到 {bounds['east']['max']:.2f}°")
        
        # 测试用例：不同地理位置
        test_locations = [
            {"name": "北京", "lat": 39.9042, "lon": 116.4074},
            {"name": "上海", "lat": 31.2304, "lon": 121.4737},
            {"name": "纽约", "lat": 40.7128, "lon": -74.0060},
            {"name": "伦敦", "lat": 51.5074, "lon": -0.1278},
            {"name": "东京", "lat": 35.6762, "lon": 139.6503},
            {"name": "悉尼", "lat": -33.8688, "lon": 151.2093},
            {"name": "南极点", "lat": -90.0, "lon": 0.0},
            {"name": "太平洋中心", "lat": 0.0, "lon": -160.0}
        ]
        
        print("\n=== 地理位置查找测试 ===")
        
        for location in test_locations:
            name = location["name"]
            lat = location["lat"]
            lon = location["lon"]
            
            print(f"\n--- {name} ({lat}°, {lon}°) ---")
            
            # 查找单个覆盖层
            overlay = finder.find_overlay_by_coordinates(lat, lon)
            if overlay:
                print(f"找到覆盖层: {overlay.name}")
                print(f"图标链接: {overlay.icon.href}")
                print(f"绘制顺序: {overlay.draw_order}")
                print(f"颜色: {overlay.color}")
                print(f"边界: 南{overlay.lat_lon_box.south}° 北{overlay.lat_lon_box.north}° "
                      f"西{overlay.lat_lon_box.west}° 东{overlay.lat_lon_box.east}°")
            else:
                print("未找到覆盖层")
            
            # 查找所有覆盖层
            all_overlays = finder.find_all_overlays_by_coordinates(lat, lon)
            if len(all_overlays) > 1:
                print(f"总共找到 {len(all_overlays)} 个重叠的覆盖层")
                for i, ov in enumerate(all_overlays[:3]):  # 只显示前3个
                    print(f"  {i+1}. {ov.name}")
                if len(all_overlays) > 3:
                    print(f"  ... 还有 {len(all_overlays) - 3} 个")
        
        # 演示附近覆盖层查找
        print("\n=== 附近覆盖层查找示例 ===")
        beijing_lat, beijing_lon = 39.9042, 116.4074
        nearby = finder.find_nearby_overlays(beijing_lat, beijing_lon, radius_degrees=2.0)
        print(f"北京附近2度范围内的覆盖层数量: {len(nearby)}")
        
        if nearby:
            print("前5个附近的覆盖层:")
            for i, overlay in enumerate(nearby[:5]):
                print(f"  {i+1}. {overlay.name}")
        
        # 演示详细信息获取
        print("\n=== 详细信息获取示例 ===")
        info = finder.get_overlay_info(beijing_lat, beijing_lon)
        print(f"位置: ({info['coordinates']['latitude']}, {info['coordinates']['longitude']})")
        print(f"覆盖层数量: {info['overlay_count']}")
        
        if info['overlays']:
            print("覆盖层详情:")
            for i, overlay_info in enumerate(info['overlays'][:2]):  # 只显示前2个
                print(f"  {i+1}. 名称: {overlay_info['name']}")
                print(f"     边界: 南{overlay_info['bounds']['south']}° 北{overlay_info['bounds']['north']}° "
                      f"西{overlay_info['bounds']['west']}° 东{overlay_info['bounds']['east']}°")
        
        # 错误处理示例
        print("\n=== 错误处理示例 ===")
        try:
            # 测试无效坐标
            finder.find_overlay_by_coordinates(100, 200)  # 无效的纬度和经度
        except ValueError as e:
            print(f"捕获到预期的错误: {e}")
        
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