#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Tuple

from .public_api import analyze_area, analyze_area_simple, init_stargazing_analyzer


def _deg_per_km(lat: float) -> Tuple[float, float]:
    """
    计算纬度与经度每公里所对应的度数近似值

    Args:
        lat: 中心经度对应的纬度，用于经度的缩放

    Returns:
        (lat_deg_per_km, lon_deg_per_km) 的近似值
    """
    lat_deg_per_km = 1.0 / 111.0
    lon_deg_per_km = 1.0 / (111.0 * max(0.1, abs(__import__('math').cos(__import__('math').radians(lat)))) )
    return lat_deg_per_km, lon_deg_per_km


def _bbox_from_center(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    根据中心点与半径生成近似边界框 (south, west, north, east)

    Args:
        lat: 中心纬度
        lon: 中心经度
        radius_km: 半径（公里）

    Returns:
        (south, west, north, east) 边界框
    """
    import math
    lat_km, lon_km = _deg_per_km(lat)
    dlat = radius_km * lat_km
    dlon = radius_km * lon_km
    return (lat - dlat, lon - dlon, lat + dlat, lon + dlon)


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行解析器，支持中心坐标+半径或直接提供边界框

    Returns:
        已配置的 ArgumentParser 对象
    """
    parser = argparse.ArgumentParser(
        prog="stargazing-finder",
        description="Stargazing Place Finder - 综合观星地点分析 CLI"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--center", nargs=3, type=float, metavar=("LAT", "LON", "RADIUS_KM"),
                       help="使用中心点 (lat, lon) 及半径（公里）指定搜索区域")
    group.add_argument("--bbox", nargs=4, type=float, metavar=("SOUTH", "WEST", "NORTH", "EAST"),
                       help="直接提供边界框坐标 (south, west, north, east)")

    parser.add_argument("--max-locations", type=int, default=30, help="最大位置数量，默认 30")
    parser.add_argument("--network-type", type=str, default="drive", help="道路网络类型，默认 drive")
    parser.add_argument("--no-light-pollution", action="store_true", help="不计算光污染")
    parser.add_argument("--no-road-connectivity", action="store_true", help="不计算道路连通性")
    parser.add_argument("--db-config", type=str, help="数据库配置文件路径 (JSON/TOML)")

    parser.add_argument("--output", type=str, help="输出文件路径 (JSON)")
    parser.add_argument("--top-n", type=int, default=0, help="仅输出前 N 个推荐结果，0 表示全部")
    parser.add_argument("--verbose", "-v", action="store_true", help="开启详细输出")

    return parser


def main() -> None:
    """
    CLI 入口函数：解析参数并执行综合观星地点分析
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.center:
      lat, lon, radius = args.center
      bbox = _bbox_from_center(lat, lon, radius)
    else:
      south, west, north, east = args.bbox
      bbox = (south, west, north, east)

    include_lp = not args.no_light_pollution
    include_road = not args.no_road_connectivity

    if args.verbose:
        print("[cli] bbox:", bbox)
        print("[cli] include_light_pollution:", include_lp)
        print("[cli] include_road_connectivity:", include_road)
        print("[cli] max_locations:", args.max_locations)
        if args.db_config:
            print("[cli] db_config_path:", args.db_config)

    if args.db_config:
        init_stargazing_analyzer(db_config_path=Path(args.db_config))

    results = analyze_area(
        bbox=bbox,
        max_locations=args.max_locations,
        network_type=args.network_type,
        include_light_pollution=include_lp,
        include_road_connectivity=include_road,
    )

    if args.top_n and args.top_n > 0:
        results = results[:args.top_n]

    output_text = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
        if args.verbose:
            print("[cli] wrote:", args.output)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
