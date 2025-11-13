import os
import sys

# 保证从项目根目录运行示例时可以导入 src 下模块
PROJECT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if PROJECT_SRC not in sys.path:
    sys.path.append(PROJECT_SRC)

from light_pollution.public_api import (
    init_light_pollution_analyzer,
    get_light_pollution_grid,
    get_light_pollution_images,
    analyze_coordinate,
)
from stargazing_analyzer.public_api import (
    init_stargazing_analyzer,
    analyze_area,
    analyze_area_simple,
)

def main():
    print("[demo] 初始化分析器...")
    lp = init_light_pollution_analyzer()
    sa = init_stargazing_analyzer()

    print("[demo] 单点坐标分析...")
    coord_res = analyze_coordinate(39.9042, 116.4074)
    print("[demo] result:", coord_res)

    print("[demo] 边界图片数据...")
    imgs = get_light_pollution_images(north=40.0, south=39.8, east=116.6, west=116.2)
    print("[demo] images count:", imgs['count'])

    print("[demo] 网格数据采样...")
    grid = get_light_pollution_grid(north=40.0, south=39.8, east=116.6, west=116.2, zoom=12)
    print("[demo] grid points:", grid['metadata']['total_points'])

    print("[demo] 区域分析(便捷函数)...")
    simple = analyze_area_simple(south=39.8, west=116.2, north=40.0, east=116.6, max_locations=10)
    print("[demo] simple count:", len(simple))

    print("[demo] 区域分析(高级函数)...")
    advanced = analyze_area((39.8, 116.2, 40.0, 116.6), max_locations=10, include_road_connectivity=False)
    print("[demo] advanced count:", len(advanced))


if __name__ == '__main__':
    main()
