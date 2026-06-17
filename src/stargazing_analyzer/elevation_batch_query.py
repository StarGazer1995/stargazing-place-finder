# -*- coding: utf-8 -*-
"""
批量海拔查询模块（已弃用）

.. deprecated::
    此模块的功能已合并到 :class:`gis_service.backends.postgis_backend.PostgisBackend`。
    新代码应直接使用 ``PostgisBackend.batch_query_elevations()``。
    ``BatchElevationQuery`` 保留仅为向后兼容，内部委托给 ``PostgisBackend``。
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import psycopg2

from models import ElevationResult, NetworkError

logger = logging.getLogger(__name__)


class BatchElevationQuery:
    """
    批量海拔查询器

    .. deprecated::
        请改用 ``gis_service.backends.postgis_backend.PostgisBackend``。
    """

    def __init__(self, db_config: Dict, batch_size: int = 50):
        self.db_config = db_config
        self.batch_size = batch_size

    def query_elevations(
        self,
        coordinates: List[Tuple[float, float]],
        names: Optional[List[str]] = None,
        use_batch_query: bool = True,  # noqa: ARG002
    ) -> List[ElevationResult]:
        """查询海拔数据，内部委托给 PostgisBackend。"""
        if not coordinates:
            return []

        if names is None:
            names = [f"Point_{i + 1}" for i in range(len(coordinates))]
        elif len(names) < len(coordinates):
            names.extend([f"Point_{i + 1}" for i in range(len(names), len(coordinates))])

        logger.info("查询 %d 个点的海拔数据", len(coordinates))
        start_time = time.time()

        try:
            from gis_service.backends.postgis_backend import PostgisBackend

            backend = PostgisBackend(self.db_config)
            results = backend.batch_query_elevations(coordinates, names, batch_size=self.batch_size)

            elapsed = time.time() - start_time
            ok = sum(1 for r in results if r.elevation is not None)
            logger.info("查询完成: %d/%d 成功, 耗时: %.2f秒", ok, len(coordinates), elapsed)
            return results

        except (psycopg2.Error, NetworkError, ValueError, KeyError) as e:
            logger.error("批量查询失败: %s", e)
            return [ElevationResult(latitude=lat, longitude=lon, error=str(e)) for lat, lon in coordinates]

    def get_statistics(self) -> Dict:
        """获取 PostGIS 中海拔数据统计信息。"""
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_points,
                    COUNT(ele) as points_with_elevation,
                    MIN(ele::float) as min_elevation,
                    MAX(ele::float) as max_elevation,
                    AVG(ele::float) as avg_elevation
                FROM planet_osm_point
                WHERE ele IS NOT NULL
                    AND ele ~ '^[0-9]+(\.[0-9]+)?$'
                    AND ele::float >= -500
                    AND ele::float <= 9000;
            """)
            row = cursor.fetchone()
            return {
                "total_points": row[0],
                "points_with_elevation": row[1],
                "min_elevation": row[2],
                "max_elevation": row[3],
                "avg_elevation": float(row[4]) if row[4] else None,
            }
        finally:
            cursor.close()
            conn.close()


def batch_query_elevations(
    coordinates: List[Tuple[float, float]],
    db_config: Dict,
    batch_size: int = 50,
    names: Optional[List[str]] = None,
) -> List[ElevationResult]:
    """快捷函数（已弃用），请直接使用 ``PostgisBackend.batch_query_elevations()``。"""
    query = BatchElevationQuery(db_config, batch_size=batch_size)
    return query.query_elevations(coordinates, names=names)


def get_elevation_statistics(db_config: Dict) -> Dict:
    """快捷函数（已弃用），保留仅为向后兼容。"""
    query = BatchElevationQuery(db_config)
    return query.get_statistics()
