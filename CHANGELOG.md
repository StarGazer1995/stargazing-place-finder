# Changelog

## Unreleased — Phase 4 shooting plan

### Features
- **Shooting plan API + UI**: `POST /api/telescope/plan` generates a minute-by-minute single-night
  shooting schedule via `generate_shooting_schedule` from stargazing-core.
  - Algorithm: `np.interp` altitude interpolation + `np.nanargmax` per-minute best target + `np.diff` run merge
  - Frontend: collapsible plan panel with per-slot cards (target, time range, altitude bounds, FOV fit)
  - Click any plan slot → Aladin jumps to target + altitude chart opens
  - Moon-aware: delay banner, narrowband recommendation, unused time warnings
- **Altitude chart enhanced**: dynamic suitability score curve (green dashed line, right Y-axis)

### Other
- Switch stargazing-core from git dependency to local path (`../stargazing-core`)

## 0.7.1 (2026-07-02)

### Features
- **PostGIS road network graph**: `RoadConnectivityChecker` now queries local `planet_osm_line` via PostGIS
  instead of downloading from Overpass API via OSMnx.  Eliminates HTTP timeouts for areas in China.
  - `PostgisBackend.query_road_graph_by_bbox()` — build a NetworkX `MultiDiGraph` from LINESTRINGs
    within a bounding box (replaces `ox.graph_from_bbox`).
  - `PostgisBackend.query_road_graph_by_point()` — build a graph from roads near a point
    (replaces `ox.graph_from_point`).
  - `GisQueryService` delegating methods for transparent PostGIS/fallback switching.
  - `RoadConnectivityChecker.preload_network_for_bbox` and `_get_road_network` try PostGIS
    first, falling back to OSMnx only when PostGIS is unavailable.
  - ~3000× speedup for single-point road connectivity checks (50ms vs 143s OSMnx).

### Other
- New code comments in English to align with project conventions.

## 0.7.0 (2026-07-02)

### Bug Fixes
- Tile cache: replace unbounded dict with LRU+TTL (1h) — prevents OOM on long-running tile servers
- Overpass: add wall-clock `total_timeout` deadline to prevent hung queries blocking analysis
- PostGIS: fix duplicate query when multiple location types share the same bbox
- Thread safety: add `graph_lock` for `_shared_graph` concurrent access; `threading.Lock` for `GisQueryCache` and `RoadAccessInfoCache`
- Python 3.9 compat: replace PEP 604 `int | None` with `Optional[int]`

### Features
- Scoring v2: configurable weights via `StargazingConfig`; sigmoid-based road distance; logarithmic town isolation
- Parallel tiles: `ThreadPoolExecutor` for concurrent road network tile downloads (~3-8× on multi-tile areas)
- Dockerfile: multi-stage build with uv for containerized deployment
- Atomic cache writes: `tempfile.mkstemp` + `os.replace` for TOCTOU-safe persistence

### Other
- Web 启动链路: `start.sh` 对齐当前仓库结构，直接服务 `src/source/template.html`，并改为使用模块方式启动 `light_pollution.light_pollution_api`
- 前端配置: `src/source/assets/js/app.js` 新增 API 基地址解析逻辑，支持 `apiBaseUrl` 查询参数和 `window.APP_CONFIG.apiBaseUrl`
- Docs: add uv policy to CLAUDE.md

## 0.6.2 (2026-06-17)

- Bug 修复: Overpass 后端网络异常捕获面过窄 — 新增 `requests.exceptions.RequestException` 兜底
  - `OverpassBackend._request()` 增加 `RequestException` catch，避免 `ConnectionError` / `SSLError` 等击穿重试与 fallback 链路
  - `RoadConnectivityChecker` 所有 OSMnx 调用路径（`preload_network_for_bbox`、`_get_road_network`、`get_road_accessibility`）统一增加 `RequestException` 捕获
- 资源生命周期: 全局单例重建前先释放旧资源，防止 GeoTIFF 句柄泄漏
  - `light_pollution/public_api.py` — `init_light_pollution_analyzer()` 重建前调用 `close()`
  - `stargazing_analyzer/public_api.py` — `init_stargazing_analyzer()` 重建前调用 `close()`
  - `StargazingLocationAnalyzer` 新增 `close()` 方法，释放内部 LightPollutionAnalyzer

## 0.6.1 (2026-06-16)

- Bug 修复: Overpass API 主站 406 Not Acceptable — 添加 `User-Agent` 和 `Accept: application/json` 请求头
- 性能优化: 道路连通性分析从 N 次独立路网下载降为 1 次
  - `RoadConnectivityChecker` 新增 `preload_network_for_bbox()`，对整个 bbox 预加载路网
  - `StargazingLocationAnalyzer.analyze_area()` 在并行分析前调用预加载
  - `_get_road_network()` 优先复用共享路网，N 个地点共享同一张图

## 0.6.0 (2026-06-15)

- 性能优化: Phase 1 完成 — 50 点 analysis_area 从 200-500s 降至 ~3-5s
  - **PostGIS 道路连通性**: 新增 `PostgisBackend.query_road_connectivity()`，kNN 查询 ~30ms/点（vs OSMnx 1-5s）
  - **GisQueryService 接线**: `StargazingLocationAnalyzer` 创建并传入 Finder + Checker，使 PostGIS 加速真正生效
  - **缓存 key 修复**: `_generate_cache_key()` 加 bbox 参数，不同 bbox 查询不互相覆盖
  - **海拔 API 批量**: 新增 `batch_get_elevation()`，移除逐点 0.1s sleep
  - **光污染网格批量**: `/api/light_pollution` 改用 `batch_analyze_coordinates()`，~3-10×
  - **analyze_area 光污染批量**: 提前 `batch_analyze_coordinates()` 一次，循环内查表
  - **逐点并行处理**: `ThreadPoolExecutor(max_workers=4)` 并行处理 50 点分析
- 新功能: 道路距离过滤 — 命令行 `--min-road-distance` / `--max-road-distance`，API `min_distance_to_road_km` / `max_distance_to_road_km`
- 变更: 道路连通性判定阈值从 5km 缩小到 200m（`max_distance_to_road_km=0.2`），更符合实际携带装备步行的场景
- 变更: 道路评分档次调整，反映新的 200m 阈值（50–200m 为理想区间）
- 基础设施: 引入 ruff 作为格式化/静态检查工具，配置写入 `pyproject.toml` `[tool.ruff]`
- 基础设施: CI 新增 `lint` job，在 PR 时自动检查 `ruff format` 和 `ruff check`
- 代码清理: 修复多处 bare `except`、未使用的 import/变量，添加 `__all__` 导出声明
- 基础设施: GeoTIFF 数据从 Git LFS 迁移至 GitHub Release 托管，消除 LFS 配额限制对 CI/CD 的影响
- 基础设施: 引入 Sphinx API 文档系统，配置 autodoc + napoleon 解析 Google 风格 docstring，支持 `docs/sphinx/source/` 源码文档管理；利用 `sphinx-apidoc` 在构建时自动生成模块 RST 存根，无需手动维护
- 基础设施: 引入 bandit 静态安全扫描，识别并标记 Python 安全弱点和恶意代码模式，跳过明确安全的误报（pickle 本地缓存、MD5 缓存 key 等）
- 基础设施: CI 新增 bandit security scan job（`--severity-level medium`），仅阻断中等及以上严重性问题
- 重构: 移除已空的 `location_finder` 和 `mountain_peak` 包，功能已迁移至 `stargazing_analyzer.stargazing_place_finder`
- 重构: 统一使用 Pydantic dataclass 模型作为函数签名
  - `RoadConnectivityChecker` 所有公共方法接受 `GeoCoordinate` 而非原始 `(lat, lon)` 参数
  - `GisQueryService.query_locations()` 等接受 `LatLonBox` 而非 `Tuple[float, float, float, float]`
  - `extract_coordinates()` 返回 `Optional[GeoCoordinate]` 而非 `Tuple[Optional[float], Optional[float]]`
  - `find_nearest_town()` 返回 `TownInfo` 模型而非原始三元组
  - 新增 `TownInfo` Pydantic 模型 (`src/models/town.py`)

## 0.5.2 (2026-06-11)

- 依赖修复: 新增 `scikit-learn>=1.3.0` 为正式依赖，修复 OSMnx BallTree 未投影图最近邻搜索时的 `ImportError`
  - osmnx 的 `nearest_nodes()` 在 lat/lon 坐标下依赖 `sklearn.neighbors.BallTree`，缺失时所有道路可达性检测全返回 `False`
- 版本升级: `pyproject.toml` 版本号更新为 `0.5.2`

## 0.5.1 (2026-06-11)

- 文档修复: 修正 AGENTS.md 中错误的发布流程（移除被 branch protection 拦截的 `git push origin main`）
- 文档新增: AGENTS.md 新增 "Tag Push Triggers Duplicate PyPI Publish" 常见陷阱说明
- 版本升级: `pyproject.toml` 版本号更新为 `0.5.1`

## 0.5.0 (2026-06-11)

- 架构重构: 新增 `src/gis_service/` 统一 GIS 查询服务模块，集中管理 PostGIS、Overpass API 和海拔查询
- 新模块: `GisQueryService` 统一入口，支持 `query_locations()`、`find_elevation()`、`batch_find_elevations()`
- 海拔查询: 4 级降级链（OSM 标签 → PostGIS → Open-Elevation API → 0.0）
- 缓存重构: 统一内存 + 磁盘缓存，替换旧的 LocationCache / OverpassCache
- 向后兼容: `StarGazingPlaceFinder` 新增 `gis_service` 参数，未提供时自动降级到旧路径
- 版本升级: `pyproject.toml` 版本号更新为 `0.5.0`

## 0.4.2 (2026-06-06)

- Bug 修复: GeoTIFF 后端初始化时缺少 `self.mountain_finder`，导致 `analyze_area()` 报 `AttributeError`
- 代码清理: 移除 KML 后端分支中重复的异常打印行
- 版本升级: `pyproject.toml` 版本号更新为 `0.4.2`

## 0.4.1 (2026-07-13)

- 天光散射模型: 新增高斯模糊天光散射修正算法，修复 VIIRS vcm 数据背景扣除导致光污染低估的问题
- 数据修正: 崇明东滩等受城市散射光影响的区域 Bortle 等级从 1-2 修正为 4-5
- 架构文档: README 新增 Mermaid 架构图和数据流图
- 打包修复: CI 发布流程增加 `lfs: true` 参数，修复 GeoTIFF 数据被错误打包为 LFS 指针的问题
- 版本升级: `pyproject.toml` 版本号更新为 `0.4.1`

## 0.4.0 (2026-06-05)

- 数据升级: 光污染数据源从 KML 图像瓦片升级为 VIIRS DNB 2025 GeoTIFF，数据更精确、更新
- 缓存重构: 缓存配置模块从 `cache/` 迁移至 `src/cache/`，解决 `.gitignore` 误排除问题
- CI 修复: 网络测试覆盖 `FAST_TESTS=1` 环境变量，避免 CI 中 Overpass API 超时
- 新依赖: `rasterio` 用于 GeoTIFF 数据读取
- 格式支持: 辐射度值直接读取（nW/cm²/sr），无需图片反向解析
- 配置更新: 数据库服务器 IP 变更为 192.168.1.8，配置文件新增 JSON/TOML 示例
- 文档更新: README 新增数据库配置章节，包含完整的连接信息

## 0.3.1 (2025-12-25)

- 配置增强: Web 服务支持通过 `STARGAZING_DB_CONFIG` 环境变量加载 PostGIS 数据库配置
- API 更新: `analyze_stargazing_area` 函数新增 `db_config_path` 参数
- 版本升级: `pyproject.toml` 版本号更新为 `0.3.1`

## 0.2.0 (2025-11-19)

- CLI: 添加命令行入口 `stargazing-finder`
- 公共 API: 顶层包 `stargazingplacefinder` 提供重导出接口
- 导入统一：内部模块优先使用顶层包路径，保留本地运行回退
- 测试提速：增加 `FAST_TESTS` 环境变量的快速模式
- KML 路径修复：通过包资源加载 `light_pollution/resources/world_atlas/doc.kml`
- 版本升级：`pyproject.toml` 版本号更新为 `0.2.0`

关联提交：
- 6bed94e feat(cli,api): add CLI entry and top-level stargazingplacefinder API; unify imports; fast test mode; fix KML path via package resources; bump version to 0.2.0
- a533054 chore(publish): auto-build dist and show dynamic version in publish script
