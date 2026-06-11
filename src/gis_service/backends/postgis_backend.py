# -*- coding: utf-8 -*-
"""
PostGIS 查询后端封装。

将 stargazing_place_finder.py 中的 PostGISClient 和
elevation_batch_query.py 中的 BatchElevationQuery 统一到此模块。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PostgisBackend:
    """
    PostGIS 数据库后端。

    提供统一的 OSM 空间数据查询，查询结果格式兼容 Overpass API 响应，
    允许上层在 PostGIS 与 Overpass 间透明切换。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: psycopg2 连接参数字典 (host, port, database, user, password)
        """
        self.config = config

    # ── OSM 位置查询 ──────────────────────────────────────────

    def query_locations_in_bbox(
        self,
        lon_min: float, lat_min: float, lon_max: float, lat_max: float,
        location_type: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        在 bounding box 内查询 OSM 位置，返回 Overpass 兼容的 dict 列表。

        Args:
            lon_min, lat_min, lon_max, lat_max: WGS84 包围盒
            location_type: 类型筛选 ('town', 'observatory', 'viewpoint', 'peak')
            filters: 额外 SQL 条件

        Returns:
            Overpass 兼容的 element dict 列表
        """
        import psycopg2

        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()

        base_query = """
            SELECT
                osm_id, name,
                ST_X(ST_Transform(way, 4326)) as longitude,
                ST_Y(ST_Transform(way, 4326)) as latitude,
                amenity, tourism, shop, highway, place,
                man_made, "tower:type" as tower_type,
                leisure, "natural"
            FROM planet_osm_point
            WHERE ST_Transform(way, 4326) && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
        """

        type_conditions = []
        if location_type == 'town':
            type_conditions.append(
                "place IN ('city', 'town', 'village', 'hamlet') AND name IS NOT NULL"
            )
        elif location_type == 'observatory':
            type_conditions.append(
                "(amenity = 'observatory' OR man_made = 'telescope' "
                "OR (man_made = 'tower' AND \"tower:type\" = 'astronomical') "
                "OR amenity = 'planetarium')"
            )
        elif location_type == 'viewpoint':
            type_conditions.append(
                "(tourism = 'viewpoint' "
                "OR (man_made = 'tower' AND \"tower:type\" = 'observation') "
                "OR amenity = 'observation_deck' "
                "OR leisure = 'viewing_platform')"
            )
        elif location_type == 'peak':
            type_conditions.append('("natural" IN (\'peak\',\'volcano\'))')

        conditions = list(type_conditions)
        if filters:
            conditions.append(filters)

        if conditions:
            query = base_query + " AND " + " AND ".join(conditions)
        else:
            query = base_query

        cursor.execute(query, (lon_min, lat_min, lon_max, lat_max))
        results = cursor.fetchall()

        formatted: List[Dict[str, Any]] = []
        for row in results:
            elem: Dict[str, Any] = {'type': 'node', 'id': row[0], 'lat': row[3], 'lon': row[2], 'tags': {}}
            tag_keys = [
                ('name', 1), ('amenity', 4), ('tourism', 5), ('shop', 6),
                ('highway', 7), ('place', 8), ('man_made', 9),
                ('tower:type', 10), ('leisure', 11), ('natural', 12),
            ]
            for key, idx in tag_keys:
                if row[idx]:
                    elem['tags'][key] = row[idx]
            formatted.append(elem)

        cursor.close()
        conn.close()
        return formatted

    # ── 批量高程查询 ──────────────────────────────────────────

    def batch_query_elevations(
        self, coordinates: List[Tuple[float, float]],
        names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        批量查询多个坐标的海拔。

        Args:
            coordinates: [(lat, lon), ...]
            names: 可选地点名称列表

        Returns:
            [{'lat': .., 'lon': .., 'elevation': .. or None, 'name': .., 'distance_meters': .., 'feature_type': ..}, ...]
        """
        if not coordinates:
            return []

        import psycopg2

        if names is None:
            names = [f"Point_{i+1}" for i in range(len(coordinates))]
        elif len(names) < len(coordinates):
            names.extend([f"Point_{i+1}" for i in range(len(names), len(coordinates))])

        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TEMP TABLE _gis_elev_pts (
                id SERIAL PRIMARY KEY, lat DOUBLE PRECISION,
                lon DOUBLE PRECISION, name VARCHAR(255)
            ) ON COMMIT DROP;
        """)
        for i, (lat, lon) in enumerate(coordinates):
            cursor.execute(
                "INSERT INTO _gis_elev_pts (lat, lon, name) VALUES (%s, %s, %s)",
                (lat, lon, names[i]),
            )

        cursor.execute("""
            SELECT
                t.id, t.lat, t.lon, t.name,
                p.ele::float as elevation,
                p.name as source_name,
                ST_Distance(
                    ST_Transform(p.way, 4326),
                    ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)
                ) * 111000 as distance_meters,
                CASE
                    WHEN p.amenity  IS NOT NULL THEN 'amenity=' || p.amenity
                    WHEN p.tourism  IS NOT NULL THEN 'tourism=' || p.tourism
                    WHEN p."natural" IS NOT NULL THEN 'natural=' || p."natural"
                    WHEN p.man_made IS NOT NULL THEN 'man_made=' || p.man_made
                    ELSE 'unknown'
                END as feature_type
            FROM _gis_elev_pts t
            CROSS JOIN LATERAL (
                SELECT name, ele, way, amenity, tourism, "natural", man_made
                FROM planet_osm_point
                WHERE ele IS NOT NULL
                    AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                    AND ele::float >= -500
                    AND ele::float <= 9000
                ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)
                LIMIT 1
            ) p
            ORDER BY t.id;
        """)

        results = []
        for row in cursor.fetchall():
            _id, lat, lon, name, elev, source, dist, ftype = row
            results.append({
                'lat': lat,
                'lon': lon,
                'name': name,
                'elevation': elev,
                'source_name': source or 'unknown',
                'distance_meters': dist,
                'feature_type': ftype,
            })

        cursor.close()
        conn.close()
        logger.info(
            "Elevation batch query: %d points, %d found",
            len(coordinates), sum(1 for r in results if r['elevation'] is not None),
        )
        return results

    # ── 单点高程查询 ──────────────────────────────────────────

    def find_elevation_at_point(self, lat: float, lon: float) -> Optional[float]:
        """
        查找单点附近最邻近 OSM 元素的海拔。

        Returns:
            海拔（米），未找到则返回 None
        """
        import psycopg2

        try:
            conn = psycopg2.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ele::float FROM planet_osm_point
                WHERE ele IS NOT NULL
                    AND ele ~ '^[0-9]+(\\.[0-9]+)?$'
                    AND ele::float >= -500 AND ele::float <= 9000
                ORDER BY ST_Transform(way, 4326) <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                LIMIT 1;
                """,
                (lon, lat),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception:
            return None
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    # ── 统计信息 ──────────────────────────────────────────────

    def get_elevation_statistics(self) -> Dict[str, Any]:
        """返回 OSM 中海拔数据的统计信息。"""
        import psycopg2

        try:
            conn = psycopg2.connect(**self.config)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    MIN(ele::float), MAX(ele::float),
                    AVG(ele::float),
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ele::float)
                FROM planet_osm_point
                WHERE ele IS NOT NULL AND ele ~ '^[0-9]+(\\.[0-9]+)?$';
            """)
            row = cursor.fetchone()
            if row:
                return {
                    'total_points': row[0],
                    'min_elevation': float(row[1]) if row[1] else None,
                    'max_elevation': float(row[2]) if row[2] else None,
                    'avg_elevation': float(row[3]) if row[3] else None,
                    'median_elevation': float(row[4]) if row[4] else None,
                }
            return {}
        except Exception as e:
            logger.error("Elevation stats query failed: %s", e)
            return {'error': str(e)}
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
