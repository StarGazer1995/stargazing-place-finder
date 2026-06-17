# 项目锐评与问题清单

生成时间: 2026-06-17

## 结论摘要

这个项目的业务目标很明确: 用光污染、地理要素和道路可达性来筛选观星地点，主流程也已经搭起来了。

但从工程质量看，当前仓库有一种明显的特征: 核心能力已经成型，运行边界却没有彻底收口。最突出的问题不在算法本身，而在以下几类基础设施层面:

- 运行环境假设不统一
- 打包后资源定位不可靠
- 配置入口定义不一致
- 网络异常处理覆盖不完整
- 长生命周期资源释放不彻底

一句话锐评:

> 这是一个“产品思路比工程收尾成熟”的项目。仓库内开发体验大概率还行，但一旦换运行环境、换入口、换部署方式，隐藏问题就会开始冒头。

## 整体评价

### 做得好的地方

- 业务模型清晰，`光污染 + GIS 查询 + 路网可达性 + 综合评分` 这条主线是成立的。
- 模块分层大体合理，核心能力集中在 `stargazing_analyzer`、`light_pollution`、`gis_service`、`road_connectivity`。
- 主流程和部分核心逻辑已经有一定测试覆盖，尤其是 `stargazing_analyzer` 模块。
- 已经有正确的包内资源访问实现和一些较规范的公共 API 封装，说明项目并不是完全没有工程意识。

### 主要短板

- 同一个能力在不同入口上的实现不一致。
- 文档、配置、运行时行为之间存在明显偏差。
- 某些“看起来有 fallback”的逻辑，在真实异常下并不一定成立。
- 包发布场景和源码运行场景没有完全打通。
- 生命周期管理和资源释放还停留在“多数时候能用”的阶段。

## 问题清单

### 1. `light_pollution_api` 仍依赖源码目录路径，打包安装后容易失效

**严重级别**: 高

**问题描述**

`light_pollution_api.py` 通过 `__file__` 回推项目根目录，然后硬编码拼接 `src/light_pollution/resources/viirs_china_2025.tif`。这个路径在源码仓库中通常成立，但安装到 `site-packages` 之后通常不会再存在 `src/` 这一层。

仓库里其实已经有更正确的做法: `light_pollution/public_api.py` 使用 `importlib.resources` 读取包内资源。这说明当前 API 层保留了旧的源码路径思维，没有完成一致化迁移。

**影响**

- 本地源码运行正常，不代表安装后可运行。
- Flask API 的初始化和区域分析接口在打包环境下可能直接找不到 GeoTIFF。
- 这类问题对“作为 Python 包发布”的伤害很大，因为它会让用户觉得包已经装好了，但功能就是跑不起来。

**证据**

- [light_pollution_api.py:L40-L48](file:///Users/gongzhao/workspace/stargazing-place-finder/src/light_pollution/light_pollution_api.py#L40-L48)
- [light_pollution_api.py:L766-L781](file:///Users/gongzhao/workspace/stargazing-place-finder/src/light_pollution/light_pollution_api.py#L766-L781)
- [public_api.py:L24-L28](file:///Users/gongzhao/workspace/stargazing-place-finder/src/light_pollution/public_api.py#L24-L28)
- [pyproject.toml:L66-L68](file:///Users/gongzhao/workspace/stargazing-place-finder/pyproject.toml#L66-L68)

**建议**

- 统一改成 `importlib.resources` 读取包内资源。
- 让 `light_pollution_api.py` 和 `light_pollution/public_api.py` 共用同一套默认 GeoTIFF 解析逻辑。
- 补一个“安装后运行 API 初始化成功”的测试或最小验证脚本。

### 2. 项目声明支持 `Python >= 3.9`，但 `.toml` 配置加载实际上依赖 `3.11+`

**严重级别**: 高

**问题描述**

项目元数据声明支持 `Python 3.9`、`3.10`、`3.11`、`3.12`，但实际读取 `.toml` 配置时直接 `import tomllib`。`tomllib` 是 `Python 3.11+` 才内置的标准库，因此在 `3.9` 和 `3.10` 下会直接失败。

更糟的是，这里并没有对 `ImportError` 做兼容处理，也没有用 `tomli` 作为低版本回退。

**影响**

- 对外宣称的 Python 兼容矩阵和真实行为不一致。
- 用户只要在 `3.9/3.10` 环境里传入 `.toml` 数据库配置，就会在运行时炸掉。
- 这不属于边角兼容问题，而是“公开承诺和实现冲突”。

**证据**

- [pyproject.toml:L20-L28](file:///Users/gongzhao/workspace/stargazing-place-finder/pyproject.toml#L20-L28)
- [config.py:L23-L38](file:///Users/gongzhao/workspace/stargazing-place-finder/src/gis_service/config.py#L23-L38)
- [stargazing_location_analyzer.py:L138-L149](file:///Users/gongzhao/workspace/stargazing-place-finder/src/stargazing_analyzer/stargazing_location_analyzer.py#L138-L149)

**建议**

- 如果要继续支持 `Python 3.9/3.10`，则增加 `tomli` 回退逻辑。
- 如果不想维护这层兼容，则应把 `requires-python` 提升到 `>=3.11`。
- 配套补一个低版本行为测试，避免再次出现“元数据说能跑，实际功能不通”的情况。

### 3. 数据库配置环境变量名不统一，导致不同入口行为分裂

**严重级别**: 高

**问题描述**

文档和 API 层对外暴露的是 `STARGAZING_DB_CONFIG`，但核心分析器和 GIS 配置加载默认读取的是 `DB_CONFIG_PATH`。这意味着同一个项目里，不同入口对数据库配置的识别方式并不一致。

这不是简单的命名风格问题，而是运行行为不一致的问题。用户即便按照文档设置了环境变量，也不一定能让所有入口都按预期启用数据库配置。

**影响**

- Web API 可能能读到配置，但 CLI、公共 API 或其他初始化路径未必读得到。
- 部分入口会静默退化成无 PostGIS 的模式，问题不容易第一时间被发现。
- 这类配置分裂极其伤用户信任，因为看起来“已经配置过了”，但程序行为不一致。

**证据**

- [README.md:L187-L194](file:///Users/gongzhao/workspace/stargazing-place-finder/README.md#L187-L194)
- [CHANGELOG.md:L84-L87](file:///Users/gongzhao/workspace/stargazing-place-finder/CHANGELOG.md#L84-L87)
- [light_pollution_api.py:L771-L786](file:///Users/gongzhao/workspace/stargazing-place-finder/src/light_pollution/light_pollution_api.py#L771-L786)
- [stargazing_location_analyzer.py:L81-L87](file:///Users/gongzhao/workspace/stargazing-place-finder/src/stargazing_analyzer/stargazing_location_analyzer.py#L81-L87)
- [config.py:L18-L24](file:///Users/gongzhao/workspace/stargazing-place-finder/src/gis_service/config.py#L18-L24)

**建议**

- 全仓库统一只认一个环境变量名，建议收敛到 `STARGAZING_DB_CONFIG`。
- 为兼容历史用法，可以短期同时支持旧变量，并在日志中提示迁移。
- 把配置解析逻辑收敛到一个公共函数，避免每个入口都自定义一套。

### 4. 网络异常捕获面过窄，fallback 链路没有想象中稳

**严重级别**: 高

**问题描述**

`OverpassBackend` 只显式捕获了 `Timeout`、`HTTPError` 和项目自定义的 `NetworkError`。但真实网络故障里，更常见的往往是 `ConnectionError`、`SSLError`、`ProxyError` 以及更广义的 `RequestException`。

这意味着当前代码里的重试与备用 URL 切换，并不能覆盖很多真实故障场景。类似问题也出现在 OSMnx 和其他第三方调用路径上: 代码假设第三方异常会以项目内部异常的形式出现，但这种假设并不稳。

**影响**

- 应该被重试的请求直接中断。
- 应该走 fallback 的路径没有真正 fallback。
- 第三方库升级后，一些异常类型变化可能直接击穿当前逻辑。

**证据**

- [overpass_backend.py:L153-L199](file:///Users/gongzhao/workspace/stargazing-place-finder/src/gis_service/backends/overpass_backend.py#L153-L199)
- [road_connectivity_checker.py:L203-L249](file:///Users/gongzhao/workspace/stargazing-place-finder/src/road_connectivity/road_connectivity_checker.py#L203-L249)
- [road_connectivity_checker.py:L305-L315](file:///Users/gongzhao/workspace/stargazing-place-finder/src/road_connectivity/road_connectivity_checker.py#L305-L315)
- [road_connectivity_checker.py:L343-L362](file:///Users/gongzhao/workspace/stargazing-place-finder/src/road_connectivity/road_connectivity_checker.py#L343-L362)
- [exceptions.py:L27-L28](file:///Users/gongzhao/workspace/stargazing-place-finder/src/models/exceptions.py#L27-L28)

**建议**

- `requests` 相关逻辑至少统一兜底到 `requests.exceptions.RequestException`。
- 第三方网络和地理库的异常应尽量转换成项目内异常，再进入统一降级流程。
- 为重试、fallback 和最终失败语义分别补测试，避免“代码里写了重试”但真实行为不对。

### 5. 全局分析器重复初始化时没有释放旧的 GeoTIFF 句柄

**严重级别**: 中

**问题描述**

`LightPollutionAnalyzer` 已经提供了 `close()` 用于释放底层 GeoTIFF 句柄，但全局单例分析器在重新初始化时是直接覆盖旧实例的，没有先关闭旧资源。

这在一次性脚本里未必马上暴露，但在长期进程、热重载、测试反复构造或配置切换场景下，会逐步积累资源释放不及时的问题。

**影响**

- 文件句柄和底层资源可能无法及时释放。
- 长生命周期服务更容易出现隐性资源泄漏。
- 这类问题平时不显山露水，但一旦积累，会非常恶心。

**证据**

- [public_api.py:L50-L59](file:///Users/gongzhao/workspace/stargazing-place-finder/src/light_pollution/public_api.py#L50-L59)
- [public_api.py:L50-L61](file:///Users/gongzhao/workspace/stargazing-place-finder/src/stargazing_analyzer/public_api.py#L50-L61)
- [light_pollution_analyzer.py:L515-L519](file:///Users/gongzhao/workspace/stargazing-place-finder/src/light_pollution/light_pollution_analyzer.py#L515-L519)

**建议**

- 全局单例重建前先判断旧实例是否存在并显式 `close()`。
- `StargazingLocationAnalyzer` 也应提供统一的释放接口，把内部资源关闭逻辑封装起来。
- 给重复初始化路径补一个简单测试，防止后续回归。

## 次级观察

这些点没有进入本轮最高优先级问题清单，但值得后续继续看:

- 道路缓存粒度偏粗，长期运行可能造成缓存文件膨胀。
- 部分缓存和内存字典缺少明显的上限或淘汰策略。
- `light_pollution_api.py` 这类关键入口缺少足够的 HTTP 层测试。
- 有些测试文件更像“脚本化验证”，自动回归价值不如纯断言型测试高。

## 优先级建议

建议按以下顺序处理:

1. 先修资源路径、Python 版本兼容、环境变量统一这三项。
2. 再修网络异常处理和 fallback 覆盖。
3. 最后补资源释放和测试完善。

原因很简单:

- 前三项直接影响“用户能不能按文档把项目跑起来”。
- 网络异常问题影响“项目在真实外部环境里稳不稳”。
- 资源释放问题更像中期技术债，但越早收拾越省事。

## 最终评价

如果把这个项目看成一个原型或个人主导的功能型项目，它已经超过“能演示”的阶段了。

但如果把它看成一个要持续发布、安装、部署、被别人直接使用的工程化 Python 项目，那它现在还差最后一公里，而且这最后一公里主要不是功能开发，而是工程收口。

再锐一点说:

> 这个项目目前最缺的不是新功能，而是把已经存在的正确做法统一推广到所有入口，把“局部正确”变成“整体一致”。
