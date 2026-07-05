# 望远镜天体匹配推荐 — 功能设计

> **状态：Phase 1 方案已确定，Phase 2-4 设计中** | 上次更新：2026-07-03

## 1. 动机

现有系统能够：

- **SPF**：找到光污染低、道路可达的观星地点
- **mcp-stargazing `get_nightly_forecast`**：根据时间+地点推荐当晚适合观看的天体（按星等、高度角、月光干扰排序）
- **mcp-stargazing `get_best_stargazing_plan`**：将地点+天气+天体预报组合成完整观星计划

但以上推荐都是**"肉眼/通用"视角**——不考虑用户的具体设备。一台 80mm 折射镜 + APS-C 相机，和一台 14" SCT + 全画幅冷冻相机，适合拍摄的目标完全不同。

**核心问题**：给定我的望远镜/相机配置，今晚在这个地点适合拍哪些天体？

---

## 2. 实现路线图

采用渐进式实现，每阶段产出可用的功能增量。

### Phase 1：可视化闭环 ← 当前阶段 ✅

> **目标**：在 SPF 页面中看到"我的设备框住的天空范围"
> **原则**：纯前端，零后端改动

| # | 任务 | 说明 |
|---|------|------|
| 1.1 | 嵌入 Aladin Lite v3 | `<script>` 引入，DSS2 巡天底图，默认指向 M31 |
| 1.2 | 地图 ↔ 星图切换按钮 | 新增模式切换，Leaflet 地图与 Aladin 星图互斥显示 |
| 1.3 | 望远镜参数面板 | 在星图模式下显示：焦距、传感器宽/高、设备预设选择 |
| 1.4 | FOV 画幅框渲染 | 纯客户端计算 FOV 角度 → Aladin graphicOverlay 画蓝色矩形 |
| 1.5 | 画幅实时更新 | 参数变更/星图拖动时 FOV 矩形跟随更新 |

**交互流程**：

```
浏览模式 (Leaflet 地图)                   望远镜模式 (Aladin 星图)
┌────────────────────────┐              ┌────────────────────────────┐
│                        │              │                            │
│    光污染地图           │  ──[🔭]──→   │   DSS2 星图 + 蓝色FOV框    │
│    搜索观星地点         │  ←──[🗺️]──   │   望远镜参数面板            │
│                        │              │                            │
└────────────────────────┘              └────────────────────────────┘
```

**不做的事**：不推荐目标、不涉及后端、不查询天体数据。

---

### Phase 2：后端匹配引擎 + 目标推荐

> **目标**：输入设备+地点+时间 → 输出排序后的推荐拍摄目标列表
> **依赖**：Phase 1 完成
> **放置**：✅ 已确定 — mcp-stargazing 新增 `telescope` 工具域

| # | 任务 | 说明 |
|---|------|------|
| 2.1 | 天体角直径数据 enrich | SIMBAD `galdim_*` 字段批量查询 ~10,000 天体（~90% 覆盖率），无数据天体回退类型估算 |
| 2.2 | 匹配管线实现 | 在 `mcp-stargazing/src/functions/telescope/impl.py`，直接 import 本地 celestial，不需要共享包 |
| 2.3 | MCP 工具暴露 | `get_telescope_targets` 工具，天然双用：SPF 前端通过 HTTP 调，AI 客户端通过 MCP 协议调 |
| 2.4 | 前端对接 | Aladin `addCatalog()` 标记推荐目标 + 推荐列表 + 详情 popup |
| 2.5 | 表面亮度计算 | 圆形近似优先（`SB ≈ m + 2.5×log₁₀(area)`），后续可升级为椭圆轮廓 |

---

### Phase 3：与 SPF 现有功能融合

> **目标**：打通"找地点"和"找目标"两个核心流程
> **依赖**：Phase 2 完成

| # | 任务 | 说明 |
|---|------|------|
| 3.1 | 地点 → 目标串联 | 分析结果中选一个地点 → 切望远镜模式 → 自动带入坐标 |
| 3.2 | 反向查询 | 选一个目标天体 → 地图上高亮适合拍它的低光污染区域 |
| 3.3 | 天气接入 | 结合 mcp-stargazing 天气数据，标注"今晚此目标可见时段" |
| 3.4 | 月相叠加 | 星图模式下显示月相信息，辅助判断拍摄窗口 |

---

### Phase 4：增强功能

> **目标**：专业级天文摄影规划工具
> **依赖**：Phase 3 完成

| # | 功能 | 说明 |
|---|------|------|
| 4.1 | 马赛克规划 | 超大天体 → 自动计算拼接网格（Aladin 可显示 grid） |
| 4.2 | 设备预设库 | 内置 20+ 常见组合（Seestar S50、RedCat51+ASI2600、RASA8 等） |
| 4.3 | 曝光计算器 | 口径+焦比+目标表面亮度 → 建议子帧时长和总积分时间 |
| 4.4 | 多晚规划 | 未来一周每晚最佳拍摄目标排序 |
| 4.5 | MCP 工具 | 在 mcp-stargazing 中暴露为 MCP tool，供 AI 客户端调用 |
| 4.6 | 配置持久化 | 用户保存自己的设备配置（SPF PostGIS / 文件存储） |

---

## 3. 功能定位（Phase 2 架构决策）

### 候选方案

| 方案 | 位置 | 说明 |
|------|------|------|
| **A. SPF 新模块** | `src/telescope_matching/` | 作为 SPF 的分析模块，和 light_pollution、road_connectivity 平级 |
| **B. mcp-stargazing 新工具域** | `src/functions/telescope/impl.py` | 作为 MCP 工具，和 celestial、planning 平级 |
| **C. 跨项目：SPF 管设备模型，mcp-stargazing 管匹配逻辑** | 两边各加一部分 | SPF 定义 TelescopeConfig 模型 + 持久化，mcp-stargazing 做匹配计算 |

### 分析

**SPF 的优势：**
- 已有 REST API，可直接给前端 Web UI 用
- 已有 `StargazingLocationAnalyzer` 编排模式可参考
- 用户配置可持久化（用户望远镜配置保存/加载）

**SPF 的劣势：**
- **完全没有天文计算能力**——天体坐标、升落时间、星等等全部在 mcp-stargazing 的 `celestial.py` 中
- 需要新增对 Astropy 的依赖（目前 SPF 只做地理空间计算）
- 天体数据（objects.json, SIMBAD）都在 mcp-stargazing 侧

**mcp-stargazing 的优势：**
- 已有全部天文计算基础设施（`celestial.py`、`objects.json`、SIMBAD）
- 已有 `get_nightly_forecast` 评分管线可直接复用和扩展
- 新增 tool 即可被 MCP 客户端（Claude Desktop 等）调用
- 遵循现有 `planning` 域的组合模式

**mcp-stargazing 的劣势：**
- 没有前端，纯 API
- 没有用户配置持久化

**结论：匹配引擎放在 mcp-stargazing 新增 `telescope` 工具域。不需要抽取共享 pip 包。**

理由：
1. mcp-stargazing 已有全部天文计算（`celestial.py`、`objects.json`、SIMBAD），匹配管线直接 import 即可，零额外依赖
2. 新增 MCP 工具天然双用——SPF 前端走 HTTP 调用，AI 客户端走 MCP 协议调用，一套代码两个渠道
3. 不产生循环依赖：SPF → mcp-stargazing（调用匹配工具），mcp-stargazing → SPF（placefinder 桥接），方向一致
4. SPF 专注地点 + 可视化，mcp-stargazing 专注天文计算 + 匹配推荐，边界清晰
5. 遵循现有 `planning` 域的组合模式——`get_telescope_targets` 可以像 `get_best_stargazing_plan` 一样编排已有工具

```
          ┌─────────────────────────┐
          │     mcp-stargazing       │
          │                          │
          │  telescope/impl.py ──────┤  ← 新增：匹配引擎
          │      │                   │
          │      ├── celestial.py    │  ← 已有：天体计算
          │      ├── objects.json    │  ← 已有：深空天体目录
          │      └── planning/       │  ← 已有：组合编排模式
          │                          │
          │  placefinder.py ─────────│  ← 已有：桥接 SPF
          └───────────┬──────────────┘
                      │
          ┌───────────▼──────────────┐
          │          SPF              │
          │                           │
          │  地点搜索、光污染、道路    │  ← 不变
          │  Web UI + Aladin Lite     │  ← 新增：星图面板
          └───────────────────────────┘
```

## 4. 核心数据缺口（Phase 2 阻塞项）

### 4.1 天体角直径（angular size）✅ 已调研

`objects.json`（10,000+ Messier/NGC）当前字段缺少 `angular_size`。经过 SIMBAD 调研（2026-07-04），**`galdim_*` 字段对所有类型天体有效**：

| SIMBAD 字段 | 含义 | 单位 |
|-------------|------|------|
| `galdim_majaxis` | 长轴角直径 | arcmin |
| `galdim_minaxis` | 短轴角直径 | arcmin |
| `galdim_angle` | 位置角 (PA) | degree |

**实测覆盖率 9/10**：

| 对象 | 类型 | majaxis | minaxis | PA |
|------|------|---------|---------|-----|
| M31 | Galaxy | 199.5' | 70.8' | 35° |
| M42 | HII Nebula | 66.0' | 66.0' | 90° |
| M13 | Globular Cluster | 33.0' | 33.0' | — |
| M57 | Planetary Nebula | 1.2' | 1.2' | 90° |
| M1 | Supernova Remnant | 7.0' | 5.0' | — |
| NGC 7000 | Emission Nebula | — | — | 无数据 |

仅超大不规则天体（如北美洲星云）无数据。

**Phase 2 实现策略**：

```python
Simbad.add_votable_fields('galdim_majaxis', 'galdim_minaxis', 'galdim_angle')
```

- **批量 enrich**：对 ~10,000 天体批量查询 SIMBAD，预计 ~90% 有数据
- **本地缓存**：写入 `angular_size_maj_arcmin`、`angular_size_min_arcmin`、`angular_size_pa_deg`
- **回退**：无数据天体标记 `null`，匹配时按类型估算

### 4.2 天体表面亮度（surface brightness）

有长轴/短轴后可直接计算椭圆面积，精度优于圆形近似：

```
SB = m + 2.5 × log₁₀(π × a × b)   [mag/arcmin²]
```

其中 a、b 为长轴/短轴半径（arcmin）。

## 5. 望远镜配置模型（Phase 1+2 共用）

### 4.1 输入参数

```python
class TelescopeConfig(BaseModel):
    """用户望远镜+相机配置"""

    # ── 光学参数 ──
    aperture_mm: float = Field(ge=1, le=1000)
    focal_length_mm: float = Field(ge=1, le=10000)
    central_obstruction_pct: float = Field(default=0, ge=0, le=50)

    # ── 相机参数（可选，纯目视不填） ──
    sensor_width_mm: float | None = None
    sensor_height_mm: float | None = None
    sensor_pixel_size_um: float | None = None
    sensor_qe_percent: float | None = None  # 量子效率

    # ── 配件 ──
    reducer_factor: float = Field(default=1.0)  # 减焦镜倍率
    barlow_factor: float = Field(default=1.0)   # 增倍镜倍率
    filter_type: str | None = None  # "broadband" | "narrowband(Hα)" | "narrowband(OIII)" | ...

    # ── 架台 ──
    mount_type: str = "equatorial"  # "equatorial" | "altaz"
    guiding_supported: bool = False  # 是否支持导星
```

### 4.2 派生计算

从输入参数可以算出：

```
有效焦距 = focal_length × reducer_factor × barlow_factor
焦比 = 有效焦距 / aperture_mm
视场宽度 = 2 × atan(sensor_width / (2 × 有效焦距))  # 弧度
视场高度 = 2 × atan(sensor_height / (2 × 有效焦距))
像元采样 = 206.265 × pixel_size_um / 有效焦距  # arcsec/pixel
极限星等 ≈ 2 + 5 × log₁₀(aperture_mm)  # 粗略公式
有效口径 = aperture_mm × sqrt(1 - (obstruction/100)²)
```

## 6. 匹配算法设计（Phase 2）

### 5.1 输入

- `TelescopeConfig` — 设备参数
- `lon, lat, time, time_zone` — 观测条件
- 可选：`target_types` — 限定天体类型（如只拍发射星云）

### 5.2 管线

```
观测条件 (lon, lat, time)
        │
        ▼
┌─────────────────────────┐
│ 1. 候选天体粗筛          │  ← 复用 get_nightly_forecast 的 LST 过滤
│    - 近中天 (±6h RA)     │
│    - 高度角 > 20°         │
│    - 排除月光盲区         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. 设备维度过滤          │
│    - 星等 ≤ 极限星等     │
│    - 角直径适配画幅       │  ← 核心新增逻辑
│    - 表面亮度可探测       │
│    - 滤镜-天体类型匹配    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. 综合评分排序          │
│    - 画幅占比分          │ 天体占画面 30-70% 最佳
│    - 采样精度分          │ 1-3 arcsec/pixel 最佳
│    - 高度角分            │ 越高越好
│    - 滤镜匹配分          │ 发射星云 + 窄带 = 高分
│    - 月光干扰惩罚         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 4. 输出推荐列表          │
│    - 前 N 个最佳目标     │
│    - 每个目标的匹配理由  │
│    - 建议曝光参数范围    │
└─────────────────────────┘
```

### 5.3 画幅匹配度（核心指标）

```python
def fov_fit_score(obj_angular_size_arcmin, fov_width_arcmin, fov_height_arcmin):
    """计算天体在画幅中的占比得分 (0-1)"""
    obj_area = π * (obj_angular_size / 2)²  # 假设圆形
    fov_area = fov_width * fov_height
    fill_ratio = obj_area / fov_area

    # 最优占比: 10%-60%
    if 0.10 <= fill_ratio <= 0.60:
        return 1.0
    elif fill_ratio < 0.10:
        return fill_ratio / 0.10 * 0.5  # 太小，0-0.5分
    elif fill_ratio < 1.0:
        return 1.0 - (fill_ratio - 0.60) / 0.40 * 0.5  # 偏大但仍可拍
    else:
        return 0.0  # 超出画幅，拼接可考虑但默认不推荐
```

### 5.4 滤镜匹配度

| 天体类型 | 宽带 (LRGB) | Hα 窄带 | OIII 窄带 | SII 窄带 |
|----------|-------------|---------|-----------|----------|
| 星系     | ★★★ | ★ | — | — |
| 反射星云 | ★★★ | — | — | — |
| 发射星云 | ★★ | ★★★ | ★★★ | ★★ |
| 行星状星云 | ★ | — | ★★★ | — |
| 球状星团 | ★★★ | — | — | — |
| 疏散星团 | ★★★ | — | — | — |
| 超新星遗迹 | ★ | ★★ | ★★★ | ★★ |
| 暗星云   | — | — | — | — |

## 7. 输出模型（Phase 2）

```python
class TelescopeTarget(BaseModel):
    """单个推荐目标"""
    name: str                           # 天体名称
    type: str                           # 类型
    magnitude: float                    # 累积星等
    surface_brightness: float | None    # 表面亮度 (mag/arcmin²)
    angular_size_arcmin: float | None   # 角直径
    altitude: float                     # 高度角
    azimuth: float                      # 方位角

    # 匹配指标
    fov_fill_ratio: float               # 画幅占比 (0-1)
    fov_fit_score: float                # 画幅适配分 (0-1)
    sampling_arcsec_per_pixel: float | None  # 采样精度
    limiting_magnitude_reached: bool     # 是否在极限星等内
    filter_match_score: float           # 滤镜匹配分 (0-1)
    suitability_score: float            # 综合推荐分 (0-100)

    # 拍摄建议
    recommended_sub_exposure_s: int | None  # 建议单张曝光时间
    recommended_total_integration_min: int | None  # 建议总积分时间
    framing_tip: str | None             # 构图建议（如"竖构图"）

class TelescopeTargetResult(BaseModel):
    """完整推荐结果"""
    config: TelescopeConfig             # 回显配置
    derived_params: DerivedOpticalParams  # 派生光学参数
    location: GeoPoint                  # 观测位置
    time_info: TimeInfo                 # 观测时间
    moon_phase: MoonInfo                # 月相（影响拍摄）
    targets: list[TelescopeTarget]      # 排序后的推荐列表
    warnings: list[str]                 # 注意事项
```

## 8. 可视化方案：自建 vs 复用现有服务（Phase 1 决策依据）

### 7.1 需要可视化什么？

匹配算法给出的是**数据**——目标列表、FOV 参数、评分。但用户真正想看的是：

- 我的画幅（蓝色矩形）叠加在真实星图上
- 推荐天体在星图中的位置和大小
- 不同目标的相对位置关系（方便规划拍摄顺序）

这是一个**专业天文星图渲染**问题，如果从零做需要星表、HiPS 瓦片、投影引擎——不可行。

### 7.2 候选现有服务

| | Aladin Lite v3 | Stellarium Web Engine | AstroMosaic |
|---|---|---|---|
| **定位** | 专业天文档案浏览器 | 高保真数字天象仪 | FOV/马赛克规划工具 |
| **FOV 叠加** | ✅ `addFootprint()` API | ✅ Layer/Shape API | ✅ 核心功能 |
| **嵌入方式** | 一行 `<script>` 引入 div | JS/WASM 模块 | iframe 或 JS 引擎 |
| **体积** | ~500KB | 较大 (WASM) | 轻量 |
| **巡天底图** | ✅ HiPS (DSS2 等) | ✅ HiPS | ❌ |
| **自定义叠加** | ✅ 叠加自定义源表 | ✅ | 有限 |
| **已有用户** | ESASky、ESO、ALMA | 天文台控制面板 | 业余天文摄影社区 |
| **维护方** | CDS Strasbourg（天文数据权威） | Stellarium 社区 | 个人开发者 |

### 7.3 推荐：Aladin Lite v3

**核心理由：**

1. **FOV Footprint 是一等公民** — `A.graphicOverlay.addFootprint(overlay)` API 直接支持画幅矩形叠加，传入角坐标即可
2. **自定义源表叠加** — 匹配结果作为 catalog 传入 `A.catalog()`，目标天体直接高亮在星图上
3. **一行嵌入** — 不需要 npm/build，SPF 的纯 HTML/JS 前端直接 `<script>` 引入
4. **CDS 长期维护** — 斯特拉斯堡天文数据中心出品，不会突然弃坑
5. **DSS2 + PanSTARRS 底图** — 用户看到的是真实巡天照片，不是示意图

**基本嵌入方式：**

```html
<div id="aladin-lite-div" style="width:800px; height:600px"></div>
<script src="https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js"></script>
<script>
  A.init.then(() => {
    let aladin = A.aladin('#aladin-lite-div', {
      target: 'M 31',        // 初始指向目标天体
      fov: 2.5,              // 初始视场 (度)
      survey: 'P/DSS2/color', // DSS2 彩色巡天
      showFov: true,
    });
    // 叠加用户设备画幅矩形
    // aladin.addFootprint(...)
  });
</script>
```

### 7.4 端到端架构

```
┌──────────────────────────────────────────────────────────┐
│                     SPF Web UI                            │
│                                                            │
│  [🗺️ 浏览模式]  ←──切换按钮──→  [🔭 望远镜模式]           │
│                                                            │
│  ┌─ Leaflet 地图 ─┐    ┌─ Aladin Lite 星图 ────────────┐ │
│  │ 光污染分布      │    │                               │ │
│  │ 地点搜索        │    │  DSS2 巡天底图                 │ │
│  │ 区域分析        │    │  ┌─ 蓝色矩形 = 设备画幅        │ │
│  └─────────────────┘    │  ├─ 黄色标记 = 推荐天体        │ │
│                         │  ├─ 点击 popup = 详细信息       │ │
│  ┌─────────────────┐    │  └─ gotoObject = 搜索天体      │ │
│  │ 望远镜参数面板    │    └───────────────────────────────┘ │
│  │ [预设选择]       │                                       │
│  │ 焦距/传感器      │    ┌───────────────────────────────┐ │
│  │ [匹配目标] 按钮   │───▶│  推荐列表面板                  │ │
│  └─────────────────┘    │  1. M42 ★★★★★ 占画幅72%       │ │
│                         │  2. NGC2024 ★★★★☆ ...         │ │
│                         └───────────────────────────────┘ │
└─────────────────────────┬──────────────────────────────────┘
                          │
                          │ HTTP (MCP 协议)
                          ▼
┌──────────────────────────────────────────────────────────┐
│                  mcp-stargazing                           │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │  src/functions/telescope/impl.py  (新增)          │    │
│  │                                                    │    │
│  │  @mcp.tool()                                       │    │
│  │  get_telescope_targets(config, lon, lat, time)     │    │
│  │    │                                               │    │
│  │    ├─ 派生光学参数 (FOV / 采样 / 极限星等)          │    │
│  │    ├─ 调用 get_nightly_forecast → 候选粗筛         │    │
│  │    ├─ 设备过滤 (画幅 / 星等 / 滤镜)                │    │
│  │    ├─ 综合评分排序                                  │    │
│  │    └─ 返回 Top N + FOV坐标 + 拍摄建议              │    │
│  │                                                    │    │
│  │  直接 import 本地 celestial.py (天体坐标/月相/     │    │
│  │    objects.json/SIMBAD)，无需共享包                 │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │  已有工具 (不变):                                   │    │
│  │  celestial / weather / places / planning / time    │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

**职责分工：**

| | SPF | mcp-stargazing |
|---|---|---|
| **做什么** | 地点搜索、光污染分析、Web UI、Aladin 星图 | 天文计算、匹配推荐、天气、MCP 工具 |
| **Phase 1** | 嵌入 Aladin + 望远镜面板 + FOV 画幅框 | 不改动 |
| **Phase 2** | 前端调用匹配 API + 渲染推荐结果 | 新增 `telescope` 工具域 |
| **不做什么** | 不碰 astropy、不存天体数据 | 不碰 Leaflet 地图、不渲染 UI |

### 7.5 自建可视化的边界

Aladin Lite 负责**星图渲染**，但我们仍需自建：

- **设备画幅矩形计算**：从 `sensor_size + focal_length` 算出 FOV 四个角的 ICRS 坐标 → 传给 Aladin 的 `addFootprint()`
- **推荐列表 UI**：排序、筛选、详情面板
- **目标天体图标叠加**：用 Aladin 的 `addCatalog()` 传入自定义源表
- **曝光计算器 UI**：基于口径+焦比+目标表面亮度给出建议曝光时间
- **设备预设库**：常见望远镜+相机组合的预设配置

## 9. 架构决策总结

| # | 决策 | 结论 |
|---|------|------|
| 1 | 匹配引擎放哪 | **mcp-stargazing** 新增 `telescope` 工具域（不产生循环依赖，复用已有计算） |
| 2 | 需要抽共享包吗 | **不需要**，telescope tool 直接 import 本地 celestial.py |
| 3 | 可视化方案 | **Aladin Lite v3**，`<script>` CDN 引入 |
| 4 | 前端交互 | Leaflet 地图 ↔ Aladin 星图 **切换按钮** |
| 5 | Phase 1 策略 | 纯前端，最大化调用 Aladin 内置服务 |

---

## 10. Phase 1 工作量评估

### 10.1 任务拆分与估算

| # | 任务 | 涉及文件 | 估时 |
|---|------|---------|------|
| 1.1 | **Aladin Lite 嵌入** | `template.html` — 新增 `<script>` 引入 + `<div>` 容器 | 30min |
| | | `assets/css/styles.css` — 星图容器样式 | 30min |
| 1.2 | **地图 ↔ 星图切换按钮** | `assets/js/app.js` — 新增模式状态管理 + 切换逻辑 | 1h |
| | | `template.html` — 切换按钮 DOM | 15min |
| 1.3 | **望远镜参数面板** | `template.html` — 面板 DOM（预设下拉 + 焦距/传感器输入） | 1h |
| | | `assets/css/styles.css` — 面板样式 | 30min |
| 1.4 | **FOV 画幅框渲染** | `assets/js/app.js` — FOV 计算函数 + Aladin graphicOverlay 矩形 | 1.5h |
| | | `assets/js/app.js` — 预设配置数据 | 30min |
| 1.5 | **画幅实时更新** | `assets/js/app.js` — 参数变更监听 + 星图拖动监听 → 重绘 FOV | 1h |
| 1.6 | **调试 & 边界处理** | 预设切换时参数同步、FOV 矩形超出视场范围、移动端适配 | 1h |

**合计：约 7 小时（1 个工作日）**

### 10.2 不涉及的部分

Phase 1 明确不碰：

- ❌ SPF 后端（不新增 route、不修改 python 代码）
- ❌ mcp-stargazing（零改动）
- ❌ 天体数据查询（所有搜索走 Aladin 内置 `gotoObject` / `catalogFromSimbad`）
- ❌ 匹配算法
- ❌ 后端 API

### 10.3 Phase 1 交付物

1. SPF 页面新增「🔭 望远镜模式」切换按钮
2. 点击后 Leaflet 地图替换为 Aladin Lite DSS2 星图
3. 右侧/底部显示望远镜参数面板（预设选择 + 手动输入）
4. 星图上显示蓝色 FOV 画幅矩形，参数变更实时更新
5. 用户拖动星图可探索不同天区，FOV 框始终跟随显示当前指向

### 10.4 开发顺序

```
1.1 Aladin 嵌入 ──→ 1.2 切换按钮 ──→ 1.3 参数面板
                                            │
                                            ▼
                           1.4 FOV 画幅框 ←── 1.5 实时更新
                                            │
                                            ▼
                                       1.6 打磨

## 11. 参考资料

- 已有相关代码：
  - `mcp-stargazing/src/celestial.py` — 天体位置、评分管线
  - `mcp-stargazing/src/data/objects.json` — 10,000+ 深空天体目录
  - `mcp-stargazing/src/functions/planning/impl.py` — 组合工具编排模式
  - `SPF/src/stargazing_analyzer/` — 分析器编排模式
- 外部服务：
  - Aladin Lite v3: <https://aladin.cds.unistra.fr/AladinLite/doc/>
  - Aladin Lite API: <https://cds-astro.github.io/aladin-lite/>
  - Stellarium Web Engine: <https://github.com/Stellarium/stellarium-web-engine>
  - AstroMosaic: <https://ruuth.xyz/AstroMosaicConfigurationInfo.html>
