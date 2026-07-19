# 前端重构计划 — Stargazing Place Finder

> **状态**: Phase 1 完成，Phase 2 更新为 TypeScript 迁移  
> **日期**: 2026-07-13（原始），2026-07-18（更新）  
> 📋 **Notion 追踪**: [Stargazing 项目任务板](https://app.notion.com/p/39ab3b0281c481e684d0dbc5ecd41805)  
> **关联文档**: [TypeScript 迁移计划](./frontend_typescript_migration_plan.md) · [多仓库管理方案](./multi_repo_management.md) · [项目管理面板](https://github.com/StarGazer1995/stargazing-place-finder/wiki/Project-Dashboard)

> **⚠️ 重要更新 (2026-07-18):** 原计划的 Phase 2-4（vanilla JS 状态管理 + 测试 + 质量提升）已被新的 [TypeScript 迁移计划](./frontend_typescript_migration_plan.md) 取代。新计划将 TypeScript 引入提前到 Phase 2，同时覆盖 100% diff-cover 要求。本文档中的 Phase 2-4 内容保留作为架构参考，但实际执行请遵循 TypeScript 迁移计划。

---

## 目录

1. [现状评估](#1-现状评估)
2. [问题分析](#2-问题分析)
3. [重构目标与原则](#3-重构目标与原则)
4. [技术选型](#4-技术选型)
5. [目标架构](#5-目标架构)
6. [分阶段路线图](#6-分阶段路线图)
7. [风险与缓解](#7-风险与缓解)
8. [成功指标](#8-成功指标)

---

## 1. 现状评估

### 1.1 当前技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI (Python) | `src/server/main.py`，uvicorn 启动 |
| 前端 HTML | 单文件 `template.html` (234行) | SPA 入口，Leaflet 地图容器 |
| 前端 JS | 单文件 `app.js` (3,293行) | 全部业务逻辑，全局作用域 |
| 前端 CSS | 单文件 `styles.css` (2,049行) | 全部样式，无预处理器 |
| 地图库 | Leaflet 1.9.4 + MarkerCluster + Leaflet.Draw | 通过 unpkg CDN 加载 |
| 构建工具 | **无** | 零构建流程 |
| 包管理 | **无** | 前端依赖均为 CDN 外链 |
| 测试 | **无** | 零前端测试 |

### 1.2 功能模块清单

`app.js` 包含以下所有功能区域：

| 模块 | 估计行数 | 说明 |
|------|----------|------|
| 多语言 (i18n) | ~180 行 | 中/英双语配置对象 + DOM 更新函数 |
| 地图核心 | ~400 行 | Leaflet 初始化、图层管理、事件绑定 |
| 光污染图层 | ~250 行 | 热力图渲染、Tile 图层、颜色映射 |
| 搜索 | ~180 行 | 地名搜索、坐标定位 |
| 位置信息面板 | ~200 行 | 点击地图显示 Bortle 等级、SQM 值 |
| 统计面板 | ~200 行 | 暗空面积统计、等级分布 |
| 图例 | ~80 行 | Bortle 1-9 渐变图例 |
| 观星区域分析 | ~400 行 | 矩形绘制、API 调用、结果标记 |
| 望远镜模式 | ~500 行 | Aladin Lite 天文视场、目标匹配、拍摄计划 |
| 马赛克拼接 | ~400 行 | FOV 拼接网格、Canvas 叠加层 |
| 天气云层 | ~250 行 | 云量 Tile 图层、时间滑块 |
| 初始化/工具函数 | ~250 行 | DOM ready、事件绑定、工具函数 |

### 1.3 优点（值得保留）

- **Leaflet 选型正确** — GIS 可视化场景下 Leaflet 是最合适的库
- **i18n 支持完善** — 中英文双语已经覆盖主要 UI 文案
- **无障碍考虑** — 有 `aria-label`、`sr-only`、`role` 等无障碍标记
- **API 配置集中** — `API_CONFIG` 对象统一管理接口地址
- **FastAPI 静态文件挂载** — 前后端同源部署，无需 CORS 配置

---

## 2. 问题分析

### 2.1 🔴 严重问题

#### P1. 单文件巨石 (God Object)

3,293 行 JS 在一个文件里，所有变量和函数都在全局作用域。问题表现：

```javascript
// 全局变量散布在文件开头 — 任何函数都能读写
let map;                    // 行 2
let currentOverlay = null;  // 行 3
let analysisResults = [];   // 行 16
let _mosaicGrid = null;     // 行 ~3100（后加的功能，变量定义在底部）

// 函数间隐式依赖全局状态
function updateLanguageElements() { /* 读取 currentLanguage */ }
function renderLightPollutionLayer(data) { /* 读取 map */ }
```

- 新增功能（如望远镜模式、天气云层）只能继续往文件末尾追加
- 函数间依赖关系不透明，修改任何函数都有不可预见的副作用
- 变量命名冲突风险（如 `_mosaicOverlay` 与 `currentOverlay` 并存）

#### P2. DOM 状态分散

应用状态存储在三处：
- 全局 JS 变量 (`analysisResults`, `isAnalysisMode`)
- DOM 元素属性 (`element.style.display`, `element.innerHTML`)
- 闭包缓存 (`dataCache`, `imageCache`)

没有统一的 state → view 更新机制，每个函数需要手动操作 DOM：

```javascript
// 典型的 "意大利面" 模式 — 业务逻辑和 UI 更新交织
function updateStatsPanel() {
    // 读全局变量
    if (!currentOverlay) return;
    // 手动 DOM 操作
    const statsContent = document.querySelector('.stats-content');
    statsContent.innerHTML = '<div>...' + someVar + '</div>';
    // 再读 DOM 状态
    if (statsPanel.style.display === 'none') { ... }
}
```

#### P3. 零测试覆盖

前端没有任何自动化测试。所有的 UI 交互、API 调用封装、状态变更都是黑盒。随着功能增加，回归测试完全依赖手动操作，阻碍迭代速度。

### 2.2 🟡 中等问题

#### P4. 前端依赖无版本锁定

```html
<!-- 直接引用 unpkg，无 SRI hash -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

- unpkg CDN 不稳定的风险
- 无 Subresource Integrity 校验，供应链安全风险
- 离线环境下完全不可用

#### P5. CSS 无组织结构

2,049 行的 CSS 没有使用变量、嵌套或任何组织方法论（BEM/SMACSS）。颜色值、间距值硬编码重复出现。

#### P6. 重复文件

`styled_map_output/index.html` 和 `src/source/template.html` 是两个不同版本的前端入口文件，`styled_map_output/` 目录下的 `app.js`/`styles.css` 与 `src/source/assets/` 下的版本也不同。没有文档说明哪个是权威版本。

### 2.3 🟢 低优先级

#### P7. 无 Tree Shaking / Code Splitting

用户访问页面时一次性加载全部 3,293 行 JS，即使只使用地图浏览而不使用望远镜模式。

#### P8. 无热更新开发体验

修改 JS/CSS 后需手动刷新浏览器，无 HMR。

---

## 3. 重构目标与原则

### 3.1 核心目标

1. **模块化** — 将单文件拆分为职责清晰的 ES modules
2. **可测试** — 核心业务逻辑可脱离 DOM 进行单元测试
3. **可维护** — 新人能快速定位和修改特定功能
4. **不出故障** — 重构过程不影响现有功能，可通过渐进式切换验证

### 3.2 重构原则

- **渐进式** — 每个 Phase 独立交付价值，可随时暂停或调整
- **向后兼容** — 每个 Phase 结束时应用功能与重构前完全一致
- **不引入重型框架** — 保持 Vanilla JS 为主，仅在收益明确时引入轻量辅助库
- **先拆分再优化** — Phase 1 只做结构重组，不改变任何行为逻辑
- **保留 Leaflet 生态** — 继续使用 Leaflet 及其插件，不做地图库替换

---

## 4. 技术选型

### 4.1 为什么不选 React / Vue / Svelte

| 原因 | 说明 |
|------|------|
| **Leaflet 是命令式 API** | React/Vue 的声明式范式与 Leaflet 的 `L.map()`, `L.layer()` 等命令式调用天然冲突。需要大量 `useRef`/`ref` 和 `useEffect`/`watch` 去桥接，代码反而更复杂 |
| **应用规模不匹配** | 5,500 行代码引入 React 全家桶是杀鸡用牛刀。框架带来的 bundle 体积（React+ReactDOM ≈ 40KB gzip）超过应用本身逻辑代码的体积 |
| **GIS 场景特殊** | 地图应用的核心逻辑是图层增删、坐标变换、事件监听——这些都是命令式操作，Vanilla JS 反而是最直接的表达方式 |
| **学习成本** | 如果未来有其他贡献者，Vanilla JS + ES modules 的学习成本远低于 React 生态 |

### 4.2 选型方案

| 需求 | 选择 | 理由 |
|------|------|------|
| **模块打包** | [Vite](https://vitejs.dev) | 零配置 ES module 支持，HMR 开发服务器，生产构建优化。对 Vanilla JS 项目支持极好 |
| **CSS 预处理** | 继续 Vanilla CSS，引入 CSS Variables | 不增加构建复杂度，CSS Variables 已在所有现代浏览器中原生支持 |
| **状态管理** | 自定义 EventEmitter + Proxy（Phase 2） | 30 行代码即可实现简单的响应式状态，不需要引入库 |
| **测试框架** | [Vitest](https://vitest.dev) | 与 Vite 共享配置，零配置启动，兼容 Jest API |
| **DOM 测试** | [Testing Library](https://testing-library.com) (可选) | 按需在 Phase 2 后期引入 |
| **前端依赖管理** | npm + `package.json` | 替代 CDN 外链，版本锁定 + SRI |
| **HTTP 请求** | 保持 `fetch` | 不引入 axios，Vanilla `fetch` 足够用 |
| **可选轻量库** | [Alpine.js](https://alpinejs.dev)（Phase 2 评估） | 15KB，声明式 DOM 绑定，与 Leaflet 无冲突。仅在实际需要时引入 |

### 4.3 目标 Bundle 对比

| 指标 | 当前 | Phase 1 后 | Phase 2 后 |
|------|------|------------|------------|
| JS 文件数 | 1 | ~15 | ~15 |
| 是否构建 | 否 | Vite 打包 | Vite 打包 |
| JS bundle 大小 | ~90KB (原始) | ~30KB (min+gzip) | ~35KB (min+gzip) |
| CSS 文件数 | 1 | 1 (CSS Variables) | 3-4 (按模块拆分) |
| npm 依赖数 | 0 | 4 (leaflet 系列) | 4-5 |
| 前端测试 | 0 | 0 | 核心模块 ≥80% 覆盖 |

---

## 5. 目标架构

### 5.1 目录结构

```
src/source/                       # SPA 根目录（由 FastAPI 挂载）
├── index.html                    # 入口 HTML（更名自 template.html）
├── package.json                  # 前端依赖管理
├── vite.config.js                # Vite 配置
│
├── js/
│   ├── main.js                   # 应用入口，初始化协调
│   │
│   ├── core/
│   │   ├── state.js              # 全局应用状态（响应式 store）
│   │   ├── events.js             # 事件总线
│   │   ├── api.js                # API 请求封装（fetch + 错误处理）
│   │   └── i18n.js              # 多语言配置 + t() 函数
│   │
│   ├── map/
│   │   ├── map-instance.js       # Leaflet 地图工厂（创建/销毁）
│   │   ├── layers.js             # 图层管理（添加/移除/排序）
│   │   ├── markers.js            # 标记创建与样式
│   │   └── controls.js           # 自定义控件（搜索、定位、语言切换）
│   │
│   ├── panels/
│   │   ├── info-panel.js         # 点击位置信息面板
│   │   ├── stats-panel.js        # 光污染统计面板
│   │   ├── legend.js             # Bortle 图例面板
│   │   └── results-panel.js      # 分析结果面板
│   │
│   ├── features/
│   │   ├── stargazing/           # 观星区域分析
│   │   │   ├── draw-control.js   # 矩形绘制控制
│   │   │   ├── analyzer.js       # 分析请求与响应处理
│   │   │   └── renderer.js       # 分析结果可视化
│   │   ├── telescope/            # 望远镜模式
│   │   │   ├── aladin-view.js    # Aladin Lite 集成
│   │   │   ├── target-matcher.js # 目标匹配逻辑
│   │   │   └── shooting-plan.js  # 拍摄计划
│   │   ├── mosaic/               # 马赛克拼接
│   │   │   ├── grid-calc.js      # 网格计算（纯函数，可测试）
│   │   │   ├── overlay.js        # Canvas 叠加层渲染
│   │   │   └── panel-ui.js       # 马赛克面板 UI
│   │   └── weather/              # 天气云层
│   │       ├── tile-layer.js     # 云量 Tile 图层
│   │       └── time-slider.js    # 时间轴控件
│   │
│   └── utils/
│       ├── dom.js                # DOM 操作工具函数
│       ├── format.js             # 格式化工具（坐标、面积等）
│       └── geo.js                # 地理计算工具函数
│
├── css/
│   ├── variables.css             # CSS 自定义属性（颜色、间距、字体）
│   ├── base.css                  # 重置、排版、工具类
│   ├── layout.css                # 面板布局、响应式
│   ├── components/               # 按组件拆分样式
│   │   ├── map.css               # 地图容器
│   │   ├── panels.css            # 通用面板样式
│   │   ├── controls.css          # 按钮、输入框
│   │   ├── telescope.css         # 望远镜模式样式
│   │   └── weather.css           # 天气图层样式
│   └── themes/
│       └── dark.css              # 暗色主题（当前默认）
│
└── test/                         # 前端测试
    ├── core/
    │   ├── api.test.js
    │   ├── i18n.test.js
    │   └── state.test.js
    ├── features/
    │   ├── telescope.test.js
    │   └── mosaic-grid.test.js   # 纯计算逻辑，优先测试
    └── utils/
        ├── format.test.js
        └── geo.test.js
```

### 5.2 模块依赖图

```
main.js
  ├── core/state.js          ← 被所有模块依赖
  ├── core/events.js         ← 模块间通信
  ├── core/i18n.js           ← 被 panels/ 和 features/ 使用
  ├── core/api.js            ← 被 features/ 使用
  ├── map/map-instance.js    ← 被 panels/ 和 features/ 使用
  ├── map/layers.js          → 依赖 map-instance.js
  ├── panels/*               → 依赖 core/state.js + core/i18n.js
  └── features/*
        ├── stargazing/      → 依赖 map/, core/api.js, core/state.js
        ├── telescope/       → 依赖 map/, core/api.js
        ├── mosaic/          → 依赖 map/, core/api.js
        └── weather/         → 依赖 map/layers.js
```

关键约束：
- `core/state.js` **不依赖**任何其他模块（零依赖）
- `core/api.js` **不依赖** DOM 或地图（可独立测试）
- `features/` 中的纯计算逻辑（如 `mosaic/grid-calc.js`）**不依赖** DOM 或地图（可纯函数测试）
- 地图实例通过 `map-instance.js` 的 getter/setter 访问，不直接暴露全局 `map` 变量

---

## 6. 分阶段路线图

### Phase 1: 模块化 + 构建管线 ✅ 已完成（2026-07-18）

**目标**: 将单文件拆分为 ES modules，引入 Vite 开发服务器，前端依赖 npm 化。**不改变任何业务逻辑。**

#### 步骤

1. **初始化前端工程** ✅
   - ~~在 `src/source/` 下创建 `package.json`~~ → 将在 TypeScript 迁移 Phase 0 完成
   - ~~`npm install leaflet leaflet.markercluster leaflet-draw leaflet.locatecontrol`~~ → 同上
   - ~~配置 `vite.config.js`~~ → 同上

2. **HTML 拆分** ✅
   - ~~将 `template.html` 重命名为 `index.html`~~ → 已完成
   - 脚本引用改为 `<script type="module" src="js/main.js">` → 当前为普通 `<script>` 标签，将在 TypeScript 迁移 Phase 1 完成
   - CDN 引用改为 node_modules import → 同上

3. **JS 模块拆分** ✅（18 个文件，按目标架构目录结构）
   - ✅ `i18n.js`：移动 `i18nConfig` 对象和 `getText()` 等函数
   - ✅ `api.js`：移动 `API_CONFIG` 和 `fetch` 调用封装
   - ✅ `map-instance.js`：移动地图创建逻辑
   - ✅ `layers.js`：移动图层函数
   - ✅ `panels/`：info-panel.js、stats-panel.js
   - ✅ `features/stargazing/`：analyzer.js、draw.js、index.js、results.js
   - ✅ `features/telescope/`：aladin-core.js、altitude-chart.js、target-renderer.js、targets.js、telescope-ui.js
   - ✅ `features/mosaic/`：index.js
   - ✅ `utils/dom.js`

4. **全局变量 → 模块导出** ⚠️ 未完成
   - 全局 `let map`, `let currentOverlay` 等仍存在（48 个全局变量）
   - **推迟到 [TypeScript 迁移 Phase 1](./frontend_typescript_migration_plan.md#phase-1--全局变量--es-modules预计-1-天)**

5. **CSS 引入 CSS Variables** ✅
   - ✅ 颜色值、间距值已提取为 CSS 自定义属性（variables.css）
   - ✅ 6 个 CSS 文件：variables.css、base.css、layout.css、panels.css、stargazing.css、telescope.css

6. **FastAPI 适配** ⚠️ 部分完成
   - ✅ 静态文件路径更新：`template.html` → `index.html`
   - ⚠️ Vite dev server proxy 未配置 → 推迟到 TypeScript 迁移 Phase 7
   - ⚠️ 生产模式 `vite build` 未配置 → 同上

7. **清理重复文件** ✅
   - ✅ `styled_map_output/` 已删除
   - ✅ `.gitignore` 已更新

#### 验收标准

- [x] JS 文件已拆分为 18 个独立模块
- [x] 每个模块文件不超过 300 行
- [x] `app.js` 不再存在
- [ ] `npm run dev` 启动 Vite 开发服务器 → 推迟到 TypeScript 迁移
- [ ] `npm run build` 成功生成优化后的静态文件 → 推迟到 TypeScript 迁移
- [ ] 全局变量完全消除 → 推迟到 TypeScript 迁移

> **下一步：** 按 [TypeScript 迁移计划](./frontend_typescript_migration_plan.md) 执行 Phase 0-9。

---

### Phase 2: 状态管理 + 可测试架构（预计 3-4 天）

**目标**: 引入集中式状态管理，将核心逻辑与 DOM 操作分离，为核心模块编写单元测试。

#### 步骤

1. **实现响应式 Store**
   ```javascript
   // core/state.js
   // 基于 Proxy 的简单响应式状态
   const state = reactive({
       language: 'zh',
       analysisMode: false,
       analysisResults: [],
       currentBortle: null,
       // ...
   });
   
   // 订阅机制：state 变更自动更新 UI
   watch('language', () => updateLanguageElements());
   watch('analysisResults', () => renderAnalysisResults());
   ```

2. **分离业务逻辑和 DOM 操作**
   - 将 `features/mosaic/grid-calc.js` 提取为纯函数
   - 将 `features/telescope/target-matcher.js` 提取为纯计算
   - DOM 渲染逻辑集中在 `renderer.js` 文件中

3. **事件总线解耦**
   ```javascript
   // core/events.js
   // 模块间不直接调用，通过事件通信
   events.on('map:click', (latlng) => { ... });
   events.on('analysis:complete', (results) => { ... });
   events.emit('map:click', { lat: 30.5, lng: 120.2 });
   ```

4. **编写核心单元测试**
   - 优先测试纯逻辑：网格计算、坐标格式化、API 响应解析
   - 目标：核心模块 ≥80% 覆盖率

5. **CSS 模块拆分**
   - 按组件拆分 `styles.css`
   - 使用 CSS `@import` 或 Vite CSS 处理

#### 验收标准

- [ ] 核心状态变更通过 state.js 统一管理
- [ ] 至少 3 个 features 模块有单元测试
- [ ] `npm test` 可运行前端测试
- [ ] CSS Variables 覆盖率 ≥80%（颜色、间距不再硬编码）

---

### Phase 3: 质量提升（预计 2-3 天）

**目标**: 提升代码健壮性、错误处理、性能优化。

#### 步骤

1. **错误处理完善**
   - API 调用统一错误处理（网络超时、服务端错误、数据格式错误）
   - 用户友好的错误提示 UI

2. **性能优化**
   - 图片懒加载
   - 大数据量标记的虚拟化渲染
   - 防抖节流优化（搜索输入、地图拖动事件）

3. **可访问性增强**
   - 键盘导航支持
   - 屏幕阅读器优化
   - 焦点管理

4. **CI 集成**
   - GitHub Actions 中加入前端 lint + test
   - Vite build 作为 CI 步骤

#### 验收标准

- [ ] 所有 API 调用有错误处理
- [ ] Lighthouse 性能分数 ≥80
- [ ] CI 中前端测试通过

---

### Phase 4: 可选增强（待评估）

以下项目根据实际需求决定是否实施：

- [ ] **Alpine.js 引入评估** — 如果手动 DOM 绑定仍然繁琐，引入 Alpine.js 作为声明式增强
- [ ] **TypeScript 迁移** — 当模块数量 >30 或贡献者 >3 时考虑
- [ ] **E2E 测试** — Playwright/Cypress 浏览器自动化测试
- [ ] **PWA 支持** — Service Worker 离线缓存、添加到主屏幕
- [ ] **组件文档** — Storybook 或类似工具

---

## 7. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| **Leaflet 插件与 ES module 不兼容** | 中 | 高 | Leaflet 1.9+ 官方支持 ES module。若插件不兼容，可保留 CDN 加载方式待后续迁移 |
| **Aladin Lite 与模块化冲突** | 中 | 中 | Aladin Lite 通过 CDN 全局加载，作为例外保留在当前加载方式。通过 `window.A` 访问 |
| **重构引入回归 bug** | 高 | 中 | 每个 Phase 完成后手动回归测试全部功能；Phase 2 引入单元测试后可逐步减少手动测试量 |
| **FastAPI 静态文件路径变化导致 404** | 低 | 中 | 重构全程保持 `src/source/` 目录结构，仅改变内部文件组织 |
| **构建后的前端与开发模式表现不同** | 低 | 低 | Vite 的开发/生产模式高度一致，差异主要在优化（压缩、tree-shaking），不影响功能 |
| **时间投入超过预期** | 中 | 中 | 每个 Phase 独立交付价值，可在任一 Phase 结束后暂停或调整后续计划 |

---

## 8. 成功指标

### 定量指标

| 指标 | 当前 | Phase 1 后 | Phase 2 后 |
|------|------|------------|------------|
| 最大 JS 文件行数 | 3,293 | <300 | <300 |
| 单文件最大圈复杂度 | 未知（估计 >50） | <15 | <15 |
| 前端构建产物大小 | ~90KB raw | ~30KB gzip | ~35KB gzip |
| 前端测试覆盖率 | 0% | 0% | 核心模块 ≥80% |
| npm 依赖可离线构建 | 否 | 是 | 是 |
| 开发 HMR 支持 | 无 | 有 | 有 |

### 定性指标

- 新增一个功能模块无需修改已有模块文件
- 新人能在 30 分钟内定位到特定功能对应的文件
- 修改面板样式不影响其他组件
- 单模块可独立在浏览器 console 中调试

---

## 附录 A: 模块接口示例

### `core/state.js`

```javascript
// 应用状态的唯一真实来源
export const state = {
    language: 'zh',
    analysisMode: false,
    isMapLoaded: false,
};

// 订阅 state 变更
export function watch(key, callback) { ... }

// 修改 state（触发订阅回调）
export function setState(key, value) { ... }
```

### `core/api.js`

```javascript
import { API_CONFIG } from './config';

export async function analyzeStargazingArea(bounds, options) {
    const url = `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.analyze}`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bounds, ...options }),
    });
    if (!response.ok) throw new ApiError(response.status, await response.json());
    return response.json();
}
```

### `map/map-instance.js`

```javascript
let _map = null;

export function createMap(containerId, options = {}) {
    if (_map) destroyMap();
    _map = L.map(containerId, { ...DEFAULT_OPTIONS, ...options });
    return _map;
}

export function getMap() {
    if (!_map) throw new Error('Map not initialized');
    return _map;
}

export function destroyMap() {
    if (_map) { _map.remove(); _map = null; }
}
```

---

## 附录 B: 相关资源

- [Leaflet ES Module Guide](https://leafletjs.com/reference.html)
- [Vite Vanilla JS Template](https://vitejs.dev/guide/#scaffolding-your-first-vite-project)
- [Vitest Getting Started](https://vitest.dev/guide/)
- [CSS Custom Properties (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [Alpine.js (备选方案)](https://alpinejs.dev/)
