#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光污染数据API服务器

这个模块提供了一个Flask API服务器，用于根据地图视窗范围动态获取光污染图像数据。
"""

import math
import os
import sys
from io import BytesIO
from typing import Dict, Optional, Tuple

import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from PIL import Image

from stargazing_analyzer.stargazing_location_analyzer import analyze_stargazing_area
from .light_pollution_analyzer import LightPollutionAnalyzer

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
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        geotiff_file = os.path.join(project_root, "src/light_pollution/resources/viirs_china_2025.tif")

        print("Initializing light pollution analyzer...")
        print(f"GeoTIFF file path: {geotiff_file}")

        analyzer = LightPollutionAnalyzer(
            geotiff_path=geotiff_file,
            skyglow_sigma_km=15.0,
            skyglow_weight=0.4,
        )
        print("✅ Light pollution analyzer initialization completed")

        # 显示统计信息
        stats = analyzer.get_statistics()
        print(f"Dataset dimensions: {stats.get('width')}x{stats.get('height')}")
        print(f"Data path: {stats.get('data_path')}")

    except Exception as e:
        print(f"❌ Light pollution analyzer initialization failed: {e}")
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


@app.route("/api/light_pollution/tiles/<int:z>/<int:x>/<int:y>.png")
def serve_light_pollution_tile(z: int, x: int, y: int) -> Response:
    """
    Dynamic tile endpoint — samples the VIIRS GeoTIFF and returns a PNG tile.

    Tile coordinate system: XYZ (Slippy Map) — same as OpenStreetMap.
    Callers fetch tiles via: /api/light_pollution/tiles/{z}/{x}/{y}.png
    """
    if analyzer is None or analyzer._src is None:
        return _empty_tile()

    # Check cache
    cache_key = f"{z}/{x}/{y}"
    cached = _tile_cache.get(cache_key)
    if cached is not None:
        return Response(cached, mimetype="image/png", headers={"Cache-Control": "public, max-age=3600"})

    src = analyzer._src

    # Get tile geographic bounds
    north, south, east, west = _tile_bounds(x, y, z)

    # Clamp to valid latitude range
    north = min(north, 90.0)
    south = max(south, -90.0)

    # Quick rejection: no overlap with GeoTIFF coverage
    if west > src.bounds.right or east < src.bounds.left or south > src.bounds.top or north < src.bounds.bottom:
        return _empty_tile()

    # Clamp bounds to GeoTIFF extent to avoid edge reads
    west = max(west, float(src.bounds.left))
    east = min(east, float(src.bounds.right))
    south = max(south, float(src.bounds.bottom))
    north = min(north, float(src.bounds.top))

    try:
        # Convert geographic bounds to pixel coordinates
        # src.index(lon, lat) → (row, col)
        # row = vertical (latitude, 0=top/north), col = horizontal (longitude, 0=left/west)
        row_nw, col_nw = src.index(west, north)  # NW corner of tile
        row_se, col_se = src.index(east, south)  # SE corner of tile

        # Row increases southward, col increases eastward
        row_start = min(row_nw, row_se)
        row_end = max(row_nw, row_se) + 1
        col_start = min(col_nw, col_se)
        col_end = max(col_nw, col_se) + 1

        # Clamp to raster dimensions
        row_start = max(0, row_start)
        row_end = min(int(src.height), row_end)
        col_start = max(0, col_start)
        col_end = min(int(src.width), col_end)

        if row_end <= row_start or col_end <= col_start:
            return _empty_tile()

        # Read window with decimation to tile size
        data = src.read(
            1,
            window=((row_start, row_end), (col_start, col_end)),
            out_shape=(_TILE_SIZE, _TILE_SIZE),
        )

        # Build RGBA tile
        lut = _build_tile_cmap_lut()

        # Determine valid pixels (not nodata, not NaN)
        if data.dtype.kind == "f":
            valid = ~np.isnan(data)
        else:
            valid = np.ones_like(data, dtype=bool)

        nodata = src.nodata
        if nodata is not None:
            valid = valid & (data != nodata)

        # Add skyglow correction to compensate for VIIRS background subtraction
        # The skyglow model diffuses city lights to simulate atmospheric scattering
        if hasattr(analyzer, "get_skyglow_for_window") and analyzer._skyglow_grid is not None:
            sg = analyzer.get_skyglow_for_window(west, east, south, north, (_TILE_SIZE, _TILE_SIZE))
            data = data.astype(np.float32) + analyzer._skyglow_weight * sg

        # Calculate intensity using same formula as brightness_to_intensity:
        # intensity = 1.0 - 1.0/(1.0 + radiance * 0.1), capped at 1.0
        with np.errstate(divide="ignore", invalid="ignore"):
            intensity = np.where(valid, data, 0.0)
            intensity = np.minimum(1.0, 1.0 - 1.0 / (1.0 + intensity * 0.1))

        # Map through lookup table
        idx = np.clip((intensity * 255).astype(np.uint8), 0, 255)
        rgba = lut[idx].copy()
        rgba[~valid] = (0, 0, 0, 0)

        # Encode as PNG
        img = Image.fromarray(rgba, "RGBA")
        buf = BytesIO()
        img.save(buf, format="PNG")
        png_data = buf.getvalue()

        # Cache (limit size)
        _tile_cache[cache_key] = png_data
        if len(_tile_cache) > _MAX_TILE_CACHE:
            _tile_cache.clear()

        return Response(png_data, mimetype="image/png", headers={"Cache-Control": "public, max-age=3600"})

    except Exception as e:
        print(f"⚠️ Tile render error ({z}/{x}/{y}): {e}")
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
    # 使用Haversine公式计算距离
    R = 6371  # 地球半径（公里）

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_pollution_level_description(bortle: int) -> str:
    """
    根据波特尔等级获取描述

    Args:
        bortle: 波特尔等级 (1-9)

    Returns:
        等级描述
    """
    descriptions = {
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
    return descriptions.get(bortle, "未知等级")


def brightness_to_bortle(brightness: int) -> int:
    """
    将亮度值转换为波特尔等级

    Args:
        brightness: 亮度值 (0-255)

    Returns:
        波特尔等级 (1-9)
    """
    # 将0-255的亮度值映射到1-9的波特尔等级
    # 亮度越高，光污染越严重，波特尔等级越高
    if brightness <= 28:  # 0-28
        return 1
    elif brightness <= 56:  # 29-56
        return 2
    elif brightness <= 84:  # 57-84
        return 3
    elif brightness <= 112:  # 85-112
        return 4
    elif brightness <= 140:  # 113-140
        return 5
    elif brightness <= 168:  # 141-168
        return 6
    elif brightness <= 196:  # 169-196
        return 7
    elif brightness <= 224:  # 197-224
        return 8
    else:  # 225-255
        return 9


def bortle_to_sqm(bortle: int) -> float:
    """
    将波特尔等级转换为SQM值（每平方角秒星等）
    根据标准的波特尔-SQM对应关系

    Args:
        bortle: 波特尔等级 (1-9)

    Returns:
        SQM值
    """
    # 波特尔等级与SQM值的标准对应关系
    sqm_values = {
        1: 21.9,  # 优秀暗空 (21.7-22.0)
        2: 21.6,  # 典型暗空 (21.5-21.6)
        3: 21.3,  # 乡村天空 (21.3-21.4)
        4: 20.4,  # 乡村/郊区过渡 (20.4-21.2)
        5: 19.5,  # 郊区天空 (19.1-20.3)
        6: 18.5,  # 明亮郊区 (18.0-19.0)
        7: 17.5,  # 郊区/城市过渡 (17.0-18.0)
        8: 16.5,  # 城市天空 (16.0-17.0)
        9: 15.5,  # 内城天空 (<16.0)
    }
    return sqm_values.get(bortle, 20.0)


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
        # 获取查询参数
        north = float(request.args.get("north", 0))
        south = float(request.args.get("south", 0))
        east = float(request.args.get("east", 0))
        west = float(request.args.get("west", 0))
        zoom = int(request.args.get("zoom", 10))

        print(f"🌍 Getting light pollution data: bounds=({south}, {west}) to ({north}, {east}), zoom={zoom}")

        # 根据缩放级别确定网格分辨率
        if zoom <= 8:
            grid_resolution = 0.1  # 低缩放级别，粗网格
        elif zoom <= 12:
            grid_resolution = 0.05  # 中等缩放级别
        elif zoom <= 16:
            grid_resolution = 0.02  # 高缩放级别
        else:
            grid_resolution = 0.01  # 非常高缩放级别，细网格

        # 计算网格范围
        lat_range = north - south
        lng_range = east - west
        grid_rows = max(1, int(lat_range / grid_resolution))
        grid_cols = max(1, int(lng_range / grid_resolution))

        # 限制最大网格数量以避免性能问题
        max_points = 2000
        total_points = grid_rows * grid_cols

        if total_points > max_points:
            # 调整网格分辨率
            scale_factor = math.sqrt(max_points / total_points)
            grid_rows = max(1, int(grid_rows * scale_factor))
            grid_cols = max(1, int(grid_cols * scale_factor))
            print(f"⚠️ Too many grid points, adjusted to {grid_rows}x{grid_cols} = {grid_rows * grid_cols} points")

        print(f"🔢 Generating grid: {grid_rows}x{grid_cols} = {grid_rows * grid_cols} points")

        # 批量构建坐标列表，一次性查询
        coordinates_list = []
        grid_info = []  # (lat, lng) per point
        for row in range(grid_rows):
            for col in range(grid_cols):
                lat = south + (row + 0.5) * (lat_range / grid_rows)
                lng = west + (col + 0.5) * (lng_range / grid_cols)
                coordinates_list.append((lat, lng))
                grid_info.append((lat, lng))

        # 一次性批量查询（按行读取 GeoTIFF，效率远高于逐点读取）
        batch_results = analyzer.batch_analyze_coordinates(coordinates_list)

        data = []
        for idx, result in enumerate(batch_results):
            lat, lng = grid_info[idx]
            pollution_info = result.get("pollution_info")

            if pollution_info:
                # 从批量查询结果中提取信息
                brightness = pollution_info.brightness
                bortle = brightness_to_bortle(brightness)
                sqm = bortle_to_sqm(bortle)
                intensity = brightness / 255.0

                data.append(
                    {
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
                )
            else:
                data.append(
                    {
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
                )

        print(f"✅ Successfully retrieved {len(data)} light pollution data points")

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

    except Exception as e:
        print(f"❌ Error getting light pollution data: {e}")
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

        print(f"Getting light pollution image data: North{north}° South{south}° East{east}° West{west}°")

        # GeoTIFF 后端不支持图片提取，返回空数据
        processed_data = []
        print("⚠️ GeoTIFF backend does not support image extraction")
        print("✅ Returned 0 light pollution images")

        return jsonify(
            {
                "success": True,
                "count": len(processed_data),
                "images": processed_data,
                "query_bounds": {"north": north, "south": south, "east": east, "west": west},
            }
        )

    except Exception as e:
        print(f"❌ Error getting light pollution image data: {e}")
        import traceback

        traceback.print_exc()
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

        print(f"🎯 Analyzing coordinate point: ({lat}, {lng})")

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

            print(f"✅ Successfully analyzed coordinate point: Bortle class={bortle}, SQM={sqm:.1f}")
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

            print(f"⚠️ No data found for coordinate point ({lat}, {lng}), using default values")
            return jsonify(result)

    except ValueError as e:
        return jsonify({"error": "无效的坐标参数", "success": False, "details": str(e)}), 400

    except Exception as e:
        print(f"❌ Error analyzing coordinate point: {e}")
        return jsonify({"error": str(e), "success": False}), 500


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
        # 根据请求方法获取参数
        if request.method == "POST":
            # POST请求从JSON body获取参数
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "Missing JSON data", "message": "缺少JSON数据"}), 400

            bbox = data.get("bbox", {})
            south = float(bbox.get("south", 0))
            west = float(bbox.get("west", 0))
            north = float(bbox.get("north", 0))
            east = float(bbox.get("east", 0))
            max_locations = int(data.get("max_locations", 30))
            min_height_diff = float(data.get("min_height_diff", 100.0))
            road_radius_km = float(data.get("road_radius_km", 10.0))
            network_type = data.get("network_type", "drive")
        else:
            # GET请求从URL参数获取
            south = float(request.args.get("south", 0))
            west = float(request.args.get("west", 0))
            north = float(request.args.get("north", 0))
            east = float(request.args.get("east", 0))
            max_locations = int(request.args.get("max_locations", 30))
            min_height_diff = float(request.args.get("min_height_diff", 100.0))
            road_radius_km = float(request.args.get("road_radius_km", 10.0))
            network_type = request.args.get("network_type", "drive")

        print(f"Analyzing stargazing area: North{north}° South{south}° East{east}° West{west}°")

        # 获取 GeoTIFF 文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        geotiff_path = os.path.join(project_root, "src/light_pollution/resources/viirs_china_2025.tif")

        # Get DB config from environment variable
        db_config_path = os.environ.get("STARGAZING_DB_CONFIG")
        if db_config_path:
            print(f"Using DB config from: {db_config_path}")

        # 调用分析函数
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

        # 转换为JSON格式
        locations_data = []
        for loc in locations:
            loc_dict = {
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
            locations_data.append(loc_dict)

        print(f"✅ Successfully analyzed {len(locations_data)} stargazing locations")

        return jsonify(
            {
                "success": True,
                "count": len(locations_data),
                "locations": locations_data,
                "bounds": {"south": south, "west": west, "north": north, "east": east},
            }
        )

    except Exception as e:
        print(f"❌ Stargazing area analysis failed: {e}")
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
    print("🚀 Starting light pollution data API server...")
    print("📡 API endpoints:")
    print("  - GET /api/light_pollution         - Get light pollution data (JSON)")
    print("  - GET /api/light_pollution/tiles/{z}/{x}/{y}.png  - Dynamic raster tiles")
    print("  - GET /api/coordinate_analysis     - Analyze single coordinate point")
    print("  - GET/POST /api/analyze_stargazing_area - Analyze stargazing area")
    print("  - GET /api/health                  - Health check")
    print("🌐 Server address: http://localhost:5001")

    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
