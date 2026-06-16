# -*- coding: utf-8 -*-
"""
统一高程查询后端，内置 fallback 链：

    OSM tags → PostGIS → Open-Elevation API → 0.0

将 stargazing_place_finder.py 中散落的高程查询逻辑集中于此。
"""

import logging
import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import requests

from models import DataError, NetworkError

if TYPE_CHECKING:
    from gis_service.backends.postgis_backend import PostgisBackend

logger = logging.getLogger(__name__)


class ElevationBackend:
    """
    高程查询器。

    支持从 OSM tags、PostGIS、HTTP API 等多级来源获取海拔，自动 fallback。
    """

    def __init__(self, postgis_backend: Optional["PostgisBackend"] = None):
        """
        Args:
            postgis_backend: PostgisBackend 实例（可选），用于 PostGIS 高程回退查询。
        """
        self._postgis = postgis_backend

    # ── 单点高程（完整 fallback 链）────────────────────────────

    def find_elevation(
        self,
        lat: float,
        lon: float,
        osm_tags: Optional[Dict[str, str]] = None,
    ) -> float:
        """
        查找坐标海拔，带完整 fallback 链。

        Fallback 顺序：
            1. OSM tags（如 tags['ele']）
            2. PostGIS 最近邻查询
            3. Open-Elevation HTTP API
            4. 0.0（默认值）

        Args:
            lat: 纬度
            lon: 经度
            osm_tags: 可选 OSM tags dict，从中读取 'ele'

        Returns:
            海拔（米），始终返回 float
        """
        # Level 1: OSM tags
        if osm_tags and "ele" in osm_tags:
            try:
                val = float(osm_tags["ele"])
                if val is not None:
                    return val
            except (ValueError, TypeError) as e:
                logger.debug("Failed to parse elevation from OSM tags: %s", e)

        # Level 2: PostGIS
        if self._postgis:
            try:
                val = self._postgis.find_elevation_at_point(lat, lon)
                if val is not None:
                    return val
            except DataError as e:
                logger.debug("PostGIS elevation query failed: %s", e)

        # Level 3: HTTP API
        try:
            val = self._query_open_elevation(lat, lon)
            if val is not None:
                return val
        except Exception as e:
            logger.debug("Open-Elevation API failed: %s", e)

        # Level 4: default
        return 0.0

    # ── 批量高程 ──────────────────────────────────────────────

    def batch_find_elevations(
        self,
        coordinates: List[Tuple[float, float]],
        osm_tags_list: Optional[List[Optional[Dict[str, str]]]] = None,
    ) -> List[float]:
        """
        批量查找海拔。优先使用 PostGIS 批量查询，再对未找到的逐个 fallback。

        Args:
            coordinates: [(lat, lon), ...]
            osm_tags_list: 每个坐标对应的 OSM tags（可选）

        Returns:
            海拔列表，保证与 coordinates 等长
        """
        n = len(coordinates)
        results: List[Optional[float]] = [None] * n

        # Phase 1: OSM tags
        if osm_tags_list:
            for i, tags in enumerate(osm_tags_list):
                if tags and "ele" in tags:
                    try:
                        results[i] = float(tags["ele"])
                    except (ValueError, TypeError) as e:
                        logger.debug("Failed to parse elevation from OSM tags (batch): %s", e)

        # Phase 2: PostGIS 批量查询
        remaining = [i for i in range(n) if results[i] is None]
        if remaining and self._postgis:
            try:
                batch_coords = [coordinates[i] for i in remaining]
                batch_names = [f"pt_{i}" for i in remaining]
                elev_data = self._postgis.batch_query_elevations(batch_coords, batch_names)
                for idx, data in zip(remaining, elev_data):
                    if data.elevation is not None:
                        results[idx] = data.elevation
            except DataError as e:
                logger.debug("PostGIS batch elevation failed: %s", e)

        # Phase 3: Open-Elevation API（仅对仍未找到的）
        remaining = [i for i in range(n) if results[i] is None]
        for i in remaining:
            try:
                val = self._query_open_elevation(coordinates[i][0], coordinates[i][1])
                if val is not None:
                    results[i] = val
                    time.sleep(0.1)
            except (NetworkError, DataError) as e:
                logger.debug("Open-Elevation API failed for batch item: %s", e)

        # Phase 4: 剩余默认 0.0
        return [r if r is not None else 0.0 for r in results]

    # ── Open-Elevation API 调用 ──────────────────────────────

    @staticmethod
    def _query_open_elevation(lat: float, lon: float) -> Optional[float]:
        """调用 Open-Elevation API 查询海拔。"""
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            return data["results"][0].get("elevation")
        return None
