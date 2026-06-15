# -*- coding: utf-8 -*-
"""
GisQueryService — 统一的 GIS 查询服务入口。

将所有 GIS 空间查询（PostGIS、Overpass API、高程）聚合为一个服务，
上层模块只需注入此服务即可获得全部 GIS 能力，无需关心数据来源。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .backends.elevation_backend import ElevationBackend
from .backends.overpass_backend import OverpassBackend
from .backends.postgis_backend import PostgisBackend
from .caching import GisQueryCache
from .config import load_db_config

logger = logging.getLogger(__name__)


class GisQueryService:
    """
    统一 GIS 查询服务。

    职责：
    · 在 PostGIS 与 Overpass API 之间透明切换
    · 统一高程查询（含 multi-level fallback）
    · 缓存管理

    用法：
        gis = GisQueryService(db_config_path="db.json")
        peaks = gis.query_locations(bbox, "peak")
        elevation = gis.find_elevation(lat, lon)
    """

    def __init__(
        self,
        db_config: Optional[Dict[str, Any]] = None,
        db_config_path: Optional[str] = None,
        enable_cache: bool = True,
        cache_expiry_hours: int = 24,
    ):
        """
        Args:
            db_config: 数据库连接配置字典（优先级高于 db_config_path）
            db_config_path: 数据库配置文件的路径（JSON 或 TOML）
            enable_cache: 是否启用查询结果缓存
            cache_expiry_hours: 缓存过期时间（小时）
        """
        # 加载数据库配置
        resolved_config = db_config or load_db_config(db_config_path)
        self.postgis_enabled = resolved_config is not None

        # 初始化后端
        self._postgis: Optional[PostgisBackend] = None
        if resolved_config:
            self._postgis = PostgisBackend(resolved_config)

        self._overpass = OverpassBackend()
        self._elevation = ElevationBackend(postgis_backend=self._postgis)

        # 缓存
        self._cache: Optional[GisQueryCache] = None
        if enable_cache:
            self._cache = GisQueryCache(cache_expiry_hours=cache_expiry_hours)

    # ── 位置查询（PostGIS / Overpass 透明切换）────────────────

    def query_locations(
        self,
        bbox: Tuple[float, float, float, float],
        location_type: str = "peak",
        filters: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        在 bbox(south, west, north, east) 内查询位置。

        优先使用 PostGIS，不可用时自动切换 Overpass API。

        Args:
            bbox: (south, west, north, east)
            location_type: 类型 ('peak', 'town', 'observatory', 'viewpoint', 'mountain_peak')
            filters: 额外 SQL 筛选条件（仅 PostGIS）

        Returns:
            Overpass 兼容格式的 element dict 列表
        """
        cache_key = None
        if self._cache:
            cache_key = self._cache._make_key("query_locations", bbox, location_type, filters)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s %s", location_type, bbox)
                return cached

        lon_min, lat_min, lon_max, lat_max = bbox[1], bbox[0], bbox[3], bbox[2]

        if self.postgis_enabled and self._postgis:
            logger.info("Querying %s via PostGIS: %s", location_type, bbox)
            results = self._postgis.query_locations_in_bbox(lon_min, lat_min, lon_max, lat_max, location_type, filters)
        else:
            logger.info("Querying %s via Overpass: %s", location_type, bbox)
            results = self._overpass.query_locations_in_bbox(lon_min, lat_min, lon_max, lat_max, location_type, filters)

        if cache_key and self._cache:
            self._cache.set(cache_key, results)

        return results

    def query_towns(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """查询城镇。"""
        return self.query_locations(bbox, "town")

    def query_peaks(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """查询山峰。"""
        return self.query_locations(bbox, "peak")

    def query_observatories(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """查询天文台。"""
        return self.query_locations(bbox, "observatory")

    def query_viewpoints(self, bbox: Tuple[float, float, float, float]) -> List[Dict[str, Any]]:
        """查询观景点。"""
        return self.query_locations(bbox, "viewpoint")

    # ── 道路连通性查询 ──────────────────────────────────────

    def query_road_connectivity(
        self,
        lat: float, lon: float,
        radius_km: float = 10.0,
        network_type: str = 'drive',
    ) -> Dict[str, Any]:
        """
        查询坐标点的道路连通性。

        优先使用 PostGIS kNN 毫秒级查询，不可用时 fallback 到 OSMnx。

        Args:
            lat: 纬度 (WGS84)
            lon: 经度 (WGS84)
            radius_km: 搜索半径（千米）
            network_type: 道路类型 ('drive', 'walk', 'bike', 'all')

        Returns:
            Dict with at minimum:
                - accessible: bool
                - distance_meters: float or None
                - road_type: str or None
        """
        if self.postgis_enabled and self._postgis:
            return self._postgis.query_road_connectivity(
                lat, lon, radius_km, network_type
            )
        # Fallback: 通过 OSMnx 查询（由 RoadConnectivityChecker 处理）
        logger.info(
            "PostGIS not available, road connectivity must use OSMnx fallback: "
            "(%.4f, %.4f)", lat, lon
        )
        return {
            'accessible': False,
            'distance_meters': None,
            'road_type': None,
            'road_name': None,
            'nearest_lat': None,
            'nearest_lon': None,
            'fallback_needed': True,
        }

    # ── 高程查询 ─────────────────────────────────────────────

    def find_elevation(
        self,
        lat: float,
        lon: float,
        osm_tags: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        查询坐标海拔（含 fallback 链）。

        Returns:
            海拔（米），始终返回 float
        """
        return self._elevation.find_elevation(lat, lon, osm_tags)

    def batch_find_elevations(
        self,
        coordinates: List[Tuple[float, float]],
        osm_tags_list: Optional[List[Optional[Dict[str, Any]]]] = None,
    ) -> List[float]:
        """批量查询海拔。"""
        return self._elevation.batch_find_elevations(coordinates, osm_tags_list)

    # ── 缓存管理 ─────────────────────────────────────────────

    def clear_cache(self):
        """清空所有查询缓存。"""
        if self._cache:
            self._cache.clear()
            logger.info("GIS query cache cleared")

    # ── 统计 ──────────────────────────────────────────────────

    def get_elevation_statistics(self) -> Dict[str, Any]:
        """返回数据库海拔统计信息（仅 PostGIS 可用时）。"""
        if self._postgis:
            return self._postgis.get_elevation_statistics()
        return {"error": "PostGIS not enabled"}
