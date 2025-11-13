#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量海拔查询模块

提供高效的批量海拔数据查询功能，支持PostGIS数据库。
"""

import psycopg2
import time
from typing import List, Dict, Tuple, Optional, Union
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ElevationResult:
    """海拔查询结果"""
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    source_name: Optional[str] = None
    distance_meters: Optional[float] = None
    feature_type: Optional[str] = None
    error: Optional[str] = None

class BatchElevationQuery:
    """
    批量海拔查询器
    
    提供高效的批量海拔数据查询，支持两种模式：
    1. 单查询模式：为每个点执行单独查询
    2. 批量查询模式：一次性查询所有点（推荐）
    """
    
    def __init__(self, db_config: Dict, batch_size: int = 50):
        """
        初始化批量查询器
        
        Args:
            db_config: 数据库连接配置
            batch_size: 每批处理的最大点数
        """
        self.db_config = db_config
        self.batch_size = batch_size
        self._validate_config()
    
    def _validate_config(self):
        """验证数据库配置"""
        required_keys = ['host', 'port', 'database', 'user', 'password']
        missing_keys = [key for key in required_keys if key not in self.db_config]
        if missing_keys:
            raise ValueError(f"数据库配置缺少必需字段: {missing_keys}")
    
    def query_elevations(self, 
                        coordinates: List[Tuple[float, float]], 
                        names: Optional[List[str]] = None,
                        use_batch_query: bool = True) -> List[ElevationResult]:
        """
        批量查询海拔数据
        
        Args:
            coordinates: 坐标列表 [(lat, lon), ...]
            names: 地点名称列表（可选）
            use_batch_query: 是否使用批量查询模式（推荐True）
            
        Returns:
            海拔结果列表
        """
        if not coordinates:
            return []
        
        # 生成默认名称
        if names is None:
            names = [f"Point_{i+1}" for i in range(len(coordinates))]
        elif len(names) < len(coordinates):
            names.extend([f"Point_{i+1}" for i in range(len(names), len(coordinates))])
        
        logger.info(f"开始查询 {len(coordinates)} 个点的海拔数据")
        start_time = time.time()
        
        try:
            if use_batch_query:
                results = self._batch_query(coordinates, names)
            else:
                results = self._individual_queries(coordinates, names)
            
            elapsed_time = time.time() - start_time
            successful_count = sum(1 for r in results if r.elevation is not None)
            
            logger.info(f"查询完成: {successful_count}/{len(coordinates)} 成功, "
                       f"耗时: {elapsed_time:.2f}秒, "
                       f"平均: {elapsed_time/len(coordinates):.3f}秒/点")
            
            return results
            
        except Exception as e:
            logger.error(f"批量查询失败: {e}")
            # 返回错误结果
            return [
                ElevationResult(latitude=lat, longitude=lon, error=str(e))
                for lat, lon in coordinates
            ]
    
    def _batch_query(self, coordinates: List[Tuple[float, float]], names: List[str]) -> List[ElevationResult]:
        """使用批量查询模式"""
        results = []
        
        # 分批处理
        for i in range(0, len(coordinates), self.batch_size):
            batch_coords = coordinates[i:i + self.batch_size]
            batch_names = names[i:i + self.batch_size]
            
            logger.debug(f"处理批次 {i//self.batch_size + 1}: "
                        f"{len(batch_coords)} 个点")
            
            batch_results = self._execute_batch_query(batch_coords, batch_names)
            results.extend(batch_results)
        
        return results
    
    def _execute_batch_query(self, coordinates: List[Tuple[float, float]], names: List[str]) -> List[ElevationResult]:
        """执行单个批量查询"""
        conn = None
        cursor = None
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # 创建临时表
            cursor.execute("""
                CREATE TEMP TABLE temp_elevation_points (
                    id SERIAL PRIMARY KEY,
                    lat DOUBLE PRECISION,
                    lon DOUBLE PRECISION,
                    name VARCHAR(255)
                ) ON COMMIT DROP;
            """)
            
            # 插入坐标数据
            for i, (lat, lon) in enumerate(coordinates):
                cursor.execute(
                    "INSERT INTO temp_elevation_points (lat, lon, name) VALUES (%s, %s, %s)",
                    (lat, lon, names[i])
                )
            
            # 执行批量查询
            cursor.execute("""
                SELECT 
                    t.id,
                    t.lat,
                    t.lon,
                    t.name,
                    p.ele::float as elevation,
                    p.name as source_name,
                    ST_Distance(
                        ST_Transform(p.way, 4326), 
                        ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)
                    ) * 111000 as distance_meters,
                    CASE 
                        WHEN p.amenity IS NOT NULL THEN 'amenity=' || p.amenity
                        WHEN p.tourism IS NOT NULL THEN 'tourism=' || p.tourism
                        WHEN p."natural" IS NOT NULL THEN 'natural=' || p."natural"
                        WHEN p.man_made IS NOT NULL THEN 'man_made=' || p.man_made
                        ELSE '普通地点'
                    END as feature_type
                FROM temp_elevation_points t
                CROSS JOIN LATERAL (
                    SELECT 
                        name,
                        ele,
                        way,
                        amenity,
                        tourism,
                        "natural",
                        man_made
                    FROM planet_osm_point
                    WHERE ele IS NOT NULL 
                        AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                        AND ele::float >= -500  -- 最低海拔限制（死海约-430米）
                        AND ele::float <= 9000  -- 最高海拔限制（珠峰8848.86米，留一点余量）
                    ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)
                    LIMIT 1
                ) p
                ORDER BY t.id;
            """)
            
            query_results = cursor.fetchall()
            
            # 构建结果
            results = []
            for row in query_results:
                (point_id, lat, lon, name, elevation, source_name, 
                 distance, feature_type) = row
                
                result = ElevationResult(
                    latitude=lat,
                    longitude=lon,
                    elevation=elevation,
                    source_name=source_name,
                    distance_meters=distance,
                    feature_type=feature_type
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"批量查询执行失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def _individual_queries(self, coordinates: List[Tuple[float, float]], names: List[str]) -> List[ElevationResult]:
        """使用单独查询模式（较慢，但更简单）"""
        results = []
        
        for i, (lat, lon) in enumerate(coordinates):
            try:
                result = self._query_single_point(lat, lon, names[i])
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.debug(f"进度: {i + 1}/{len(coordinates)}")
                    
            except Exception as e:
                logger.warning(f"查询点 {names[i]} ({lat}, {lon}) 失败: {e}")
                results.append(ElevationResult(lat, lon, error=str(e)))
        
        return results
    
    def _query_single_point(self, lat: float, lon: float, name: str) -> ElevationResult:
        """查询单个点的海拔"""
        conn = None
        cursor = None
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    ele::float as elevation,
                    name as source_name,
                    ST_Distance(
                        ST_Transform(way, 4326), 
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    ) * 111000 as distance_meters,
                    CASE 
                        WHEN amenity IS NOT NULL THEN 'amenity=' || amenity
                        WHEN tourism IS NOT NULL THEN 'tourism=' || tourism
                        WHEN "natural" IS NOT NULL THEN 'natural=' || "natural"
                        WHEN man_made IS NOT NULL THEN 'man_made=' || man_made
                        ELSE '普通地点'
                    END as feature_type
                FROM planet_osm_point
                WHERE ele IS NOT NULL 
                    AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                    AND ele::float >= -500  -- 最低海拔限制（死海约-430米）
                    AND ele::float <= 9000  -- 最高海拔限制（珠峰8848.86米，留一点余量）
                ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                LIMIT 1;
            """, (lon, lat, lon, lat))
            
            result = cursor.fetchone()
            
            if result:
                elevation, source_name, distance, feature_type = result
                return ElevationResult(
                    latitude=lat,
                    longitude=lon,
                    elevation=elevation,
                    source_name=source_name or '未知地点',
                    distance_meters=distance,
                    feature_type=feature_type
                )
            else:
                return ElevationResult(
                    latitude=lat,
                    longitude=lon,
                    error="未找到海拔数据"
                )
                
        except Exception as e:
            logger.error(f"单点查询失败: {e}")
            return ElevationResult(lat, lon, error=str(e))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_statistics(self) -> Dict:
        """获取数据库中海拔数据的统计信息"""
        conn = None
        cursor = None
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_points,
                    MIN(ele::float) as min_elevation,
                    MAX(ele::float) as max_elevation,
                    AVG(ele::float) as avg_elevation,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ele::float) as median_elevation
                FROM planet_osm_point
                WHERE ele IS NOT NULL 
                    AND ele ~ '^[0-9]+(\\.[0-9]+)?$';
            """)
            
            stats = cursor.fetchone()
            if stats:
                return {
                    'total_points': stats[0],
                    'min_elevation': float(stats[1]) if stats[1] else None,
                    'max_elevation': float(stats[2]) if stats[2] else None,
                    'avg_elevation': float(stats[3]) if stats[3] else None,
                    'median_elevation': float(stats[4]) if stats[4] else None
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

# 便捷函数
def batch_query_elevations(coordinates: List[Tuple[float, float]], 
                          db_config: Dict,
                          names: Optional[List[str]] = None,
                          batch_size: int = 50) -> List[ElevationResult]:
    """
    便捷的批量海拔查询函数
    
    Args:
        coordinates: 坐标列表 [(lat, lon), ...]
        db_config: 数据库配置
        names: 地点名称列表（可选）
        batch_size: 批处理大小
        
    Returns:
        海拔结果列表
    """
    querier = BatchElevationQuery(db_config, batch_size)
    return querier.query_elevations(coordinates, names)

def get_elevation_statistics(db_config: Dict) -> Dict:
    """
    获取数据库海拔统计信息
    
    Args:
        db_config: 数据库配置
        
    Returns:
        统计信息字典
    """
    querier = BatchElevationQuery(db_config)
    return querier.get_statistics()