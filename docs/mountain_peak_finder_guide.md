# 山峰查找器使用指南

## 功能概述

山峰查找器是一个强大的工具，用于在指定地理坐标范围内查找与周围城镇有足够高度差的山峰。基于统一的Location数据模型，该工具现在支持山峰、天文台和观景台等多种地点类型。这个功能特别适用于：

- 🌟 **观星地点选择**：寻找远离城市光污染、海拔较高的观测点
- 🏔️ **登山路线规划**：发现具有挑战性的山峰
- 📊 **地理数据分析**：分析地形特征和城镇分布
- 🗺️ **户外活动规划**：寻找适合徒步、摄影的高地

## 核心功能

### 1. 智能山峰检测
- 基于OpenStreetMap数据获取山峰信息
- 支持自然山峰和火山的识别
- 自动获取海拔高度数据

### 2. 城镇距离分析
- 计算山峰到最近城镇的距离
- 分析高度差，筛选符合条件的山峰
- 支持多种居住地类型（城市、城镇、村庄等）

### 3. 灵活的搜索参数
- 可自定义最小高度差要求
- 可限制搜索结果数量
- 支持任意地理边界框搜索

## 数据模型说明

### 统一Location类

项目现在使用统一的Location类来表示所有类型的地理位置：

```python
from src.stargazing_place_finder import Location, Peak, Observatory, Viewpoint

# 直接使用Location类创建山峰
mountain = Location(
    name="泰山",
    latitude=36.2532,
    longitude=117.1011,
    elevation=1545.0,
    location_type="mountain_peak",  # 指定类型
    prominence=1545.0,
    distance_to_nearest_town=5.2,
    nearest_town_name="泰安市",
    height_difference=200.0
)

# 使用类型别名（向后兼容）
peak = Peak(
    name="华山",
    latitude=34.4749,
    longitude=110.0851,
    elevation=2154.9,
    location_type="mountain_peak",
    prominence=2154.9,
    distance_to_nearest_town=8.1,
    nearest_town_name="华阴市",
    height_difference=300.0
)

# 类型检查方法
print(mountain.is_mountain_peak())  # True
print(peak.is_observatory())        # False
```

## 快速开始

### 基本使用

```python
from src.stargazing_place_finder import find_peaks_with_height_difference

# 搜索北京周边与城镇有100米以上高度差的山峰
peaks = find_peaks_with_height_difference(
    south=39.5,    # 南边界
    west=115.5,    # 西边界  
    north=40.5,    # 北边界
    east=117.5,    # 东边界
    min_height_diff=100.0,  # 最小高度差（米）
    max_locations=20   # 最大搜索数量
)

# 显示结果
for peak in peaks:
    print(f"{peak.name}: 高度差 {peak.height_difference:.1f}m")
    print(f"类型: {peak.location_type}")
    print(f"是否为山峰: {peak.is_mountain_peak()}")
```

### 详细使用

```python
from src.stargazing_place_finder import StarGazingPlaceFinder, Location

# 创建查找器实例
finder = StarGazingPlaceFinder(min_height_difference=150.0)

# 定义搜索区域
bbox = (39.8, 115.8, 40.8, 117.2)  # (south, west, north, east)

# 执行搜索
peaks = finder.find_peaks_in_area(bbox, max_locations=15)

# 查看结果类型
for peak in peaks:
    print(f"{peak.name} - 类型: {peak.location_type}")
    print(f"是否为山峰: {peak.is_mountain_peak()}")

# 按类型过滤
mountain_peaks = [p for p in peaks if p.is_mountain_peak()]
print(f"找到 {len(mountain_peaks)} 个山峰")

# 保存结果
finder.save_results_to_json(peaks, "mountain_results.json")
```

## 实际应用示例

### 示例1：观星地点筛选

```python
# 查找适合观星的山峰（高海拔、远离城镇）
finder = StarGazingPlaceFinder(min_height_difference=200.0)
peaks = finder.find_peaks_in_area((40.0, 116.0, 40.5, 116.8))

# 筛选距离城镇较远的山峰
stargazing_peaks = [
    peak for peak in peaks 
    if peak.distance_to_nearest_town > 5.0  # 距离城镇5公里以上
]

for peak in stargazing_peaks:
    score = peak.height_difference + peak.distance_to_nearest_town * 10
    print(f"{peak.name} - 观星评分: {score:.1f}")
```

### 示例2：批量区域搜索

```python
# 搜索多个著名山区
regions = {
    "华山地区": (34.3, 109.8, 34.8, 110.3),
    "黄山地区": (29.8, 118.0, 30.5, 118.8),
    "泰山地区": (35.8, 116.8, 36.5, 117.5)
}

all_results = {}
for region_name, bbox in regions.items():
    finder = StarGazingPlaceFinder(min_height_difference=120.0)
    peaks = finder.find_peaks_in_area(bbox, max_locations=10)
    all_results[region_name] = peaks
    
    if peaks:
        best_peak = max(peaks, key=lambda p: p.height_difference)
        print(f"{region_name}最佳山峰: {best_peak.name}")
```

### 示例3：自定义筛选条件

```python
# 查找特定条件的山峰
finder = StarGazingPlaceFinder(min_height_difference=100.0)
peaks = finder.find_peaks_in_area((29.0, 110.0, 29.8, 110.8))

# 按不同标准筛选
high_peaks = [p for p in peaks if p.elevation > 1000]  # 海拔1000米以上
remote_peaks = [p for p in peaks if p.distance_to_nearest_town > 10]  # 距离城镇10公里以上
steep_peaks = [p for p in peaks if p.height_difference > 300]  # 高度差300米以上

print(f"高海拔山峰: {len(high_peaks)}个")
print(f"偏远山峰: {len(remote_peaks)}个")
print(f"陡峭山峰: {len(steep_peaks)}个")
```

## 参数配置

### StarGazingPlaceFinder 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `min_height_difference` | float | 100.0 | 与周围城镇的最小高度差（米） |

### find_peaks_in_area 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `bbox` | tuple | 边界框 (south, west, north, east) |
| `max_locations` | int | 最大搜索山峰数量，默认50 |

### 便捷函数参数

```python
find_peaks_with_height_difference(
    south: float,           # 南边界纬度
    west: float,            # 西边界经度
    north: float,           # 北边界纬度
    east: float,            # 东边界经度
    min_height_diff=100.0,  # 最小高度差（米）
    max_locations=50           # 最大搜索数量
)
```

## 返回数据结构

### Peak 对象属性

```python
@dataclass
class Peak:
    name: str                    # 山峰名称
    latitude: float              # 纬度
    longitude: float             # 经度
    elevation: float             # 海拔高度（米）
    prominence: float            # 相对高度（米）
    distance_to_nearest_town: float  # 到最近城镇距离（公里）
    nearest_town_name: str       # 最近城镇名称
    height_difference: float     # 与最近城镇高度差（米）
```

### JSON 输出格式

```json
{
  "search_criteria": {
    "min_height_difference": 100.0
  },
  "total_peaks_found": 5,
  "peaks": [
    {
      "name": "黄道岭",
      "latitude": 40.0189,
      "longitude": 116.1911,
      "elevation": 481.0,
      "height_difference": 346.0,
      "distance_to_nearest_town": 2.4,
      "nearest_town_name": "香山"
    }
  ]
}
```

## 性能优化建议

### 1. 合理设置搜索范围
- **小范围精确搜索**：0.1° × 0.1° 适合城市周边
- **中等范围搜索**：0.5° × 0.5° 适合省级区域
- **大范围概览**：1° × 1° 适合跨省搜索

### 2. 调整搜索参数
```python
# 城市周边：较低高度差要求
finder = StarGazingPlaceFinder(min_height_difference=50.0)

# 山区：较高高度差要求
finder = StarGazingPlaceFinder(min_height_difference=200.0)

# 高原地区：更高高度差要求
finder = StarGazingPlaceFinder(min_height_difference=500.0)
```

### 3. 批量处理优化
```python
# 避免频繁API调用
import time

for region in regions:
    peaks = finder.find_peaks_in_area(region)
    time.sleep(1)  # 添加延迟避免API限制
```

## 错误处理

### 常见问题及解决方案

1. **网络连接问题**
   ```python
   try:
       peaks = finder.find_peaks_in_area(bbox)
   except Exception as e:
       print(f"搜索失败: {e}")
       # 可以尝试减小搜索范围或稍后重试
   ```

2. **API限制**
   ```python
   # 添加重试机制
   import time
   
   for attempt in range(3):
       try:
           peaks = finder.find_peaks_in_area(bbox)
           break
       except Exception as e:
           if attempt < 2:
               time.sleep(5)  # 等待5秒后重试
           else:
               raise e
   ```

3. **数据质量问题**
   ```python
   # 过滤无效数据
   valid_peaks = [
       peak for peak in peaks 
       if peak.elevation > 0 and peak.height_difference > 0
   ]
   ```

## 集成到观星项目

### 与现有功能结合

```python
# 结合光污染分析和道路连通性检测
from src.light_pollution_analyzer import LightPollutionAnalyzer
from src.simple_road_checker import quick_road_check
from src.stargazing_place_finder import StarGazingPlaceFinder

def find_optimal_stargazing_peaks(bbox, min_height_diff=150.0):
    """
    综合分析找到最佳观星山峰
    """
    # 1. 查找山峰
    finder = StarGazingPlaceFinder(min_height_difference=min_height_diff)
    peaks = finder.find_peaks_in_area(bbox)
    
    # 2. 检查道路连通性
    accessible_peaks = []
    for peak in peaks:
        if quick_road_check(peak.latitude, peak.longitude):
            accessible_peaks.append(peak)
    
    # 3. 分析光污染（如果有相关数据）
    # light_analyzer = LightPollutionAnalyzer()
    # for peak in accessible_peaks:
    #     pollution_level = light_analyzer.get_pollution_level(
    #         peak.latitude, peak.longitude
    #     )
    #     peak.light_pollution = pollution_level
    
    # 4. 综合评分
    for peak in accessible_peaks:
        # 评分 = 高度差 + 距离城镇*10 + 海拔/100
        peak.stargazing_score = (
            peak.height_difference + 
            peak.distance_to_nearest_town * 10 + 
            peak.elevation / 100
        )
    
    # 按评分排序
    accessible_peaks.sort(key=lambda p: p.stargazing_score, reverse=True)
    
    return accessible_peaks

# 使用示例
best_peaks = find_optimal_stargazing_peaks((40.0, 116.0, 40.5, 116.8))
for i, peak in enumerate(best_peaks[:5], 1):
    print(f"{i}. {peak.name} - 评分: {peak.stargazing_score:.1f}")
```

## 技术细节

### 数据源
- **地理数据**：OpenStreetMap (Overpass API)
- **海拔数据**：Open-Elevation API
- **距离计算**：Haversine公式

### 依赖库
- `requests`：API请求
- `json`：数据处理
- `math`：地理计算
- `dataclasses`：数据结构

### API限制
- Overpass API：每次查询有超时限制（25秒）
- Open-Elevation API：建议添加请求间隔避免限制
- 网络依赖：需要稳定的互联网连接

## 扩展功能

### 1. 添加更多筛选条件
```python
class AdvancedMountainPeakFinder(StarGazingPlaceFinder):
    def filter_by_accessibility(self, peaks, max_distance_to_road=5.0):
        """按道路可达性筛选"""
        pass
    
    def filter_by_weather(self, peaks, weather_api_key):
        """按天气条件筛选"""
        pass
    
    def filter_by_season(self, peaks, season):
        """按季节适宜性筛选"""
        pass
```

### 2. 可视化功能
```python
def visualize_peaks_on_map(peaks, output_file="peaks_map.html"):
    """在地图上可视化山峰位置"""
    import folium
    
    # 创建地图
    center_lat = sum(p.latitude for p in peaks) / len(peaks)
    center_lon = sum(p.longitude for p in peaks) / len(peaks)
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # 添加山峰标记
    for peak in peaks:
        folium.Marker(
            [peak.latitude, peak.longitude],
            popup=f"{peak.name}<br>海拔: {peak.elevation}m<br>高度差: {peak.height_difference}m",
            icon=folium.Icon(color='red', icon='mountain')
        ).add_to(m)
    
    m.save(output_file)
    print(f"地图已保存到: {output_file}")
```

## 注意事项

1. **数据准确性**：OpenStreetMap数据质量因地区而异
2. **API稳定性**：外部API可能有访问限制或临时不可用
3. **搜索效率**：大范围搜索可能需要较长时间
4. **网络依赖**：功能需要稳定的网络连接
5. **坐标系统**：使用WGS84坐标系统（GPS标准）

## 常见用例

- 🌟 **天文观测**：寻找无光污染的高地观测点
- 🏔️ **登山徒步**：发现具有挑战性的登山目标
- 📸 **风景摄影**：寻找制高点拍摄位置
- 🗺️ **地理研究**：分析地形和城镇分布关系
- 🏕️ **户外露营**：寻找远离城镇的露营地点

通过合理使用这个工具，你可以高效地找到符合特定需求的山峰位置，为各种户外活动和科学观测提供有力支持。