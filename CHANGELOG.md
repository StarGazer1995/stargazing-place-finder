# Changelog

## 0.4.0 (2026-06-05)

- 数据升级: 光污染数据源从 KML 图像瓦片升级为 VIIRS DNB 2025 GeoTIFF，数据更精确、更新
- 缓存重构: 缓存配置模块从 `cache/` 迁移至 `src/cache/`，解决 `.gitignore` 误排除问题
- CI 修复: 网络测试覆盖 `FAST_TESTS=1` 环境变量，避免 CI 中 Overpass API 超时
- 新依赖: `rasterio` 用于 GeoTIFF 数据读取
- 格式支持: 辐射度值直接读取（nW/cm²/sr），无需图片反向解析

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