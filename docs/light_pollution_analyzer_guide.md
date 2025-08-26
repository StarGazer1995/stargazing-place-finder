# 光污染分析器使用指南

## 概述

`LightPollutionAnalyzer` 是一个专门用于分析地理位置光污染强度的Python模块。该模块通过解析KML文件和对应的图像数据，能够根据地理坐标精确获取光污染颜色数值和污染等级信息。

## 主要功能

- 🌍 **地理坐标光污染查询**: 根据经纬度坐标获取精确的光污染信息
- 🎨 **颜色信息提取**: 从光污染图像中提取RGB颜色值和亮度信息
- 📊 **污染等级分类**: 自动计算并分类光污染等级（Class 1-7+）
- 🚀 **批量分析**: 支持批量处理多个坐标点
- 💾 **智能缓存**: 内存和磁盘双重缓存机制提升性能
- 🗺️ **区域图像提取**: 获取指定地理边界内的光污染图像数据
- 🔍 **双线性插值**: 使用插值算法提供sub-pixel级别的精确颜色值

## 安装和依赖

### 必需依赖

```python
from PIL import Image
import numpy as np
```

### 内部模块依赖

- `location_finder.LocationFinder`: 地理位置查找器
- `kml_parser.GroundOverlay`: KML文件解析器
- `cache_config.get_cache_dir`: 缓存配置管理

## 快速开始

### 基本使用

```python
from light_pollution_analyzer import LightPollutionAnalyzer

# 初始化分析器
analyzer = LightPollutionAnalyzer(
    kml_file_path="path/to/your/light_pollution.kml",
    images_base_path="path/to/images/folder"  # 可选，自动推断
)

# 查询单个坐标的光污染信息
latitude = 39.9042  # 北京天安门
longitude = 116.4074

result = analyzer.get_light_pollution_color(latitude, longitude)
if result:
    print(f"RGB颜色: {result['rgb']}")
    print(f"十六进制颜色: {result['hex']}")
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

### 区域图像数据提取

```python
# 获取指定区域内的光污染图像
north, south = 40.0, 39.0
east, west = 117.0, 116.0

image_data = analyzer.get_light_pollution_images_in_bounds(
    north, south, east, west
)

for img_info in image_data:
    print(f"图像名称: {img_info['name']}")
    print(f"文件存在: {img_info['exists']}")
    print(f"地理边界: {img_info['bounds']}")
    if img_info['image_data']:
        print(f"图像数据长度: {len(img_info['image_data'])} 字符")
```

## 详细API参考

### 类初始化

```python
LightPollutionAnalyzer(kml_file_path: str, images_base_path: Optional[str] = None)
```

**参数:**
- `kml_file_path`: KML文件的完整路径
- `images_base_path`: 图像文件基础路径，如果为None则自动推断为KML文件同目录下的`files`文件夹

**异常:**
- `FileNotFoundError`: KML文件不存在
- `ValueError`: KML文件格式错误

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
    'pollution_level': str,              # 污染等级描述
    'overlay_name': str,                 # 对应的覆盖层名称
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
- 基础统计信息（来自LocationFinder）
- 图像基础路径
- 缓存的图像数量
- 图像目录是否存在

#### clear_image_cache()

```python
clear_image_cache() -> None
```

清除所有图像缓存（内存和磁盘），用于释放内存空间。

## 光污染等级分类

分析器根据亮度值自动分类光污染等级：

| 亮度范围 | 等级 | 描述 | 观星条件 |
|---------|------|------|----------|
| 0-31 | Class 1 | 极低污染 | 优秀观星条件 |
| 32-63 | Class 2 | 低污染 | 良好观星条件 |
| 64-95 | Class 3 | 轻度污染 | 一般观星条件 |
| 96-127 | Class 4 | 中度污染 | 较差观星条件 |
| 128-159 | Class 5 | 重度污染 | 差观星条件 |
| 160-191 | Class 6 | 严重污染 | 很差观星条件 |
| 192+ | Class 7+ | 极重污染 | 极差观星条件 |

## 性能优化

### 缓存机制

分析器实现了两级缓存系统：

1. **内存缓存**: 将加载的图像保存在内存中，避免重复读取
2. **磁盘缓存**: 使用pickle序列化图像到磁盘，程序重启后仍可使用

### 双线性插值

为了提供更精确的颜色值，分析器使用双线性插值算法计算sub-pixel位置的颜色，而不是简单的最近邻插值。

### 批量处理

使用 `batch_analyze_coordinates()` 方法可以更高效地处理多个坐标，因为它可以复用已加载的图像缓存。

## 错误处理

### 常见异常

- `ValueError`: 坐标超出有效范围
- `FileNotFoundError`: KML文件或图像文件不存在
- `PIL.UnidentifiedImageError`: 图像文件格式不支持

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
    
    brightness = result['brightness']
    level = result['pollution_level']
    
    print(f"\n=== {location_name} 光污染评估 ===")
    print(f"坐标: ({lat}, {lon})")
    print(f"RGB颜色: {result['rgb']}")
    print(f"亮度值: {brightness}")
    print(f"污染等级: {level}")
    
    # 给出观星建议
    if brightness < 64:
        recommendation = "🌟 强烈推荐！优秀的观星地点"
    elif brightness < 128:
        recommendation = "⭐ 可以考虑，观星条件一般"
    else:
        recommendation = "❌ 不推荐，光污染严重"
    
    print(f"观星建议: {recommendation}")

# 使用示例
analyzer = LightPollutionAnalyzer("data/light_pollution.kml")

# 评估多个地点
locations = [
    (40.3467, 116.8747, "密云水库"),
    (39.9042, 116.4074, "天安门广场"),
    (40.4319, 116.5704, "怀柔区"),
]

for lat, lon, name in locations:
    evaluate_stargazing_location(analyzer, lat, lon, name)

# 清理缓存
analyzer.clear_image_cache()
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

1. **合理使用缓存**: 对于大量查询，保持分析器实例以利用缓存
2. **批量处理**: 使用批量方法处理多个坐标以提高效率
3. **内存管理**: 处理完成后调用 `clear_image_cache()` 释放内存
4. **错误处理**: 始终检查返回值是否为None
5. **坐标验证**: 确保输入的坐标在有效范围内

## 故障排除

### 常见问题

**Q: 返回None值**
- 检查坐标是否在KML文件覆盖范围内
- 确认图像文件是否存在
- 验证坐标格式是否正确

**Q: 图像加载失败**
- 检查图像文件路径是否正确
- 确认图像文件格式是否支持（PNG, JPG等）
- 检查文件权限

**Q: 内存使用过高**
- 定期调用 `clear_image_cache()`
- 考虑分批处理大量坐标
- 监控缓存大小

## 技术细节

### 坐标转换算法

分析器使用线性映射将地理坐标转换为图像像素坐标：

```python
# 计算相对位置（0-1之间）
lat_ratio = (latitude - south) / (north - south)
lon_ratio = (longitude - west) / (east - west)

# 转换为像素坐标（注意Y轴翻转）
pixel_x = lon_ratio * image_width
pixel_y = (1 - lat_ratio) * image_height
```

### 亮度计算公式

使用标准的亮度计算公式：

```python
brightness = 0.299 * R + 0.587 * G + 0.114 * B
```

这个公式考虑了人眼对不同颜色的敏感度差异。

## 扩展开发

### 自定义污染等级

可以通过继承类来自定义污染等级分类：

```python
class CustomLightPollutionAnalyzer(LightPollutionAnalyzer):
    def _calculate_pollution_level(self, brightness: int) -> str:
        # 自定义分类逻辑
        if brightness < 50:
            return "极佳观星条件"
        elif brightness < 100:
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

---

*本指南涵盖了光污染分析器的主要功能和使用方法。如有问题或需要更多功能，请参考源代码或联系开发团队。*