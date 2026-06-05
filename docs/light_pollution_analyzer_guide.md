# 光污染分析器使用指南

## 概述

`LightPollutionAnalyzer` 是一个专门用于分析地理位置光污染强度的Python模块。该模块通过读取 VIIRS DNB 卫星年度复合辐射度 GeoTIFF 文件，能够根据地理坐标精确获取辐射度数值、波特尔暗空等级和污染等级信息。结合道路连通性检测功能，可以全面评估观星地点的质量。

## 主要功能

- 🌍 **地理坐标光污染查询**: 根据经纬度坐标获取精确的光污染信息
- 📡 **VIIRS DNB 数据**: 直接读取卫星辐射度（nW/cm²/sr），无需图片反解
- 📊 **波特尔等级分类**: 基于辐射度自动转换为波特尔暗空等级 (Bortle 1-9)
- 🚀 **批量分析**: 支持批量处理多个坐标点
- 💾 **智能缓存**: 内存缓存机制提升性能，避免重复读取 GeoTIFF
- 🗺️ **区域图像提取**: 获取指定地理边界内的光污染网格数据
- 🔍 **双线性插值**: 使用插值算法提供sub-pixel级别的精确值
- 🚗 **道路连通性检测**: 分析地点的道路可达性，确保推荐地点交通便利

## 安装和依赖

### 必需依赖

```python
import rasterio  # GeoTIFF 读取
import numpy as np
```

### 内部模块依赖

- `location_finder.LocationFinder`: 地理位置查找器
- `src.cache.cache_config`: 缓存配置管理

## 快速开始

### 基本使用

```python
from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer

# 初始化分析器（使用默认 VIIRS GeoTIFF 数据）
analyzer = LightPollutionAnalyzer(
    geotiff_path="src/light_pollution/resources/viirs_china_2025.tif"
)

# 查询单个坐标的光污染信息
latitude = 39.9042  # 北京天安门
longitude = 116.4074

result = analyzer.get_light_pollution_color(latitude, longitude)
if result:
    print(f"波特尔等级: {result['bortle']}")
    print(f"辐射度: {result.get('radiance', 'N/A')} nW/cm²/sr")
    print(f"亮度值: {result['brightness']}")
    print(f"污染等级: {result['pollution_level']}")
else:
    print("该坐标位置没有光污染数据")
```

### 批量分析

```python
# 准备坐标列表
coordinates = [
    (39.9042, 116.4074),  # 北京
    (31.2304, 121.4737),  # 上海
    (22.3193, 114.1694),  # 香港
]

# 批量分析
results = analyzer.batch_analyze_coordinates(coordinates)

for result in results:
    if result['success']:
        info = result['pollution_info']
        print(f"坐标 {result['coordinates']}: {info['pollution_level']}")
    else:
        print(f"坐标 {result['coordinates']}: 分析失败")
```

### 区域网格数据提取

```python
# 获取指定区域内的光污染网格数据
north, south = 40.0, 39.0
east, west = 117.0, 116.0

# 使用 get_light_pollution_grid 获取网格数据
from light_pollution.public_api import get_light_pollution_grid
grid_data = get_light_pollution_grid(north, south, east, west, zoom=10)

if grid_data['success']:
    print(f"数据点数: {grid_data['metadata']['total_points']}")
    for point in grid_data['data'][:3]:  # 显示前3个
        print(f"  波特尔: {point['bortle']}, SQM: {point['sqm']}")
```

## 详细API参考

### 类初始化

```python
LightPollutionAnalyzer(geotiff_path: Optional[Union[str, Path]] = None)
```

**参数:**
- `geotiff_path`: VIIRS GeoTIFF 文件的完整路径。为 None 时分析器未初始化，需调用 `load_geotiff()`。

**异常:**
- `FileNotFoundError`: GeoTIFF 文件不存在
- `ImportError`: rasterio 未安装

### 主要方法

#### get_light_pollution_color()

```python
get_light_pollution_color(latitude: float, longitude: float) -> Optional[Dict[str, Any]]
```

根据地理坐标获取光污染信息。

**参数:**
- `latitude`: 纬度 (-90 到 90)
- `longitude`: 经度 (-180 到 180)

**返回值:**
返回包含以下键的字典，如果未找到数据则返回None：

```python
{
    'rgb': (r, g, b),                    # RGB颜色值元组
    'hex': '#rrggbb',                    # 十六进制颜色值
    'brightness': int,                   # 亮度值 (0-255)
    'bortle': int,                       # 波特尔暗空等级 (1-9)
    'radiance': float,                   # VIIRS DNB 辐射度 (nW/cm²/sr)
    'pollution_level': str,              # 污染等级描述
    'overlay_name': str,                 # 对应的数据源名称
    'coordinates': {                     # 输入的坐标信息
        'latitude': float,
        'longitude': float
    }
}
```

#### batch_analyze_coordinates()

```python
batch_analyze_coordinates(coordinates_list: list) -> list
```

批量分析多个坐标的光污染信息。

**参数:**
- `coordinates_list`: 坐标列表，每个元素为 `(latitude, longitude)` 元组

**返回值:**
分析结果列表，每个元素包含：

```python
{
    'index': int,                        # 在输入列表中的索引
    'coordinates': (lat, lon),           # 坐标元组
    'pollution_info': dict or None,      # 光污染信息字典
    'success': bool,                     # 是否成功分析
    'error': str                         # 错误信息（仅在失败时）
}
```

#### get_light_pollution_images_in_bounds()

```python
get_light_pollution_images_in_bounds(north: float, south: float, 
                                   east: float, west: float) -> list
```

获取指定地理边界内的光污染图像数据。

**参数:**
- `north`: 北边界纬度
- `south`: 南边界纬度
- `east`: 东边界经度
- `west`: 西边界经度

**返回值:**
图像信息列表，每个元素包含：

```python
{
    'overlay': GroundOverlay,            # GroundOverlay对象
    'image_path': str,                   # 图像文件路径
    'image_data': str or None,           # base64编码的图像数据
    'bounds': {                          # 图像的地理边界
        'north': float,
        'south': float,
        'east': float,
        'west': float
    },
    'exists': bool,                      # 图像文件是否存在
    'name': str                          # 覆盖层名称
}
```

### 工具方法

#### get_statistics()

```python
get_statistics() -> Dict[str, Any]
```

获取分析器的统计信息，包括：
- 后端类型（geotiff）
- 数据文件路径
- GeoTIFF 元数据（波段数、坐标参考系）

#### get_metadata()

```python
get_metadata() -> Dict[str, Any]
```

获取已加载 GeoTIFF 的元数据。

#### close()

```python
close() -> None
```

关闭 GeoTIFF 文件句柄，释放资源。

## 光污染等级分类

分析器基于 VIIRS DNB 辐射度（nW/cm²/sr）自动转换为波特尔暗空等级 (Bortle Scale)：

| 辐射度范围 (nW/cm²/sr) | 波特尔等级 | 描述 | 观星条件 |
|---------|------|------|----------|
| ≤ 0 | Bortle 1 | 优秀暗空 | 银河清晰可见，深空天体观测极佳 |
| 0.01 – 0.5 | Bortle 2 | 典型暗空 | 银河结构明显 |
| 0.5 – 1.5 | Bortle 3 | 乡村天空 | 银河可见，部分光污染 |
| 1.5 – 4.0 | Bortle 4 | 乡村/郊区过渡 | 银河微弱可见 |
| 4.0 – 10.0 | Bortle 5 | 郊区天空 | 银河难以察觉 |
| 10.0 – 25.0 | Bortle 6 | 明亮郊区 | 银河不可见 |
| 25.0 – 60.0 | Bortle 7 | 郊区/城市过渡 | 严重光污染 |
| 60.0 – 150.0 | Bortle 8 | 城市天空 | 只能看到最亮星体 |
| > 150 | Bortle 9 | 内城天空 | 几乎无法观测 |

## 性能优化

### 缓存机制

分析器实现了内存缓存系统：

1. **GeoTIFF 数据**: 通过 rasterio 惰性读取，仅在查询时加载所需波段数据
2. **结果缓存**: 查询结果在分析器生命周期内缓存，避免重复计算

### 双线性插值

为了提供更精确的颜色值，分析器使用双线性插值算法计算sub-pixel位置的颜色，而不是简单的最近邻插值。

### 批量处理

使用 `batch_analyze_coordinates()` 方法可以更高效地处理多个坐标，因为它可以复用已加载的图像缓存。

## 错误处理

### 常见异常

- `FileNotFoundError`: GeoTIFF 文件不存在
- `ImportError`: rasterio 未安装

### 容错机制

- 当图像文件不存在时，返回默认的灰色值
- 当像素坐标超出图像范围时，使用边界像素值
- 双线性插值失败时，回退到最近邻插值

## 使用示例

### 完整示例：观星地点评估

```python
from light_pollution_analyzer import LightPollutionAnalyzer

def evaluate_stargazing_location(analyzer, lat, lon, location_name):
    """评估观星地点的光污染情况"""
    result = analyzer.get_light_pollution_color(lat, lon)
    
    if not result:
        print(f"{location_name}: 无光污染数据")
        return
    
    bortle = result.get('bortle', 'N/A')
    radiance = result.get('radiance', 0)
    
    print(f"\n=== {location_name} 光污染评估 ===")
    print(f"坐标: ({lat}, {lon})")
    print(f"辐射度: {radiance} nW/cm²/sr")
    print(f"波特尔等级: {bortle}")
    print(f"污染等级: {result['pollution_level']}")
    
    # 给出观星建议
    if bortle <= 2:
        recommendation = "🌟 强烈推荐！优秀的观星地点"
    elif bortle <= 4:
        recommendation = "⭐ 推荐，观星条件良好"
    elif bortle <= 6:
        recommendation = "👍 可以考虑，观星条件一般"
    else:
        recommendation = "❌ 不推荐，光污染严重"
    
    print(f"观星建议: {recommendation}")

# 使用示例
analyzer = LightPollutionAnalyzer(geotiff_path="src/light_pollution/resources/viirs_china_2025.tif")

# 评估多个地点
locations = [
    (40.3467, 116.8747, "密云水库"),
    (39.9042, 116.4074, "天安门广场"),
    (40.4319, 116.5704, "怀柔区"),
]

for lat, lon, name in locations:
    evaluate_stargazing_location(analyzer, lat, lon, name)
```

### 区域光污染热力图数据准备

```python
def prepare_heatmap_data(analyzer, bounds, grid_size=50):
    """为热力图准备网格数据"""
    north, south, east, west = bounds
    
    lat_step = (north - south) / grid_size
    lon_step = (east - west) / grid_size
    
    coordinates = []
    for i in range(grid_size):
        for j in range(grid_size):
            lat = south + i * lat_step
            lon = west + j * lon_step
            coordinates.append((lat, lon))
    
    # 批量分析
    results = analyzer.batch_analyze_coordinates(coordinates)
    
    # 整理数据
    heatmap_data = []
    for result in results:
        if result['success']:
            info = result['pollution_info']
            lat, lon = result['coordinates']
            heatmap_data.append({
                'lat': lat,
                'lon': lon,
                'brightness': info['brightness'],
                'rgb': info['rgb']
            })
    
    return heatmap_data

# 使用示例
bounds = (40.5, 39.5, 117.0, 116.0)  # 北京周边区域
heatmap_data = prepare_heatmap_data(analyzer, bounds)
print(f"生成了 {len(heatmap_data)} 个数据点")
```

## 最佳实践

1. **合理缓存**: 保持分析器实例复用，避免重复打开 GeoTIFF 文件
2. **批量处理**: 使用批量方法处理多个坐标以提高效率
3. **资源管理**: 处理完成后调用 `analyzer.close()` 释放 GeoTIFF 文件句柄
4. **错误处理**: 始终检查返回值是否为 None
5. **坐标验证**: 确保输入的坐标在 GeoTIFF 覆盖范围内

## 故障排除

### 常见问题

**Q: 返回None值**
- 检查坐标是否在 GeoTIFF 文件覆盖范围内
- 确认 GeoTIFF 文件是否存在
- 验证坐标格式是否正确

**Q: GeoTIFF 加载失败**
- 检查 rasterio 是否正确安装：`pip install rasterio`
- 验证 GeoTIFF 文件路径是否正确
- 确认文件格式是否有效（.tif / .tiff）

**Q: 内存使用过高**
- 定期调用 `clear_image_cache()`
- 考虑分批处理大量坐标
- 监控缓存大小

## 技术细节

### 坐标转换算法

分析器使用 rasterio 的 `index()` 方法将地理坐标转换为像素坐标：

```python
# 使用 rasterio 进行地理坐标到像素坐标的转换
row, col = self._src.index(longitude, latitude)
```

### 辐射度转换公式

VIIRS DNB 辐射度值（nW/cm²/sr）通过以下公式转换为 0-255 亮度值（向后兼容）：

```python
brightness = 255.0 * (1.0 - 1.0 / (1.0 + radiance * 0.1))
```

波特尔等级通过辐射量阈值直接映射，无需经过亮度中间值：

```python
def radiance_to_bortle(radiance: float) -> int:
    if radiance <= 0.0:   return 1  # 优秀暗空
    if radiance <= 0.5:   return 2  # 典型暗空
    if radiance <= 1.5:   return 3  # 乡村天空
    if radiance <= 4.0:   return 4  # 乡村/郊区过渡
    if radiance <= 10.0:  return 5  # 郊区天空
    if radiance <= 25.0:  return 6  # 明亮郊区
    if radiance <= 60.0:  return 7  # 郊区/城市过渡
    if radiance <= 150.0: return 8  # 城市天空
    return 9                        # 内城天空
```

### 道路连通性评分算法

道路连通性检测使用以下算法计算评分：

```python
def calculate_connectivity_score(nearest_road_distance, road_type):
    # 基础分数（满分100）
    base_score = 100
    
    # 根据最近道路距离扣分（每100米扣5分，最多扣50分）
    distance_penalty = min(50, (nearest_road_distance / 100) * 5)
    
    # 根据道路类型调整分数
    road_type_multiplier = {
        'highway': 1.0,      # 高速公路，不调整
        'primary': 0.9,      # 主干道，轻微降低
        'secondary': 0.8,    # 次干道，适度降低
        'tertiary': 0.7,     # 三级道路，明显降低
        'residential': 0.6,  # 居民区道路，大幅降低
        'track': 0.5,        # 小路，严重降低
        'path': 0.4,         # 小径，极大降低
        'none': 0.0          # 无道路，零分
    }
    
    multiplier = road_type_multiplier.get(road_type, 0.5)  # 默认为0.5
    
    # 计算最终得分
    final_score = (base_score - distance_penalty) * multiplier
    
    # 确保分数在0-100之间
    return max(0, min(100, final_score))
```

这个算法综合考虑了最近道路距离和道路类型，为观星地点提供全面的交通便利性评估。

## 扩展开发

### 自定义污染等级

可以通过继承类来自定义波特尔等级阈值：

```python
class CustomLightPollutionAnalyzer(LightPollutionAnalyzer):
    def _calculate_pollution_level(self, radiance: float) -> str:
        # 自定义分类逻辑
        if radiance < 0.3:
            return "极佳观星条件"
        elif radiance < 2.0:
            return "良好观星条件"
        else:
            return "不适合观星"
```

### 添加新的分析指标

可以扩展颜色信息提取方法：

```python
def get_extended_color_info(self, latitude, longitude):
    """获取扩展的颜色信息"""
    basic_info = self.get_light_pollution_color(latitude, longitude)
    if not basic_info:
        return None
    
    r, g, b = basic_info['rgb']
    
    # 添加更多指标
    extended_info = basic_info.copy()
    extended_info.update({
        'saturation': self._calculate_saturation(r, g, b),
        'hue': self._calculate_hue(r, g, b),
        'contrast': self._calculate_contrast(r, g, b),
    })
    
    return extended_info
```

### 自定义道路连通性检测

可以扩展道路连通性检测功能：

```python
class EnhancedRoadConnectivityChecker(RoadConnectivityChecker):
    def check_connectivity(self, latitude, longitude, max_distance=5000):
        """增强版道路连通性检测"""
        # 获取基础连通性信息
        basic_info = super().check_connectivity(latitude, longitude, max_distance)
        
        # 添加额外的连通性分析
        enhanced_info = basic_info.copy()
        
        # 检查多种交通方式
        transport_modes = ['driving', 'walking', 'cycling', 'public_transport']
        accessibility = {}
        
        for mode in transport_modes:
            accessibility[mode] = self._check_transport_mode(latitude, longitude, mode)
        
        enhanced_info['multi_modal_access'] = accessibility
        enhanced_info['best_transport_mode'] = self._determine_best_mode(accessibility)
        enhanced_info['parking_availability'] = self._check_parking(latitude, longitude)
        
        return enhanced_info
    
    def _check_transport_mode(self, lat, lon, mode):
        # 实现特定交通方式的检测逻辑
        pass
    
    def _determine_best_mode(self, accessibility_data):
        # 确定最佳交通方式
        pass
    
    def _check_parking(self, lat, lon):
        # 检查停车场可用性
        pass
```

---

*本指南涵盖了光污染分析器的主要功能和使用方法。如有问题或需要更多功能，请参考源代码或联系开发团队。*