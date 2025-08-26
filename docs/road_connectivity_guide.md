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
pip install osmnx networkx geopandas
```

或者使用项目的依赖管理：

```bash
pip install -e .
```

## 快速开始

### 1. 简单检测

使用 `simple_road_checker.py` 进行快速检测：

```python
from src.simple_road_checker import quick_road_check

# 检测单个坐标
lat, lon = 40.3242, 116.6312  # 北京怀柔
is_accessible = quick_road_check(lat, lon)
print(f"坐标可达性: {'可达' if is_accessible else '不可达'}")
```

### 2. 批量检测

```python
from src.simple_road_checker import batch_road_check

# 批量检测多个候选地点
locations = [
    (40.3242, 116.6312),  # 北京怀柔
    (31.6270, 121.3975),  # 上海崇明岛
    (30.0, 125.0),        # 海上某点
]

results = batch_road_check(locations)
for (lat, lon), accessible in zip(locations, results):
    status = "可达" if accessible else "不可达"
    print(f"({lat}, {lon}): {status}")
```

### 3. 详细分析

使用 `road_connectivity_checker.py` 进行详细分析：

```python
from src.road_connectivity_checker import RoadConnectivityChecker

checker = RoadConnectivityChecker(search_radius_km=10.0)

# 获取详细的可达性信息
info = checker.get_accessibility_info(40.3242, 116.6312)
print(f"可达性: {info['accessible']}")
print(f"距离道路: {info['distance_to_road_km']:.2f} km")
print(f"网络节点数: {info['network_nodes_count']}")
```

## 集成到观星地点查找流程

### 完整的筛选流程

```python
from src.simple_road_checker import SimpleRoadChecker

def find_accessible_stargazing_spots(candidates):
    """
    筛选可达的观星地点
    
    Args:
        candidates: 候选地点列表，格式为 [{'lat': float, 'lon': float, 'score': float}, ...]
    
    Returns:
        list: 可达的观星地点列表
    """
    checker = SimpleRoadChecker(search_radius_km=8.0)
    accessible_spots = []
    
    for candidate in candidates:
        if checker.is_connected(candidate['lat'], candidate['lon']):
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

### SimpleRoadChecker 参数

- `search_radius_km`: 搜索半径（公里），默认5.0
- `max_distance_to_road_km`: 到道路的最大可接受距离（公里），默认2.0

### RoadConnectivityChecker 参数

- `search_radius_km`: 搜索半径（公里），默认10.0
- `max_distance_to_road_km`: 到道路的最大可接受距离（公里），默认5.0
- `network_type`: 网络类型，可选 'drive'（驾车）、'walk'（步行）、'bike'（骑行）

## 性能优化建议

### 1. 合理设置搜索半径

```python
# 城市地区：较小半径即可
checker = SimpleRoadChecker(search_radius_km=3.0)

# 郊区或山区：需要较大半径
checker = SimpleRoadChecker(search_radius_km=10.0)
```

### 2. 批量处理

```python
# 推荐：批量处理多个坐标
results = batch_road_check(coordinates)

# 不推荐：逐个处理
# for lat, lon in coordinates:
#     result = quick_road_check(lat, lon)
```

### 3. 缓存网络数据

```python
# 对于同一区域的多次查询，可以复用 RoadConnectivityChecker 实例
checker = RoadConnectivityChecker()
for candidate in candidates:
    result = checker.is_road_accessible(candidate['lat'], candidate['lon'])
```

## 错误处理

### 常见错误及解决方案

1. **网络连接错误**
   - 确保网络连接正常
   - 检查是否被防火墙阻止

2. **坐标超出范围**
   - 确保坐标在有效范围内（纬度：-90到90，经度：-180到180）

3. **无道路数据**
   - 某些偏远地区可能没有道路数据
   - 尝试增大搜索半径

### 错误处理示例

```python
try:
    result = quick_road_check(lat, lon)
except Exception as e:
    print(f"检测失败: {e}")
    result = False  # 默认为不可达
```

## 实际应用示例

查看 `road_connectivity_example.py` 文件，其中包含了完整的使用示例，包括：

- 简单检测演示
- 详细分析演示
- 批量检测演示
- 集成到观星地点查找流程
- 结果保存和处理

运行示例：

```bash
python src/road_connectivity_example.py
```

## 注意事项

1. **数据来源**：道路数据来自 OpenStreetMap，数据质量可能因地区而异
2. **网络依赖**：首次查询某个区域时需要下载数据，需要网络连接
3. **性能考虑**：大范围或高精度查询可能较慢，建议合理设置参数
4. **坐标系统**：使用 WGS84 坐标系统（GPS坐标）

## 技术细节

### 工作原理

1. 使用 OSMnx 从 OpenStreetMap 下载指定区域的道路网络
2. 构建道路网络图（NetworkX）
3. 查找距离目标坐标最近的道路节点
4. 计算目标坐标到最近道路的距离
5. 根据设定的阈值判断是否可达

### 依赖库

- **OSMnx**: 用于下载和处理 OpenStreetMap 数据
- **NetworkX**: 用于图论计算和路径分析
- **GeoPandas**: 用于地理空间数据处理

## 扩展功能

### 自定义交通方式

```python
# 检测步行可达性
checker = RoadConnectivityChecker()
info = checker.get_accessibility_info(lat, lon, network_type='walk')

# 检测骑行可达性
info = checker.get_accessibility_info(lat, lon, network_type='bike')
```

### 路径规划

```python
# 计算两点间的路径
from src.road_connectivity_checker import RoadConnectivityChecker

checker = RoadConnectivityChecker()
path_info = checker.get_route_info(start_lat, start_lon, end_lat, end_lon)
print(f"路径距离: {path_info['distance_km']:.2f} km")
print(f"预计时间: {path_info['travel_time_minutes']:.1f} 分钟")
```

这个功能可以帮助你在观星地点查找项目中有效地筛选出既有良好观星条件又能够实际到达的地点。