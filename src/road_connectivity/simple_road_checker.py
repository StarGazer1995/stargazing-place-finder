#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Road Connectivity Checker

.. deprecated::
    此模块已弃用。请使用 :class:`road_connectivity.RoadConnectivityChecker`。
    ``SimpleRoadChecker`` 保留仅为向后兼容，内部委托给 ``RoadConnectivityChecker``。
"""

import logging
import warnings
from typing import List, Optional, Tuple

from config import StargazingConfig
from models import GeoCoordinate

from .geo_fence import GeoFence
from .road_connectivity_checker import RoadConnectivityChecker

logger = logging.getLogger(__name__)


class SimpleRoadChecker:
    """
    Simplified Road Connectivity Checker

    .. deprecated::
        请改用 :class:`road_connectivity.road_connectivity_checker.RoadConnectivityChecker`。
        本类保留仅为向后兼容，内部委托给 ``RoadConnectivityChecker``。
    """

    def __init__(
        self,
        search_radius_km: float = 5.0,
        max_distance_to_road_km: float = 2.0,
        config: Optional[StargazingConfig] = None,
        geo_fence: Optional[GeoFence] = None,
    ):
        """
        Initialize road connectivity checker

        Args:
            search_radius_km: Search radius (kilometers)
            max_distance_to_road_km: Maximum acceptable distance to road (kilometers)
            config: Optional StargazingConfig instance. When provided, overrides
                    search_radius_km and max_distance_to_road_km with config values.
            geo_fence: Optional GeoFence instance for testing. When enabled, returns
                       pre-defined results without real backend queries.
        """
        warnings.warn(
            "SimpleRoadChecker is deprecated, use RoadConnectivityChecker instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if config is not None:
            search_radius_km = config.road_search_radius_km
            max_distance_to_road_km = config.max_distance_to_road_km
        self.search_radius_km = search_radius_km
        self.max_distance_to_road_km = max_distance_to_road_km
        self._inner = RoadConnectivityChecker(
            search_radius_km=search_radius_km,
            max_distance_to_road_km=max_distance_to_road_km,
            geo_fence=geo_fence,  # 可 None，RoadConnectivityChecker 内部不再 fallback
        )

    def is_connected(self, lat: float, lon: float) -> bool:
        """检查坐标是否有道路连通（已弃用，委托给 RoadConnectivityChecker）。"""
        point = GeoCoordinate(latitude=lat, longitude=lon)
        return self._inner.is_road_accessible(point)

    def batch_check(self, coordinates: List[Tuple[float, float]]) -> List[bool]:
        """批量检查道路连通性（已弃用，委托给 RoadConnectivityChecker）。"""
        points = [GeoCoordinate(latitude=lat, longitude=lon) for lat, lon in coordinates]
        return self._inner.batch_check_accessibility(points)


# Convenience functions
def quick_road_check(
    lat: float,
    lon: float,
    search_radius_km: float = 5.0,
    geo_fence: Optional[GeoFence] = None,
) -> bool:
    """
    Convenience function for quickly checking if specified coordinates have road connectivity

    .. deprecated::
        请直接使用 ``RoadConnectivityChecker``。

    Args:
        lat: Latitude
        lon: Longitude
        search_radius_km: Search radius (kilometers), default 5 kilometers
        geo_fence: Optional GeoFence instance for testing.

    Returns:
        bool: True indicates road connectivity, False indicates no road connectivity
    """
    warnings.warn(
        "quick_road_check is deprecated, use RoadConnectivityChecker instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    checker = SimpleRoadChecker(search_radius_km=search_radius_km, geo_fence=geo_fence)
    return checker.is_connected(lat, lon)


def batch_road_check(
    coordinates: List[Tuple[float, float]],
    search_radius_km: float = 5.0,
    geo_fence: Optional[GeoFence] = None,
) -> List[bool]:
    """
    Convenience function for batch checking road connectivity of multiple coordinates

    .. deprecated::
        请直接使用 ``RoadConnectivityChecker.batch_check_accessibility()``。

    Args:
        coordinates: List of coordinates in format [(lat1, lon1), (lat2, lon2), ...]
        search_radius_km: Search radius (kilometers), default 5 kilometers
        geo_fence: Optional GeoFence instance for testing.

    Returns:
        list: Corresponding connectivity result list [True, False, ...]
    """
    warnings.warn(
        "batch_road_check is deprecated, use RoadConnectivityChecker instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    checker = SimpleRoadChecker(search_radius_km=search_radius_km, geo_fence=geo_fence)
    return checker.batch_check(coordinates)


# Usage example
if __name__ == "__main__":
    # Test some coordinates
    test_locations = [
        (40.3242, 116.6312),  # Beijing Huairou
        (31.6270, 121.3975),  # Shanghai Chongming Island
        (30.0, 125.0),  # Some point at sea (should be unreachable)
    ]

    logger.info("🛣️  Simplified Road Connectivity Detection")
    logger.info("=" * 40)

    # Single detection example
    logger.info("\nSingle detection example:")
    lat, lon = 40.3242, 116.6312
    result = quick_road_check(lat, lon)
    logger.info(f"Coordinates ({lat}, {lon}): {'✅ Reachable' if result else '❌ Unreachable'}")

    # Batch detection example
    logger.info("\nBatch detection example:")
    results = batch_road_check(test_locations)

    for (lat, lon), connected in zip(test_locations, results):
        status = "✅ Reachable" if connected else "❌ Unreachable"
        logger.info(f"Coordinates ({lat}, {lon}): {status}")

    logger.info("\n✨ Detection completed!")
