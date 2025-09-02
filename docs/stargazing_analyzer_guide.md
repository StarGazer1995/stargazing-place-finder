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

#### 推荐数据源

1. **Light Pollution Map** (推荐)
   - 网址：https://www.lightpollutionmap.info/
   - 特点：数据更新频繁，覆盖全球
   - 下载方式：选择区域后导出KML格式

2. **Dark Site Finder**
   - 网址：https://darksitefinder.com/
   - 特点：专为天文观测设计
   - 下载方式：提供KML格式下载

#### 下载步骤

1. 访问 https://www.lightpollutionmap.info/
2. 导航到你感兴趣的地理区域
3. 点击右上角的"Export"按钮
4. 选择"KML"格式
5. 下载文件并重命名为 `light_pollution_map.kml`
6. 将文件放置在项目根目录

## 核心功能

### 1. 山峰查找与筛选
- 基于OpenStreetMap数据查找指定区域内的山峰
- 计算山峰与周围城镇的高度差
- 筛选符合最小高度差要求的山峰

### 2. 光污染分析
- 基于KML光污染地图数据
- 计算每个山峰位置的光污染等级
- 提供RGB颜色值和亮度信息

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
from src.stargazing_location_analyzer import StargazingLocationAnalyzer

# 初始化分析器（提供光污染数据文件）
analyzer = StargazingLocationAnalyzer(
    kml_file_path="light_pollution_map.kml",
    min_height_difference=100.0,
    road_search_radius_km=10.0
)

# 分析指定区域（北京周边示例）
bbox = (39.5, 115.5, 40.5, 117.0)  # (south, west, north, east)
locations = analyzer.analyze_area(
    bbox=bbox,
    max_peaks=20,
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
from src.stargazing_location_analyzer import analyze_stargazing_area

# 使用便捷函数进行快速分析
locations = analyze_stargazing_area(
    south=39.5, west=115.5, north=40.5, east=117.0,
    kml_file_path="light_pollution_map.kml",
    max_peaks=15,
    min_height_diff=150.0
)

print(f"找到 {len(locations)} 个观星地点")
```

## 无光污染数据的影响

### 警告提示
当没有提供光污染数据时，系统会显示以下警告：

```
⚠️  警告: 未提供光污染数据文件
⚠️  光污染数据是观星地点分析的重要组成部分
⚠️  建议从以下网站下载光污染地图KML文件:
   - Light Pollution Map: https://www.lightpollutionmap.info/
   - Dark Site Finder: https://darksitefinder.com/
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
    kml_file_path="light_pollution_map.kml",  # 光污染KML文件路径（强烈推荐）
    min_height_difference=100.0,              # 最小高度差要求（米）
    road_search_radius_km=10.0                # 道路搜索半径（公里）
)
```

### 分析参数

```python
locations = analyzer.analyze_area(
    bbox=(south, west, north, east),          # 搜索边界框
    max_peaks=20,                             # 最大山峰数量
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
    kml_file_path="light_pollution_map.kml",
    max_peaks=15,
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
        kml_file_path="light_pollution_map.kml",
        max_peaks=10
    )
    all_results[region_name] = locations
```

### 3. 自定义评分权重

```python
# 对于更注重交通便利性的用户
analyzer = StargazingLocationAnalyzer(
    kml_file_path="light_pollution_map.kml",
    min_height_difference=50.0,    # 降低高度差要求
    road_search_radius_km=15.0     # 增加道路搜索范围
)
```

## 性能优化建议

1. **合理设置搜索范围**：避免过大的边界框
2. **限制山峰数量**：使用 `max_peaks` 参数控制结果数量
3. **缓存光污染数据**：系统会自动缓存已加载的KML数据
4. **批量处理**：对多个区域使用同一个分析器实例

## 错误处理

系统会自动处理以下错误情况：

1. **无效的边界框坐标**
2. **网络连接问题**
3. **KML文件读取错误**
4. **API调用失败**

## 集成到观星项目

### 与现有功能结合

```python
# 结合山峰查找器
from src.mountain_peak_finder import StarGazingPlaceFinder
from src.stargazing_location_analyzer import StargazingLocationAnalyzer

# 先用山峰查找器获取候选地点
mountain_finder = StarGazingPlaceFinder(min_height_difference=200.0)
peaks = mountain_finder.find_peaks_in_area((39.5, 115.5, 40.5, 117.0))

# 再用综合分析器进行详细评估
analyzer = StargazingLocationAnalyzer(kml_file_path="light_pollution_map.kml")
detailed_analysis = analyzer.analyze_peaks(peaks)
```

### Web应用集成

```python
# Flask应用示例
from flask import Flask, request, jsonify

app = Flask(__name__)
analyzer = StargazingLocationAnalyzer(kml_file_path="light_pollution_map.kml")

@app.route('/api/analyze_stargazing', methods=['POST'])
def analyze_stargazing():
    data = request.json
    bbox = (data['south'], data['west'], data['north'], data['east'])
    
    locations = analyzer.analyze_area(
        bbox=bbox,
        max_peaks=data.get('max_peaks', 20),
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
- **光污染数据**: 用户提供的KML文件
- **道路网络**: OpenStreetMap

### 算法说明
1. **高度差计算**: 使用海拔API获取精确高度数据
2. **光污染分析**: 基于KML文件的颜色映射
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
4. **光污染数据**: 强烈建议提供最新的光污染KML文件
5. **坐标系统**: 使用WGS84坐标系统（经纬度）

## 常见问题

### Q: 为什么必须提供光污染数据？
A: 光污染是影响观星质量的最重要因素，占评分权重的40%。没有这些数据，分析结果的准确性会大大降低。

### Q: 如何获取最新的光污染数据？
A: 建议从 https://www.lightpollutionmap.info/ 下载最新的KML格式光污染地图。

### Q: 分析速度很慢怎么办？
A: 可以减小搜索范围、降低max_peaks参数，或者使用更快的网络连接。

### Q: 结果中没有找到山峰怎么办？
A: 可能是搜索区域内确实没有符合条件的山峰，或者可以降低min_height_difference参数。

### Q: 可以分析海外地区吗？
A: 可以，只要OpenStreetMap有相关数据，并且提供对应区域的光污染KML文件。

---

**记住：光污染数据是获得准确观星地点评估的关键！**

请确保从可靠来源下载最新的光污染地图数据，以获得最佳的分析结果。