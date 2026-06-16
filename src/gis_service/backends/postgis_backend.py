# -*- coding: utf-8 -*-
"""
PostGIS 查询后端封装。

将 stargazing_place_finder.py 中的 PostGISClient 和
elevation_batch_query.py 中的 BatchElevationQuery 统一到此模块。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from models import DataError, ElevationResult, NetworkError

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
        lon_min: float,
        lat_min: float,
        lon_max: float,
        lat_max: float,
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
        try:
            query = self._build_location_query(location_type, filters)
            cursor.execute(query, (lon_min, lat_min, lon_max, lat_max))
            results = cursor.fetchall()
            return [self._format_location_row(row) for row in results]
        finally:
            cursor.close()
            conn.close()

    def _build_location_query(self, location_type: Optional[str], filters: Optional[str]) -> str:
        """构建位置查询 SQL。"""
        base = """
            SELECT osm_id, name,
                   ST_X(ST_Transform(way, 4326)) as longitude,
                   ST_Y(ST_Transform(way, 4326)) as latitude,
                   amenity, tourism, shop, highway, place,
                   man_made, "tower:type" as tower_type,
                   leisure, "natural"
            FROM planet_osm_point
            WHERE ST_Transform(way, 4326) && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
        """
        conditions = []
        if location_type == "town":
            conditions.append("place IN ('city','town','village','hamlet') AND name IS NOT NULL")
        elif location_type == "observatory":
            conditions.append(
                "(amenity='observatory' OR man_made='telescope' OR "
                "(man_made='tower' AND \"tower:type\"='astronomical') OR amenity='planetarium')"
            )
        elif location_type == "viewpoint":
            conditions.append(
                "(tourism='viewpoint' OR (man_made='tower' AND \"tower:type\"='observation') OR "
                "amenity='observation_deck' OR leisure='viewing_platform')"
            )
        elif location_type == "peak":
            conditions.append("(\"natural\" IN ('peak','volcano'))")
        if filters:
            conditions.append(filters)
        if conditions:
            return base + " AND " + " AND ".join(conditions)
        return base

    def _format_location_row(self, row: tuple) -> Dict[str, Any]:
        """将 SQL 查询行格式化为 Overpass 兼容 dict。"""
        elem: Dict[str, Any] = {"type": "node", "id": row[0], "lat": row[3], "lon": row[2], "tags": {}}
        tag_mappings = [
            ("name", 1),
            ("amenity", 4),
            ("tourism", 5),
            ("shop", 6),
            ("highway", 7),
            ("place", 8),
            ("man_made", 9),
            ("tower:type", 10),
            ("leisure", 11),
            ("natural", 12),
        ]
        for key, idx in tag_mappings:
            if row[idx]:
                elem["tags"][key] = row[idx]
        return elem

    # ── 批量高程查询 ──────────────────────────────────────────

    def batch_query_elevations(
        self,
        coordinates: List[Tuple[float, float]],
        names: Optional[List[str]] = None,
        batch_size: int = 50,
    ) -> List[ElevationResult]:
        """
        批量查询多个坐标的海拔（已分块），返回一致的数据模型。

        Args:
            coordinates: [(lat, lon), ...]
            names: 可选地点名称列表
            batch_size: 每批处理数量，默认 50

        Returns:
            List[ElevationResult] — 每个坐标一个结果，顺序与输入一致
        """
        if not coordinates:
            return []

        if names is None:
            names = [f"Point_{i + 1}" for i in range(len(coordinates))]
        elif len(names) < len(coordinates):
            names.extend([f"Point_{i + 1}" for i in range(len(names), len(coordinates))])

        all_results: List[ElevationResult] = []
        for start in range(0, len(coordinates), batch_size):
            batch_coords = coordinates[start : start + batch_size]
            batch_names = names[start : start + batch_size]
            all_results.extend(self._query_single_batch(batch_coords, batch_names))
        return all_results

    def _query_single_batch(
        self,
        coordinates: List[Tuple[float, float]],
        names: List[str],
    ) -> List[ElevationResult]:
        """执行单批海拔查询。"""
        import psycopg2

        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()
        try:
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

            results: List[ElevationResult] = []
            for row in cursor.fetchall():
                _id, lat, lon, name, elev, source, dist, ftype = row
                results.append(
                    ElevationResult(
                        latitude=lat,
                        longitude=lon,
                        elevation=elev,
                        source_name=source or "unknown",
                        distance_meters=dist,
                        feature_type=ftype,
                    )
                )

            logger.info(
                "Elevation batch query: %d points, %d found",
                len(coordinates),
                sum(1 for r in results if r.elevation is not None),
            )
            return results
        except Exception as e:
            logger.error("PostGIS batch elevation query failed: %s", e)
            raise DataError(f"PostGIS batch elevation query failed: {e}") from e
        finally:
            cursor.close()
            conn.close()

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
        except DataError:
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

    # ── 道路连通性查询 ────────────────────────────────────────

    # network_type → highway 类型映射
    _HIGHWAY_FILTERS: Dict[str, str] = {
        "drive": (
            "highway IN ('motorway','trunk','primary','secondary','tertiary',"
            "'unclassified','residential','motorway_link','trunk_link',"
            "'primary_link','secondary_link','tertiary_link','living_street','service')"
        ),
        "walk": ("highway IN ('footway','path','steps','pedestrian','living_street','track')"),
        "bike": ("highway IN ('cycleway','path','track','living_street','bridleway')"),
        "all": "highway IS NOT NULL",
    }

    def query_road_connectivity(
        self,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        network_type: str = "drive",
    ) -> Dict[str, Any]:
        """
        使用 PostGIS kNN 算子查询最近道路，替代 OSMnx HTTP 下载。

        查询 planet_osm_line 表，用 <-> 算子利用 GiST 空间索引
        找到最近的道路，返回距离、类型等信息，毫秒级完成。

        Args:
            lat: 纬度 (WGS84)
            lon: 经度 (WGS84)
            radius_km: 搜索半径（千米），用于判断是否可达
            network_type: 道路类型 ('drive', 'walk', 'bike', 'all')

        Returns:
            Dict with:
                - accessible: bool 是否可达（距离不超过 radius_km/2 且不超过 5km）
                - distance_meters: float 到最近道路的距离（米）
                - road_type: str 最近道路的 highway 类型
                - road_name: Optional[str] 道路名称
                - nearest_lat: Optional[float] 最近点纬度
                - nearest_lon: Optional[float] 最近点经度
        """
        highway_filter = self._HIGHWAY_FILTERS.get(network_type, "highway IS NOT NULL")
        try:
            row = self._execute_road_knn_query(lat, lon, highway_filter)
            return self._build_road_connectivity_result(row, radius_km)
        except (NetworkError, DataError) as e:
            logger.error("Road connectivity query failed for (%s, %s): %s", lat, lon, e)
            return {
                "accessible": False,
                "distance_meters": None,
                "road_type": None,
                "road_name": None,
                "nearest_lat": None,
                "nearest_lon": None,
                "error": str(e),
            }

    def _execute_road_knn_query(self, lat: float, lon: float, highway_filter: str) -> Optional[tuple]:
        """执行 kNN 道路查询，返回原始行。"""
        import psycopg2

        conn = psycopg2.connect(**self.config)
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT highway, name,
                    ST_Distance(
                        ST_Transform(way, 4326)::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) as distance_meters,
                    ST_Y(ST_ClosestPoint(ST_Transform(way, 4326),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326))) as nearest_lat,
                    ST_X(ST_ClosestPoint(ST_Transform(way, 4326),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326))) as nearest_lon
                FROM planet_osm_line
                WHERE {highway_filter}
                ORDER BY way <-> ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857)
                LIMIT 1;
            """,
                (lon, lat, lon, lat, lon, lat, lon, lat),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def _build_road_connectivity_result(self, row: Optional[tuple], radius_km: float) -> Dict[str, Any]:
        """将 kNN 查询行格式化为道路连通性结果。"""
        if row is None:
            return {
                "accessible": False,
                "distance_meters": None,
                "road_type": None,
                "road_name": None,
                "nearest_lat": None,
                "nearest_lon": None,
            }
        highway, name, distance_meters, nearest_lat, nearest_lon = row
        max_distance_meters = min(radius_km * 1000 / 2, 5000.0)
        return {
            "accessible": distance_meters <= max_distance_meters,
            "distance_meters": distance_meters,
            "road_type": highway,
            "road_name": name,
            "nearest_lat": nearest_lat,
            "nearest_lon": nearest_lon,
        }

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
                    "total_points": row[0],
                    "min_elevation": float(row[1]) if row[1] else None,
                    "max_elevation": float(row[2]) if row[2] else None,
                    "avg_elevation": float(row[3]) if row[3] else None,
                    "median_elevation": float(row[4]) if row[4] else None,
                }
            return {}
        except DataError as e:
            logger.error("Elevation stats query failed: %s", e)
            return {"error": str(e)}
        finally:
            try:
                cursor.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
