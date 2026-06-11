# Changelog

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