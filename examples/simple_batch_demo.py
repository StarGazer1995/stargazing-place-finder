#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版批量海拔查询演示

这个示例展示了如何使用批量查询功能，但会模拟数据库连接
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.stargazing_analyzer.elevation_batch_query import BatchElevationQuery
from src.models import ElevationResult

def main():
    """主函数：演示批量查询功能"""
    
    print("=== 批量海拔查询功能演示 ===\n")
    
    # 演示坐标点
    test_coordinates = [
        (39.9042, 116.4074, "北京天安门"),
        (31.2304, 121.4737, "上海外滩"),
        (30.2636, 120.1619, "杭州西湖"),
        (29.5647, 106.5507, "重庆解放碑"),
        (22.5431, 114.0579, "深圳平安大厦"),
        (23.1291, 113.2644, "广州塔"),
        (30.5728, 104.0668, "成都天府广场"),
        (34.3416, 108.9398, "西安钟楼")
    ]
    
    # 提取坐标和名称
    coords = [(lat, lon) for lat, lon, name in test_coordinates]
    names = [name for lat, lon, name in test_coordinates]
    
    print(f"准备查询 {len(coords)} 个地点的海拔数据：")
    for name in names:
        print(f"  - {name}")
    print()
    
    # 演示批量查询器的功能
    print("=== BatchElevationQuery 类功能演示 ===\n")
    
    # 1. 展示数据结构
    print("1. 查询结果数据结构示例：")
    example_result = ElevationResult(
        latitude=39.9042,
        longitude=116.4074,
        elevation=44.4,
        source_name="天安门",
        distance_meters=125.3,
        feature_type="amenity=place_of_worship"
    )
    
    print(f"  纬度: {example_result.latitude}")
    print(f"  经度: {example_result.longitude}")
    print(f"  海拔: {example_result.elevation}米")
    print(f"  数据源: {example_result.source_name}")
    print(f"  距离: {example_result.distance_meters}米")
    print(f"  特征类型: {example_result.feature_type}")
    print()
    
    # 2. 展示查询方法
    print("2. 支持的查询方法：")
    print("  - query_elevations(): 批量查询海拔")
    print("  - get_statistics(): 获取数据库统计信息")
    print("  - 支持批量查询和单独查询两种模式")
    print()
    
    # 3. 展示错误处理
    print("3. 错误处理示例：")
    error_result = ElevationResult(
        latitude=0.0,
        longitude=0.0,
        error="未找到海拔数据"
    )
    print(f"  错误示例: {error_result.error}")
    print()
    
    # 4. 展示性能特点
    print("4. 性能特点：")
    print("  - 批量查询模式：单次查询处理多个点，效率高")
    print("  - 单独查询模式：为每个点单独查询，简单但较慢")
    print("  - 支持分批处理，避免单次查询过多数据")
    print("  - 提供详细的查询统计信息")
    print()
    
    # 5. 展示使用场景
    print("5. 典型使用场景：")
    print("  - 地理信息系统中的批量海拔分析")
    print("  - 户外运动路线规划")
    print("  - 气候和环境研究")
    print("  - 城市规划和建筑设计")
    print("  - 旅游和导航应用")
    print()
    
    print("=== 如何使用 ===\n")
    print("1. 导入模块：")
    print("   from stargazing_analyzer.elevation_batch_query import BatchElevationQuery")
    print()
    print("2. 配置数据库连接：")
    print("   db_config = {")
    print("       'host': 'your_host',")
    print("       'port': 5432,")
    print("       'database': 'gis_db',")
    print("       'user': 'postgres',")
    print("       'password': 'your_password'")
    print("   }")
    print()
    print("3. 执行批量查询：")
    print("   querier = BatchElevationQuery(db_config)")
    print("   results = querier.query_elevations(coordinates, names)")
    print()
    print("4. 处理结果：")
    print("   for result in results:")
    print("       if result.elevation:")
    print("           print(f'{result.latitude}, {result.longitude}: {result.elevation}米')")
    print("       else:")
    print("           print(f'查询失败: {result.error}')")
    print()
    
    print("注意：要使用实际的海拔查询功能，需要：")
    print("- 正确配置PostgreSQL数据库连接信息")
    print("- 确保数据库中有planet_osm_point表且包含ele字段")
    print("- 数据库中启用了PostGIS扩展")

if __name__ == "__main__":
    main()