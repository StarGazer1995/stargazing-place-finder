# Performance Optimization Plan

## Context

`analysis_area` works correctly, but a 50-location analysis takes ~200-500s. Most of the time is spent in sequential I/O-bound operations that could be parallelized or batched.

## Current Bottlenecks (ranked by impact)

### Phase 1 🚀 — Quick wins (low risk, high ROI)

| # | Module | Issue | Expected Speedup |
|---|--------|-------|-----------------|
| 1 | `road_connectivity_checker.py:238` | Per-location OSMnx HTTP download, each 1-5s | **~50× via PostGIS** |
| 2 | `stargazing_place_finder.py:210` | Cache key ignores bbox → wrong hits / no caching | Correctness fix |
| 3 | `stargazing_place_finder.py:1143` | Per-location elevation API + 0.1s sleep → 50 HTTP calls | ~10× |
| 4 | `light_pollution_analyzer.py:341` | Main loop uses per-point read, not `batch_analyze_coordinates()` | ~50× |

> **关于 #1 的 PostGIS 方案**（已在 v0.8.0 完整实现）：
> - `PostgisBackend.query_road_connectivity(lat, lon, radius_km)` — kNN 单点查询，~30ms
> - `PostgisBackend.query_road_graph_by_bbox()` / `query_road_graph_by_point()` — 从 `planet_osm_line` 构建 NetworkX 图，替代 OSMnx HTTP 下载
> - `RoadConnectivityChecker.preload_network_for_bbox()` 自动走 PostGIS 快速路径
> - `GisQueryService` 统一入口：PostGIS 可用 → 毫秒级 SQL；不可用 → fallback 到 OSMnx
> - 彻底消除 HTTP 开销，邻近点共享数据库索引，无 rate limit 问题

### Phase 2 ⚡ — Parallel execution

| # | Module | Issue | Expected Speedup |
|---|--------|-------|-----------------|
| 5 | `stargazing_location_analyzer.py:201` | Sequential per-location loop → use ThreadPoolExecutor | 4~8× |
| 6 | `stargazing_location_analyzer.py:160` | Sequential location-type queries → parallelize | ~3× |
| 7 | `road_connectivity_checker.py:267` | `batch_check_accessibility` sequential → parallel | 4~8× |

### Phase 3 🧠 — Architecture

| # | Module | Issue |
|---|--------|-------|
| 8 | `light_pollution_api.py:445` | Grid endpoint 2000 per-point reads → use batch |
| 9 | `stargazing_place_finder.py` | Pickle cache → SQLite or Parquet |
| 10 | `light_pollution_api.py` | Sync Flask → background task queue |

## Release Plan

- **v0.5.2** ✅ scikit-learn dependency fix (released 2026-06-11)
- **v0.6.0**: Phase 1 optimizations
- **v0.7.0**: Phase 2 optimizations
- **v0.8.0**: Phase 3 architecture improvements
