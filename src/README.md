# KML解析器

这个模块提供了一个功能完整的KML文件解析器，专门用于解析包含地面覆盖层(GroundOverlay)的KML文件。主要用于处理暗光地图数据，帮助观星地点查找器项目分析光污染信息。

## 功能特点

- **完整的KML解析**: 支持解析标准KML格式文件
- **GroundOverlay提取**: 专门提取地面覆盖层信息，包括地理边界和图标数据
- **数据结构化**: 使用Python数据类(dataclass)提供清晰的数据结构
- **过滤功能**: 支持按名称模式和地理边界过滤数据
- **统计分析**: 提供数据统计和边界分析功能
- **错误处理**: 完善的异常处理机制

## 核心类

### KMLParser
主要的KML解析器类，负责解析KML文件并提取GroundOverlay信息。

**主要方法：**
- `parse()`: 解析KML文件，返回GroundOverlay列表
- `get_document_name()`: 获取KML文档名称
- `filter_by_name_pattern()`: 根据名称模式过滤覆盖层
- `filter_by_bounds()`: 根据地理边界过滤覆盖层
- `get_statistics()`: 获取统计信息

### LocationFinder
地理位置查找器类，基于KMLParser提供地理坐标查询功能。

**主要方法：**
- `find_overlay_by_coordinates(lat, lon)`: 根据坐标查找单个GroundOverlay
- `find_all_overlays_by_coordinates(lat, lon)`: 查找所有包含指定坐标的GroundOverlay
- `find_nearby_overlays(lat, lon, radius)`: 查找附近的GroundOverlay
- `get_overlay_info(lat, lon)`: 获取指定位置的详细覆盖层信息
- `get_statistics()`: 获取统计信息
- `reload_overlays()`: 重新加载覆盖层数据

### LightPollutionAnalyzer
光污染分析器类，基于LocationFinder提供光污染分析功能。

**主要方法：**
- `get_light_pollution_color(lat, lon)`: 根据经纬度坐标获取光污染颜色数值和等级
- `batch_analyze_coordinates(coordinates)`: 批量分析多个坐标的光污染情况
- `get_statistics()`: 获取分析器统计信息（包括缓存状态）
- `clear_image_cache()`: 清除图像缓存以释放内存
- `_get_pollution_level(brightness)`: 根据亮度值计算光污染等级
- `_geo_to_pixel(lat, lon, bounds, image_size)`: 地理坐标到像素坐标转换

### LightPollutionVisualizer
光污染可视化器类，用于对指定地点周围的光污染数据进行可视化处理，支持生成热力图、等高线图和散点图。

**主要方法：**
- `create_heatmap(center_lat, center_lon, radius_km)`: 生成光污染热力图
- `create_contour_map(center_lat, center_lon, radius_km)`: 生成光污染等高线图
- `create_scatter_plot(center_lat, center_lon, radius_km)`: 生成光污染散点图
- `create_comprehensive_report(center_lat, center_lon, radius_km)`: 生成综合分析报告
- `get_statistics()`: 获取可视化器的统计信息

### LightPollutionMap
光污染地图可视化器类，用于在真实地图上展示光污染数据。

**主要方法：**
- `create_heatmap()`: 生成交互式热力图地图
- `create_marker_map()`: 生成标记点地图
- `create_cluster_map()`: 生成聚类地图
- `create_comprehensive_map()`: 生成综合地图报告
- `get_statistics()`: 获取统计信息

### 数据类
- `GroundOverlay`: 地面覆盖层数据
- `LatLonBox`: 地理边界框
- `Icon`: 图标信息

## 使用示例

### KMLParser 基础使用

```python
from kml_parser import KMLParser

# 创建解析器
parser = KMLParser('path/to/your/file.kml')

# 解析文件
overlays = parser.parse()

# 获取统计信息
stats = parser.get_statistics(overlays)
print(f"总共找到 {stats['count']} 个地面覆盖层")
```

### LightPollutionAnalyzer 光污染分析

```python
from src import LightPollutionAnalyzer

# 初始化光污染分析器
analyzer = LightPollutionAnalyzer('world_atlas/doc.kml')

# 分析单个坐标的光污染情况
beijing_lat, beijing_lon = 39.9042, 116.4074
pollution_info = analyzer.get_light_pollution_color(beijing_lat, beijing_lon)
if pollution_info:
    print(f"北京光污染信息:")
    print(f"  RGB颜色: {pollution_info['rgb']}")
    print(f"  十六进制颜色: {pollution_info['hex']}")
    print(f"  亮度值: {pollution_info['brightness']}/255")
    print(f"  污染等级: {pollution_info['pollution_level']}")
    print(f"  覆盖层: {pollution_info['overlay_name']}")

# 批量分析多个坐标
coordinates = [
    (39.9042, 116.4074),  # 北京
    (31.2304, 121.4737),  # 上海
    (22.3193, 114.1694),  # 香港
]

results = analyzer.batch_analyze_coordinates(coordinates)
for result in results:
    lat, lon = result['coordinates']
    if result['success'] and result['pollution_info']:
        info = result['pollution_info']
        print(f"坐标 ({lat}, {lon}): 亮度={info['brightness']}, {info['pollution_level']}")
    else:
        error_msg = result.get('error', '未找到数据')
        print(f"坐标 ({lat}, {lon}): {error_msg}")

# 获取分析器统计信息
stats = analyzer.get_statistics()
print(f"覆盖层数量: {stats['count']}")
print(f"缓存的图像数量: {stats['cached_images']}")
print(f"图像目录是否存在: {stats['images_directory_exists']}")

# 清除缓存以释放内存
analyzer.clear_image_cache()

### LightPollutionVisualizer 光污染可视化

```python
from src import LightPollutionVisualizer

# 初始化可视化器
visualizer = LightPollutionVisualizer('world_atlas/doc.kml')

# 生成北京周围10km范围的热力图
heatmap_result = visualizer.create_heatmap(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    save_path='beijing_heatmap.png'
)
print(f"热力图生成结果: {heatmap_result}")

# 生成等高线图
contour_result = visualizer.create_contour_map(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    save_path='beijing_contour.png'
)
print(f"等高线图生成结果: {contour_result}")

# 生成散点图
scatter_result = visualizer.create_scatter_plot(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    save_path='beijing_scatter.png'
)
print(f"散点图生成结果: {scatter_result}")

# 生成综合分析报告
report_results = visualizer.create_comprehensive_report(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    location_name='北京',
    output_dir='./visualization_output'
)
print(f"综合报告生成结果: {report_results}")

# 获取可视化器统计信息
vis_stats = visualizer.get_statistics()
print(f"可视化器统计: {vis_stats}")
```

### LightPollutionMap 地图可视化

```python
from src import LightPollutionMap

# 初始化地图可视化器
map_visualizer = LightPollutionMap('world_atlas/doc.kml')

# 生成交互式热力图地图
heatmap_result = map_visualizer.create_heatmap(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    save_path='beijing_heatmap.html'
)
print(f"热力图地图生成结果: {heatmap_result}")

# 生成标记点地图
marker_result = map_visualizer.create_marker_map(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    save_path='beijing_markers.html'
)
print(f"标记点地图生成结果: {marker_result}")

# 生成聚类地图
cluster_result = map_visualizer.create_cluster_map(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    save_path='beijing_cluster.html'
)
print(f"聚类地图生成结果: {cluster_result}")

# 生成综合地图报告
map_report_results = map_visualizer.create_comprehensive_map(
    center_lat=39.9042,
    center_lon=116.4074,
    radius_km=10.0,
    location_name='北京',
    output_dir='./map_output'
)
print(f"综合地图报告生成结果: {map_report_results}")

# 获取地图可视化器统计信息
map_stats = map_visualizer.get_statistics()
print(f"地图可视化器统计: {map_stats}")
```
```

### 性能优化说明

`LocationFinder` 类已经过性能优化，主要包括：

1. **统计信息缓存**: 避免重复计算边界和统计数据
2. **复用Parser方法**: 使用 `KMLParser` 的 `filter_by_bounds` 方法减少重复代码
3. **一次性加载**: 初始化时加载所有数据到内存，提高查询速度
4. **智能缓存管理**: 重新加载时自动清除缓存并重新计算

### 性能测试

运行性能测试脚本来验证优化效果：

```bash
# 运行性能测试
uv run python src/performance_test.py
```

测试结果示例：
- 初始化时间: ~0.017秒
- 统计信息获取: ~0.0000毫秒（缓存）
- 坐标查询: ~0.030毫秒/次
- 附近搜索: ~0.016毫秒/次

### LocationFinder 地理坐标查询

```python
from src import LocationFinder

# 初始化位置查找器
finder = LocationFinder('world_atlas/doc.kml')

# 根据坐标查找覆盖层
beijing_lat, beijing_lon = 39.9042, 116.4074
overlay = finder.find_overlay_by_coordinates(beijing_lat, beijing_lon)
if overlay:
    print(f"北京位置找到覆盖层: {overlay.name}")
    print(f"图标链接: {overlay.icon.href}")

# 查找所有重叠的覆盖层
all_overlays = finder.find_all_overlays_by_coordinates(beijing_lat, beijing_lon)
print(f"北京位置共有 {len(all_overlays)} 个覆盖层")

# 查找附近的覆盖层
nearby = finder.find_nearby_overlays(beijing_lat, beijing_lon, radius_degrees=2.0)
print(f"北京附近2度范围内有 {len(nearby)} 个覆盖层")

# 获取详细信息
info = finder.get_overlay_info(beijing_lat, beijing_lon)
print(f"位置详情: {info}")
```

### 过滤功能

```python
# 按名称模式过滤
brightness_overlays = parser.filter_by_name_pattern(overlays, "ArtificialSkyBrightness*.JPG")

# 按地理边界过滤（中国大陆区域）
china_overlays = parser.filter_by_bounds(overlays, 
                                        min_lat=18.0, max_lat=54.0,
                                        min_lon=73.0, max_lon=135.0)
```

### 访问数据

```python
for overlay in overlays[:5]:
    print(f"名称: {overlay.name}")
    print(f"图标: {overlay.icon.href}")
    print(f"边界: 北{overlay.lat_lon_box.north}, 南{overlay.lat_lon_box.south}")
    print(f"      东{overlay.lat_lon_box.east}, 西{overlay.lat_lon_box.west}")
```

## 运行示例

项目包含一个完整的使用示例：

```bash
# 从项目根目录运行
uv run python src/example_usage.py
```

这个示例会：
1. 解析 `world_atlas/doc.kml` 文件
2. 显示基本统计信息
3. 展示前5个GroundOverlay的详细信息
4. 演示过滤功能
5. 显示中国区域的覆盖层信息

## 数据结构

### GroundOverlay
```python
@dataclass
class GroundOverlay:
    name: str              # 覆盖层名称
    draw_order: int        # 绘制顺序
    color: str            # 颜色（十六进制）
    description: str      # 描述
    icon: Icon           # 图标信息
    lat_lon_box: LatLonBox  # 地理边界框
```

### LatLonBox
```python
@dataclass
class LatLonBox:
    north: float    # 北边界（纬度）
    south: float    # 南边界（纬度）
    east: float     # 东边界（经度）
    west: float     # 西边界（经度）
    rotation: float # 旋转角度
```

## 错误处理

解析器包含完善的错误处理：
- `FileNotFoundError`: 文件不存在
- `ValueError`: KML格式错误或解析失败
- 自动跳过无效的GroundOverlay元素

## 性能特点

- 使用XML ElementTree进行高效解析
- 支持大型KML文件（如示例中的731个覆盖层）
- 内存友好的流式处理
- 快速的地理边界过滤算法

## 应用场景

这个解析器特别适用于：
- 暗光地图数据处理
- 光污染分析
- 观星地点评估
- 地理信息系统(GIS)应用
- 卫星图像覆盖层管理