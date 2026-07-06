#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Road connectivity detection module
Used to detect whether specified coordinate points can be reached by road
"""

import hashlib
import logging
import os
import pickle
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

import networkx as nx
import osmnx as ox
import requests
from geopy.distance import geodesic

from cache.cache_config import get_cache_dir, setup_osmnx_cache
from config import StargazingConfig
from models import DataError, GeoPoint, NetworkError, NoDataError, RoadAccessInfo

from .geo_fence import GeoFence

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RoadAccessInfoCache:
    """
    Cache for road access info query results.
    Uses disk-based pickle cache, standalone replacement for LocationCache.
    """

    def __init__(self, cache_expiry_hours: int = 24):
        self.cache_dir = Path(get_cache_dir("default")) / "location_results"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.expiry_hours = cache_expiry_hours * 3600
        self.cache_mem_data = {}
        self._lock = threading.Lock()

    def _generate_cache_key(self, location_type: str) -> str:
        return hashlib.md5(location_type.encode("utf-8")).hexdigest()

    def _get_cache_file_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.pkl"

    def _is_cache_valid(self, cache_file: Path) -> bool:
        if not cache_file.exists():
            return False
        file_mtime = cache_file.stat().st_mtime
        return (time.time() - file_mtime) < self.expiry_hours

    def save_road_access_info_to_cache(self, location_type: str, data: List[RoadAccessInfo]):
        """
        Save query results to cache (thread-safe, atomic write).

        Args:
            location_type: Location type
            data: Query result data
        """
        cache_key = self._generate_cache_key(location_type)
        cache_file = self._get_cache_file_path(cache_key)

        with self._lock:
            cached_data = self.get_cached_result(location_type)
            if cached_data is None or not isinstance(cached_data, list):
                cached_data = data
            else:
                for item in data:
                    if item not in cached_data:
                        cached_data.append(item)
            self.cache_mem_data[location_type] = cached_data

        try:
            Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: temp file + rename to avoid TOCTOU corruption
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pkl", prefix=".tmp-", dir=str(Path(cache_file).parent))
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    pickle.dump(cached_data, f)
                os.replace(tmp_path, cache_file)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            logger.info(f"💾 Query results cached: {len(data)} records")
        except DataError as e:
            logger.error(f"⚠️ Failed to save cache: {e}")

    def get_cached_result(self, location_type: str) -> Optional[List[RoadAccessInfo]]:
        """
        Get query results from cache

        Args:
            location_type: Location type

        Returns:
            Cached query results, returns None if no valid cache
        """
        if location_type in self.cache_mem_data:
            return self.cache_mem_data[location_type]

        cache_key = self._generate_cache_key(location_type)
        cache_file = self._get_cache_file_path(cache_key)

        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    cached_data = pickle.load(f)
                    logger.info(f"✅ Data loaded from cache: {len(cached_data)} records")
                    return cached_data
            except (DataError, pickle.PickleError) as e:
                logger.error(f"⚠️ Failed to read cache file: {e}")
                # Delete corrupted cache file
                try:
                    cache_file.unlink()
                except (OSError, PermissionError) as e:
                    logger.warning("Failed to delete corrupted cache file %s: %s", cache_file, e)

        return None

    def get_location_by_coordinates(
        self, cache_data: List[RoadAccessInfo], latitude: float, longitude: float, tolerance: float = 0.001
    ) -> Optional[RoadAccessInfo]:
        """
        Find specific location from cache based on location type and coordinates

        Args:
            cache_data: Cached data
            latitude: Latitude
            longitude: Longitude
            tolerance: Coordinate matching tolerance, default 0.001 degrees (about 100 meters)

        Returns:
            Matched location object, returns None if not found
        """
        if cache_data is None:
            return None
        for location in cache_data:
            if abs(location.lat - latitude) <= tolerance and abs(location.lon - longitude) <= tolerance:
                return location
        return None


class RoadConnectivityChecker:
    """
    Road connectivity checker
    Used to detect whether specified coordinates have road network connections
    """

    def __init__(
        self,
        search_radius_km: float = 10.0,
        max_distance_to_road_km: float = 0.2,
        gis_service=None,
        config: Optional[StargazingConfig] = None,
        geo_fence: Optional[GeoFence] = None,
    ):
        """
        Initialize road connectivity checker

        Args:
            search_radius_km: Search radius (kilometers), default 10 kilometers
            max_distance_to_road_km: Maximum acceptable distance to road (kilometers),
                                      default 0.2 km (200m) — assumes user parks and walks
            gis_service: GisQueryService instance for PostGIS-accelerated queries.
                         When provided and PostGIS is enabled, road connectivity
                         queries use millisecond-level kNN SQL instead of OSMnx HTTP.
            config: Optional StargazingConfig instance. When provided, overrides
                    search_radius_km and max_distance_to_road_km with config values.
            geo_fence: Optional GeoFence instance for testing. When provided and
                       enabled, returns pre-defined results without real backend queries.
        """
        if config is not None:
            search_radius_km = config.road_search_radius_km
            max_distance_to_road_km = config.max_distance_to_road_km
            self._tile_max_area_km2 = config.road_network_tile_max_area_km2
        else:
            self._tile_max_area_km2 = StargazingConfig.model_fields["road_network_tile_max_area_km2"].default
        self.search_radius_km = search_radius_km
        self.max_distance_to_road_km = max_distance_to_road_km
        self.graph_cache = {}  # Cache downloaded road networks
        self._shared_graph = None  # Pre-loaded graph for batch checking (set via preload_network_for_bbox)
        self._graph_lock = threading.Lock()  # Protects concurrent access to _shared_graph
        self.gis_service = gis_service  # Optional GisQueryService for PostGIS fast path
        self.geo_fence = geo_fence  # 仅当上游显式传入时才使用
        # Set OSMnx cache directory
        setup_osmnx_cache()

        # Set road network cache directory
        self._road_cache_dir = get_cache_dir("road_networks")
        self.location_cache = RoadAccessInfoCache()

    def is_road_accessible(self, point: GeoPoint, network_type: str = "drive") -> bool:
        """
        Detect whether specified coordinates can be reached by road

        Args:
            point: Geographic coordinate.
            network_type: Network type ('drive', 'walk', 'bike', 'all')

        Returns:
            bool: True means accessible, False means inaccessible
        """
        lat, lon = point.lat, point.lon

        def process_and_return(res):
            # No longer use Location object to save road connectivity info, as RoadAccessInfo is more suitable
            road_info = RoadAccessInfo(lat=lat, lon=lon, is_road_accessible=res)
            self.location_cache.save_road_access_info_to_cache(f"accessible_{network_type}", [road_info])
            return res

        if self.geo_fence is not None:
            fence_result = self.geo_fence.check_road_accessible(lat, lon)
            if fence_result is not None:
                return process_and_return(fence_result)
        try:
            # Try to get road network around this point
            cached_results = self.location_cache.get_cached_result(f"accessible_{network_type}")
            if cached_results is not None:
                logger.info("Read road accessible from cache")
                cache = self.location_cache.get_location_by_coordinates(cached_results, lat, lon)
                if cache is not None:
                    return cache.is_road_accessible

            logger.info("Not found in cache, try PostGIS fast path")
            postgis_result = self._check_via_postgis(point, network_type)
            if postgis_result is not None:
                return postgis_result["accessible"]

            logger.info("PostGIS not available or no result, try OSMnx download")
            graph = self._get_road_network(point, network_type)

            if graph is None or len(graph.nodes()) == 0:
                logger.warning(f"No road network found around coordinates ({lat}, {lon})")
                return process_and_return(False)

            # Find nearest road node
            nearest_node = ox.distance.nearest_nodes(graph, lon, lat)

            if nearest_node is None:
                logger.warning(f"No road nodes found near coordinates ({lat}, {lon})")
                return process_and_return(False)

            # Check distance to nearest node
            node_data = graph.nodes[nearest_node]
            node_lat, node_lon = node_data["y"], node_data["x"]
            distance_km = geodesic((lat, lon), (node_lat, node_lon)).kilometers

            # If nearest road node is too far, consider inaccessible
            max_distance_km = self.max_distance_to_road_km  # Default 0.2 km (park + walk)
            if distance_km > max_distance_km:
                logger.info(
                    f"Coordinates ({lat}, {lon}) distance to nearest road {distance_km:.2f}km, exceeds threshold {max_distance_km}km"
                )
                return process_and_return(False)

            logger.info(f"Coordinates ({lat}, {lon}) accessible, distance to nearest road {distance_km:.2f}km")
            return process_and_return(True)

        except (NetworkError, NoDataError, requests.exceptions.RequestException) as e:
            logger.error(f"Error detecting accessibility for coordinates ({lat}, {lon}): {str(e)}")
            return False

    def _check_via_postgis(self, point: GeoPoint, network_type: str = "drive") -> Optional[dict]:
        """
        通过 PostGIS kNN 查询检查道路连通性（毫秒级）。

        Returns:
            包含 accessible/distance_meters/road_type 的 dict 如果查询成功，
            None 如果 PostGIS 不可用或需要回退
        """
        if self.gis_service is None:
            return None
        if not getattr(self.gis_service, "postgis_enabled", False):
            return None

        lat, lon = point.lat, point.lon
        result = self.gis_service.query_road_connectivity(lat, lon, self.search_radius_km, network_type)
        if result.get("fallback_needed"):
            return None

        accessible = result["accessible"]
        road_info = RoadAccessInfo(
            lat=lat,
            lon=lon,
            is_road_accessible=accessible,
            distance_to_road_km=(result["distance_meters"] / 1000.0 if result["distance_meters"] is not None else None),
            nearest_road_type=result.get("road_type"),
        )
        self.location_cache.save_road_access_info_to_cache(f"accessible_{network_type}", [road_info])
        return {
            "accessible": accessible,
            "distance_meters": result.get("distance_meters"),
            "road_type": result.get("road_type"),
        }

    @staticmethod
    def _bbox_area_km2(south: float, west: float, north: float, east: float) -> float:
        """Approximate area of a lat/lon bounding box in km²."""
        import math

        mid_lat = (south + north) / 2.0
        lat_km = (north - south) * 111.32
        lon_km = (east - west) * 111.32 * math.cos(math.radians(mid_lat))
        return lat_km * lon_km

    @staticmethod
    def _split_bbox(
        south: float, west: float, north: float, east: float, max_area_km2: float
    ) -> list[tuple[float, float, float, float]]:
        """Split a bounding box into equal-area tiles ≤ *max_area_km2* each."""
        import math

        area = RoadConnectivityChecker._bbox_area_km2(south, west, north, east)
        if area <= max_area_km2:
            return [(south, west, north, east)]

        # How many tiles along each axis?
        n_total = math.ceil(area / max_area_km2)
        # Prefer splitting along the longer side
        lat_range = north - south
        lon_range = east - west
        aspect = lat_range / max(lon_range, 1e-9)
        n_lat = max(1, round(math.sqrt(n_total * aspect)))
        n_lon = max(1, math.ceil(n_total / n_lat))

        step_lat = lat_range / n_lat
        step_lon = lon_range / n_lon

        tiles = []
        for i in range(n_lat):
            s = south + i * step_lat
            n = s + step_lat
            for j in range(n_lon):
                w = west + j * step_lon
                e = w + step_lon
                tiles.append((s, w, n, e))
        return tiles

    def _download_tile(self, bbox_tuple, network_type: str):
        """Download a single tile and return the graph (or None on failure)."""
        south, west, north, east = bbox_tuple
        try:
            return ox.graph_from_bbox(
                bbox=(west, south, east, north),
                network_type=network_type,
                simplify=True,
            )
        except Exception as e:
            logger.warning(
                "Failed to download tile (%.2f,%.2f)-(%.2f,%.2f): %s",
                south,
                west,
                north,
                east,
                e,
            )
            return None

    def preload_network_for_bbox(
        self,
        bbox,
        network_type: str = "drive",
    ) -> None:
        """
        Pre-download road network for the entire bounding box.

        When PostGIS is available, queries ``planet_osm_line`` directly
        (millisecond-level, no network I/O).  Otherwise falls back to OSMnx:
        for areas ≤ 500 km² a single OSM query is used; larger areas are
        automatically split into tiles (each ≤ 500 km²), downloaded
        individually, and merged via :func:`networkx.compose_all`.

        All subsequent ``_get_road_network`` calls reuse the merged graph.
        """
        if isinstance(bbox, (tuple, list)):
            south, west, north, east = bbox
        else:
            south, west, north, east = bbox.south, bbox.west, bbox.north, bbox.east

        # ── PostGIS fast path ──────────────────────────────────────
        if self.gis_service is not None and getattr(self.gis_service, "postgis_enabled", False):
            area_km2 = self._bbox_area_km2(south, west, north, east)
            logger.info(
                "Pre-loading road network via PostGIS for bbox (%.4f, %.4f, %.4f, %.4f) — %.0f km²",
                south,
                west,
                north,
                east,
                area_km2,
            )
            graph = self.gis_service.query_road_graph_by_bbox(south, west, north, east, network_type)
            if graph is not None and len(graph.nodes()) > 0:
                with self._graph_lock:
                    self._shared_graph = graph
                logger.info(
                    "Pre-loaded PostGIS road graph: %d nodes, %d edges",
                    graph.number_of_nodes(),
                    graph.number_of_edges(),
                )
                return
            logger.warning("PostGIS road graph query returned empty — falling back to OSMnx")

        # ── OSMnx fallback ─────────────────────────────────────────
        area_km2 = self._bbox_area_km2(south, west, north, east)
        tiles = self._split_bbox(south, west, north, east, self._tile_max_area_km2)

        if len(tiles) == 1:
            logger.info(
                "Pre-loading road network for bbox (%.4f, %.4f, %.4f, %.4f) — %.0f km²",
                south,
                west,
                north,
                east,
                area_km2,
            )
        else:
            logger.info(
                "Pre-loading road network for bbox (%.4f, %.4f, %.4f, %.4f) — %.0f km², %d tiles",
                south,
                west,
                north,
                east,
                area_km2,
                len(tiles),
            )

        graphs = []
        with ThreadPoolExecutor(max_workers=min(len(tiles), 8)) as executor:
            futures = {executor.submit(self._download_tile, tile, network_type): tile for tile in tiles}
            for future in as_completed(futures):
                g = future.result()
                if g is not None:
                    graphs.append(g)

        if not graphs:
            logger.error("Failed to download any road network tiles")
            with self._graph_lock:
                self._shared_graph = None
            return

        if len(graphs) == 1:
            with self._graph_lock:
                self._shared_graph = graphs[0]
        else:
            logger.info("Merging %d road network tiles…", len(graphs))
            merged = nx.compose_all(graphs)
            with self._graph_lock:
                self._shared_graph = merged

        logger.info("Pre-loaded road network with %d nodes", len(self._shared_graph.nodes()))

    def _get_road_network(self, point: GeoPoint, network_type: str) -> Optional[nx.MultiDiGraph]:
        """
        Get road network around specified coordinates.
        If a shared graph was pre-loaded via preload_network_for_bbox, uses that
        instead of downloading a per-location graph.

        Priority: shared graph → PostGIS query → in-memory cache → OSMnx download.

        Args:
            point: Geographic coordinate.
            network_type: Network type

        Returns:
            Road network graph, returns None if failed to get
        """
        # Use the pre-loaded shared graph if available (much faster — 1 download vs N)
        with self._graph_lock:
            shared = self._shared_graph
        if shared is not None:
            return shared

        lat, lon = point.lat, point.lon
        cache_key = f"{lat:.4f}_{lon:.4f}_{network_type}_{self.search_radius_km}"

        # Check cache
        if cache_key in self.graph_cache:
            logger.debug(f"Using cached road network: {cache_key}")
            return self.graph_cache[cache_key]

        # Try PostGIS graph query first (avoids OSMnx HTTP download)
        if self.gis_service is not None and getattr(self.gis_service, "postgis_enabled", False):
            graph = self.gis_service.query_road_graph_by_point(lat, lon, self.search_radius_km, network_type)
            if graph is not None and len(graph.nodes()) > 0:
                self.graph_cache[cache_key] = graph
                logger.info("Road network built from PostGIS: %d nodes", len(graph.nodes()))
                return graph

        try:
            logger.info(f"Downloading road network around coordinates ({lat}, {lon}) within {self.search_radius_km}km")

            # Download road network
            graph = ox.graph_from_point(
                (lat, lon),
                dist=self.search_radius_km * 1000,  # Convert to meters
                network_type=network_type,
                simplify=True,
            )

            # Cache results
            self.graph_cache[cache_key] = graph
            logger.info(f"Successfully downloaded road network with {len(graph.nodes())} nodes")

            return graph

        except (NetworkError, requests.exceptions.RequestException) as e:
            logger.error(f"Failed to download road network: {str(e)}")
            return None

    def batch_check_accessibility(self, coordinates: List[GeoPoint], network_type: str = "drive") -> list:
        """
        Batch check road accessibility for multiple coordinates

        Args:
            coordinates: List of GeoPoint objects.
            network_type: Network type

        Returns:
            list: List of accessibility results corresponding to input coordinates order
        """
        results = []

        for i, point in enumerate(coordinates):
            lat, lon = point.lat, point.lon
            logger.info(f"Checking coordinate {i + 1}/{len(coordinates)}: ({lat}, {lon})")
            accessible = self.is_road_accessible(point, network_type)
            results.append(accessible)

        accessible_count = sum(results)
        logger.info(f"Batch detection completed: {accessible_count}/{len(coordinates)} coordinates accessible")

        return results

    def get_accessibility_info(self, point: GeoPoint, network_type: str = "drive") -> dict:
        """
        Get detailed accessibility information.

        Delegates to: geo_fence → cache → PostGIS → OSMnx fallback.

        Args:
            point: Geographic coordinate.
            network_type: Network type

        Returns:
            dict: Dictionary containing accessibility and detailed information
        """
        lat, lon = point.lat, point.lon
        result = {
            "accessible": False,
            "distance_to_road_km": None,
            "nearest_road_type": None,
            "network_nodes_count": 0,
            "error": None,
        }

        try:
            if self._try_geo_fence_info(result, lat, lon, network_type):
                return result

            if self._try_cache_info(result, lat, lon, network_type):
                return result

            if self._try_postgis_info(result, point, network_type):
                return result

            self._try_osmnx_info(result, point, lat, lon, network_type)
        except (DataError, NoDataError) as e:
            result["error"] = str(e)

        return result

    def _try_geo_fence_info(self, result: dict, lat: float, lon: float, network_type: str) -> bool:
        """GeoFence 围栏拦截（测试用）。返回 True 表示已命中围栏结果。"""
        if self.geo_fence is None:
            return False
        fence_result = self.geo_fence.get_fake_accessibility_info(lat, lon)
        if fence_result is None:
            return False
        result.update(fence_result)
        self._save_accessibility_cache(result, lat, lon, network_type)
        return True

    def _try_cache_info(self, result: dict, lat: float, lon: float, network_type: str) -> bool:
        """从缓存读取。返回 True 表示命中缓存。"""
        cached_res = self.location_cache.get_cached_result(f"access_info_{network_type}")
        cache = self.location_cache.get_location_by_coordinates(cached_res, lat, lon)
        if cache is None:
            logger.info("No road accessible info in cache")
            return False
        result["accessible"] = cache.is_road_accessible
        result["distance_to_road_km"] = cache.distance_to_road_km
        result["nearest_road_type"] = cache.nearest_road_type
        result["network_nodes_count"] = cache.network_nodes_count
        result["error"] = cache.error
        logger.info("Read road accessible info from cache")
        return True

    def _try_postgis_info(self, result: dict, point: GeoPoint, network_type: str) -> bool:
        """PostGIS kNN 快速路径。返回 True 表示成功获取结果。"""
        postgis_result = self._check_via_postgis(point, network_type)
        if postgis_result is None:
            return False
        result["accessible"] = postgis_result["accessible"]
        result["distance_to_road_km"] = (
            postgis_result["distance_meters"] / 1000.0 if postgis_result["distance_meters"] is not None else None
        )
        result["nearest_road_type"] = postgis_result.get("road_type")
        result["error"] = None
        return True

    def _try_osmnx_info(self, result: dict, point: GeoPoint, lat: float, lon: float, network_type: str) -> None:
        """OSMnx 回退路径：下载路网图并查询最近道路节点。"""
        graph = self._get_road_network(point, network_type)
        if graph is None or len(graph.nodes()) == 0:
            result["error"] = "Unable to get road network data"
            return

        result["network_nodes_count"] = len(graph.nodes())
        nearest_node = ox.distance.nearest_nodes(graph, lon, lat)

        if nearest_node is not None:
            node_data = graph.nodes[nearest_node]
            node_lat, node_lon = node_data["y"], node_data["x"]
            distance_km = geodesic((lat, lon), (node_lat, node_lon)).kilometers
            result["distance_to_road_km"] = distance_km
            result["accessible"] = distance_km <= self.max_distance_to_road_km

            edges = graph.edges(nearest_node, data=True)
            if edges:
                edge_data = list(edges)[0][2]
                result["nearest_road_type"] = edge_data.get("highway", "unknown")
                result["error"] = None

        self._save_accessibility_cache(result, lat, lon, network_type)

    def _save_accessibility_cache(self, result: dict, lat: float, lon: float, network_type: str) -> None:
        """将可达性结果写入缓存。"""
        cache = RoadAccessInfo(
            is_road_accessible=result["accessible"],
            distance_to_road_km=result["distance_to_road_km"],
            nearest_road_type=result["nearest_road_type"],
            network_nodes_count=result["network_nodes_count"],
            error=result["error"],
            lat=lat,
            lon=lon,
        )
        self.location_cache.save_road_access_info_to_cache(f"access_info_{network_type}", [cache])


def simple_road_check(point: GeoPoint) -> bool:
    """
    Simple road connectivity detection function

    .. deprecated::
        请直接使用 ``RoadConnectivityChecker``。

    Args:
        point: Geographic coordinate.

    Returns:
        bool: True means accessible, False means inaccessible
    """
    import warnings

    warnings.warn(
        "simple_road_check is deprecated, use RoadConnectivityChecker directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    checker = RoadConnectivityChecker(search_radius_km=5.0)
    return checker.is_road_accessible(point)
