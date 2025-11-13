#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量海拔查询演示脚本

这个脚本演示如何批量查询多个经纬度点的海拔数据，提高查询效率。
"""

import psycopg2
import time
from typing import List, Dict, Tuple, Optional
import concurrent.futures
from dataclasses import dataclass

@dataclass
class ElevationPoint:
    """海拔数据点"""
    lat: float
    lon: float
    name: str = ""
    elevation: Optional[float] = None
    distance: Optional[float] = None
    source_name: Optional[str] = None
    feature_type: Optional[str] = None

class BatchElevationQuerier:
    """批量海拔查询器"""
    
    def __init__(self, db_config: Dict):
        """
        初始化批量查询器
        
        Args:
            db_config: 数据库连接配置
        """
        self.db_config = db_config
        self.batch_size = 100  # 每批处理的数量
        
    def batch_query_elevations(self, points: List[ElevationPoint], max_workers: int = 5) -> List[ElevationPoint]:
        """
        批量查询多个点的海拔数据
        
        Args:
            points: 要查询的点列表
            max_workers: 最大并发工作线程数
            
        Returns:
            包含海拔数据的点列表
        """
        print(f"开始批量查询 {len(points)} 个点的海拔数据...")
        start_time = time.time()
        
        # 使用线程池进行并发查询
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有查询任务
            future_to_point = {
                executor.submit(self._query_single_point, point): point 
                for point in points
            }
            
            # 收集结果
            completed_points = []
            for i, future in enumerate(concurrent.futures.as_completed(future_to_point)):
                point = future_to_point[future]
                try:
                    result_point = future.result()
                    completed_points.append(result_point)
                    if (i + 1) % 10 == 0:
                        print(f"进度: {i + 1}/{len(points)} 完成")
                except Exception as e:
                    print(f"查询点 {point.name} ({point.lat}, {point.lon}) 时出错: {e}")
                    completed_points.append(point)
        
        elapsed_time = time.time() - start_time
        print(f"批量查询完成，耗时: {elapsed_time:.2f}秒，平均每个点: {elapsed_time/len(points):.3f}秒")
        
        return completed_points
    
    def efficient_batch_query(self, points: List[ElevationPoint]) -> List[ElevationPoint]:
        """
        使用单个大查询批量获取海拔数据（更高效的方法）
        
        Args:
            points: 要查询的点列表
            
        Returns:
            包含海拔数据的点列表
        """
        print(f"使用高效批量查询方法处理 {len(points)} 个点...")
        start_time = time.time()
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 构建包含所有点的临时表
            point_data = []
            for i, point in enumerate(points):
                point_data.append(f"({i}, {point.lat}, {point.lon}, '{point.name}')")
            
            # 创建临时表并插入所有点
            cursor.execute("""
                CREATE TEMP TABLE temp_query_points (
                    id INTEGER,
                    lat FLOAT,
                    lon FLOAT,
                    name VARCHAR(255)
                ) ON COMMIT DROP;
            """)
            
            # 批量插入点数据
            for i in range(0, len(point_data), self.batch_size):
                batch = point_data[i:i + self.batch_size]
                values_str = ', '.join(batch)
                cursor.execute(f"INSERT INTO temp_query_points (id, lat, lon, name) VALUES {values_str};")
            
            # 执行批量查询 - 为每个点找到最近的海拔数据
            cursor.execute("""
                SELECT 
                    t.id,
                    t.name,
                    t.lat as query_lat,
                    t.lon as query_lon,
                    p.ele as elevation,
                    p.name as source_name,
                    ST_X(ST_Transform(p.way, 4326)) as source_lon,
                    ST_Y(ST_Transform(p.way, 4326)) as source_lat,
                    CASE 
                        WHEN p.amenity IS NOT NULL THEN 'amenity=' || p.amenity
                        WHEN p.tourism IS NOT NULL THEN 'tourism=' || p.tourism
                        WHEN p."natural" IS NOT NULL THEN 'natural=' || p."natural"
                        WHEN p.man_made IS NOT NULL THEN 'man_made=' || p.man_made
                        ELSE '普通地点'
                    END as feature_type,
                    ST_Distance(
                        ST_Transform(p.way, 4326), 
                        ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)
                    ) * 111000 as distance_meters
                FROM temp_query_points t
                CROSS JOIN LATERAL (
                    SELECT 
                        name,
                        ele,
                        way,
                        amenity,
                        tourism,
                        "natural",
                        man_made,
                        ST_Distance(
                            ST_Transform(way, 4326), 
                            ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)
                        ) as distance
                    FROM planet_osm_point
                    WHERE ele IS NOT NULL 
                        AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                    ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)
                    LIMIT 1
                ) p
                ORDER BY t.id;
            """)
            
            results = cursor.fetchall()
            
            # 将结果映射回原始点
            result_map = {}
            for row in results:
                (point_id, name, query_lat, query_lon, elevation, source_name, 
                 source_lon, source_lat, feature_type, distance) = row
                
                if elevation is not None:
                    result_map[point_id] = {
                        'elevation': float(elevation),
                        'source_name': source_name or '未知地点',
                        'source_coordinates': (source_lat, source_lon),
                        'feature_type': feature_type,
                        'distance': distance
                    }
            
            # 更新原始点的数据
            for i, point in enumerate(points):
                if i in result_map:
                    data = result_map[i]
                    point.elevation = data['elevation']
                    point.source_name = data['source_name']
                    point.distance = data['distance']
                    point.feature_type = data['feature_type']
                else:
                    print(f"未找到点 {point.name} ({point.lat}, {point.lon}) 的海拔数据")
            
            elapsed_time = time.time() - start_time
            print(f"高效批量查询完成，耗时: {elapsed_time:.2f}秒，平均每个点: {elapsed_time/len(points):.3f}秒")
            
            return points
            
        except Exception as e:
            print(f"高效批量查询时出错: {e}")
            return self.batch_query_elevations(points)  # 回退到普通批量查询
            
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def _query_single_point(self, point: ElevationPoint) -> ElevationPoint:
        """
        查询单个点的海拔数据
        
        Args:
            point: 要查询的点
            
        Returns:
            包含海拔数据的点
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    name,
                    ele as elevation_meters,
                    ST_X(ST_Transform(way, 4326)) as longitude,
                    ST_Y(ST_Transform(way, 4326)) as latitude,
                    CASE 
                        WHEN amenity IS NOT NULL THEN 'amenity=' || amenity
                        WHEN tourism IS NOT NULL THEN 'tourism=' || tourism
                        WHEN "natural" IS NOT NULL THEN 'natural=' || "natural"
                        WHEN man_made IS NOT NULL THEN 'man_made=' || man_made
                        ELSE '普通地点'
                    END as feature_type,
                    ST_Distance(
                        ST_Transform(way, 4326), 
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    ) * 111000 as distance_meters
                FROM planet_osm_point
                WHERE ele IS NOT NULL 
                    AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                LIMIT 1;
            """
            
            cursor.execute(query, (point.lon, point.lat, point.lon, point.lat))
            result = cursor.fetchone()
            
            if result:
                (name, elevation, longitude, latitude, feature_type, distance) = result
                point.elevation = float(elevation)
                point.source_name = name or '未知地点'
                point.distance = distance
                point.feature_type = feature_type
            
            return point
            
        except Exception as e:
            print(f"查询点 {point.name} 时出错: {e}")
            return point
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

def main():
    """主函数：演示批量海拔查询"""
    
    # 数据库配置
    db_config = {
        'host': '10.0.0.16',
        'port': 5455,
        'database': 'osm_db',
        'user': 'postgres',
        'password': 'postgres123'
    }
    
    # 创建批量查询器
    querier = BatchElevationQuerier(db_config)
    
    # 测试数据：多个观测点
    test_points = [
        ElevationPoint(39.9042, 116.4074, "北京天安门"),
        ElevationPoint(31.2304, 121.4737, "上海外滩"),
        ElevationPoint(39.9163, 116.3972, "北京故宫"),
        ElevationPoint(30.2636, 120.1616, "杭州西湖"),
        ElevationPoint(29.8782, 121.5736, "宁波天一阁"),
        ElevationPoint(32.0603, 118.7969, "南京紫金山"),
        ElevationPoint(34.3416, 108.9398, "西安大雁塔"),
        ElevationPoint(30.5728, 104.0668, "成都宽窄巷子"),
        ElevationPoint(22.5431, 114.0579, "深圳世界之窗"),
        ElevationPoint(23.1291, 113.2644, "广州塔"),
    ]
    
    print("🏔️ 批量海拔查询演示")
    print("=" * 60)
    
    # 方法1：高效批量查询
    print("\n📊 使用高效批量查询方法：")
    efficient_results = querier.efficient_batch_query(test_points.copy())
    
    print("\n📍 查询结果：")
    for point in efficient_results:
        if point.elevation is not None:
            print(f"   {point.name}: {point.elevation:.1f}米 (距离: {point.distance:.0f}米, 来源: {point.source_name})")
        else:
            print(f"   {point.name}: 未找到海拔数据")
    
    # 方法2：并发批量查询
    print("\n📊 使用并发批量查询方法：")
    concurrent_results = querier.batch_query_elevations(test_points.copy(), max_workers=3)
    
    print("\n📍 查询结果：")
    for point in concurrent_results:
        if point.elevation is not None:
            print(f"   {point.name}: {point.elevation:.1f}米 (距离: {point.distance:.0f}米, 来源: {point.source_name})")
        else:
            print(f"   {point.name}: 未找到海拔数据")
    
    # 性能测试：大量数据
    print("\n🚀 性能测试：查询100个随机点")
    import random
    
    # 生成100个测试点（在中国范围内）
    performance_points = []
    for i in range(100):
        lat = random.uniform(20.0, 45.0)  # 中国纬度范围
        lon = random.uniform(100.0, 125.0)  # 中国经度范围
        performance_points.append(ElevationPoint(lat, lon, f"测试点_{i+1}"))
    
    start_time = time.time()
    performance_results = querier.efficient_batch_query(performance_points)
    elapsed_time = time.time() - start_time
    
    successful_queries = sum(1 for p in performance_results if p.elevation is not None)
    print(f"\n📈 性能测试结果：")
    print(f"   总点数: 100")
    print(f"   成功查询: {successful_queries}")
    print(f"   总耗时: {elapsed_time:.2f}秒")
    print(f"   平均每个点: {elapsed_time/100:.3f}秒")
    print(f"   查询成功率: {successful_queries}%")

if __name__ == "__main__":
    main()