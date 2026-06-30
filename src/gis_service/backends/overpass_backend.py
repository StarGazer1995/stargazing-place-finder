# -*- coding: utf-8 -*-
"""
Overpass API 查询后端封装。

将 stargazing_place_finder.py 中的 Overpass 查询逻辑迁移至此。
"""

import logging
import random
import time
from typing import Dict, List, Optional, Tuple

import requests

from models import NetworkError

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_FALLBACK_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
]
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 3
DEFAULT_TOTAL_TIMEOUT = 90  # wall-clock deadline for the entire _request method


class OverpassBackend:
    """
    Overpass API 后端。

    提供与 PostgisBackend.query_locations_in_bbox 兼容的接口，
    返回格式相同的 dict 列表。
    """

    def __init__(
        self,
        url: str = OVERPASS_URL,
        fallback_urls: Optional[List[str]] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        total_timeout: int | None = DEFAULT_TOTAL_TIMEOUT,
    ):
        self.urls = [url] + (fallback_urls or OVERPASS_FALLBACK_URLS)
        self.timeout = timeout
        self.max_retries = max_retries
        self.total_timeout = total_timeout

    # ── 公开查询方法 ──────────────────────────────────────────

    def query_locations_in_bbox(
        self,
        lon_min: float,
        lat_min: float,
        lon_max: float,
        lat_max: float,
        location_type: str,
        filters: Optional[str] = None,
    ) -> List[Dict[str, object]]:
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

    def _query_peaks(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, object]]:
        q = (
            "[out:json][timeout:25];\n"
            f'(node["natural"="peak"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' node["natural"="volcano"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}););\n'
            "out geom;"
        )
        return self._request(q, "peaks")

    def _query_towns(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, object]]:
        q = (
            "[out:json][timeout:25];\n"
            f'(node["place"~"^(city|town|village|hamlet)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' way["place"~"^(city|town|village|hamlet)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});\n'
            f' relation["place"~"^(city|town|village|hamlet)$"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}););\n'
            "out center geom;"
        )
        return self._request(q, "towns")

    def _query_observatories(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, object]]:
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

    def _query_viewpoints(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, object]]:
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

    def _request(self, query: str, data_type: str) -> List[Dict[str, object]]:
        """
        向 Overpass API 发送 POST 请求，多 URL 轮询 + 自动重试。

        先尝试主 URL（含重试），失败后逐个尝试备用 URL。
        受 total_timeout 约束，超时后直接放弃返回空列表。
        """
        started_at = time.time()

        for url_idx, url in enumerate(self.urls):
            prefix = f"[{url_idx}] " if url_idx > 0 else ""
            for attempt in range(self.max_retries):
                # Check total deadline before each attempt
                elapsed = time.time() - started_at
                if self.total_timeout is not None and elapsed >= self.total_timeout:
                    logger.warning(
                        "%sOverpass total timeout (%ss) reached, giving up on %s",
                        prefix,
                        self.total_timeout,
                        data_type,
                    )
                    return []

                try:
                    if attempt > 0:
                        delay = random.uniform(1, 3) * (attempt + 1)
                        logger.info(
                            "%sOverpass retry %d/%d at %s, waiting %.1fs",
                            prefix,
                            attempt + 1,
                            self.max_retries,
                            url,
                            delay,
                        )
                        time.sleep(delay)

                    logger.info("%sQuerying Overpass for %s at %s", prefix, data_type, url)
                    resp = requests.post(
                        url,
                        data={"data": query},
                        timeout=self.timeout,
                        headers={
                            "User-Agent": "stargazing-place-finder/0.6.0 (+https://github.com/StarGazer1995/stargazing-place-finder)",
                            "Accept": "application/json",
                        },
                    )
                    resp.raise_for_status()
                    elements = resp.json().get("elements", [])
                    logger.info(
                        "%sOverpass %s at %s: found %d",
                        prefix,
                        data_type,
                        url,
                        len(elements),
                    )
                    return elements

                except requests.exceptions.Timeout:
                    logger.warning(
                        "%sOverpass timeout (%s, attempt %d/%d)",
                        prefix,
                        data_type,
                        attempt + 1,
                        self.max_retries,
                    )
                except requests.exceptions.HTTPError as e:
                    logger.warning(
                        "%sOverpass HTTP %s (%s, attempt %d/%d)",
                        prefix,
                        e,
                        data_type,
                        attempt + 1,
                        self.max_retries,
                    )
                except NetworkError as e:
                    logger.warning(
                        "%sOverpass error (%s, attempt %d/%d): %s",
                        prefix,
                        data_type,
                        attempt + 1,
                        self.max_retries,
                        e,
                    )
                except requests.exceptions.RequestException as e:
                    logger.warning(
                        "%sOverpass request failed (%s, attempt %d/%d): %s",
                        prefix,
                        data_type,
                        attempt + 1,
                        self.max_retries,
                        e,
                    )

            if url_idx < len(self.urls) - 1:
                logger.info(
                    "%sAll retries exhausted for %s, trying fallback URL...",
                    prefix,
                    url,
                )

        logger.error("Overpass query failed for %s after all URLs exhausted", data_type)
        return []
