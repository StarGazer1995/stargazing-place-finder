# 道路连通性检测指南

本指南介绍如何在观星地点查找项目中使用道路连通性检测功能，帮助筛选出既有良好观星条件又能够通过道路到达的地点。

## 功能概述

道路连通性检测功能可以：
- 快速判断指定坐标是否有道路可达
- 批量检测多个候选地点的可达性
- 支持不同的交通方式（驾车、步行、骑行）
- 提供详细的可达性分析信息

## 安装依赖

确保已安装必要的依赖包：

```bash
uv sync
```

或者只安装核心依赖：

```bash
uv sync --no-dev
```

## 快速开始

### 1. 使用 GeoCoordinate 模型

所有道路连通性接口统一使用 `GeoCoordinate` 模型，不再接收原始 `lat, lon` 参数：

```python
from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

# 构造坐标点
point = GeoCoordinate(latitude=40.3242, longitude=116.6312)  # 北京怀柔

checker = RoadConnectivityChecker(search_radius_km=10.0)

# 快速检测
is_accessible = checker.simple_road_check(point)
print(f"坐标可达性: {'可达' if is_accessible else '不可达'}")
```

### 2. 批量检测

```python
from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

checker = RoadConnectivityChecker(search_radius_km=10.0)

points = [
    GeoCoordinate(latitude=40.3242, longitude=116.6312),  # 北京怀柔
    GeoCoordinate(latitude=31.6270, longitude=121.3975),  # 上海崇明岛
    GeoCoordinate(latitude=30.0, longitude=125.0),        # 海上某点
]

results = checker.batch_check_accessibility(points)
for point, info in zip(points, results):
    status = "可达" if info.is_accessible else "不可达"
    print(f"({point.latitude}, {point.longitude}): {status}, 距道路 {info.distance_km:.2f} km")
```

### 3. 详细分析

```python
from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

checker = RoadConnectivityChecker(search_radius_km=10.0)

point = GeoCoordinate(latitude=40.3242, longitude=116.6312)
info = checker.get_accessibility_info(point)
print(f"可达性: {info.is_accessible}")
print(f"距离道路: {info.distance_km:.2f} km")
print(f"网络节点数: {info.node_count}")
print(f"最近道路节点: ({info.nearest_node_lat:.4f}, {info.nearest_node_lon:.4f})")
```

## 集成到观星地点查找流程

### 完整的筛选流程

```python
from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

def find_accessible_stargazing_spots(candidates):
    """
    筛选可达的观星地点
    
    Args:
        candidates: 候选地点列表，格式为 [{'lat': float, 'lon': float, 'score': float}, ...]
    
    Returns:
        list: 可达的观星地点列表
    """
    checker = RoadConnectivityChecker(search_radius_km=8.0)
    accessible_spots = []
    
    for candidate in candidates:
        point = GeoCoordinate(latitude=candidate['lat'], longitude=candidate['lon'])
        info = checker.get_accessibility_info(point)
        if info.is_accessible:
            candidate['road_accessible'] = True
            accessible_spots.append(candidate)
    
    # 按评分排序
    accessible_spots.sort(key=lambda x: x['score'], reverse=True)
    return accessible_spots

# 使用示例
candidates = [
    {'lat': 40.3242, 'lon': 116.6312, 'score': 0.85},
    {'lat': 40.4769, 'lon': 117.1230, 'score': 0.92},
    {'lat': 30.0, 'lon': 125.0, 'score': 0.95},  # 海上，不可达
]

accessible_spots = find_accessible_stargazing_spots(candidates)
print(f"找到 {len(accessible_spots)} 个可达的观星地点")
```

## 参数配置

### RoadConnectivityChecker 参数

- `search_radius_km`: 搜索半径（公里），默认 10.0。控制从目标点下载多大范围的道路网络
- `max_distance_to_road_km`: 到道路的最大可接受距离（公里），默认 0.2（200m）。超过此阈值视为"不可达"
  - 默认 200m 基于实际徒步携带装备的场景，避免筛选出需要长距离山路跋涉的地点
- `network_type`: 网络类型，可选 `'drive'`（驾车）、`'walk'`（步行）、`'bike'`（骑行），默认 `'drive'`

## 性能优化建议

### 1. 合理设置搜索半径

```python
# 城市地区：较小半径即可
checker = RoadConnectivityChecker(search_radius_km=3.0)

# 郊区或山区：需要较大半径
checker = RoadConnectivityChecker(search_radius_km=10.0)
```

### 2. 批量处理优先

```python
# 推荐：批量处理多个坐标（复用已下载的路网数据）
results = checker.batch_check_accessibility(points)

# 不推荐：逐个处理，每次独立下载路网
# for point in points:
#     result = checker.get_accessibility_info(point)
```

### 3. 缓存网络数据

```python
# RoadConnectivityChecker 内部复用已下载的路网缓存
# 同一实例的多次查询不会重复下载
checker = RoadConnectivityChecker(search_radius_km=10.0)
for point in points:
    info = checker.get_accessibility_info(point)
```

### 4. PostGIS 后端（生产环境推荐）

配置 PostGIS 数据库后，路网查询通过以下两种方式完成，彻底消除 OSMnx HTTP 下载：

| 查询方式 | 方法 | 数据来源 | 延迟 |
|---------|------|---------|------|
| 单点 kNN | `query_road_connectivity()` | `planet_osm_line` kNN 索引 | **~30ms** |
| 区域图查询 | `query_road_graph_by_bbox()` | `planet_osm_line` LINESTRING → NetworkX | **~15s/95km²** |

对比 OSMnx（单点 143s，区域易超时），PostGIS 路径有 **3000× 加速**。

```json
{
  "host": "192.168.1.8",
  "port": 5455,
  "database": "osm_db",
  "user": "postgres",
  "password": "your_password"
}
```

设置环境变量 `STARGAZING_DB_CONFIG=config/postgis_config.json` 即可启用。
`RoadConnectivityChecker.preload_network_for_bbox()` 和 `_get_road_network()` 会自动检测 PostGIS 可用性，
优先使用本地查询，仅在 PostGIS 不可用时回退到 OSMnx。

## 错误处理

### 常见错误及解决方案

1. **网络连接错误**
   - 确保网络连接正常
   - 检查是否被防火墙阻止
   - 首次查询需要下载 OSM 路网数据

2. **坐标超出范围**
   - 确保坐标在有效范围内（纬度：-90到90，经度：-180到180）

3. **无道路数据**
   - 某些偏远地区可能没有道路数据
   - 尝试增大搜索半径

### 错误处理示例

```python
from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

checker = RoadConnectivityChecker()
point = GeoCoordinate(latitude=40.3242, longitude=116.6312)

try:
    info = checker.get_accessibility_info(point)
    status = "可达" if info.is_accessible else "不可达"
    print(f"{status}，距道路 {info.distance_km:.2f} km")
except Exception as e:
    print(f"检测失败: {e}")
```

## 实际应用示例

查看 `examples/road_connectivity_example.py` 文件，其中包含了完整的使用示例，包括：

- 简单检测演示
- 详细分析演示
- 批量检测演示
- 集成到观星地点查找流程
- 结果保存和处理

运行示例：

```bash
uv run python examples/road_connectivity_example.py
```

## 注意事项

1. **数据来源**：道路数据来自 OpenStreetMap，数据质量可能因地区而异
2. **网络依赖**：首次查询某个区域时需要下载数据，需要网络连接
3. **性能考虑**：大范围或高精度查询可能较慢，建议合理设置参数；生产环境推荐使用 PostGIS 后端
4. **坐标系统**：使用 WGS84 坐标系统（GPS坐标）
5. **可达性阈值**：默认 200m（**0.2 km**），可通过 `max_distance_to_road_km` 调整

## 技术细节

### 工作原理

1. 优先通过 PostGIS kNN 查询最近道路（毫秒级），或从 `planet_osm_line` 构建 NetworkX 路网图
2. PostGIS 不可用时回退到 OSMnx 从 OpenStreetMap 下载路网
3. 查找距离目标坐标最近的道路节点
4. 计算目标坐标到最近道路的距离
5. 根据设定的阈值判断是否可达

### 依赖库

- **PostGIS**（推荐）: 用于生产环境的毫秒级路网查询
- **OSMnx**: 用于 PostGIS 不可用时的回退路网下载
- **NetworkX**: 用于图论计算和路径分析
- **GeoPandas**: 用于地理空间数据处理

## 扩展功能

### 自定义交通方式

```python
from models import GeoCoordinate
from road_connectivity.road_connectivity_checker import RoadConnectivityChecker

point = GeoCoordinate(latitude=40.3242, longitude=116.6312)

# 检测步行可达性
checker = RoadConnectivityChecker(network_type='walk')
info = checker.get_accessibility_info(point)

# 检测骑行可达性
checker = RoadConnectivityChecker(network_type='bike')
info = checker.get_accessibility_info(point)
```