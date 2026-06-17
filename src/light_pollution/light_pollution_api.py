#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染数据API服务器

这个模块提供了一个Flask API服务器，用于根据地图视窗范围动态获取光污染图像数据。
"""

import logging
import math
import os
from io import BytesIO
from typing import Dict, Optional, Tuple

import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from PIL import Image

from gis_service.parsers import bortle_to_sqm, brightness_to_bortle, get_pollution_level_description
from models import ConfigError, DataError
from stargazing_analyzer.stargazing_location_analyzer import analyze_stargazing_area

from .light_pollution_analyzer import LightPollutionAnalyzer
from .public_api import _default_geotiff_path

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局光污染分析器实例
analyzer = None


def init_analyzer():
    """
    初始化光污染分析器
    """
    global analyzer
    try:
        geotiff_file = str(_default_geotiff_path())

        logger.info("Initializing light pollution analyzer...")
        logger.info("GeoTIFF file path: %s", geotiff_file)

        analyzer = LightPollutionAnalyzer(
            geotiff_path=geotiff_file,
            skyglow_sigma_km=15.0,
            skyglow_weight=0.4,
        )
        logger.info("✅ Light pollution analyzer initialization completed")

        # 显示统计信息
        stats = analyzer.get_statistics()
        logger.info("Dataset dimensions: %sx%s", stats.get("width"), stats.get("height"))
        logger.info("Data path: %s", stats.get("data_path"))

    except (ConfigError, FileNotFoundError) as e:
        logger.error("❌ Light pollution analyzer initialization failed: %s", e)
        analyzer = None


# ---------------------------------------------------------------------------
# Dynamic tile server — samples GeoTIFF and renders PNG tiles on the fly
# ---------------------------------------------------------------------------

# Tile size in pixels
_TILE_SIZE = 256
# Simple in-memory tile cache
_tile_cache: Dict[str, bytes] = {}
_MAX_TILE_CACHE = 500

# Colormap stops matching the heatmap gradient (value → RGB)
_TILE_CMAP_STOPS = [
    (0.00, (0, 0, 51)),
    (0.10, (0, 0, 102)),
    (0.20, (0, 51, 153)),
    (0.30, (0, 102, 204)),
    (0.40, (0, 153, 255)),
    (0.50, (0, 204, 102)),
    (0.60, (102, 255, 51)),
    (0.70, (255, 255, 0)),
    (0.80, (255, 153, 0)),
    (0.90, (255, 51, 0)),
    (1.00, (204, 0, 0)),
]

# Pre-built 256-entry RGBA lookup table
_TILE_CMAP_LUT: Optional[np.ndarray] = None


def _build_tile_cmap_lut() -> np.ndarray:
    """Build a 256x4 RGBA lookup table from the colormap stops."""
    global _TILE_CMAP_LUT
    if _TILE_CMAP_LUT is not None:
        return _TILE_CMAP_LUT

    lut = np.zeros((256, 4), dtype=np.uint8)
    for i in range(256):
        v = i / 255.0
        if v <= 0:
            r, g, b = _TILE_CMAP_STOPS[0][1]
        elif v >= 1.0:
            r, g, b = _TILE_CMAP_STOPS[-1][1]
        else:
            for j in range(len(_TILE_CMAP_STOPS) - 1):
                t0, (r0, g0, b0) = _TILE_CMAP_STOPS[j]
                t1, (r1, g1, b1) = _TILE_CMAP_STOPS[j + 1]
                if t0 <= v <= t1:
                    f = (v - t0) / (t1 - t0)
                    r = int(r0 + (r1 - r0) * f)
                    g = int(g0 + (g1 - g0) * f)
                    b = int(b0 + (b1 - b0) * f)
                    break
        lut[i] = (r, g, b, 255)
    lut[0] = (0, 0, 51, 255)  # intensity=0 → dark sky

    _TILE_CMAP_LUT = lut
    return lut


def _tile_to_lat(y: int, z: int) -> float:
    """Convert XYZ tile Y coordinate to latitude (Web Mercator inverse)."""
    n = math.pi - 2.0 * math.pi * y / (1 << z)
    return math.degrees(math.atan(math.sinh(n)))


def _tile_to_lng(x: int, z: int) -> float:
    """Convert XYZ tile X coordinate to longitude."""
    return x / (1 << z) * 360.0 - 180.0


def _tile_bounds(x: int, y: int, z: int) -> Tuple[float, float, float, float]:
    """Get (north, south, east, west) geographic bounds for an XYZ tile."""
    north = _tile_to_lat(y, z)
    south = _tile_to_lat(y + 1, z)
    west = _tile_to_lng(x, z)
    east = _tile_to_lng(x + 1, z)
    return north, south, east, west


def _empty_tile() -> Response:
    """Return a 256x256 fully transparent PNG tile."""
    key = "__empty__"
    if key in _tile_cache:
        return Response(_tile_cache[key], mimetype="image/png", headers={"Cache-Control": "public, max-age=3600"})
    rgba = np.zeros((_TILE_SIZE, _TILE_SIZE, 4), dtype=np.uint8)
    img = Image.fromarray(rgba, "RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    _tile_cache[key] = buf.getvalue()
    return Response(buf.getvalue(), mimetype="image/png", headers={"Cache-Control": "public, max-age=3600"})


def _validate_tile_request(z: int, x: int, y: int) -> Optional[Response]:
    """Check analyzer readiness and tile cache. Returns a cached Response or None."""
    if analyzer is None or analyzer._src is None:
        return _empty_tile()
    cache_key = f"{z}/{x}/{y}"
    cached = _tile_cache.get(cache_key)
    if cached is not None:
        return Response(cached, mimetype="image/png", headers={"Cache-Control": "public, max-age=3600"})
    return None


def _clamp_tile_bounds(
    north: float,
    south: float,
    east: float,
    west: float,
    src,
) -> Optional[Tuple[float, float, float, float]]:
    """Clamp tile bounds to valid latitude range and GeoTIFF extent. Returns None if no overlap."""
    north = min(north, 90.0)
    south = max(south, -90.0)
    if west > src.bounds.right or east < src.bounds.left or south > src.bounds.top or north < src.bounds.bottom:
        return None
    west = max(west, float(src.bounds.left))
    east = min(east, float(src.bounds.right))
    south = max(south, float(src.bounds.bottom))
    north = min(north, float(src.bounds.top))
    return north, south, east, west


def _read_tile_window(
    src,
    west: float,
    east: float,
    south: float,
    north: float,
) -> Optional[np.ndarray]:
    """Read GeoTIFF data for the geographic window, decimated to tile size."""
    row_nw, col_nw = src.index(west, north)
    row_se, col_se = src.index(east, south)
    row_start = max(0, min(row_nw, row_se))
    row_end = min(int(src.height), max(row_nw, row_se) + 1)
    col_start = max(0, min(col_nw, col_se))
    col_end = min(int(src.width), max(col_nw, col_se) + 1)
    if row_end <= row_start or col_end <= col_start:
        return None
    data = src.read(1, window=((row_start, row_end), (col_start, col_end)), out_shape=(_TILE_SIZE, _TILE_SIZE))
    if hasattr(analyzer, "get_skyglow_for_window") and analyzer._skyglow_grid is not None:
        sg = analyzer.get_skyglow_for_window(west, east, south, north, (_TILE_SIZE, _TILE_SIZE))
        data = data.astype(np.float32) + analyzer._skyglow_weight * sg
    return data


def _render_tile_png(data: np.ndarray, src, cache_key: str) -> Response:
    """Apply colormap, encode as PNG, cache the result, and return a Response."""
    lut = _build_tile_cmap_lut()
    if data.dtype.kind == "f":
        valid = ~np.isnan(data)
    else:
        valid = np.ones_like(data, dtype=bool)
    nodata = src.nodata
    if nodata is not None:
        valid = valid & (data != nodata)
    with np.errstate(divide="ignore", invalid="ignore"):
        intensity = np.where(valid, data, 0.0)
        intensity = np.minimum(1.0, 1.0 - 1.0 / (1.0 + intensity * 0.1))
    idx = np.clip((intensity * 255).astype(np.uint8), 0, 255)
    rgba = lut[idx].copy()
    rgba[~valid] = (0, 0, 0, 0)
    img = Image.fromarray(rgba, "RGBA")
    buf = BytesIO()
    img.save(buf, format="PNG")
    png_data = buf.getvalue()
    _tile_cache[cache_key] = png_data
    if len(_tile_cache) > _MAX_TILE_CACHE:
        _tile_cache.clear()
    return Response(png_data, mimetype="image/png", headers={"Cache-Control": "public, max-age=3600"})


@app.route("/api/light_pollution/tiles/<int:z>/<int:x>/<int:y>.png")
def serve_light_pollution_tile(z: int, x: int, y: int) -> Response:
    """
    Dynamic tile endpoint — samples the VIIRS GeoTIFF and returns a PNG tile.

    Tile coordinate system: XYZ (Slippy Map) — same as OpenStreetMap.
    Callers fetch tiles via: /api/light_pollution/tiles/{z}/{x}/{y}.png
    """
    cached = _validate_tile_request(z, x, y)
    if cached is not None:
        return cached

    src = analyzer._src
    cache_key = f"{z}/{x}/{y}"

    north, south, east, west = _tile_bounds(x, y, z)
    bounds = _clamp_tile_bounds(north, south, east, west, src)
    if bounds is None:
        return _empty_tile()
    north, south, east, west = bounds

    try:
        data = _read_tile_window(src, west, east, south, north)
        if data is None:
            return _empty_tile()
        return _render_tile_png(data, src, cache_key)
    except DataError as e:
        logger.warning("⚠️ Tile render error (%s/%s/%s): %s", z, x, y, e)
        return _empty_tile()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    计算两个地理坐标之间的距离（公里）

    Args:
        lat1, lon1: 第一个点的纬度和经度
        lat2, lon2: 第二个点的纬度和经度

    Returns:
        距离（公里）
    """
    R = 6371  # 地球半径（公里）

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def _parse_pollution_request():
    """解析并验证请求参数中的地理边界和缩放级别."""
    north = float(request.args.get("north", 0))
    south = float(request.args.get("south", 0))
    east = float(request.args.get("east", 0))
    west = float(request.args.get("west", 0))
    zoom = int(request.args.get("zoom", 10))
    return north, south, east, west, zoom


def _calculate_grid_resolution(zoom, lat_range, lng_range):
    """根据缩放级别和地理范围确定网格分辨率及行列数."""
    if zoom <= 8:
        grid_resolution = 0.1
    elif zoom <= 12:
        grid_resolution = 0.05
    elif zoom <= 16:
        grid_resolution = 0.02
    else:
        grid_resolution = 0.01

    grid_rows = max(1, int(lat_range / grid_resolution))
    grid_cols = max(1, int(lng_range / grid_resolution))

    max_points = 2000
    total_points = grid_rows * grid_cols
    if total_points > max_points:
        scale_factor = math.sqrt(max_points / total_points)
        grid_rows = max(1, int(grid_rows * scale_factor))
        grid_cols = max(1, int(grid_cols * scale_factor))
        logger.warning(
            "⚠️ Too many grid points, adjusted to %sx%s = %s points", grid_rows, grid_cols, grid_rows * grid_cols
        )

    return grid_resolution, grid_rows, grid_cols


def _build_coordinate_grid(south, north, west, east, grid_rows, grid_cols):
    """构建采样坐标网格."""
    lat_range = north - south
    lng_range = east - west
    coordinates_list = []
    grid_info = []
    for row in range(grid_rows):
        for col in range(grid_cols):
            lat = south + (row + 0.5) * (lat_range / grid_rows)
            lng = west + (col + 0.5) * (lng_range / grid_cols)
            coordinates_list.append((lat, lng))
            grid_info.append((lat, lng))
    return coordinates_list, grid_info


def _format_pollution_point(result, lat, lng, idx):
    """格式化单个采样点的光污染数据."""
    pollution_info = result.get("pollution_info")
    if pollution_info:
        brightness = pollution_info.brightness
        bortle = brightness_to_bortle(brightness)
        sqm = bortle_to_sqm(bortle)
        intensity = brightness / 255.0
        return {
            "name": f"数据点 {idx + 1}",
            "lat": lat,
            "lng": lng,
            "bortle": bortle,
            "sqm": f"{sqm:.1f}",
            "intensity": intensity,
            "brightness": brightness,
            "rgb": pollution_info.rgb,
            "hex": pollution_info.hex,
            "overlay_name": pollution_info.overlay_name,
        }
    return {
        "name": f"数据点 {idx + 1}",
        "lat": lat,
        "lng": lng,
        "bortle": 5,
        "sqm": "20.0",
        "intensity": 0.5,
        "brightness": 128,
        "rgb": [128, 128, 128],
        "hex": "#808080",
        "overlay_name": "默认数据",
    }


def _build_pollution_response(data, north, south, east, west, zoom, grid_resolution):
    """构建光污染数据的JSON响应."""
    return jsonify(
        {
            "success": True,
            "data": data,
            "metadata": {
                "bounds": {"north": north, "south": south, "east": east, "west": west},
                "zoom": zoom,
                "grid_resolution": grid_resolution,
                "total_points": len(data),
            },
        }
    )


@app.route("/api/light_pollution", methods=["GET"])
def get_light_pollution_data():
    """
    获取指定边界范围内的光污染数据

    查询参数:
        north: 北边界纬度
        south: 南边界纬度
        east: 东边界经度
        west: 西边界经度
        zoom: 地图缩放级别（可选，默认为10）

    Returns:
        JSON格式的光污染数据数组
    """
    if analyzer is None:
        return jsonify({"error": "光污染分析器未初始化", "data": []}), 500

    try:
        north, south, east, west, zoom = _parse_pollution_request()

        logger.info(
            "🌍 Getting light pollution data: bounds=(%s, %s) to (%s, %s), zoom=%s", south, west, north, east, zoom
        )

        lat_range = north - south
        lng_range = east - west
        grid_resolution, grid_rows, grid_cols = _calculate_grid_resolution(zoom, lat_range, lng_range)

        logger.info("🔢 Generating grid: %sx%s = %s points", grid_rows, grid_cols, grid_rows * grid_cols)

        coordinates_list, grid_info = _build_coordinate_grid(south, north, west, east, grid_rows, grid_cols)

        batch_results = analyzer.batch_analyze_coordinates(coordinates_list)

        data = []
        for idx, (result, (lat, lng)) in enumerate(zip(batch_results, grid_info)):
            data.append(_format_pollution_point(result, lat, lng, idx))

        logger.info("✅ Successfully retrieved %s light pollution data points", len(data))

        return _build_pollution_response(data, north, south, east, west, zoom, grid_resolution)

    except DataError as e:
        logger.error("❌ Error getting light pollution data: %s", e)
        return jsonify({"error": str(e), "data": []}), 500


@app.route("/api/light_pollution_images", methods=["GET"])
def get_light_pollution_images():
    """
    获取指定地理边界内的光污染图片数据

    查询参数:
    - north: 北边界纬度
    - south: 南边界纬度
    - east: 东边界经度
    - west: 西边界经度

    返回:
    - 包含图片信息的JSON数组
    """
    global analyzer

    if analyzer is None:
        return jsonify({"error": "光污染分析器未初始化"}), 500

    try:
        # 获取查询参数
        north = request.args.get("north", type=float)
        south = request.args.get("south", type=float)
        east = request.args.get("east", type=float)
        west = request.args.get("west", type=float)

        # 验证参数
        if any(param is None for param in [north, south, east, west]):
            return jsonify({"error": "缺少必需的参数: north, south, east, west"}), 400

        # 验证坐标范围
        if not (-90 <= north <= 90) or not (-90 <= south <= 90):
            return jsonify({"error": "纬度必须在-90到90之间"}), 400

        if not (-180 <= east <= 180) or not (-180 <= west <= 180):
            return jsonify({"error": "经度必须在-180到180之间"}), 400

        if north <= south:
            return jsonify({"error": "北边界必须大于南边界"}), 400

        logger.info("Getting light pollution image data: North%s° South%s° East%s° West%s°", north, south, east, west)

        # GeoTIFF 后端不支持图片提取，返回空数据
        processed_data = []
        logger.warning("⚠️ GeoTIFF backend does not support image extraction")
        logger.info("✅ Returned 0 light pollution images")

        return jsonify(
            {
                "success": True,
                "count": len(processed_data),
                "images": processed_data,
                "query_bounds": {"north": north, "south": south, "east": east, "west": west},
            }
        )

    except DataError as e:
        logger.exception("❌ Error getting light pollution image data: %s", e)
        return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500


@app.route("/api/coordinate_analysis", methods=["GET"])
def analyze_coordinate():
    """
    分析单个坐标点的光污染数据

    查询参数:
        lat: 纬度
        lng: 经度

    Returns:
        JSON格式的光污染分析结果
    """
    if analyzer is None:
        return jsonify({"error": "光污染分析器未初始化", "success": False}), 500

    try:
        # 获取查询参数
        lat = float(request.args.get("lat", 0))
        lng = float(request.args.get("lng", 0))

        logger.info("🎯 Analyzing coordinate point: (%s, %s)", lat, lng)

        # 使用光污染分析器获取真实数据
        pollution_info = analyzer.get_light_pollution_color(lat, lng)

        if pollution_info:
            # 从真实数据中提取信息 — 使用直接辐射度→波特尔转换，而非过时的亮度映射
            bortle = pollution_info.bortle
            sqm = bortle_to_sqm(bortle)
            brightness = pollution_info.brightness
            intensity = brightness / 255.0
            description = get_pollution_level_description(bortle)

            result = {
                "success": True,
                "data": {
                    "coordinates": {"lat": lat, "lng": lng},
                    "light_pollution": {
                        "bortle_class": bortle,
                        "sqm_value": round(sqm, 1),
                        "intensity": round(intensity, 3),
                        "brightness": brightness,
                        "radiance": pollution_info.radiance,
                        "description": description,
                    },
                    "color_info": {"rgb": pollution_info.rgb, "hex": pollution_info.hex},
                    "source": {"overlay_name": pollution_info.overlay_name, "data_type": "real_data"},
                },
            }

            logger.info("✅ Successfully analyzed coordinate point: Bortle class=%s, SQM=%.1f", bortle, sqm)
            return jsonify(result)
        else:
            # 如果没有找到数据，返回默认值
            result = {
                "success": True,
                "data": {
                    "coordinates": {"lat": lat, "lng": lng},
                    "light_pollution": {
                        "bortle_class": 5,
                        "sqm_value": 20.0,
                        "intensity": 0.5,
                        "brightness": 128,
                        "description": get_pollution_level_description(5),
                    },
                    "color_info": {"rgb": [128, 128, 128], "hex": "#808080"},
                    "source": {"overlay_name": "默认数据", "data_type": "default_data"},
                },
                "warning": "该坐标点没有找到光污染数据，使用默认值",
            }

            logger.warning("⚠️ No data found for coordinate point (%s, %s), using default values", lat, lng)
            return jsonify(result)

    except ValueError as e:
        return jsonify({"error": "无效的坐标参数", "success": False, "details": str(e)}), 400

    except DataError as e:
        logger.error("❌ Error analyzing coordinate point: %s", e)
        return jsonify({"error": str(e), "success": False}), 500


def _parse_stargazing_params() -> Tuple[float, float, float, float, int, float, float, str]:
    """Parse request params from POST JSON body or GET query args.

    Returns:
        (south, west, north, east, max_locations, min_height_diff, road_radius_km, network_type)
    """
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return None  # signal: missing JSON body
        bbox = data.get("bbox", {})
        return (
            float(bbox.get("south", 0)),
            float(bbox.get("west", 0)),
            float(bbox.get("north", 0)),
            float(bbox.get("east", 0)),
            int(data.get("max_locations", 30)),
            float(data.get("min_height_diff", 100.0)),
            float(data.get("road_radius_km", 10.0)),
            data.get("network_type", "drive"),
        )
    # GET request from URL query args
    return (
        float(request.args.get("south", 0)),
        float(request.args.get("west", 0)),
        float(request.args.get("north", 0)),
        float(request.args.get("east", 0)),
        int(request.args.get("max_locations", 30)),
        float(request.args.get("min_height_diff", 100.0)),
        float(request.args.get("road_radius_km", 10.0)),
        request.args.get("network_type", "drive"),
    )


def _location_to_dict(loc) -> dict:
    """Convert a StargazingLocation to a JSON-compatible dictionary."""
    return {
        "name": loc.name,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "elevation": loc.elevation,
        "prominence": loc.prominence,
        "distance_to_nearest_town": loc.distance_to_nearest_town,
        "nearest_town_name": loc.nearest_town_name,
        "height_difference": loc.height_difference,
        "light_pollution_rgb": loc.light_pollution_rgb,
        "light_pollution_hex": loc.light_pollution_hex,
        "light_pollution_brightness": loc.light_pollution_brightness,
        "light_pollution_level": loc.light_pollution_level,
        "light_pollution_overlay": loc.light_pollution_overlay,
        "road_accessible": loc.road_accessible,
        "distance_to_road_km": loc.distance_to_road_km,
        "road_network_type": loc.road_network_type,
        "road_check_error": loc.road_check_error,
        "stargazing_score": loc.stargazing_score,
        "recommendation_level": loc.recommendation_level,
        "analysis_notes": loc.analysis_notes,
    }


def _build_stargazing_response(locations, south: float, west: float, north: float, east: float):
    """Build jsonify response from analyzed locations and bounding box."""
    locations_data = [_location_to_dict(loc) for loc in locations]
    logger.info("✅ Successfully analyzed %s stargazing locations", len(locations_data))
    return jsonify(
        {
            "success": True,
            "count": len(locations_data),
            "locations": locations_data,
            "bounds": {"south": south, "west": west, "north": north, "east": east},
        }
    )


@app.route("/api/analyze_stargazing_area", methods=["GET", "POST", "OPTIONS"])
def analyze_stargazing_area_endpoint():
    """
    分析指定区域的观星地点

    参数:
        south: 南边界纬度
        west: 西边界经度
        north: 北边界纬度
        east: 东边界经度
        max_locations: 最大山峰数量（可选，默认30）
        min_height_diff: 最小高度差（可选，默认100.0）
        road_radius_km: 道路搜索半径（可选，默认10.0）
    """
    if request.method == "OPTIONS":
        return "", 200

    try:
        params = _parse_stargazing_params()
        if params is None:
            return jsonify({"success": False, "error": "Missing JSON data", "message": "缺少JSON数据"}), 400

        south, west, north, east, max_locations, min_height_diff, road_radius_km, network_type = params

        logger.info("Analyzing stargazing area: North%s° South%s° East%s° West%s°", north, south, east, west)

        # 获取 GeoTIFF 文件路径
        geotiff_path = str(_default_geotiff_path())

        # Get DB config from environment variable
        db_config_path = os.environ.get("STARGAZING_DB_CONFIG")
        if db_config_path:
            logger.info("Using DB config from: %s", db_config_path)

        locations = analyze_stargazing_area(
            south=south,
            west=west,
            north=north,
            east=east,
            geotiff_path=geotiff_path if os.path.exists(geotiff_path) else None,
            max_locations=max_locations,
            min_height_diff=min_height_diff,
            road_radius_km=road_radius_km,
            network_type=network_type,
            db_config_path=db_config_path,
        )

        return _build_stargazing_response(locations, south, west, north, east)

    except DataError as e:
        logger.error("❌ Stargazing area analysis failed: %s", e)
        return jsonify({"success": False, "error": str(e), "message": "观星区域分析失败"}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """
    健康检查端点
    """
    return jsonify({"status": "healthy", "analyzer_initialized": analyzer is not None})


if __name__ == "__main__":
    # 初始化分析器
    init_analyzer()

    # 启动Flask服务器
    logger.info("🚀 Starting light pollution data API server...")
    logger.info("📡 API endpoints:")
    logger.info("  - GET /api/light_pollution         - Get light pollution data (JSON)")
    logger.info("  - GET /api/light_pollution/tiles/{z}/{x}/{y}.png  - Dynamic raster tiles")
    logger.info("  - GET /api/coordinate_analysis     - Analyze single coordinate point")
    logger.info("  - GET/POST /api/analyze_stargazing_area - Analyze stargazing area")
    logger.info("  - GET /api/health                  - Health check")
    logger.info("🌐 Server address: http://localhost:5001")

    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
