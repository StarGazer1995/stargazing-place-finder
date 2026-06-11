# Performance Optimization Plan

## Context

`analysis_area` works correctly, but a 50-location analysis takes ~200-500s. Most of the time is spent in sequential I/O-bound operations that could be parallelized or batched.

PostGIS database available at `localhost:5455` with complete China OSM data (9M road segments, 5.7M POIs).

## Current Bottlenecks (ranked by impact)

### Phase 1 🚀 — Quick wins (low risk, high ROI)

| # | Module | Issue | Expected Speedup | Status |
|---|--------|-------|-----------------|--------|
| 1 | `road_connectivity_checker.py:238` | Per-location OSMnx HTTP download, each 1-5s | **~50× via PostGIS** | ✅ Done |
| 1b | `stargazing_location_analyzer.py:101` | GisQueryService 未接线，PostGIS 加速未生效 | **关键修复** | ✅ Done |
| 2 | `stargazing_place_finder.py:210` | Cache key ignores bbox → wrong hits / no caching | Correctness fix | ⏳ |
| 3 | `stargazing_place_finder.py:1143` | Per-location elevation API + 0.1s sleep → 50 HTTP calls | ~10× | ⏳ |
| 4 | `light_pollution_api.py:445` | Grid endpoint 2000 per-point reads → use `batch_analyze_coordinates()` | ~3-10× | ✅ Done |

> **#1 实现**：
> - `PostgisBackend.query_road_connectivity()` — kNN 查询 `planet_osm_line`
> - `GisQueryService.query_road_connectivity()` — 统一入口（PostGIS → OSMnx fallback）
> - `RoadConnectivityChecker` 新增 `gis_service` 参数
> - `StargazingLocationAnalyzer` 创建 `GisQueryService` 并传入 Finder + Checker
> - 实测：50 点从 **50-250s → ~1.2s**

### Phase 1 新增（当前评估补充）

| # | Module | Issue | Expected Speedup | Status |
|---|--------|-------|-----------------|--------|
| 4b | `stargazing_location_analyzer.py:238` | analyze_area 逐个地点 `get_light_pollution_color()` | ~5-10× | ⏳ |
| 2 | `stargazing_place_finder.py:210` | Cache key ignores bbox → wrong hits / no caching | Correctness fix | ⏳ |

### Phase 2 ⚡ — Parallel execution

| # | Module | Issue | Expected Speedup | Status |
|---|--------|-------|-----------------|--------|
| 5 | `stargazing_location_analyzer.py:211` | Sequential per-location loop → use ThreadPoolExecutor | 3-5× | ⏳ |
| 6 | `stargazing_location_analyzer.py:160` | Sequential location-type queries → parallelize | ~2× (PostGIS 下边际收益低) | ⏳ |
| 7 | `road_connectivity_checker.py:267` | `batch_check_accessibility` sequential → parallel | 3-5× | ⏳ |

### Phase 3 🧠 — Architecture

| # | Module | Issue | Status |
|---|--------|-------|--------|
| 9 | `stargazing_place_finder.py` | Pickle cache → SQLite or Parquet | ⏳ |
| 10 | `light_pollution_api.py` | Sync Flask → background task queue | ⏳ |

## 当前瓶颈分析（PostGIS 可用场景）

50 点 analysis_area 各环节耗时拆解（PostGIS 就绪后）：

| 环节 | 预计耗时 (50点) | 说明 |
|------|----------------|------|
| 地点数据获取（3 类 × PostGIS） | ~0.1s | ✅ 毫秒级 |
| 城镇数据（PostGIS） | ~0.03s | ✅ 毫秒级 |
| 海拔查询（PostGIS） | ~1.5s | 30ms/点 |
| 海拔 API fallback | ~0-30s | 仅 PostGIS 缺失时触发 |
| 光污染分析（逐点 50×） | ~0.3s | 可批量 → ~0.05s |
| 道路连通性（PostGIS） | ~1.5s | 30ms/点，可并行 |
| 缓存 key 错误 | 数据错误 | 正确性修复 |

## 推荐执行顺序

1. **缓存 key 修复**（#2）— 5 行代码，正确性修复
2. **analyze_area 光污染批量**（#4b）— 收拢 Loop 2 的逐点调用
3. **海拔 API 批量**（#3）— 移除逐点 sleep
4. **Phase 2 并行化**（#5, #7）— ThreadPoolExecutor
5. **架构改进**（#9, #10）— 缓存和任务队列

## Release Plan

- **v0.5.2** ✅ scikit-learn dependency fix (released 2026-06-11)
- **v0.6.0**: Phase 1 optimizations (#1, #2, #3, #4, #4b)
- **v0.7.0**: Phase 2 optimizations (#5, #7)
- **v0.8.0**: Phase 3 architecture improvements (#9, #10)
