# -*- coding: utf-8 -*-
"""
GeoFence — 测试用地理围栏。

在生产环境为无操作（no-op）；在测试环境中返回预定义的硬编码结果，
避免对真实 OSMnx/PostGIS 后端的依赖。
"""

from typing import Dict, Optional


class GeoFence:
    """地理围栏，用于在测试中模拟道路可达性判断结果。

    默认行为是无操作（:meth:`check_road_accessible` 返回 ``None``），
    表示不做拦截，交由真实后端判断。

    测试时可通过 ``GeoFence(enabled=True)`` 启用，
    由硬编码的经纬度范围决定返回结果。

    Args:
        enabled: 是否启用围栏。默认 ``False``。
    """

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def check_road_accessible(self, lat: float, lon: float) -> Optional[bool]:
        """检查坐标是否在围栏规则范围内。

        Returns:
            ``True`` 表示可达，``False`` 表示不可达，
            ``None`` 表示围栏未命中，交由真实后端判断。
        """
        if not self.enabled:
            return None
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return False
        if 120.0 <= lon <= 135.0 and 20.0 <= lat <= 35.0:
            return False
        if 115.0 <= lon <= 118.0 and 39.0 <= lat <= 41.0:
            return True
        return True

    def get_fake_accessibility_info(self, lat: float, lon: float) -> Optional[Dict]:
        """返回模拟的道路可达性详情。

        Returns:
            包含可达性信息的字典，或 ``None`` 表示不拦截。
        """
        if not self.enabled:
            return None
        accessible = self.check_road_accessible(lat, lon)
        if accessible is None:
            return None
        return {
            "accessible": accessible,
            "distance_to_road_km": 0.8 if accessible else None,
            "nearest_road_type": "residential" if accessible else None,
            "network_nodes_count": 1200 if accessible else 0,
            "error": None if accessible else "fast_mode_unreachable",
        }
