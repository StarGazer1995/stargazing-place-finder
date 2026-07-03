"""Light-pollution data endpoints — grid sampling, coordinate analysis, images."""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from light_pollution.public_api import (
    _require_analyzer,
    analyze_coordinate,
    get_light_pollution_grid,
)

router = APIRouter(tags=["pollution"])


# ---------------------------------------------------------------------------
# GET /api/light_pollution
# ---------------------------------------------------------------------------


@router.get("/api/light_pollution")
async def get_light_pollution_data(
    north: float = Query(..., description="北边界纬度"),
    south: float = Query(..., description="南边界纬度"),
    east: float = Query(..., description="东边界经度"),
    west: float = Query(..., description="西边界经度"),
    zoom: int = Query(10, description="地图缩放级别"),
) -> dict:
    """返回指定地图范围内的光污染网格采样数据。

    自动根据缩放级别计算网格分辨率，上限 2000 个采样点。
    """
    # Ensure analyzer is initialised
    try:
        await asyncio.to_thread(_require_analyzer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="光污染分析器未初始化") from exc

    result = await asyncio.to_thread(
        get_light_pollution_grid,
        north=north,
        south=south,
        east=east,
        west=west,
        zoom=zoom,
    )
    return result


# ---------------------------------------------------------------------------
# GET /api/light_pollution_images  (deprecated — always returns empty)
# ---------------------------------------------------------------------------


@router.get("/api/light_pollution_images")
async def get_light_pollution_images(
    north: Optional[float] = Query(None),
    south: Optional[float] = Query(None),
    east: Optional[float] = Query(None),
    west: Optional[float] = Query(None),
) -> dict:
    """获取光污染图片数据（已废弃，GeoTIFF 后端不支持图片提取）。

    保留此端点以维持向后兼容，始终返回空的 images 数组。
    """
    # Validate required params like the old Flask endpoint did
    if any(p is None for p in [north, south, east, west]):
        raise HTTPException(status_code=400, detail="缺少必需的参数: north, south, east, west")

    if not (-90 <= (north or 0) <= 90) or not (-90 <= (south or 0) <= 90):
        raise HTTPException(status_code=400, detail="纬度必须在-90到90之间")
    if not (-180 <= (east or 0) <= 180) or not (-180 <= (west or 0) <= 180):
        raise HTTPException(status_code=400, detail="经度必须在-180到180之间")
    if (north or 0) <= (south or 0):
        raise HTTPException(status_code=400, detail="北边界必须大于南边界")

    return {
        "success": True,
        "count": 0,
        "images": [],
        "query_bounds": {
            "north": north,
            "south": south,
            "east": east,
            "west": west,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/coordinate_analysis
# ---------------------------------------------------------------------------


@router.get("/api/coordinate_analysis")
async def get_coordinate_analysis(
    lat: float = Query(..., description="纬度"),
    lng: float = Query(..., description="经度"),
) -> dict:
    """分析单个坐标点的光污染指标（波特尔等级、SQM、辐射度）。"""
    # Validate coordinates
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail="无效的坐标参数")
    if not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="无效的坐标参数")

    # Ensure analyzer is initialised
    try:
        await asyncio.to_thread(_require_analyzer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="光污染分析器未初始化") from exc

    result = await asyncio.to_thread(analyze_coordinate, lat=lat, lng=lng)
    return result
