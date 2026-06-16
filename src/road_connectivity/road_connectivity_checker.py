#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Road connectivity detection module
Used to detect whether specified coordinate points can be reached by road
"""

import hashlib
import logging
import pickle
import time
from pathlib import Path
from typing import List, Optional

import networkx as nx
import osmnx as ox
from geopy.distance import geodesic

from cache.cache_config import get_cache_dir, setup_osmnx_cache
from config import StargazingConfig
from models import DataError, GeoCoordinate, NetworkError, NoDataError, RoadAccessInfo

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
        Save query results to cache

        Args:
            location_type: Location type
            data: Query result data
        """
        cache_key = self._generate_cache_key(location_type)
        cache_file = self._get_cache_file_path(cache_key)
        cached_data = self.get_cached_result(location_type)
        if cached_data is None or not isinstance(cached_data, list):
            cached_data = data
        else:
            for item in data:
                if item not in cached_data:
                    cached_data.append(item)
        self.cache_mem_data[location_type] = cached_data
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(cached_data, f)
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
                except Exception:
                    pass

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
            if abs(location.latitude - latitude) <= tolerance and abs(location.longitude - longitude) <= tolerance:
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
        self.search_radius_km = search_radius_km
        self.max_distance_to_road_km = max_distance_to_road_km
        self.graph_cache = {}  # Cache downloaded road networks
        self.gis_service = gis_service  # Optional GisQueryService for PostGIS fast path
        self.geo_fence = geo_fence or GeoFence()
        # Set OSMnx cache directory
        setup_osmnx_cache()

        # Set road network cache directory
        self._road_cache_dir = get_cache_dir("road_networks")
        self.location_cache = RoadAccessInfoCache()

    def is_road_accessible(self, point: GeoCoordinate, network_type: str = "drive") -> bool:
        """
        Detect whether specified coordinates can be reached by road

        Args:
            point: Geographic coordinate.
            network_type: Network type ('drive', 'walk', 'bike', 'all')

        Returns:
            bool: True means accessible, False means inaccessible
        """
        lat, lon = point.latitude, point.longitude

        def process_and_return(res):
            # No longer use Location object to save road connectivity info, as RoadAccessInfo is more suitable
            road_info = RoadAccessInfo(latitude=lat, longitude=lon, is_road_accessible=res)
            self.location_cache.save_road_access_info_to_cache(f"accessible_{network_type}", [road_info])
            return res

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
                return postgis_result

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

        except (NetworkError, NoDataError) as e:
            logger.error(f"Error detecting accessibility for coordinates ({lat}, {lon}): {str(e)}")
            return False

    def _check_via_postgis(self, point: GeoCoordinate, network_type: str = "drive") -> Optional[bool]:
        """
        通过 PostGIS kNN 查询检查道路连通性（毫秒级）。

        Returns:
            True/False 如果查询成功，None 如果 PostGIS 不可用
        """
        if self.gis_service is None:
            return None
        if not getattr(self.gis_service, "postgis_enabled", False):
            return None

        lat, lon = point.latitude, point.longitude
        result = self.gis_service.query_road_connectivity(lat, lon, self.search_radius_km, network_type)
        if result.get("fallback_needed"):
            return None

        accessible = result["accessible"]
        road_info = RoadAccessInfo(
            latitude=lat,
            longitude=lon,
            is_road_accessible=accessible,
            distance_to_road_km=(result["distance_meters"] / 1000.0 if result["distance_meters"] is not None else None),
            nearest_road_type=result.get("road_type"),
        )
        self.location_cache.save_road_access_info_to_cache(f"accessible_{network_type}", [road_info])
        return accessible

    def _get_road_network(self, point: GeoCoordinate, network_type: str) -> Optional[nx.MultiDiGraph]:
        """
        Get road network around specified coordinates

        Args:
            point: Geographic coordinate.
            network_type: Network type

        Returns:
            Road network graph, returns None if failed to get
        """
        lat, lon = point.latitude, point.longitude
        cache_key = f"{lat:.4f}_{lon:.4f}_{network_type}_{self.search_radius_km}"

        # Check cache
        if cache_key in self.graph_cache:
            logger.debug(f"Using cached road network: {cache_key}")
            return self.graph_cache[cache_key]

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

        except NetworkError as e:
            logger.error(f"Failed to download road network: {str(e)}")
            return None

    def batch_check_accessibility(self, coordinates: List[GeoCoordinate], network_type: str = "drive") -> list:
        """
        Batch check road accessibility for multiple coordinates

        Args:
            coordinates: List of GeoCoordinate objects.
            network_type: Network type

        Returns:
            list: List of accessibility results corresponding to input coordinates order
        """
        results = []

        for i, point in enumerate(coordinates):
            lat, lon = point.latitude, point.longitude
            logger.info(f"Checking coordinate {i + 1}/{len(coordinates)}: ({lat}, {lon})")
            accessible = self.is_road_accessible(point, network_type)
            results.append(accessible)

        accessible_count = sum(results)
        logger.info(f"Batch detection completed: {accessible_count}/{len(coordinates)} coordinates accessible")

        return results

    def get_accessibility_info(self, point: GeoCoordinate, network_type: str = "drive") -> dict:
        """
        Get detailed accessibility information

        Args:
            point: Geographic coordinate.
            network_type: Network type

        Returns:
            dict: Dictionary containing accessibility and detailed information
        """
        lat, lon = point.latitude, point.longitude
        result = {
            "accessible": False,
            "distance_to_road_km": None,
            "nearest_road_type": None,
            "network_nodes_count": 0,
            "error": None,
        }

        try:
            fence_result = self.geo_fence.get_fake_accessibility_info(lat, lon)
            if fence_result is not None:
                result.update(fence_result)
                cache = RoadAccessInfo(
                    is_road_accessible=result["accessible"],
                    distance_to_road_km=result["distance_to_road_km"],
                    nearest_road_type=result["nearest_road_type"],
                    network_nodes_count=result["network_nodes_count"],
                    error=result["error"],
                    latitude=lat,
                    longitude=lon,
                )
                self.location_cache.save_road_access_info_to_cache(f"access_info_{network_type}", [cache])
                return result
            cached_res = self.location_cache.get_cached_result(f"access_info_{network_type}")
            cache = self.location_cache.get_location_by_coordinates(cached_res, lat, lon)
            if cache is not None:
                result["accessible"] = cache.is_road_accessible
                result["distance_to_road_km"] = cache.distance_to_road_km
                result["nearest_road_type"] = cache.nearest_road_type
                result["network_nodes_count"] = cache.network_nodes_count
                result["error"] = cache.error
                logger.info("Read road accessible info from cache")
                return result
            else:
                logger.info("No road accessible info in cache")

            # Try PostGIS fast path first
            postgis_result = self._check_via_postgis(point, network_type)
            if postgis_result is not None:
                result["accessible"] = postgis_result
                # Try to get more details from a separate query
                if self.gis_service and getattr(self.gis_service, "postgis_enabled", False):
                    details = self.gis_service.query_road_connectivity(lat, lon, self.search_radius_km, network_type)
                    if not details.get("fallback_needed"):
                        result["distance_to_road_km"] = (
                            details["distance_meters"] / 1000.0 if details["distance_meters"] is not None else None
                        )
                        result["nearest_road_type"] = details.get("road_type")
                        result["error"] = None
                return result

            graph = self._get_road_network(point, network_type)

            if graph is None or len(graph.nodes()) == 0:
                result["error"] = "Unable to get road network data"
                return result

            result["network_nodes_count"] = len(graph.nodes())

            # Find nearest road node
            nearest_node = ox.distance.nearest_nodes(graph, lon, lat)

            if nearest_node is not None:
                node_data = graph.nodes[nearest_node]
                node_lat, node_lon = node_data["y"], node_data["x"]
                distance_km = geodesic((lat, lon), (node_lat, node_lon)).kilometers

                result["distance_to_road_km"] = distance_km
                result["accessible"] = distance_km <= self.max_distance_to_road_km

                # Try to get road type information
                edges = graph.edges(nearest_node, data=True)
                if edges:
                    edge_data = list(edges)[0][2]
                    result["nearest_road_type"] = edge_data.get("highway", "unknown")
                    result["error"] = None

            cache = RoadAccessInfo(
                is_road_accessible=result["accessible"],
                distance_to_road_km=result["distance_to_road_km"],
                nearest_road_type=result["nearest_road_type"],
                network_nodes_count=result["network_nodes_count"],
                error=result["error"],
                latitude=lat,
                longitude=lon,
            )
            self.location_cache.save_road_access_info_to_cache(f"access_info_{network_type}", [cache])

        except (DataError, NoDataError) as e:
            result["error"] = str(e)

        return result


def simple_road_check(point: GeoCoordinate) -> bool:
    """
    Simple road connectivity detection function

    Args:
        point: Geographic coordinate.

    Returns:
        bool: True means accessible, False means inaccessible
    """
    checker = RoadConnectivityChecker(search_radius_km=5.0)
    return checker.is_road_accessible(point)


if __name__ == "__main__":
    # Example usage
    checker = RoadConnectivityChecker(search_radius_km=10.0)

    # Test some coordinates
    test_coordinates = [
        (39.9042, 116.4074),  # Beijing Tiananmen
        (31.2304, 121.4737),  # Shanghai Bund
        (90.0, 0.0),  # North Pole (should be inaccessible)
    ]

    for lat, lon in test_coordinates:
        point = GeoCoordinate(latitude=lat, longitude=lon)
        logger.info(f"Detecting coordinates ({lat}, {lon}):")
        info = checker.get_accessibility_info(point)
        logger.info(f"Accessibility: {info['accessible']}")
        if info["distance_to_road_km"] is not None:
            logger.info(f"Distance to nearest road: {info['distance_to_road_km']:.2f} km")
        if info["error"]:
            logger.info(f"Error: {info['error']}")
