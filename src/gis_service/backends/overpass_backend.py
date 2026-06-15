# -*- coding: utf-8 -*-
"""
Overpass API 查询后端封装。

将 stargazing_place_finder.py 中的 Overpass 查询逻辑迁移至此。
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from models import NetworkError

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_TIMEOUT = 45
DEFAULT_MAX_RETRIES = 3


class OverpassBackend:
    """
    Overpass API 后端。

    提供与 PostgisBackend.query_locations_in_bbox 兼容的接口，
    返回格式相同的 dict 列表。
    """

    def __init__(
        self,
        url: str = OVERPASS_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.url = url
        self.timeout = timeout
        self.max_retries = max_retries

    # ── 公开查询方法 ──────────────────────────────────────────

    def query_locations_in_bbox(
        self,
        lon_min: float,
        lat_min: float,
        lon_max: float,
        lat_max: float,
        location_type: str,
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        在 bounding box 内查询 OSM 位置。

        Args 与返回格式兼容 PostgisBackend。
        """
        _ = filters  # Overpass 不使用额外 SQL 条件
        bbox = (lat_min, lon_min, lat_max, lon_max)

        method_map = {
            "peak": self._query_peaks,
            "town": self._query_towns,
            "observatory": self._query_observatories,
            "viewpoint": self._query_viewpoints,
            "mountain_peak": self._query_peaks,
        }
        query_fn = method_map.get(location_type)
        if query_fn is None:
            raise ValueError(f"Unsupported location type: {location_type}")

        return query_fn(bbox)

    # ── Overpass QL 查询构造 ──────────────────────────────────

    def _query_peaks(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        q = (
            "[out:json][timeout:25];\n"
            f'(node["natural"="peak"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' node["natural"="volcano"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}););\n'
            "out geom;"
        )
        return self._request(q, "peaks")

    def _query_towns(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        q = (
            "[out:json][timeout:25];\n"
            f'(node["place"~"^(city|town|village|hamlet)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["place"~"^(city|town|village|hamlet)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' relation["place"~"^(city|town|village|hamlet)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}););\n'
            "out center geom;"
        )
        return self._request(q, "towns")

    def _query_observatories(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        q = (
            "[out:json][timeout:25];\n"
            f'(node["man_made"="observatory"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["man_made"="observatory"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' relation["man_made"="observatory"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' node["amenity"="planetarium"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["amenity"="planetarium"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' node["building"="observatory"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["building"="observatory"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}););\n'
            "out center geom;"
        )
        return self._request(q, "observatories")

    def _query_viewpoints(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        q = (
            "[out:json][timeout:25];\n"
            f'(node["tourism"="viewpoint"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["tourism"="viewpoint"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' relation["tourism"="viewpoint"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' node["man_made"="tower"]["tower:type"="observation"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["man_made"="tower"]["tower:type"="observation"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' node["amenity"="observation_deck"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["amenity"="observation_deck"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' node["leisure"="viewing_platform"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["leisure"="viewing_platform"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}););\n'
            "out center geom;"
        )
        return self._request(q, "viewpoints")

    # ── 请求执行 ──────────────────────────────────────────────

    def _request(self, query: str, data_type: str) -> List[Dict[str, Any]]:
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    delay = random.uniform(1, 3) * (attempt + 1)
                    logger.info("Overpass retry %d/%d, waiting %.1fs", attempt + 1, self.max_retries, delay)
                    time.sleep(delay)

                logger.info("Querying Overpass for %s ...", data_type)
                resp = requests.post(self.url, data=query, timeout=self.timeout)
                resp.raise_for_status()
                elements = resp.json().get("elements", [])
                logger.info("Overpass %s: found %d", data_type, len(elements))
                return elements

            except requests.exceptions.Timeout:
                logger.warning("Overpass timeout (%s, attempt %d/%d)", data_type, attempt + 1, self.max_retries)
            except requests.exceptions.HTTPError as e:
                logger.warning("Overpass HTTP %s (%s, attempt %d/%d)", e, data_type, attempt + 1, self.max_retries)
            except NetworkError as e:
                logger.warning("Overpass error (%s, attempt %d/%d): %s", data_type, attempt + 1, self.max_retries, e)

        logger.error("Overpass query failed for %s after %d attempts", data_type, self.max_retries)
        return []
