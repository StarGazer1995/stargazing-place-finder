import os
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

try:
    import importlib.resources as res
except ImportError:
    # Python<3.9 fallback
    import importlib_resources as res  # type: ignore

from .light_pollution_analyzer import (
    LightPollutionAnalyzer,
    radiance_to_bortle as _radiance_to_bortle,
    radiance_to_brightness as _radiance_to_brightness,
    radiance_to_pollution_level as _radiance_to_pollution_level,
)

_lp_analyzer: Optional[LightPollutionAnalyzer] = None

def _default_geotiff_path() -> Path:
    """
    返回包内默认的 VIIRS 中国区域 GeoTIFF 路径
    """
    return Path(res.files(__package__).joinpath('resources', 'viirs_china_2025.tif'))

def init_light_pollution_analyzer(
    kml_file_path: Optional[Path] = None,
    images_base_path: Optional[Path] = None,
    geotiff_path: Optional[Union[Path, str]] = None,
) -> LightPollutionAnalyzer:
    """
    初始化并返回光污染分析器实例。

    默认使用 VIIRS GeoTIFF 数据源（裁剪中国区域）。
    可以通过传入 kml_file_path 切换到旧版的 KML 图片后端。

    Args:
        kml_file_path: KML 文件路径（旧版后端）。设为非空值则使用 KML 后端。
        images_base_path: 光污染图片目录（旧版），默认与 KML 同目录下 files。
        geotiff_path: VIIRS GeoTIFF 文件路径。默认使用包内裁剪的中国区域数据。

    Returns:
        已初始化的 LightPollutionAnalyzer 实例
    """
    global _lp_analyzer

    if kml_file_path is not None:
        # Legacy KML backend
        if images_base_path is None:
            _, default_images = _default_kml_paths()
            images_base_path = images_base_path or default_images
        _lp_analyzer = LightPollutionAnalyzer(
            kml_file_path=str(kml_file_path),
            images_base_path=str(images_base_path),
        )
    else:
        # Default: GeoTIFF backend
        if geotiff_path is None:
            geotiff_path = _default_geotiff_path()
        _lp_analyzer = LightPollutionAnalyzer(
            geotiff_path=str(geotiff_path),
            skyglow_sigma_km=15.0,
            skyglow_weight=0.4,
        )
    return _lp_analyzer

def _require_analyzer() -> LightPollutionAnalyzer:
    """
    确保分析器已初始化，未初始化则使用默认路径进行初始化。

    Returns:
        LightPollutionAnalyzer 实例
    """
    global _lp_analyzer
    if _lp_analyzer is None:
        init_light_pollution_analyzer()
    return _lp_analyzer  # type: ignore

# ---------------------------------------------------------------------------
# Conversion utilities
# ---------------------------------------------------------------------------

def brightness_to_bortle(brightness: int) -> int:
    """
    将亮度值(0-255)映射到波特尔等级(1-9)
    保留用于向后兼容。
    """
    if brightness <= 28:
        return 1
    elif brightness <= 56:
        return 2
    elif brightness <= 84:
        return 3
    elif brightness <= 112:
        return 4
    elif brightness <= 140:
        return 5
    elif brightness <= 168:
        return 6
    elif brightness <= 196:
        return 7
    elif brightness <= 224:
        return 8
    else:
        return 9

def bortle_to_sqm(bortle: int) -> float:
    """
    将波特尔等级转换为SQM（每平方角秒星等）
    """
    sqm_values = {
        1: 21.9,
        2: 21.6,
        3: 21.3,
        4: 20.4,
        5: 19.5,
        6: 18.5,
        7: 17.5,
        8: 16.5,
        9: 15.5,
    }
    return float(sqm_values.get(bortle, 20.0))

def radiance_to_bortle(radiance: float) -> int:
    """将 VIIRS DNB 辐射度 (nW/cm²/sr) 转换为波特尔等级。"""
    return _radiance_to_bortle(radiance)

def radiance_to_brightness(radiance: float) -> int:
    """将辐射度转换为 0-255 亮度值（向后兼容）。"""
    return _radiance_to_brightness(radiance)

def radiance_to_pollution_level(radiance: float) -> str:
    """将辐射度转换为可读的污染等级描述。"""
    return _radiance_to_pollution_level(radiance)

def get_light_pollution_grid(north: float, south: float, east: float, west: float, zoom: int = 10) -> Dict[str, Any]:
    """
    生成指定边界范围内的光污染网格数据，返回结构与HTTP接口一致。

    Args:
        north: 北边界纬度
        south: 南边界纬度
        east: 东边界经度
        west: 西边界经度
        zoom: 地图缩放级别（影响网格分辨率）

    Returns:
        dict: {success, data: List[点数据], metadata}
    """
    analyzer = _require_analyzer()

    if zoom <= 8:
        grid_resolution = 0.1
    elif zoom <= 12:
        grid_resolution = 0.05
    elif zoom <= 16:
        grid_resolution = 0.02
    else:
        grid_resolution = 0.01

    lat_range = north - south
    lng_range = east - west
    grid_rows = max(1, int(lat_range / grid_resolution))
    grid_cols = max(1, int(lng_range / grid_resolution))

    max_points = 2000
    total_points = grid_rows * grid_cols
    if total_points > max_points:
        scale_factor = math.sqrt(max_points / total_points)
        grid_rows = max(1, int(grid_rows * scale_factor))
        grid_cols = max(1, int(grid_cols * scale_factor))

    data: List[Dict[str, Any]] = []
    point_index = 0
    for row in range(grid_rows):
        for col in range(grid_cols):
            lat = south + (row + 0.5) * (lat_range / grid_rows)
            lng = west + (col + 0.5) * (lng_range / grid_cols)
            try:
                pollution_info = analyzer.get_light_pollution_color(lat, lng)
                if pollution_info:
                    bortle = pollution_info.bortle
                    sqm = bortle_to_sqm(bortle)
                    brightness = pollution_info.brightness
                    intensity = brightness / 255.0
                    entry = {
                        'name': f'数据点 {point_index + 1}',
                        'lat': lat,
                        'lng': lng,
                        'bortle': bortle,
                        'sqm': f'{sqm:.1f}',
                        'intensity': intensity,
                        'brightness': brightness,
                        'rgb': pollution_info.rgb,
                        'hex': pollution_info.hex,
                        'overlay_name': pollution_info.overlay_name,
                        'radiance': pollution_info.radiance,
                    }
                    data.append(entry)
                else:
                    data.append({
                        'name': f'数据点 {point_index + 1}',
                        'lat': lat,
                        'lng': lng,
                        'bortle': 5,
                        'sqm': '20.0',
                        'intensity': 0.5,
                        'brightness': 128,
                        'rgb': [128, 128, 128],
                        'hex': '#808080',
                        'overlay_name': '默认数据',
                    })
            except Exception:
                data.append({
                    'name': f'数据点 {point_index + 1}',
                    'lat': lat,
                    'lng': lng,
                    'bortle': 5,
                    'sqm': '20.0',
                    'intensity': 0.5,
                    'brightness': 128,
                    'rgb': [128, 128, 128],
                    'hex': '#808080',
                    'overlay_name': '默认数据',
                })
            point_index += 1

    return {
        'success': True,
        'data': data,
        'metadata': {
            'bounds': {
                'north': north,
                'south': south,
                'east': east,
                'west': west,
            },
            'zoom': zoom,
            'grid_resolution': grid_resolution,
            'total_points': len(data),
        },
    }

def analyze_coordinate(lat: float, lng: float) -> Dict[str, Any]:
    """
    分析单点坐标光污染指标，返回与HTTP接口一致的结构。

    Args:
        lat: 纬度
        lng: 经度

    Returns:
        dict: {success, data 或 warning}
    """
    analyzer = _require_analyzer()
    pollution_info = analyzer.get_light_pollution_color(lat, lng)
    if pollution_info:
        bortle = pollution_info.bortle
        brightness = pollution_info.brightness
        sqm = bortle_to_sqm(bortle)
        description_map = {
            1: "优秀暗空",
            2: "典型暗空",
            3: "乡村天空",
            4: "乡村/郊区过渡",
            5: "郊区天空",
            6: "明亮郊区",
            7: "郊区/城市过渡",
            8: "城市天空",
            9: "内城天空",
        }
        result = {
            'success': True,
            'data': {
                'coordinates': {'lat': lat, 'lng': lng},
                'light_pollution': {
                    'bortle_class': bortle,
                    'sqm_value': float(f"{sqm:.1f}"),
                    'intensity': brightness / 255.0,
                    'brightness': brightness,
                    'description': description_map.get(bortle, '未知等级'),
                    'radiance': pollution_info.radiance,
                },
                'color_info': {
                    'rgb': pollution_info.rgb,
                    'hex': pollution_info.hex,
                },
                'source': {
                    'overlay_name': pollution_info.overlay_name,
                    'data_type': 'real_data',
                },
            },
        }
        return result
    else:
        return {
            'success': True,
            'warning': '未找到光污染数据，返回默认值',
            'data': {
                'coordinates': {'lat': lat, 'lng': lng},
                'light_pollution': {
                    'bortle_class': 5,
                    'sqm_value': 20.0,
                    'intensity': 0.5,
                    'brightness': 128,
                    'description': '郊区天空',
                },
                'color_info': {
                    'rgb': [128, 128, 128],
                    'hex': '#808080',
                },
                'source': {
                    'overlay_name': '默认数据',
                    'data_type': 'default',
                },
            },
        }

