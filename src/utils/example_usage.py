#!/usr/bin/env python3
"""
KML解析器使用示例

这个脚本演示了如何使用KMLParser类来解析KML文件并提取GroundOverlay信息。
"""

import os
import sys
try:
    from utils.kml_parser import KMLParser
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
    from utils.kml_parser import KMLParser


def main():
    """主函数"""
    # KML文件路径
    kml_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'world_atlas', 'doc.kml')
    
    print(f"Parsing KML file: {kml_file_path}")
    
    try:
        # 创建解析器实例
        parser = KMLParser(kml_file_path)
        
        # 解析文件
        overlays = parser.parse()
        
        # 获取文档名称
        doc_name = parser.get_document_name()
        print(f"Document name: {doc_name}")
        
        # 显示基本统计信息
        stats = parser.get_statistics(overlays)
        print(f"\nStatistics:")
        print(f"  Total count: {stats['count']}")
        print(f"  Unique names count: {stats['unique_names']}")
        
        if stats['count'] > 0:
            bounds = stats['bounds']
            print(f"  Boundary range:")
            print(f"    North latitude: {bounds['north']['min']:.6f} ~ {bounds['north']['max']:.6f}")
            print(f"    South latitude: {bounds['south']['min']:.6f} ~ {bounds['south']['max']:.6f}")
            print(f"    East longitude: {bounds['east']['min']:.6f} ~ {bounds['east']['max']:.6f}")
            print(f"    West longitude: {bounds['west']['min']:.6f} ~ {bounds['west']['max']:.6f}")
        
        # 显示前5个GroundOverlay的详细信息
        print(f"\nFirst 5 GroundOverlay details:")
        for i, overlay in enumerate(overlays[:5]):
            print(f"\n{i+1}. {overlay.name}")
            print(f"   Draw order: {overlay.draw_order}")
            print(f"   Color: {overlay.color}")
            print(f"   Icon: {overlay.icon.href}")
            print(f"   Bounding box:")
            print(f"     North: {overlay.lat_lon_box.north}")
            print(f"     South: {overlay.lat_lon_box.south}")
            print(f"     East: {overlay.lat_lon_box.east}")
            print(f"     West: {overlay.lat_lon_box.west}")
            print(f"     Rotation: {overlay.lat_lon_box.rotation}")
        
        # 演示过滤功能
        print(f"\nFiltering examples:")
        
        # 按名称模式过滤
        brightness_overlays = parser.filter_by_name_pattern(overlays, "ArtificialSkyBrightness*.JPG")
        print(f"  Number of overlays containing 'ArtificialSkyBrightness': {len(brightness_overlays)}")
        
        # 按地理边界过滤（示例：中国大陆区域）
        china_overlays = parser.filter_by_bounds(overlays, 
                                                min_lat=18.0, max_lat=54.0,
                                                min_lon=73.0, max_lon=135.0)
        print(f"  Number of overlays in mainland China region: {len(china_overlays)}")
        
        # 显示中国区域的前3个覆盖层
        if china_overlays:
            print(f"\nFirst 3 overlays in China region:")
            for i, overlay in enumerate(china_overlays[:3]):
                print(f"  {i+1}. {overlay.name} - Boundary: ({overlay.lat_lon_box.south:.2f}, {overlay.lat_lon_box.west:.2f}) to ({overlay.lat_lon_box.north:.2f}, {overlay.lat_lon_box.east:.2f})")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Parse error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unknown error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()