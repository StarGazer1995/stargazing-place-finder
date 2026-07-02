# -*- coding: utf-8 -*-
"""
PostGIS 查询后端封装。

将 stargazing_place_finder.py 中的 PostGISClient 和
elevation_batch_query.py 中的 BatchElevationQuery 统一到此模块。
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

import networkx as nx
import psycopg2
from psycopg2.pool import SimpleConnectionPool

from models import DataError, ElevationResult, NetworkError

logger = logging.getLogger(__name__)


class PostgisBackend:
    """
    PostGIS 数据库后端。

    提供统一的 OSM 空间数据查询，查询结果格式兼容 Overpass API 响应，
    允许上层在 PostGIS 与 Overpass 间透明切换。

    Uses a connection pool internally to avoid per-query TCP handshakes.
    """

    # Shared elevation filter — used by both point and line kNN queries.
    _ELE_FILTER = "ele IS NOT NULL AND ele ~ '^[0-9]+(\\.[0-9]+)?$' AND ele::float >= -500 AND ele::float <= 9000"

    def __init__(self, config: Dict[str, object]):
        """
        Args:
            config: psycopg2 连接参数字典 (host, port, database, user, password)
        """
        self.config = config
        self._pool: Optional[SimpleConnectionPool] = None

    def _ensure_pool(self) -> SimpleConnectionPool:
        """Create the connection pool on first use (lazy init)."""
        if self._pool is None:
            self._pool = SimpleConnectionPool(1, 4, **self.config)
        return self._pool

    def close(self) -> None:
        """Release the connection pool.  Must be called before discarding the instance."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None

    def _get_conn(self):
        """Borrow a connection from the pool."""
        return self._ensure_pool().getconn()

    def _put_conn(self, conn, close_flag: bool = False):
        """Return a connection to the pool."""
        if self._pool is not None:
            self._pool.putconn(conn, close=close_flag)

    # ── OSM 位置查询 ──────────────────────────────────────────

    def query_locations_in_bbox(
        self,
        lon_min: float,
        lat_min: float,
        lon_max: float,
        lat_max: float,
        location_type: Optional[str] = None,
        filters: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        """
        在 bounding box 内查询 OSM 位置，返回 Overpass 兼容的 dict 列表。

        Args:
            lon_min, lat_min, lon_max, lat_max: WGS84 包围盒
            location_type: 类型筛选 ('town', 'observatory', 'viewpoint', 'peak')
            filters: 额外 SQL 条件

        Returns:
            Overpass 兼容的 element dict 列表
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            query = self._build_location_query(location_type, filters)
            cursor.execute(query, (lon_min, lat_min, lon_max, lat_max))
            results = cursor.fetchall()
            return [self._format_location_row(row) for row in results]
        finally:
            cursor.close()
            self._put_conn(conn)

    def _build_location_query(self, location_type: Optional[str], filters: Optional[str]) -> str:
        """构建位置查询 SQL。"""
        base = """
            SELECT osm_id, name,
                   ST_X(ST_Transform(way, 4326)) as longitude,
                   ST_Y(ST_Transform(way, 4326)) as latitude,
                   amenity, tourism, shop, highway, place,
                   man_made, "tower:type" as tower_type,
                   leisure, "natural", ele
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

    def _format_location_row(self, row: tuple) -> Dict[str, object]:
        """将 SQL 查询行格式化为 Overpass 兼容 dict。"""
        elem: Dict[str, object] = {"type": "node", "id": row[0], "lat": row[3], "lon": row[2], "tags": {}}
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
            ("ele", 13),
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
        batch_size: int = 500,
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
        """单次查询批量海拔，planet_osm_point → planet_osm_line 自动回退。

        使用 COALESCE + 两个 LEFT JOIN LATERAL 在一次查询中完成两层检索：
        - planet_osm_point 命中 → 直接用点要素 elevation + feature_type
        - planet_osm_point 未命中 → 回退到 planet_osm_line
        - 都未命中 → elevation 为 NULL, feature_type='unknown'
        """
        if not coordinates:
            return []

        value_rows = []
        params: List[float] = []
        for i, (lat, lon) in enumerate(coordinates):
            value_rows.append(f"({i + 1}::int, %s::float, %s::float, %s::text)")
            params.extend([lat, lon, names[i]])

        values_clause = ", ".join(value_rows)

        sql = f"""
            SELECT
                t.id, t.lat, t.lon, t.name,
                COALESCE(p.ele::float, l.ele::float) as elevation,
                COALESCE(p.name, l.name) as source_name,
                CASE
                    WHEN p.way IS NOT NULL
                        THEN ST_Distance(ST_Transform(p.way, 4326)::geography,
                                        ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)::geography)
                    ELSE ST_Distance(ST_Transform(l.way, 4326)::geography,
                                    ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326)::geography)
                END as distance_meters,
                CASE
                    WHEN p.ele IS NOT NULL THEN
                        CASE
                            WHEN p.amenity  IS NOT NULL THEN 'amenity=' || p.amenity
                            WHEN p.tourism  IS NOT NULL THEN 'tourism=' || p.tourism
                            WHEN p."natural" IS NOT NULL THEN 'natural=' || p."natural"
                            WHEN p.man_made IS NOT NULL THEN 'man_made=' || p.man_made
                            ELSE 'point'
                        END
                    WHEN l.ele IS NOT NULL THEN
                        CASE
                            WHEN l.highway  IS NOT NULL THEN 'highway=' || l.highway
                            WHEN l.waterway IS NOT NULL THEN 'waterway=' || l.waterway
                            ELSE 'line'
                        END
                    ELSE 'unknown'
                END as feature_type
            FROM (VALUES {values_clause}) AS t(id, lat, lon, name)
            LEFT JOIN LATERAL (
                SELECT name, ele, way, amenity, tourism, "natural", man_made
                FROM planet_osm_point
                WHERE {self._ELE_FILTER}
                ORDER BY way <-> ST_Transform(ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326), 3857)
                LIMIT 1
            ) p ON true
            LEFT JOIN LATERAL (
                SELECT name, ele, way, highway, waterway
                FROM planet_osm_line
                WHERE {self._ELE_FILTER}
                ORDER BY way <-> ST_Transform(ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326), 3857)
                LIMIT 1
            ) l ON true
            ORDER BY t.id;
        """

        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)

            results: List[ElevationResult] = []
            found_point = 0
            found_line = 0
            _LINE_FTYPES = frozenset({"line"})

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
                if elev is not None:
                    ftype_s = ftype or ""
                    if ftype_s in _LINE_FTYPES or ftype_s.startswith(("highway=", "waterway=")):
                        found_line += 1
                    else:
                        found_point += 1

            logger.info(
                "Elevation batch query: %d points, %d from point, %d from line, %d missing",
                len(coordinates),
                found_point,
                found_line,
                len(coordinates) - found_point - found_line,
            )
            return results
        except (psycopg2.Error, DataError) as e:
            logger.error("PostGIS batch elevation query failed: %s", e)
            raise DataError(f"PostGIS batch elevation query failed: {e}") from e
        finally:
            cursor.close()
            self._put_conn(conn)

    # ── 单点高程查询 ──────────────────────────────────────────

    def find_elevation_at_point(self, lat: float, lon: float) -> Optional[float]:
        """
        查找单点附近最邻近 OSM 元素的海拔，单次查询自动回退。

        使用 COALESCE + 两个 LEFT JOIN LATERAL：
        planet_osm_point → planet_osm_line → NULL

        Returns:
            海拔（米），未找到则返回 None
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT COALESCE(p.ele::float, l.ele::float)
                FROM (SELECT 1) AS dummy
                LEFT JOIN LATERAL (
                    SELECT ele FROM planet_osm_point
                    WHERE {self._ELE_FILTER}
                    ORDER BY way <-> ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857)
                    LIMIT 1
                ) p ON true
                LEFT JOIN LATERAL (
                    SELECT ele FROM planet_osm_line
                    WHERE {self._ELE_FILTER}
                    ORDER BY way <-> ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), 3857)
                    LIMIT 1
                ) l ON true
                """,
                (lon, lat, lon, lat),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except (psycopg2.Error, DataError):
            return None
        finally:
            try:
                cursor.close()
            except (psycopg2.Error, AttributeError):
                pass
            self._put_conn(conn)

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
    ) -> Dict[str, object]:
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
        conn = self._get_conn()
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
            self._put_conn(conn)

    def _build_road_connectivity_result(self, row: Optional[tuple], radius_km: float) -> Dict[str, object]:
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

    # ── Road network graph queries (replaces OSMnx HTTP downloads) ─

    # Regex to extract coordinates from WKT LINESTRING strings.
    _WKT_COORD_RE = re.compile(r"[\d.-]+\s+[\d.-]+")

    def query_road_graph_by_bbox(
        self,
        south: float,
        west: float,
        north: float,
        east: float,
        network_type: str = "drive",
    ) -> Optional[nx.MultiDiGraph]:
        """
        Build a NetworkX MultiDiGraph from ``planet_osm_line`` within a bounding box.

        Replaces ``ox.graph_from_bbox`` HTTP download with a local PostGIS query.

        Args:
            south: Southern latitude (WGS84).
            west: Western longitude (WGS84).
            north: Northern latitude (WGS84).
            east: Eastern longitude (WGS84).
            network_type: Road network type ('drive', 'walk', 'bike', 'all').

        Returns:
            MultiDiGraph with x(lon)/y(lat) node attributes and highway/name edge
            attributes, or ``None`` if the query fails or returns no rows.
        """
        highway_filter = self._HIGHWAY_FILTERS.get(network_type, "highway IS NOT NULL")
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # Use ST_MakeEnvelope + && to leverage the GiST spatial index.
            # ST_MakeEnvelope(xmin, ymin, xmax, ymax, srid) = (west, south, east, north).
            cursor.execute(
                f"""
                SELECT highway, name, ST_AsText(ST_Transform(way, 4326)) AS geom_wkt
                FROM planet_osm_line
                WHERE {highway_filter}
                  AND ST_Transform(way, 4326) && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                """,
                (west, south, east, north),
            )
            rows = cursor.fetchall()
            if not rows:
                logger.info(
                    "No road segments found in bbox (%.4f, %.4f, %.4f, %.4f)",
                    south,
                    west,
                    north,
                    east,
                )
                return None
            logger.info(
                "Building road graph from %d LINESTRINGs for bbox (%.2f,%.2f)-(%.2f,%.2f)",
                len(rows),
                south,
                west,
                north,
                east,
            )
            return self._build_graph_from_rows(rows)
        except (psycopg2.Error, DataError) as e:
            logger.error("Road graph bbox query failed: %s", e)
            return None
        finally:
            cursor.close()
            self._put_conn(conn)

    def query_road_graph_by_point(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        network_type: str = "drive",
    ) -> Optional[nx.MultiDiGraph]:
        """
        Build a NetworkX MultiDiGraph from ``planet_osm_line`` around a point.

        Replaces ``ox.graph_from_point`` HTTP download with a local PostGIS query.

        Args:
            lat: Center latitude (WGS84).
            lon: Center longitude (WGS84).
            radius_km: Search radius in kilometers.
            network_type: Road network type ('drive', 'walk', 'bike', 'all').

        Returns:
            MultiDiGraph with x(lon)/y(lat) node attributes and highway/name edge
            attributes, or ``None`` if the query fails or returns no rows.
        """
        highway_filter = self._HIGHWAY_FILTERS.get(network_type, "highway IS NOT NULL")
        radius_meters = radius_km * 1000.0
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT highway, name, ST_AsText(ST_Transform(way, 4326)) AS geom_wkt
                FROM planet_osm_line
                WHERE {highway_filter}
                  AND ST_DWithin(
                      ST_Transform(way, 4326)::geography,
                      ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                      %s
                  )
                """,
                (lon, lat, radius_meters),
            )
            rows = cursor.fetchall()
            if not rows:
                logger.info(
                    "No road segments found within %.1f km of (%.4f, %.4f)",
                    radius_km,
                    lat,
                    lon,
                )
                return None
            logger.info(
                "Building road graph from %d LINESTRINGs within %.1f km of (%.4f, %.4f)",
                len(rows),
                radius_km,
                lat,
                lon,
            )
            return self._build_graph_from_rows(rows)
        except (psycopg2.Error, DataError) as e:
            logger.error("Road graph point query failed: %s", e)
            return None
        finally:
            cursor.close()
            self._put_conn(conn)

    @classmethod
    def _build_graph_from_rows(cls, rows: List[tuple]) -> nx.MultiDiGraph:
        """
        Build a NetworkX MultiDiGraph from PostGIS query rows.

        Each row is (highway, name, geom_wkt) where geom_wkt is a WGS84
        LINESTRING.  Nodes use auto-increment integer IDs for osmnx
        compatibility (tuple IDs would create a pandas MultiIndex that
        breaks ``graph_to_gdfs`` / ``nearest_nodes``).
        Node attributes: ``x`` (lon), ``y`` (lat).  Graph attribute: ``crs``.
        """
        G = nx.MultiDiGraph()
        G.graph["crs"] = "EPSG:4326"

        # Coordinate → integer node ID mapping for osmnx compatibility.
        coord_to_id: dict[tuple[float, float], int] = {}
        _next_id = 0

        def _get_node_id(lon: float, lat: float) -> int:
            nonlocal _next_id
            key = (round(lon, 7), round(lat, 7))
            if key not in coord_to_id:
                coord_to_id[key] = _next_id
                _next_id += 1
                G.add_node(coord_to_id[key], x=lon, y=lat)
            return coord_to_id[key]

        for highway, name, geom_wkt in rows:
            coords = cls._parse_linestring_wkt(geom_wkt)
            if len(coords) < 2:
                continue

            for i in range(len(coords) - 1):
                lon1, lat1 = coords[i]
                lon2, lat2 = coords[i + 1]

                nid1 = _get_node_id(lon1, lat1)
                nid2 = _get_node_id(lon2, lat2)

                edge_attrs = {"highway": highway}
                if name:
                    edge_attrs["name"] = name
                G.add_edge(nid1, nid2, **edge_attrs)
                G.add_edge(nid2, nid1, **edge_attrs)

        logger.info("Built NetworkX graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
        return G

    @classmethod
    def _parse_linestring_wkt(cls, wkt: str) -> List[Tuple[float, float]]:
        """
        Parse a WKT LINESTRING into a list of (lon, lat) coordinate pairs.

        Handles both LINESTRING and MULTILINESTRING formats.
        """
        if not wkt:
            return []

        # Handle MULTILINESTRING: extract its outer group then the *first*
        # inner LINESTRING so the regex only matches that one segment.
        wkt_upper = wkt.upper().strip()
        if wkt_upper.startswith("MULTILINESTRING"):
            # Find the outer matching pair of parentheses.
            depth = 0
            start = -1
            for i, ch in enumerate(wkt):
                if ch == "(":
                    if depth == 0:
                        start = i
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0 and start >= 0:
                        wkt = wkt[start + 1 : i]  # strip outer parens
                        break
            # Now extract the first inner LINESTRING group from the comma-
            # separated list, e.g. "(116 39,116.1 39.1),(117 40,117.1 40.1)"
            inner_depth = 0
            inner_start = -1
            for i, ch in enumerate(wkt):
                if ch == "(":
                    if inner_depth == 0:
                        inner_start = i
                    inner_depth += 1
                elif ch == ")":
                    inner_depth -= 1
                    if inner_depth == 0 and inner_start >= 0:
                        wkt = wkt[inner_start : i + 1]
                        break

        # Strip LINESTRING prefix and outer parentheses.
        if wkt_upper.startswith("LINESTRING"):
            wkt = wkt[len("LINESTRING") :]
        wkt = wkt.strip().strip("()")

        points = []
        for match in cls._WKT_COORD_RE.finditer(wkt):
            parts = match.group().split()
            if len(parts) >= 2:
                points.append((float(parts[0]), float(parts[1])))

        return points

    # ── 统计信息 ──────────────────────────────────────────────

    def get_elevation_statistics(self) -> Dict[str, object]:
        """返回 OSM 中海拔数据的统计信息。"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
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
        except (psycopg2.Error, DataError) as e:
            logger.error("Elevation stats query failed: %s", e)
            return {"error": str(e)}
        finally:
            try:
                cursor.close()
            except (psycopg2.Error, AttributeError):
                pass
            self._put_conn(conn)
