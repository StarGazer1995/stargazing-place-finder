#!/usr/bin/env python3
"""
KML解析器使用示例

这个脚本演示了如何使用KMLParser类来解析KML文件并提取GroundOverlay信息。
"""

import os
import sys
from kml_parser import KMLParser


def main():
    """主函数"""
    # KML文件路径
    kml_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                'world_atlas', 'doc.kml')
    
    print(f"正在解析KML文件: {kml_file_path}")
    
    try:
        # 创建解析器实例
        parser = KMLParser(kml_file_path)
        
        # 解析文件
        overlays = parser.parse()
        
        # 获取文档名称
        doc_name = parser.get_document_name()
        print(f"文档名称: {doc_name}")
        
        # 显示基本统计信息
        stats = parser.get_statistics(overlays)
        print(f"\n统计信息:")
        print(f"  总数量: {stats['count']}")
        print(f"  唯一名称数量: {stats['unique_names']}")
        
        if stats['count'] > 0:
            bounds = stats['bounds']
            print(f"  边界范围:")
            print(f"    北纬: {bounds['north']['min']:.6f} ~ {bounds['north']['max']:.6f}")
            print(f"    南纬: {bounds['south']['min']:.6f} ~ {bounds['south']['max']:.6f}")
            print(f"    东经: {bounds['east']['min']:.6f} ~ {bounds['east']['max']:.6f}")
            print(f"    西经: {bounds['west']['min']:.6f} ~ {bounds['west']['max']:.6f}")
        
        # 显示前5个GroundOverlay的详细信息
        print(f"\n前5个GroundOverlay详细信息:")
        for i, overlay in enumerate(overlays[:5]):
            print(f"\n{i+1}. {overlay.name}")
            print(f"   绘制顺序: {overlay.draw_order}")
            print(f"   颜色: {overlay.color}")
            print(f"   图标: {overlay.icon.href}")
            print(f"   边界框:")
            print(f"     北: {overlay.lat_lon_box.north}")
            print(f"     南: {overlay.lat_lon_box.south}")
            print(f"     东: {overlay.lat_lon_box.east}")
            print(f"     西: {overlay.lat_lon_box.west}")
            print(f"     旋转: {overlay.lat_lon_box.rotation}")
        
        # 演示过滤功能
        print(f"\n过滤示例:")
        
        # 按名称模式过滤
        brightness_overlays = parser.filter_by_name_pattern(overlays, "ArtificialSkyBrightness*.JPG")
        print(f"  包含'ArtificialSkyBrightness'的覆盖层数量: {len(brightness_overlays)}")
        
        # 按地理边界过滤（示例：中国大陆区域）
        china_overlays = parser.filter_by_bounds(overlays, 
                                                min_lat=18.0, max_lat=54.0,
                                                min_lon=73.0, max_lon=135.0)
        print(f"  中国大陆区域的覆盖层数量: {len(china_overlays)}")
        
        # 显示中国区域的前3个覆盖层
        if china_overlays:
            print(f"\n中国区域的前3个覆盖层:")
            for i, overlay in enumerate(china_overlays[:3]):
                print(f"  {i+1}. {overlay.name} - 边界: ({overlay.lat_lon_box.south:.2f}, {overlay.lat_lon_box.west:.2f}) 到 ({overlay.lat_lon_box.north:.2f}, {overlay.lat_lon_box.east:.2f})")
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"解析错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"未知错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()