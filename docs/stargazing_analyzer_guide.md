# 观星地点综合分析器使用指南

## 概述

`StargazingLocationAnalyzer` 是一个综合性的观星地点分析工具，它整合了山峰查找、光污染分析和道路连通性检测功能，为指定坐标范围内的山峰提供全面的观星适宜性分析。

## ⚠️ 重要提醒：光污染数据是强制要求

**光污染数据对于准确的观星地点评估至关重要**。没有光污染数据的分析结果准确性将大大降低。

### 为什么光污染数据如此重要？

1. **观星质量的决定因素**：光污染是影响观星效果的最重要因素之一
2. **评分准确性**：光污染评分占总评分的40%权重
3. **地点筛选**：帮助识别真正适合观星的暗夜区域
4. **科学依据**：提供基于实际光污染地图的客观评估

### 如何获取光污染数据

项目默认内置 **VIIRS DNB 2025** 中国区域 GeoTIFF 数据（`src/light_pollution/resources/viirs_china_2025.tif`），无需手动下载。

如需使用其他区域的 VIIRS 数据：

1. **EOG VIIRS VNL v2.2** (推荐)
   - 网址：https://eogdata.mines.edu/products/vnl/
   - 特点：NASA / NOAA 官方数据，年度复合辐射度
   - 下载方式：选择年份和区域后下载 GeoTIFF

2. **旧版 KML 后端**（向后兼容）
   - 可通过 `kml_file_path` 参数切换
   - 适用于已有 KML 数据的用户

## 核心功能

### 1. 山峰查找与筛选
- 基于OpenStreetMap数据查找指定区域内的山峰
- 计算山峰与周围城镇的高度差
- 筛选符合最小高度差要求的山峰

### 2. 光污染分析
- 基于 VIIRS DNB 卫星辐射度数据（GeoTIFF 格式）
- 计算每个山峰位置的波特尔暗空等级（Bortle 1-9）
- 提供辐射度、RGB颜色值和亮度信息

### 3. 道路连通性检测
- 检查山峰是否有道路可达
- 计算到最近道路的距离
- 支持不同交通方式（驾车、步行等）

### 4. 综合评分系统
- **高度差评分**（30%权重）：海拔优势
- **光污染评分**（40%权重）：暗夜条件
- **道路可达性评分**（20%权重）：交通便利性
- **海拔评分**（10%权重）：绝对海拔高度

## 快速开始

### 基础使用（有光污染数据）

```python
from stargazing_analyzer import StargazingLocationAnalyzer

# 初始化分析器（使用内置 VIIRS GeoTIFF 数据）
analyzer = StargazingLocationAnalyzer(
    min_height_difference=100.0,
    road_search_radius_km=10.0
)

# 分析指定区域（北京周边示例）
bbox = (39.5, 115.5, 40.5, 117.0)  # (south, west, north, east)
locations = analyzer.analyze_area(
    bbox=bbox,
    max_locations=20,
    include_light_pollution=True,
    include_road_connectivity=True
)

# 打印结果摘要
analyzer.print_summary(locations)

# 保存结果
analyzer.save_results(locations, "beijing_stargazing_spots.json")
```

### 便捷函数使用

```python
from stargazing_analyzer import analyze_stargazing_area

# 使用便捷函数进行快速分析（默认使用内置 VIIRS GeoTIFF 数据）
locations = analyze_stargazing_area(
    south=39.5, west=115.5, north=40.5, east=117.0,
    max_locations=15,
    min_height_diff=150.0
)

print(f"找到 {len(locations)} 个观星地点")
```

## 无光污染数据的影响

### 警告提示
当没有提供光污染数据时，系统会显示以下警告：

```
⚠️  警告: 未初始化光污染分析器
⚠️  光污染数据是观星地点分析的重要组成部分
⚠️  内置 VIIRS GeoTIFF 数据默认自动加载（中国区域）
⚠️  如需其他区域数据，请使用 geotiff_path 参数指定
```

### 评分影响
- 缺少光污染数据的地点评分会受到影响
- 推荐等级会标注"⚠️缺少光污染数据"
- 分析备注会包含数据缺失提醒

### 结果示例
```
推荐等级: 推荐 (⚠️缺少光污染数据)
分析备注: 海拔优势明显，比周围高245米; ⚠️ 缺少光污染数据，无法准确评估观星条件; 交通便利，有道路可达
```

## 参数配置

### 初始化参数

```python
analyzer = StargazingLocationAnalyzer(
    geotiff_path="src/light_pollution/resources/viirs_china_2025.tif",  # GeoTIFF 路径（可选，默认自动加载）
    min_height_difference=100.0,              # 最小高度差要求（米）
    road_search_radius_km=10.0                # 道路搜索半径（公里）
)
```

### 分析参数

```python
locations = analyzer.analyze_area(
    bbox=(south, west, north, east),          # 搜索边界框
    max_locations=20,                             # 最大山峰数量
    network_type='drive',                     # 网络类型：'drive', 'walk', 'bike'
    include_light_pollution=True,             # 是否包含光污染分析
    include_road_connectivity=True            # 是否包含道路连通性分析
)
```

## 返回数据结构

每个观星地点包含以下信息：

```python
class StargazingLocation:
    name: str                           # 地点名称
    latitude: float                     # 纬度
    longitude: float                    # 经度
    elevation: float                    # 海拔（米）
    height_difference: float            # 与周围城镇的高度差（米）
    
    # 光污染信息
    light_pollution_rgb: Optional[tuple]      # RGB颜色值
    light_pollution_hex: Optional[str]        # 十六进制颜色
    light_pollution_brightness: Optional[float] # 亮度值
    light_pollution_level: Optional[str]      # 污染等级
    light_pollution_overlay: Optional[str]    # 覆盖层名称
    
    # 道路连通性
    road_accessible: Optional[bool]           # 是否有道路可达
    nearest_road_distance: Optional[float]   # 到最近道路的距离（米）
    
    # 评分和推荐
    stargazing_score: Optional[float]        # 综合评分（0-100）
    recommendation_level: str                 # 推荐等级
    analysis_notes: str                       # 分析备注
```

## 实际应用示例

### 1. 寻找北京周边观星地点

```python
# 北京周边山区
bbox = (39.5, 115.5, 40.5, 117.0)
locations = analyze_stargazing_area(
    south=39.5, west=115.5, north=40.5, east=117.0,
    max_locations=15,
    min_height_diff=150.0
)
```

### 2. 批量分析多个地区

```python
regions = {
    "华山地区": (34.3, 109.8, 34.7, 110.2),
    "泰山地区": (36.0, 116.8, 36.4, 117.2),
    "黄山地区": (29.9, 118.0, 30.3, 118.4)
}

all_results = {}
for region_name, bbox in regions.items():
    print(f"\n分析 {region_name}...")
    locations = analyze_stargazing_area(
        south=bbox[0], west=bbox[1], north=bbox[2], east=bbox[3],
        max_locations=10
    )
    all_results[region_name] = locations
```

### 3. 自定义评分权重

```python
# 对于更注重交通便利性的用户
analyzer = StargazingLocationAnalyzer(
    min_height_difference=50.0,    # 降低高度差要求
    road_search_radius_km=15.0     # 增加道路搜索范围
)
```

## 性能优化建议

1. **合理设置搜索范围**：避免过大的边界框
2. **限制山峰数量**：使用 `max_locations` 参数控制结果数量
3. **缓存光污染数据**：系统会缓存已加载的 GeoTIFF 数据
4. **批量处理**：对多个区域使用同一个分析器实例

## 错误处理

系统会自动处理以下错误情况：

1. **无效的边界框坐标**
2. **网络连接问题**
3. **GeoTIFF 文件读取错误**
4. **API调用失败**

## 集成到观星项目

### 与现有功能结合

```python
# 结合山峰查找器
from src.stargazing_place_finder import StarGazingPlaceFinder
from src.stargazing_location_analyzer import StargazingLocationAnalyzer

# 先用山峰查找器获取候选地点
mountain_finder = StarGazingPlaceFinder(min_height_difference=200.0)
peaks = mountain_finder.find_peaks_in_area((39.5, 115.5, 40.5, 117.0))

# 再用综合分析器进行详细评估（默认使用内置 GeoTIFF 数据）
analyzer = StargazingLocationAnalyzer()
detailed_analysis = analyzer.analyze_peaks(peaks)
```

### Web应用集成

```python
# Flask应用示例
from flask import Flask, request, jsonify

app = Flask(__name__)
analyzer = StargazingLocationAnalyzer()  # 默认使用内置 GeoTIFF 数据

@app.route('/api/analyze_stargazing', methods=['POST'])
def analyze_stargazing():
    data = request.json
    bbox = (data['south'], data['west'], data['north'], data['east'])
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_locations=data.get('max_locations', 20),
        include_light_pollution=True,
        include_road_connectivity=True
    )
    
    return jsonify([location.__dict__ for location in locations])
```

## 技术细节

### 依赖库
- `osmnx`: OpenStreetMap数据获取
- `networkx`: 网络分析
- `geopandas`: 地理数据处理
- `geopy`: 地理计算
- `folium`: 地图可视化支持

### 数据源
- **山峰数据**: OpenStreetMap
- **城镇数据**: OpenStreetMap
- **光污染数据**: VIIRS DNB 2025 GeoTIFF（内置，中国区域）
- **道路网络**: OpenStreetMap

### 算法说明
1. **高度差计算**: 使用海拔API获取精确高度数据
2. **光污染分析**: 基于 GeoTIFF 辐射度的波特尔等级映射
3. **道路连通性**: 使用OSMnx进行网络分析
4. **综合评分**: 加权平均多个评估维度

## 扩展功能

### 自定义评分算法

```python
class CustomStargazingAnalyzer(StargazingLocationAnalyzer):
    def _calculate_stargazing_score(self, location):
        # 自定义评分逻辑
        score = 0
        
        # 更重视光污染因素
        if location.light_pollution_brightness is not None:
            light_score = (255 - location.light_pollution_brightness) / 255 * 60
            score += light_score
        
        # 其他评分逻辑...
        return score
```

### 添加天气数据

```python
# 可以扩展添加天气API集成
def add_weather_data(location):
    # 调用天气API获取云量、湿度等数据
    pass
```

## 注意事项

1. **数据准确性**: 结果依赖于OpenStreetMap数据的完整性和准确性
2. **网络依赖**: 需要稳定的网络连接访问各种API
3. **处理时间**: 大范围搜索可能需要较长时间
4. **光污染数据**: 内置 VIIRS GeoTIFF 数据默认覆盖中国区域，可通过 geotiff_path 指定其他数据
5. **坐标系统**: 使用WGS84坐标系统（经纬度）

## 常见问题

### Q: 为什么必须提供光污染数据？
A: 光污染是影响观星质量的最重要因素，占评分权重的40%。系统内置 VIIRS 中国区域数据，默认自动加载。

### Q: 如何获取其他区域的光污染数据？
A: 可从 EOG VIIRS VNL v2.2 (https://eogdata.mines.edu/products/vnl/) 下载 GeoTIFF 数据，或使用 kml_file_path 参数切换到旧版 KML 后端。

### Q: 分析速度很慢怎么办？
A: 可以减小搜索范围、降低max_peaks参数，或者使用更快的网络连接。光污染查询使用本地 GeoTIFF，速度很快。

### Q: 结果中没有找到山峰怎么办？
A: 可能是搜索区域内确实没有符合条件的山峰，或者可以降低min_height_difference参数。

### Q: 可以分析海外地区吗？
A: 可以，只要OpenStreetMap有相关数据，并提供对应区域的 VIIRS GeoTIFF 光污染数据。

---

**记住：光污染数据是获得准确观星地点评估的关键！**

系统内置 VIIRS DNB 2025 中国区域数据，开箱即用。