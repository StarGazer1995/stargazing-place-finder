# 光污染信息集成指南

## 概述

本指南详细介绍了如何在Stargazing Place Finder项目中使用光污染分析功能。光污染信息已完全集成到所有地点类型中，包括山峰、天文台和观景台。

## 功能特点

### 🌃 完整的光污染分析
- **实时分析**: 基于NASA光污染地图数据进行实时分析
- **多级分类**: 提供7个等级的光污染分类（Class 1-7+）
- **智能排序**: 自动按光污染程度排序，优先显示观星条件更好的地点
- **全面覆盖**: 支持山峰、天文台、观景台三种地点类型

### 📊 光污染等级说明

| 等级 | 描述 | 观星条件 | 亮度范围 |
|------|------|----------|----------|
| Class 1 | 极低污染 | 优秀观星条件 | 0-20 |
| Class 2 | 低度污染 | 良好观星条件 | 21-40 |
| Class 3 | 轻度污染 | 一般观星条件 | 41-80 |
| Class 4 | 中度污染 | 较差观星条件 | 81-120 |
| Class 5 | 重度污染 | 差观星条件 | 121-160 |
| Class 6 | 严重污染 | 很差观星条件 | 161-200 |
| Class 7+ | 极重污染 | 极差观星条件 | 201-255 |

## 使用方法

### 1. 基本使用

```python
from src.mountain_peak_finder import StarGazingPlaceFinder
from src.light_pollution_analyzer import LightPollutionAnalyzer

# 初始化光污染分析器
light_analyzer = LightPollutionAnalyzer("world_atlas/doc.xml")

# 初始化查找器并集成光污染分析
finder = StarGazingPlaceFinder(
    min_height_difference=100.0,
    light_pollution_analyzer=light_analyzer
)

# 查找包含光污染信息的地点
bbox = (39.5, 115.5, 40.5, 117.5)  # 北京周边
peaks = finder.find_peaks_in_area(bbox, max_peaks=10)
```

### 2. 查看光污染信息

```python
# 遍历查找结果
for peak in peaks:
    print(f"地点: {peak.name}")
    print(f"光污染等级: {peak.light_pollution_level}")
    print(f"坐标: ({peak.latitude:.4f}, {peak.longitude:.4f})")
    print(f"海拔: {peak.elevation:.1f}m")
    print()
```

### 3. 不同地点类型的使用

#### 山峰查找
```python
# 查找山峰（自动包含光污染信息）
peaks = finder.find_peaks_in_area(bbox, max_peaks=20)
for peak in peaks:
    if peak.light_pollution_level:
        print(f"{peak.name}: {peak.light_pollution_level}")
```

#### 天文台查找
```python
# 查找天文台（自动包含光污染信息）
observatories = finder.find_observatories_in_area(bbox, max_observatories=10)
for obs in observatories:
    print(f"{obs.name} ({obs.observatory_type}): {obs.light_pollution_level}")
```

#### 观景台查找
```python
# 查找观景台（自动包含光污染信息）
viewpoints = finder.find_viewpoints_in_area(bbox, max_viewpoints=15)
for vp in viewpoints:
    print(f"{vp.name} ({vp.viewpoint_type}): {vp.light_pollution_level}")
```

## 数据结构

### Location类字段

所有地点类型都使用统一的Location类，包含以下光污染相关字段：

```python
@dataclass
class Location:
    name: str
    latitude: float
    longitude: float
    elevation: float
    distance_to_nearest_town: float
    nearest_town_name: str
    location_type: str  # "mountain_peak", "observatory", "viewpoint"
    
    # 光污染相关字段
    light_pollution_level: Optional[str] = None  # 光污染等级描述
    
    # 其他可选字段...
```

### 光污染数据格式

光污染分析器返回的详细数据格式：

```python
{
    'rgb': (220, 24, 1),  # RGB颜色值
    'hex': '#dc1801',     # 十六进制颜色
    'brightness': 79,     # 亮度值 (0-255)
    'pollution_level': '轻度污染 (Class 3 - 一般观星条件)',
    'overlay_name': 'ArtificialSkyBrightness508.JPG',
    'coordinates': {
        'latitude': 40.9711269,
        'longitude': 117.9413161
    }
}
```

## 配置选项

### 光污染分析器配置

```python
# 使用自定义KML文件
light_analyzer = LightPollutionAnalyzer(
    kml_file_path="path/to/your/light_pollution.kml",
    image_base_path="path/to/images/"
)

# 不使用光污染分析器（将显示"未知污染等级"）
finder = StarGazingPlaceFinder(light_pollution_analyzer=None)
```

### 排序配置

光污染排序在`_sort_places_by_lightpollution`方法中自动进行：
- 优先显示光污染等级较低的地点
- 未知光污染等级的地点排在最后
- 保持原有的距离和海拔排序逻辑

## 最佳实践

### 1. 选择观星地点

```python
def find_best_stargazing_spots(bbox, max_results=10):
    """
    查找最佳观星地点
    """
    finder = StarGazingPlaceFinder(light_pollution_analyzer=light_analyzer)
    
    # 获取所有类型的地点
    all_locations = []
    all_locations.extend(finder.find_peaks_in_area(bbox, max_peaks=20))
    all_locations.extend(finder.find_observatories_in_area(bbox, max_observatories=10))
    all_locations.extend(finder.find_viewpoints_in_area(bbox, max_viewpoints=20))
    
    # 筛选低光污染地点
    good_spots = []
    for location in all_locations:
        if location.light_pollution_level:
            if "Class 1" in location.light_pollution_level or "Class 2" in location.light_pollution_level:
                good_spots.append(location)
    
    return good_spots[:max_results]
```

### 2. 光污染等级过滤

```python
def filter_by_pollution_level(locations, max_class=3):
    """
    按光污染等级过滤地点
    """
    filtered = []
    for location in locations:
        if location.light_pollution_level:
            # 提取等级数字
            if f"Class {max_class}" in location.light_pollution_level:
                class_num = int(location.light_pollution_level.split("Class ")[1].split(" ")[0].replace("+", ""))
                if class_num <= max_class:
                    filtered.append(location)
    return filtered
```

### 3. 生成观星报告

```python
def generate_stargazing_report(bbox):
    """
    生成包含光污染信息的观星报告
    """
    finder = StarGazingPlaceFinder(light_pollution_analyzer=light_analyzer)
    
    print("=== 观星地点分析报告 ===")
    print(f"搜索区域: {bbox}")
    print()
    
    # 分析各类地点
    for location_type, method_name, max_count in [
        ("山峰", "find_peaks_in_area", 10),
        ("天文台", "find_observatories_in_area", 5),
        ("观景台", "find_viewpoints_in_area", 10)
    ]:
        print(f"=== {location_type}分析 ===")
        
        method = getattr(finder, method_name)
        locations = method(bbox, **{f"max_{location_type.lower()}": max_count})
        
        if locations:
            # 按光污染等级分组
            pollution_groups = {}
            for loc in locations:
                level = loc.light_pollution_level or "未知"
                if level not in pollution_groups:
                    pollution_groups[level] = []
                pollution_groups[level].append(loc)
            
            for level, locs in pollution_groups.items():
                print(f"  {level}: {len(locs)}个地点")
                for loc in locs[:3]:  # 显示前3个
                    print(f"    - {loc.name} (海拔: {loc.elevation:.0f}m)")
        else:
            print(f"  未找到{location_type}")
        print()
```

## 故障排除

### 常见问题

1. **光污染信息显示为"未知"**
   - 检查KML文件路径是否正确
   - 确认图像文件是否存在
   - 验证坐标是否在覆盖范围内

2. **光污染分析器初始化失败**
   ```python
   try:
       light_analyzer = LightPollutionAnalyzer("world_atlas/doc.xml")
   except Exception as e:
       print(f"光污染分析器初始化失败: {e}")
       light_analyzer = None
   ```

3. **性能优化**
   - 使用适当的搜索范围
   - 限制返回结果数量
   - 启用缓存机制

### 调试模式

```python
# 启用调试模式查看详细信息
finder = StarGazingPlaceFinder(light_pollution_analyzer=light_analyzer)
locations = finder.get_viewpoints_from_overpass(bbox, debug=True)
```

## 示例脚本

项目提供了完整的示例脚本：
- `examples/light_pollution_demo.py` - 光污染功能演示
- `examples/robust_api_demo.py` - 包含错误处理的完整演示

运行示例：
```bash
cd /path/to/stargazing-place-finder
python examples/light_pollution_demo.py
```

## 更新日志

- **v1.2.0**: 完整集成光污染分析功能
  - 为所有地点类型添加光污染信息
  - 实现智能排序功能
  - 添加详细的光污染等级分类
  - 提供完整的API和示例

## 相关文档

- [统一Location类指南](unified_location_guide.md)
- [系统设计文档](mountain_peak_finder_system_design.md)
- [API使用指南](mountain_peak_finder_guide.md)