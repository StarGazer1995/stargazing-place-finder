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
        print("Initializing LocationFinder...")
        finder = LocationFinder(kml_file)
        
        # 显示统计信息
        stats = finder.get_statistics()
        print(f"\n=== Overlay Statistics ===")
        print(f"Total overlay count: {stats['count']}")
        print(f"Unique names count: {stats['unique_names']}")
        bounds = stats['bounds']
        print(f"Boundary range: Latitude {bounds['south']['min']:.2f}° to {bounds['north']['max']:.2f}°")
        print(f"               Longitude {bounds['west']['min']:.2f}° to {bounds['east']['max']:.2f}°")
        
        # 测试用例：不同地理位置
        test_locations = [
            {"name": "Beijing", "lat": 39.9042, "lon": 116.4074},
            {"name": "Shanghai", "lat": 31.2304, "lon": 121.4737},
            {"name": "New York", "lat": 40.7128, "lon": -74.0060},
            {"name": "London", "lat": 51.5074, "lon": -0.1278},
            {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
            {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
            {"name": "South Pole", "lat": -90.0, "lon": 0.0},
            {"name": "Pacific Center", "lat": 0.0, "lon": -160.0}
        ]
        
        print("\n=== Geographic Location Search Test ===")
        
        for location in test_locations:
            name = location["name"]
            lat = location["lat"]
            lon = location["lon"]
            
            print(f"\n--- {name} ({lat}°, {lon}°) ---")
            
            # 查找单个覆盖层
            overlay = finder.find_overlay_by_coordinates(lat, lon)
            if overlay:
                print(f"Found overlay: {overlay.name}")
                print(f"Icon link: {overlay.icon.href}")
                print(f"Draw order: {overlay.draw_order}")
                print(f"Color: {overlay.color}")
                print(f"Bounds: South{overlay.lat_lon_box.south}° North{overlay.lat_lon_box.north}° "
                      f"West{overlay.lat_lon_box.west}° East{overlay.lat_lon_box.east}°")
            else:
                print("No overlay found")
            
            # 查找所有覆盖层
            all_overlays = finder.find_all_overlays_by_coordinates(lat, lon)
            if len(all_overlays) > 1:
                print(f"Found {len(all_overlays)} overlapping overlays in total")
                for i, ov in enumerate(all_overlays[:3]):  # 只显示前3个
                    print(f"  {i+1}. {ov.name}")
                if len(all_overlays) > 3:
                    print(f"  ... and {len(all_overlays) - 3} more")
        
        # 演示附近覆盖层查找
        print("\n=== Nearby Overlay Search Example ===")
        beijing_lat, beijing_lon = 39.9042, 116.4074
        nearby = finder.find_nearby_overlays(beijing_lat, beijing_lon, radius_degrees=2.0)
        print(f"Number of overlays within 2 degrees of Beijing: {len(nearby)}")
        
        if nearby:
            print("First 5 nearby overlays:")
            for i, overlay in enumerate(nearby[:5]):
                print(f"  {i+1}. {overlay.name}")
        
        # 演示详细信息获取
        print("\n=== Detailed Information Retrieval Example ===")
        info = finder.get_overlay_info(beijing_lat, beijing_lon)
        print(f"Location: ({info['coordinates']['latitude']}, {info['coordinates']['longitude']})")
        print(f"Overlay count: {info['overlay_count']}")
        
        if info['overlays']:
            print("Overlay details:")
            for i, overlay_info in enumerate(info['overlays'][:2]):  # 只显示前2个
                print(f"  {i+1}. Name: {overlay_info['name']}")
                print(f"     Bounds: South{overlay_info['bounds']['south']}° North{overlay_info['bounds']['north']}° "
                      f"West{overlay_info['bounds']['west']}° East{overlay_info['bounds']['east']}°")
        
        # 错误处理示例
        print("\n=== Error Handling Example ===")
        try:
            # Test invalid coordinates
            finder.find_overlay_by_coordinates(100, 200)  # Invalid latitude and longitude
        except ValueError as e:
            print(f"Caught expected error: {e}")
        
        print("\n=== Test Completed ===")
        
    except FileNotFoundError:
        print(f"Error: Cannot find KML file {kml_file}")
        print("Please ensure the file path is correct")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()