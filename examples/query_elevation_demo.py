#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostGIS海拔数据查询 - 基于实际数据库配置

这个脚本使用之前验证过的数据库连接配置来查询海拔数据。
"""

import psycopg2
import os

def get_elevation_from_postgis(lat, lon):
    """
    从PostGIS数据库获取指定坐标点的海拔数据
    
    Args:
        lat: 纬度 (WGS84)
        lon: 经度 (WGS84)
        
    Returns:
        dict: 包含海拔信息的结果，如果失败返回None
    """
    
    # 使用之前验证过的数据库连接配置
    db_config = {
    'host': '10.0.0.16',
    'port': 5455,
    'database': 'osm_db',
    'user': 'postgres',
    'password': 'postgres123'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # 主要的SQL查询：找到最近的海拔点
        # 添加海拔范围验证（地球最高点是8848.86米，最低是-430米）
        query = """
            SELECT 
                name,
                ele as elevation_meters,
                ST_X(ST_Transform(way, 4326)) as longitude,
                ST_Y(ST_Transform(way, 4326)) as latitude,
                osm_id,
                amenity,
                tourism,
                man_made,
                "natural",
                ST_Distance(
                    ST_Transform(way, 4326), 
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                ) * 111000 as distance_meters
            FROM planet_osm_point
            WHERE ele IS NOT NULL 
                AND ele ~ '^[0-9]+(\\.[0-9]+)?$'  -- 确保ele是有效数字
                AND ele::float >= -500  -- 最低海拔限制（死海约-430米）
                AND ele::float <= 9000  -- 最高海拔限制（珠峰8848.86米，留一点余量）
            ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 1;
        """
        
        cursor.execute(query, (lon, lat, lon, lat))
        result = cursor.fetchone()
        
        if result:
            name, elevation, longitude, latitude, osm_id, amenity, tourism, man_made, natural, distance = result
            
            # 构建返回结果
            elevation_data = {
                'elevation': float(elevation),
                'source_name': name or '未知地点',
                'source_coordinates': (latitude, longitude),
                'osm_id': osm_id,
                'distance_to_query_point': distance,
                'feature_type': None,
                'tags': {}
            }
            
            # 确定特征类型
            if amenity:
                elevation_data['feature_type'] = f"amenity={amenity}"
            elif tourism:
                elevation_data['feature_type'] = f"tourism={tourism}"
            elif result[8]:  # natural字段在结果中的索引位置
                elevation_data['feature_type'] = f"natural={result[8]}"
            elif man_made:
                elevation_data['feature_type'] = f"man_made={man_made}"
            else:
                elevation_data['feature_type'] = "普通地点"
            
            # 收集所有标签
            if amenity:
                elevation_data['tags']['amenity'] = amenity
            if tourism:
                elevation_data['tags']['tourism'] = tourism
            if result[8]:  # natural字段在结果中的索引位置
                elevation_data['tags']['natural'] = result[8]
            if man_made:
                elevation_data['tags']['man_made'] = man_made
            
            return elevation_data
        else:
            print(f"在坐标 ({lat}, {lon}) 附近未找到海拔数据")
            return None
            
    except Exception as e:
        print(f"查询海拔数据时出错: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_elevation_statistics():
    """获取数据库中海拔数据的统计信息"""
    
    db_config = {
    'host': '10.0.0.16',
    'port': 5455,
    'database': 'osm_db',
    'user': 'postgres',
    'password': 'postgres123'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # 基本统计 - 添加海拔范围验证
        cursor.execute("""
            SELECT 
                COUNT(*) as total_points_with_elevation,
                MIN(ele::float) as min_elevation,
                MAX(ele::float) as max_elevation,
                AVG(ele::float) as avg_elevation,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ele::float) as median_elevation
            FROM planet_osm_point
            WHERE ele IS NOT NULL 
                AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                AND ele::float >= -500  -- 最低海拔限制（死海约-430米）
                AND ele::float <= 9000; -- 最高海拔限制（珠峰8848.86米，留一点余量）
        """)
        
        stats = cursor.fetchone()
        if stats and stats[0] > 0:
            total, min_elev, max_elev, avg_elev, median_elev = stats
            print(f"📊 数据库海拔数据统计:")
            print(f"   有海拔数据的地点总数: {total:,}")
            print(f"   最低海拔: {min_elev:.1f}米")
            print(f"   最高海拔: {max_elev:.1f}米")
            print(f"   平均海拔: {avg_elev:.1f}米")
            print(f"   中位数海拔: {median_elev:.1f}米")
            
            # 按类型统计 - 添加海拔范围验证
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN amenity = 'observatory' THEN '天文台'
                        WHEN tourism = 'viewpoint' THEN '观景点'
                        WHEN "natural" = 'peak' THEN '山峰'
                        WHEN man_made = 'tower' THEN '塔'
                        WHEN railway = 'station' THEN '火车站'
                        ELSE '其他'
                    END as feature_type,
                    COUNT(*) as count,
                    ROUND(CAST(AVG(ele::float) AS NUMERIC), 1) as avg_elevation,
                    ROUND(CAST(MIN(ele::float) AS NUMERIC), 1) as min_elevation,
                    ROUND(CAST(MAX(ele::float) AS NUMERIC), 1) as max_elevation
                FROM planet_osm_point
                WHERE ele IS NOT NULL 
                    AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                    AND ele::float >= -500  -- 最低海拔限制
                    AND ele::float <= 9000  -- 最高海拔限制
                GROUP BY feature_type
                ORDER BY avg_elevation DESC;
            """)
            
            type_stats = cursor.fetchall()
            if type_stats:
                print(f"\n🏔️  按特征类型统计:")
                for feature_type, count, avg_elev, min_elev, max_elev in type_stats:
                    print(f"   {feature_type}: {count}个, 平均海拔{avg_elev}米 (范围: {min_elev}-{max_elev}米)")
            
            return True
        else:
            print("数据库中没有找到海拔数据")
            return False
            
    except Exception as e:
        print(f"获取统计信息时出错: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def main():
    """主函数：演示海拔查询功能"""
    print("🏔️  PostGIS海拔数据查询")
    print("=" * 50)
    
    # 获取统计信息
    print("\n📊 数据库统计信息:")
    get_elevation_statistics()
    
    # 测试几个地点
    test_locations = [
        (39.9042, 116.4074, "北京天安门"),
        (31.2304, 121.4737, "上海外滩"),
        (39.9163, 116.3972, "北京故宫"),
    ]
    
    print(f"\n📍 查询测试地点海拔:")
    for lat, lon, location_name in test_locations:
        print(f"\n🔍 查询 {location_name} ({lat}, {lon}):")
        elevation_data = get_elevation_from_postgis(lat, lon)
        
        if elevation_data:
            print(f"   ✅ 找到海拔数据:")
            print(f"      海拔: {elevation_data['elevation']}米")
            print(f"      来源: {elevation_data['source_name']}")
            print(f"      坐标: {elevation_data['source_coordinates']}")
            print(f"      类型: {elevation_data['feature_type']}")
            print(f"      距离查询点: {elevation_data['distance_to_query_point']:.1f}米")
        else:
            print(f"   ❌ 未找到海拔数据")

if __name__ == "__main__":
    main()