#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量海拔查询使用示例

演示如何使用 BatchElevationQuery 类进行批量海拔查询
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.stargazing_analyzer.elevation_batch_query import (
    BatchElevationQuery, 
    batch_query_elevations,
    get_elevation_statistics
)

def main():
    """主函数：演示批量海拔查询"""
    
    # 数据库配置
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'gis_db',
        'user': 'postgres',
        'password': 'postgres'
    }
    
    print("=== 批量海拔查询示例 ===\n")
    
    # 示例1：查询著名山峰的海拔
    print("示例1：查询著名山峰的海拔")
    mountain_coordinates = [
        (27.9881, 86.9250, "珠穆朗玛峰"),
        (35.8817, 76.5133, "乔戈里峰"),
        (27.7025, 88.1475, "干城章嘉峰"),
        (28.0050, 87.9150, "洛子峰"),
        (27.8894, 87.0889, "马卡鲁峰")
    ]
    
    # 提取坐标和名称
    coords = [(lat, lon) for lat, lon, name in mountain_coordinates]
    names = [name for lat, lon, name in mountain_coordinates]
    
    # 使用批量查询
    results = batch_query_elevations(coords, db_config, names)
    
    print(f"查询了 {len(results)} 个山峰的海拔：")
    for i, result in enumerate(results):
        if result.elevation:
            print(f"  {result.source_name}: {result.elevation:.1f}米 "
                  f"(距离查询点: {result.distance_meters:.1f}米)")
        else:
            print(f"  {names[i]}: 未找到海拔数据 - {result.error}")
    print()
    
    # 示例2：查询城市地标的海拔
    print("示例2：查询城市地标的海拔")
    landmark_coordinates = [
        (39.9042, 116.4074, "北京天安门"),
        (31.2304, 121.4737, "上海外滩"),
        (30.2636, 120.1619, "杭州西湖"),
        (29.5647, 106.5507, "重庆解放碑"),
        (22.5431, 114.0579, "深圳平安大厦"),
        (23.1291, 113.2644, "广州塔"),
        (30.5728, 104.0668, "成都天府广场"),
        (34.3416, 108.9398, "西安钟楼")
    ]
    
    coords = [(lat, lon) for lat, lon, name in landmark_coordinates]
    names = [name for lat, lon, name in landmark_coordinates]
    
    results = batch_query_elevations(coords, db_config, names)
    
    print(f"查询了 {len(results)} 个城市地标的海拔：")
    for result in results:
        if result.elevation:
            print(f"  {result.source_name}: {result.elevation:.1f}米 "
                  f"({result.feature_type})")
        else:
            print(f"  查询失败: {result.error}")
    print()
    
    # 示例3：查询随机坐标点（演示性能）
    print("示例3：性能测试 - 查询100个随机坐标点")
    import random
    
    # 生成随机坐标点（中国范围内）
    random_coords = []
    for i in range(100):
        lat = random.uniform(18.0, 54.0)  # 中国纬度范围
        lon = random.uniform(73.0, 135.0)  # 中国经度范围
        random_coords.append((lat, lon))
    
    # 使用批量查询器
    querier = BatchElevationQuery(db_config, batch_size=25)
    results = querier.query_elevations(random_coords, use_batch_query=True)
    
    successful = sum(1 for r in results if r.elevation is not None)
    print(f"成功查询到 {successful}/{len(results)} 个点的海拔数据")
    
    # 显示一些成功的结果
    successful_results = [r for r in results if r.elevation is not None][:5]
    if successful_results:
        print("前5个成功查询的结果：")
        for result in successful_results:
            print(f"  ({result.latitude:.4f}, {result.longitude:.4f}): "
                  f"{result.elevation:.1f}米")
    print()
    
    # 示例4：获取数据库统计信息
    print("示例4：数据库海拔数据统计")
    stats = get_elevation_statistics(db_config)
    
    if 'error' in stats:
        print(f"获取统计信息失败: {stats['error']}")
    else:
        print(f"数据库中共有 {stats['total_points']} 个海拔数据点")
        print(f"最低海拔: {stats['min_elevation']:.1f}米")
        print(f"最高海拔: {stats['max_elevation']:.1f}米")
        print(f"平均海拔: {stats['avg_elevation']:.1f}米")
        print(f"中位海拔: {stats['median_elevation']:.1f}米")
    print()
    
    # 示例5：错误处理演示
    print("示例5：错误处理演示")
    print("查询一些明显没有海拔数据的点（海洋中）...")
    
    ocean_coords = [
        (0, 0, "赤道附近"),
        (10, 110, "南海南部"),
        (25, 125, "东海东部")
    ]
    
    coords = [(lat, lon) for lat, lon, name in ocean_coords]
    names = [name for lat, lon, name in ocean_coords]
    
    results = batch_query_elevations(coords, db_config, names)
    
    for result in results:
        if result.elevation:
            print(f"  {result.latitude}, {result.longitude}: {result.elevation:.1f}米")
        else:
            print(f"  {result.latitude}, {result.longitude}: {result.error}")

if __name__ == "__main__":
    main()