import os
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

try:
    import importlib.resources as res
except ImportError:
    # Python<3.9 fallback
    import importlib_resources as res  # type: ignore

from .stargazing_location_analyzer import (
    StargazingLocationAnalyzer,
    analyze_stargazing_area as _analyze_area_fn,
)

_sa_analyzer: Optional[StargazingLocationAnalyzer] = None

def _default_geotiff_path() -> Path:
    """
    返回包内默认的 VIIRS 中国区域 GeoTIFF 路径
    """
    return Path(res.files('light_pollution').joinpath('resources', 'viirs_china_2025.tif'))

def init_stargazing_analyzer(geotiff_path: Optional[Path] = None,
                             min_height_difference: float = 100.0,
                             road_search_radius_km: float = 10.0,
                             db_config_path: Optional[Path] = None) -> StargazingLocationAnalyzer:
    """
    初始化并返回天文观测位置分析器实例，供直接导入调用。

    Args:
        geotiff_path: VIIRS GeoTIFF 文件路径，默认为包内裁剪中国区域数据
        min_height_difference: 最小高差阈值
        road_search_radius_km: 道路搜索半径（公里）
        db_config_path: 数据库配置文件路径

    Returns:
        已初始化的 StargazingLocationAnalyzer 实例
    """
    global _sa_analyzer
    if geotiff_path is None:
        geotiff_path = _default_geotiff_path()
    _sa_analyzer = StargazingLocationAnalyzer(
        geotiff_path=str(geotiff_path),
        min_height_difference=min_height_difference,
        road_search_radius_km=road_search_radius_km,
        db_config_path=str(db_config_path) if db_config_path else None,
    )
    return _sa_analyzer

def _require_analyzer() -> StargazingLocationAnalyzer:
    """
    确保分析器已初始化，未初始化则使用默认路径进行初始化。

    Returns:
        StargazingLocationAnalyzer 实例
    """
    global _sa_analyzer
    if _sa_analyzer is None:
        init_stargazing_analyzer()
    return _sa_analyzer  # type: ignore

def analyze_area(bbox: Tuple[float, float, float, float],
                 max_locations: int = 50,
                 network_type: str = 'drive',
                 include_light_pollution: bool = True,
                 include_road_connectivity: bool = True) -> List[Dict[str, Any]]:
    """
    在给定边界内进行天文观测位置综合分析，返回列表结果。

    Args:
        bbox: (south, west, north, east)
        max_locations: 最大位置数量
        network_type: 道路网络类型（如 'drive'）
        include_light_pollution: 是否计算光污染指标
        include_road_connectivity: 是否计算道路可达性

    Returns:
        位置字典列表，包含坐标、海拔、光污染与道路信息
    """
    analyzer = _require_analyzer()
    results = analyzer.analyze_area(
        bbox=bbox,
        max_locations=max_locations,
        location_types=None,
        network_type=network_type,
        include_light_pollution=include_light_pollution,
        include_road_connectivity=include_road_connectivity,
    )
    serialized: List[Dict[str, Any]] = []
    for r in results:
        serialized.append(r.model_dump(exclude_none=True))
    return serialized

def analyze_area_simple(south: float, west: float, north: float, east: float,
                        max_locations: int = 30,
                        min_height_diff: float = 100.0,
                        road_radius_km: float = 10.0,
                        network_type: str = 'drive') -> List[Dict[str, Any]]:
    """
    便捷区域分析封装，调用底层函数并返回序列化列表。

    Args:
        south: 南边界纬度
        west: 西边界经度
        north: 北边界纬度
        east: 东边界经度
        max_locations: 最大位置数量
        min_height_diff: 最小高差
        road_radius_km: 道路半径
        network_type: 道路网络类型

    Returns:
        位置字典列表
    """
    results = _analyze_area_fn(
        south=south,
        west=west,
        north=north,
        east=east,
        kml_file_path=_default_paths()[0],
        max_locations=max_locations,
        location_types=None,
        min_height_diff=min_height_diff,
        road_radius_km=road_radius_km,
        network_type=network_type,
    )
    serialized: List[Dict[str, Any]] = []
    for r in results:
        serialized.append(r.model_dump(exclude_none=True))
    return serialized
