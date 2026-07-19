# 前端 TypeScript 迁移 + 100% Diff-Cover 计划

> **状态**: Draft
> **日期**: 2026-07-18
> **关联文档**: [前端重构计划](./frontend_refactoring_plan.md) · [多仓库管理方案](./multi_repo_management.md)

---

## 目录

1. [背景与动机](#1-背景与动机)
2. [现状分析](#2-现状分析)
3. [目标与原则](#3-目标与原则)
4. [技术选型](#4-技术选型)
5. [目标架构](#5-目标架构)
6. [分阶段路线图](#6-分阶段路线图)
7. [覆盖率豁免策略](#7-覆盖率豁免策略)
8. [风险与缓解](#8-风险与缓解)
9. [过渡期策略](#9-过渡期策略)
10. [成功指标](#10-成功指标)

---

## 1. 背景与动机

### 1.1 为什么现在做

Phase 1 已完成 JS 文件的物理拆分（18 个文件），但以下关键工作还没开始：

- 模块间仍通过**全局变量**通信，48 个可变状态散布在 18 个文件中
- 没有 ES module（`import`/`export`），所有代码共享全局作用域
- 没有构建管线（无 Vite、无 package.json、无 npm 依赖）
- 零前端测试覆盖
- Leaflet 等依赖仍走 unpkg CDN，无版本锁定

**现在引入 TypeScript 的边际成本几乎为零**——因为接下来无论如何都要做「加 `import`/`export` + 搭建 Vite」这件事，而此时把 `.js` 改成 `.ts` 只多花 ~20% 的精力。

### 1.2 为什么不做会后悔

如果跳过 TS、按原计划用 vanilla JS 完成 Phase 2-3，之后再想加类型系统，需要：
- 重写所有测试的类型标注
- 重新定义所有模块接口
- 处理已经固化的隐式类型约定

**成本至少翻倍。**

---

## 2. 现状分析

### 2.1 代码规模

| 指标 | 数值 |
|------|------|
| JS 文件数 | 18 |
| 总行数 | ~2,993 |
| 单文件最大行数 | 303 (aladin-core.js) |
| 最小行数 | 51 (map-instance.js) |

### 2.2 关键架构问题

来自 2026-07-18 的完整代码探索：

1. **48 个全局变量** — 包括 28 个可变状态变量、4 个配置常量、~60 个全局函数
2. **内联 onclick 字符串** — `results.js`、`info-panel.js` 在生成的 HTML 中硬编码全局函数名（`onclick="jumpToTelescopeMode(...)"`），造成隐藏的字符串耦合
3. **循环依赖** — `aladin-core.js` → 调用 `renderMosaicOnAladin()`（mosaic 模块）→ `mosaic/index.js` → 读取 `aladinInstance`（aladin-core 模块）。目前靠 `<script>` 加载顺序 works
4. **JSDoc 覆盖仅 ~30-40%** — 仅 `api.js`、`info-panel.js`、`stats-panel.js` 有完整 JSDoc
5. **只有 ~8 个纯函数**可脱离 DOM 测试：`calculateLocationStats`、`calculateStats`、`getBortleColor`、`getSuitabilityLevel`、`debounce`、`normalizeBaseUrl`、`getText`、`getIntensityRadius`

### 2.3 模块依赖关系

```
main.js                           [入口 + 全局变量定义]
  ├── map/map-instance.js         [地图实例]
  │   └── map/layers.js           [光污染图层渲染]
  │       ├── panels/stats-panel.js
  │       └── utils/dom.js
  ├── core/i18n.js                [多语言]
  ├── core/api.js                 [API 请求封装]
  ├── panels/info-panel.js        [点击信息面板]
  ├── features/stargazing/        [观星区域分析]
  │   ├── draw.js                 [矩形绘制]
  │   ├── analyzer.js             [API 调用]
  │   ├── results.js              [结果渲染]
  │   └── index.js                [聚合入口]
  ├── features/telescope/         [望远镜模式]
  │   ├── aladin-core.js          [Aladin Lite 集成]
  │   ├── targets.js              [目标匹配]
  │   ├── target-renderer.js      [目标渲染]
  │   ├── altitude-chart.js       [高度曲线]
  │   └── telescope-ui.js         [UI 面板]
  └── features/mosaic/            [马赛克拼接]
      └── index.js
```

所有依赖通过全局变量隐式传递，无显式 import 关系。

---

## 3. 目标与原则

### 3.1 核心目标

1. **TypeScript strict mode** — 所有新代码通过 `tsc --noEmit` 零错误
2. **ES modules** — 消除全局变量，模块间显式 import/export
3. **Vite 构建管线** — 开发 HMR + 生产优化打包
4. **100% diff-cover** — 前端新增/修改代码的行覆盖率达到 100%
5. **零功能回归** — 迁移过程中每个 checkpoint 都保持应用可用

### 3.2 原则

- **渐进式** — 每个 Phase 独立交付、可合并、可验证
- **先拆纯逻辑再处理 DOM** — 优先迁移和测试纯函数，DOM 绑定层后迁
- **覆盖率豁免有据可查** — 每处豁免标注原因，写在 `coverage-exemptions.md`
- **双轨过渡** — 旧版（uvicorn 直接 serve src/source/）和新版（Vite dev server）在整个迁移过程中同时可用

---

## 4. 技术选型

| 需求 | 选择 | 理由 |
|------|------|------|
| **类型系统** | TypeScript 5.7+ strict mode | 类型安全 + 更好的 IDE 体验 |
| **模块打包** | Vite 6 | 零配置 TS 支持，HMR，生产优化 |
| **测试框架** | Vitest 2.1 + jsdom | 与 Vite 共享配置，兼容 Jest API |
| **覆盖率** | @vitest/coverage-v8 | Vite 原生集成，Cobertura XML 输出 |
| **diff-cover** | diff-cover（Python 工具，读取 Cobertura XML） | 与现有 Python CI 使用同一工具 |
| **CSS** | 保持现有 6 文件 + CSS Variables | 不增加构建复杂度 |
| **外部依赖** | npm 管理（leaflet 系列），Aladin Lite 保留 CDN | Leaflet 有官方 npm 包；Aladin Lite 无 |

### 4.1 为什么不选……

| 方案 | 淘汰理由 |
|------|----------|
| React / Vue / Svelte | 当前 3,000 行引入框架是杀鸡用牛刀；Leaflet 是命令式 API，与声明式框架天然冲突 |
| 继续 vanilla JS | 48 个全局变量、零类型标注的代码会越来越难维护；边际成本最高的选项 |
| Jest | Vite 项目中 Vitest 配置更简单，速度更快 |
| Playwright（代替单元测试） | E2E 测试有价值但不能替代单元测试的覆盖率；两者互补 |

---

## 5. 目标架构

### 5.1 目录结构（迁移后）

```
src/source/
├── index.html                      # Vite 入口（<script type="module">）
├── package.json                    # 前端依赖管理
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
│
├── assets/
│   └── css/                        # 保持现有 6 文件不变
│       ├── variables.css
│       ├── base.css
│       ├── layout.css
│       ├── panels.css
│       ├── stargazing.css
│       └── telescope.css
│
├── js/
│   ├── main.ts                     # 应用入口，初始化协调
│   ├── state.ts                    # 集中式应用状态
│   ├── vite-env.d.ts               # Vite + 全局类型声明
│   │
│   ├── types/                      # 共享类型定义
│   │   ├── api.ts                  # API 请求/响应类型
│   │   ├── stargazing.ts           # 观星相关类型
│   │   ├── telescope.ts            # 望远镜相关类型
│   │   ├── i18n.ts                 # 多语言类型
│   │   ├── state.ts                # 状态类型
│   │   ├── aladin.d.ts             # Aladin Lite 类型桩
│   │   └── leaflet-extensions.d.ts # Leaflet 扩展类型
│   │
│   ├── constants/                  # 纯数据常量
│   │   ├── telescope.ts            # TELESCOPE_PRESETS
│   │   └── markers.ts              # MARKER_STYLES
│   │
│   ├── core/
│   │   ├── i18n.ts                 # 多语言配置 + getText()
│   │   └── api.ts                  # API 请求封装
│   │
│   ├── utils/
│   │   ├── dom.ts                  # DOM 工具函数
│   │   ├── color.ts                # getBortleColor() — 纯函数 ✅
│   │   ├── suitability.ts          # getSuitabilityLevel() — 纯函数 ✅
│   │   ├── calculate.ts            # calculateStats(), calculateLocationStats() — 纯函数 ✅
│   │   └── geo.ts                  # estimateBortleClass() — 纯函数 ✅
│   │
│   ├── map/
│   │   ├── map-instance.ts         # Leaflet 地图工厂
│   │   └── layers.ts               # 图层管理
│   │
│   ├── panels/
│   │   ├── info-panel.ts           # 点击信息面板
│   │   └── stats-panel.ts          # 统计面板
│   │
│   ├── features/
│   │   ├── stargazing/
│   │   │   ├── index.ts            # 聚合入口
│   │   │   ├── draw.ts             # 矩形绘制控制
│   │   │   ├── analyzer.ts         # API 调用 + 响应处理
│   │   │   └── results.ts          # 结果渲染
│   │   ├── telescope/
│   │   │   ├── aladin-core.ts      # Aladin Lite 桥接 [部分豁免]
│   │   │   ├── altitude-chart.ts   # 高度曲线 [Canvas 豁免]
│   │   │   ├── target-renderer.ts  # 目标渲染
│   │   │   ├── targets.ts          # 目标匹配
│   │   │   └── telescope-ui.ts     # UI 面板
│   │   └── mosaic/
│   │       └── index.ts            # 马赛克拼接 [Canvas 豁免]
│   │
│   └── __tests__/                  # 测试文件（与源文件同结构）
│       ├── utils/
│       │   ├── color.test.ts
│       │   ├── suitability.test.ts
│       │   ├── calculate.test.ts
│       │   └── geo.test.ts
│       ├── core/
│       │   ├── api.test.ts
│       │   └── i18n.test.ts
│       ├── map/
│       │   └── layers.test.ts
│       ├── panels/
│       │   ├── info-panel.test.ts
│       │   └── stats-panel.test.ts
│       └── features/
│           ├── stargazing/
│           │   ├── analyzer.test.ts
│           │   └── results.test.ts
│           ├── telescope/
│           │   ├── targets.test.ts
│           │   └── telescope-ui.test.ts
│           └── mosaic/
│               └── index.test.ts
│
└── dist/                           # Vite build 输出（gitignore）
    ├── index.html
    └── assets/
```

### 5.2 模块依赖图（迁移后）

```
main.ts  ← 只做初始化协调
  ├── state.ts              ← 集中式状态（被所有模块依赖，零外部依赖）
  ├── core/i18n.ts          ← 无依赖（纯数据 + 纯函数）
  ├── core/api.ts           ← 依赖 types/api.ts
  ├── utils/*.ts            ← 纯函数，无依赖
  ├── map/map-instance.ts   ← 依赖 state.ts + core/i18n.ts
  ├── map/layers.ts         ← 依赖 map-instance + utils/ + state.ts
  ├── panels/*.ts           ← 依赖 state.ts + core/i18n.ts + utils/
  └── features/
      ├── stargazing/*      ← 依赖 map/ + core/ + state.ts
      ├── telescope/*       ← 依赖 map/ + core/ + state.ts
      └── mosaic/*          ← 依赖 telescope/aladin-core + core/api + state.ts
```

**关键约束：**
- `state.ts` 不依赖任何其他模块
- `utils/*.ts` 不依赖 DOM、不依赖地图实例
- `types/*.ts` 纯类型定义，零运行时
- Aladin Lite 桥接（`aladin-core.ts`）是唯一需要 CDN 全局的模块

---

## 6. 分阶段路线图

### Phase 0 — 工程基建（预计 0.5 天）

**目标：** 搭建 npm/Vite/TypeScript/Vitest 基础设施，不迁移任何业务代码。

#### 步骤

**0.1 创建 package.json**

在 `src/source/` 下创建：

```json
{
  "name": "spf-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "leaflet": "^1.9.4",
    "leaflet.markercluster": "^1.4.1",
    "leaflet-draw": "^1.0.4"
  },
  "devDependencies": {
    "typescript": "^5.7",
    "vite": "^6.0",
    "vitest": "^2.1",
    "@vitest/coverage-v8": "^2.1",
    "@types/leaflet": "^1.9",
    "jsdom": "^25.0"
  }
}
```

> **注意：** Aladin Lite 和 leaflet.locatecontrol 保留 CDN 方式，无可靠 npm 包。

**0.2 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "sourceMap": true,
    "declaration": false,
    "outDir": "./dist",
    "rootDir": ".",
    "baseUrl": ".",
    "paths": { "@/*": ["./js/*"] },
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals"]
  },
  "include": ["js/**/*.ts", "__tests__/**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
```

**0.3 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  base: '/',
  resolve: {
    alias: { '@': resolve(__dirname, 'js') },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true,
    rollupOptions: {
      input: resolve(__dirname, 'index.html'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:5001',
    },
  },
});
```

**0.4 创建 vitest.config.ts**

```typescript
import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  resolve: {
    alias: { '@': resolve(__dirname, 'js') },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['__tests__/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['js/**/*.ts'],
      exclude: [
        'js/main.ts',
        'js/vite-env.d.ts',
        'js/types/**/*.d.ts',
      ],
      reporter: ['text', 'cobertura', 'html'],
      reportsDirectory: './coverage',
    },
  },
});
```

**0.5 创建 js/vite-env.d.ts**

```typescript
/// <reference types="vite/client" />

// Leaflet.Draw 类型桩（社区 @types 不完整）
declare module 'leaflet-draw' {
  const draw: any;
  export default draw;
}

// Aladin Lite — CDN 全局，运行时动态加载
declare global {
  var A: any;
  interface Window {
    APP_CONFIG?: { apiBaseUrl?: string };
  }
}
```

**0.6 npm install + 验证**

```bash
cd src/source && npm install && npx tsc --noEmit
```

**验收标准：**
- [ ] `npm install` 成功
- [ ] `npx tsc --noEmit` 通过（尚无 .ts 文件）
- [ ] `npx vite build` 可执行（产物为空）

---

### Phase 1 — 全局变量 → ES Modules（预计 1 天）

**目标：** 将 18 个 JS 文件的全局变量和函数改为 `import`/`export`，同时保持为 `.js` 文件。**这是唯一一个需要同时改动所有文件且不改变语义的 Phase。**

#### 步骤

**1.1 创建 types/ 目录下的纯类型文件**

新建以下 `.ts` 文件（纯类型，不产生运行时代码）：

- `js/types/api.ts` — API_CONFIG 接口、请求/响应类型
- `js/types/stargazing.ts` — StargazingLocation, LightPollutionPoint, GeoBounds 等
- `js/types/telescope.ts` — TelescopeTarget, MosaicGrid, TelescopePreset 等
- `js/types/i18n.ts` — Language, I18nConfig
- `js/types/state.ts` — AppState 接口（所有可变状态的类型）

**1.2 创建 js/state.js — 集中式状态模块**

```javascript
// 所有可变全局状态集中管理
export let map = null;
export let currentOverlay = null;
export let analysisResults = [];
export let isAnalysisMode = false;
export let isTelescopeMode = false;
export let aladinInstance = null;
// ... （覆盖全部 28 个状态变量）

// setter 函数（为后续 Proxy/watch 预留接口）
export function setMap(m) { map = m; }
export function setAladinInstance(instance) { aladinInstance = instance; }
// ...
```

**1.3 机械转换：逐文件加 export/import**

对每个 `.js` 文件：
- 所有 `function xxx()` → `export function xxx()`
- 所有 `let xxx` / `const xxx` → `export let xxx` / `export const xxx`
- 添加 `import { ... } from '../state.js'` 替代读取全局变量
- 添加 `import { ... } from './other-module.js'` 替代调用全局函数

**转换顺序（从叶子到根）：**

| 顺序 | 文件 | 原因 |
|------|------|------|
| 1 | `core/i18n.js` | 零外部依赖 |
| 2 | `core/api.js` | 零外部依赖 |
| 3 | `utils/dom.js` | 零外部依赖 |
| 4 | `panels/stats-panel.js` | 仅依赖 core/ |
| 5 | `panels/info-panel.js` | 依赖 core/ + map/ |
| 6 | `map/map-instance.js` | 引入 leaflet npm |
| 7 | `map/layers.js` | 依赖 map-instance + panels + utils |
| 8 | `features/stargazing/*` | 4 个文件，依赖 map/ + core/ |
| 9 | `features/telescope/aladin-core.js` | Aladin CDN 桥接 |
| 10 | `features/telescope/*` | 其余 4 个文件 |
| 11 | `features/mosaic/index.js` | 依赖 telescope + core |
| 12 | `main.js` | 入口，依赖所有 |

**1.4 创建入口文件 js/index.js**

```javascript
// 确保模块按正确顺序初始化
import './core/i18n.js';
import './core/api.js';
// ... 按依赖顺序 import 所有模块
import './main.js';
```

**1.5 更新 index.html**

```html
<!-- 替换全部 18 个 <script src="..."> -->
<script type="module" src="/js/index.js"></script>
```

Leaflet CSS 保留 `<link>` 标签。Leaflet JS 从 CDN `<script>` 迁移到 npm import（在 map-instance.js 中 `import L from 'leaflet'`）。

**1.6 处理循环依赖**

`aladin-core.js` ↔ `mosaic/index.js` 的循环通过回调解耦：

```javascript
// aladin-core.js
const onReadyCallbacks = [];
export function onAladinReady(fn) { onReadyCallbacks.push(fn); }
// 在 aladinInstance 创建后调用所有回调

// mosaic/index.js
import { onAladinReady } from '../telescope/aladin-core.js';
onAladinReady((instance) => { /* 渲染 mosaic */ });
```

**验收标准：**
- [ ] `npx vite` 启动 dev server，页面功能与迁移前完全一致
- [ ] `npx vite build` 成功生成 dist/
- [ ] 旧版 `uv run uvicorn` 仍可通过 legacy index.html 正常工作（过渡期双轨）

---

### Phase 2 — 纯逻辑提取 + 首批测试（预计 1 天）

**目标：** 从 DOM 纠缠代码中提取纯函数，编写首批单元测试并达到 100% 覆盖。

#### PR 2.1: `utils/color.ts` + 测试

从 `map/layers.js` 提取：

```typescript
export const BORTLE_COLORS: Record<number, string> = {
  1: '#0a0a2e', 2: '#191970', 3: '#2c3e50', 4: '#556b2f',
  5: '#8b7355', 6: '#cd853f', 7: '#ff8c00', 8: '#ff4500', 9: '#ff00ff',
};

export function getBortleColor(bortleClass: number): string {
  return BORTLE_COLORS[bortleClass] ?? '#888888';
}

export function getIntensityRadius(bortleClass: number): number {
  return 0.5 * (bortleClass / 3);
}
```

测试（`__tests__/utils/color.test.ts`）：
```typescript
describe('getBortleColor', () => {
  it('returns correct color for each class 1-9', () => {
    expect(getBortleColor(1)).toBe('#0a0a2e');
    expect(getBortleColor(9)).toBe('#ff00ff');
  });
  it('returns fallback for out-of-range', () => {
    expect(getBortleColor(0)).toBe('#888888');
    expect(getBortleColor(10)).toBe('#888888');
  });
});
```

#### PR 2.2: `utils/suitability.ts` + 测试

```typescript
export type SuitabilityLevel = 'excellent' | 'good' | 'fair' | 'poor';

export function getSuitabilityLevel(bortleClass: number): SuitabilityLevel {
  if (bortleClass <= 2) return 'excellent';
  if (bortleClass <= 4) return 'good';
  if (bortleClass <= 6) return 'fair';
  return 'poor';
}
```

#### PR 2.3: `utils/calculate.ts` + 测试

```typescript
export function calculateStats(data: LightPollutionPoint[]): StatsResult { ... }
export function calculateLocationStats(locations: StargazingLocation[]): LocationStats { ... }
```

这两个函数是现有代码中**最值得测试的纯逻辑**——非平凡计算，零外部依赖，100% 覆盖率容易达到。

#### PR 2.4: `constants/telescope.ts` + `constants/markers.ts`

```typescript
// telescope.ts
export interface TelescopePreset {
  name: string;
  focalLength?: number;
  sensorWidth?: number;
  sensorHeight?: number;
}

export const TELESCOPE_PRESETS: Record<string, TelescopePreset> = { ... };

// markers.ts
export const MARKER_STYLES = { ... } as const;
```

#### PR 2.5: `utils/geo.ts` + 测试

从 `layers.js` 提取 `estimateBortleClass()` 纯函数。

**验收标准：**
- [ ] 5 个纯工具模块全部完成 .ts 转换 + 类型标注
- [ ] `npm test` 首次通过
- [ ] `utils/` 目录覆盖率达到 100%
- [ ] `npx tsc --noEmit` 零错误

---

### Phase 3 — Core + Map + Panels 迁移（预计 1.5 天）

#### PR 3.1: `core/i18n.ts` + `core/api.ts`

- `.js` → `.ts`，加完整类型标注
- `i18n.ts`: `getText(key: string): string`，翻译表类型化
- `api.ts`: `fetchWithTimeout<T>(...)` 泛型化，API_CONFIG 类型化
- 测试：`__tests__/core/i18n.test.ts`、`__tests__/core/api.test.ts`（mock fetch）

#### PR 3.2: `utils/dom.ts`

- 类型标注：`showToast(message: string, type: 'info' | 'error' | 'success', duration?: number): void`
- 测试：jsdom 环境下验证 DOM 操作

#### PR 3.3: `state.js` → `state.ts`

- 全部状态变量加类型
- 消除 `any`：`dataCache: Map<string, LightPollutionPoint[]>`

#### PR 3.4: `map/map-instance.ts` + `map/layers.ts`

- `.js` → `.ts`，Leaflet 类型来自 `@types/leaflet`
- `map-instance.ts`：`createMap()`, `getMap()`, `destroyMap()`
- `layers.ts`：拆分为 `layers.ts`（DOM/地图操作）+ 已提取的 `utils/color.ts`、`utils/geo.ts`、`utils/calculate.ts`
- 测试：jsdom + Leaflet mock

#### PR 3.5: `panels/info-panel.ts` + `panels/stats-panel.ts`

- 类型化所有参数和返回值
- `createPopupContent()`：返回 HTML 字符串，可测
- `updateStatsPanel()`：DOM 操作，jsdom 验证
- 替换内联 `onclick` → `data-action` 事件委托（见 Phase 5）

**验收标准：**
- [ ] 所有核心模块完成 .ts 转换
- [ ] Core/Map/Panels 测试覆盖 ≥90%

---

### Phase 4 — Features 模块迁移（预计 2 天）

#### PR 4.1: `features/stargazing/*` (4 文件)

- `draw.ts`：Leaflet.Draw 集成，类型化
- `analyzer.ts`：拆分 `buildAnalysisRequest()` 纯函数 + `analyzeStargazingArea()` DOM/API 编排
- `results.ts`：拆分 `buildResultsHTML()` / `buildLocationCard()` → 返回 HTML 字符串（可测）
- `index.ts`：聚合入口 + 事件绑定

#### PR 4.2: `features/telescope/aladin-core.ts`

- **不拆纯逻辑**（Aladin Lite CDN 桥接，标记覆盖率豁免）
- 仅加类型标注 + 导出
- `TELESCOPE_PRESETS` 已提取到 `constants/telescope.ts`
- 类型桩：`types/aladin.d.ts`

#### PR 4.3: `features/telescope/*` (其余 4 文件)

- `targets.ts`：拆分 `buildTargetRequest()` 纯函数
- `target-renderer.ts`：拆分 `renderTargetResults()` / `renderMoonCard()` → HTML 字符串
- `altitude-chart.ts`：拆分 `computeChartLayout()` 纯数学 + Canvas 绘制（Canvas 豁免）
- `telescope-ui.ts`：`applyPreset()` 纯状态计算 + 事件绑定

#### PR 4.4: `features/mosaic/index.ts`

- 拆分 `renderMosaicPanel()` HTML 生成（可测）+ Canvas 覆盖层（豁免）

#### PR 4.5: `main.ts`

- 薄初始化协调器：import 各模块的 `init*()` 函数并调用
- 标记覆盖率豁免（纯集成代码）

**验收标准：**
- [ ] 18 个 .js 文件全部替换为 .ts
- [ ] 所有功能正常
- [ ] `npm run typecheck` 零错误

---

### Phase 5 — 内联 onclick → 事件委托（预计 0.5 天）

**目标：** 消除 HTML 字符串中的 `onclick="globalFunction(...)"`.

替换策略：

```html
<!-- 旧 -->
<button onclick="jumpToTelescopeMode(30.5, 120.2, 'loc')">🔭</button>

<!-- 新 -->
<button data-action="jump-telescope" data-lat="30.5" data-lng="120.2" data-label="loc">🔭</button>
```

在 `main.ts` 中注册全局事件委托：

```typescript
document.addEventListener('click', (e) => {
  const el = (e.target as HTMLElement).closest('[data-action]') as HTMLElement | null;
  if (!el) return;
  const action = el.dataset.action;
  switch (action) {
    case 'jump-telescope':
      jumpToTelescopeMode(
        parseFloat(el.dataset.lat!),
        parseFloat(el.dataset.lng!),
        el.dataset.label!
      );
      break;
    case 'focus-location':
      focusOnLocation(parseFloat(el.dataset.lat!), parseFloat(el.dataset.lng!));
      break;
    case 'clear-results':
      clearAnalysisResults();
      break;
  }
});
```

影响文件：
- `features/stargazing/results.ts`（3 处 onclick）
- `panels/info-panel.ts`（2 处 onclick）

---

### Phase 6 — 测试补全 + 覆盖率验证（预计 1 天）

**6.1 测试清单**

| 模块 | 测试文件 | 测试内容 | 目标覆盖 |
|------|---------|---------|---------|
| `utils/color.ts` | ✅ Phase 2 完成 | 边界值、越界 | 100% |
| `utils/suitability.ts` | ✅ Phase 2 完成 | 全等级映射 | 100% |
| `utils/calculate.ts` | ✅ Phase 2 完成 | 空数组、单元素、多元素 | 100% |
| `utils/geo.ts` | ✅ Phase 2 完成 | 中国东部/西部/境外 | 100% |
| `core/i18n.ts` | Phase 3 | 中英文 key 解析、缺失 key | 100% |
| `core/api.ts` | Phase 3 | fetch mock、超时、重试、URL 解析 | 95%+ |
| `utils/dom.ts` | Phase 3 | toast 创建/销毁、debounce 时序 | 95%+ |
| `map/layers.ts` | Phase 3 | 图层创建、标记聚合、Bortle 颜色映射 | 85%+ |
| `panels/info-panel.ts` | Phase 3 | popup HTML 生成、坐标格式化 | 90%+ |
| `panels/stats-panel.ts` | Phase 3 | 统计渲染、分布条生成 | 90%+ |
| `features/stargazing/analyzer.ts` | Phase 4 | buildAnalysisRequest 纯函数 | 100% |
| `features/stargazing/results.ts` | Phase 4 | HTML 生成、结果列表渲染 | 90%+ |
| `features/telescope/targets.ts` | Phase 4 | buildTargetRequest 纯函数 | 100% |
| `features/telescope/target-renderer.ts` | Phase 4 | HTML 生成 | 90%+ |
| `features/telescope/telescope-ui.ts` | Phase 4 | applyPreset 状态计算 | 90%+ |
| `features/mosaic/index.ts` | Phase 4 | renderMosaicPanel HTML 生成 | 90%+ |

**6.2 覆盖率豁免文件（不参与 threshold 计算）**

| 文件 | 豁免原因 |
|------|---------|
| `js/main.ts` | 纯初始化集成代码，薄 orchestrator |
| `js/features/telescope/aladin-core.ts` 中的 `loadAladinScript()` + `ensureAladinReady()` | CDN 动态加载，无法在 jsdom 中运行 |
| Canvas 绘制代码（`altitude-chart.ts` 中的 `ctx.*` 调用、`mosaic/index.ts` 中的 `renderMosaicOnAladin()`） | Canvas API 的视觉输出无法通过断言验证 |

---

### Phase 7 — FastAPI 生产/开发适配（预计 0.5 天）

**7.1 开发模式**

开发者同时启动两个进程：
- Terminal 1: `uv run uvicorn server.main:app --port 5001 --reload`
- Terminal 2: `cd src/source && npm run dev`

Vite dev server (:5173) 代理 `/api` → FastAPI (:5001)，支持 HMR。

**7.2 生产模式**

修改 `server/main.py` 中的静态文件逻辑：

```python
_DIST_DIR = _STATIC_DIR.parent / "dist"  # src/dist/

# 优先使用 Vite build 产物
if (_DIST_DIR / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=str(_DIST_DIR / "assets")), name="assets")
else:
    # 降级到源文件（过渡期 / 向后兼容）
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="assets")
    app.mount("/js", StaticFiles(directory=str(_STATIC_DIR / "js")), name="js")

@app.get("/")
async def root():
    dist_index = _DIST_DIR / "index.html"
    if dist_index.is_file():
        return FileResponse(dist_index)
    return FileResponse(_STATIC_DIR / "index.html")
```

**7.3 更新 start.sh**

增加可选参数启动 Vite dev server。

**7.4 更新 Dockerfile**

多阶段构建，加入 Node.js 前端构建：

```dockerfile
# Stage 1: Frontend build
FROM node:20-slim AS frontend-build
WORKDIR /app
COPY src/source/package.json src/source/package-lock.json ./
RUN npm ci
COPY src/source/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim
# ... 现有 Python 设置 ...
COPY --from=frontend-build /app/dist ./src/dist
```

**验收标准：**
- [ ] `npm run dev` → `http://localhost:5173` 页面正常，HMR 工作
- [ ] `npm run build` 生成 dist/ 优化产物
- [ ] FastAPI 正确 serve dist/ 下的构建产物
- [ ] Docker build 成功

---

### Phase 8 — CI 集成（预计 0.5 天）

**8.1 新增 frontend job**

```yaml
frontend:
  name: Frontend — typecheck + test + coverage
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: src/source
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
        cache-dependency-path: src/source/package-lock.json

    - run: npm ci
    - run: npm run typecheck
    - run: npm run test:coverage

    - name: Check new code coverage (diff-cover)
      if: github.event_name == 'pull_request'
      run: |
        pip install diff-cover -q
        diff-cover coverage/cobertura.xml \
          --compare-branch=origin/${{ github.base_ref }} \
          --fail-under=100
```

**8.2 更新 smoke-test-package**

修复过时的静态文件路径检查：
- 旧：`assets/js/app.js`、`assets/css/styles.css`
- 新：校验 `/` 返回的 HTML 中包含 `type="module"` 和 `leaflet`

**8.3 更新 job 依赖**

```yaml
smoke-test-package:
  needs: [lint, test, frontend]
```

---

### Phase 9 — 文档更新（预计 0.25 天）

- [ ] 更新 [frontend_refactoring_plan.md](./frontend_refactoring_plan.md)：标记 Phase 1 完成，Phase 2 更新为 TypeScript 迁移
- [ ] 更新 `CLAUDE.md`：添加前端快速命令（`npm run dev`, `npm test`, `npm run typecheck`）
- [ ] 创建 `src/source/js/coverage-exemptions.md`：记录所有覆盖率豁免及原因

---

## 7. 覆盖率豁免策略

### 7.1 豁免原则

1. **必须豁免** — CDN 动态加载代码（Aladin Lite）、Canvas 像素级渲染代码
2. **可以豁免** — 纯初始化 orchestrator 代码（main.ts）
3. **不可豁免** — 任何包含业务逻辑、数据变换、条件判断的代码

### 7.2 豁免清单

| 位置 | 代码段 | 原因 |
|------|--------|------|
| `aladin-core.ts` | `loadAladinScript()` | 动态创建 `<script>` 标签从 CDN 加载 Aladin Lite，jsdom 无网络且无 `A` 全局 |
| `aladin-core.ts` | `ensureAladinReady()` | 等待 CDN 脚本就绪，依赖运行时全局 `A` |
| `altitude-chart.ts` | `ctx.*()` Canvas 绘制调用 | Canvas 2D 绘制指令的视觉正确性无法通过断言验证 |
| `mosaic/index.ts` | `renderMosaicOnAladin()` | 依赖 `aladinInstance.world2pix()`（运行时 Aladin 实例） |
| `target-renderer.ts` | `overlayTargetsOnAladin()` | 调用 `A.catalog()` 和 `aladinInstance.addCatalog()`（Aladin 第三方 API） |
| `main.ts` | 完整文件 | 薄 orchestrator，仅 import 各模块 init 函数并调用，零业务逻辑 |

豁免标记：
```typescript
/* c8 ignore start -- Aladin Lite CDN: cannot test without browser + network */
function loadAladinScript() { ... }
/* c8 ignore stop */
```

### 7.3 替代验证

| 豁免项 | 如何验证正确性 |
|--------|---------------|
| Aladin Lite 集成 | 手动浏览器测试 + 未来 Playwright E2E |
| Canvas 渲染 | 视觉回归测试 / 手动验证 |
| main.ts 初始化 | Smoke test (CI 已验证页面可加载) |

---

## 8. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| **全局变量→ES module 引入回归 bug** | 中 | 高 | Phase 1 只做机械转换，不改语义；双轨过渡保证旧版始终可用 |
| **Leaflet 类型不完整**（`@types/leaflet-draw` 不完整） | 中 | 中 | 创建补充类型桩 `types/leaflet-extensions.d.ts`；必要时用 `as any` |
| **Aladin Lite 无类型** | 高 | 低 | 手写 `types/aladin.d.ts` 声明文件 |
| **Canvas 测试困难** | 低 | 低 | Canvas 绘制标记覆盖率豁免，仅测数据计算逻辑 |
| **CI diff-cover 门槛太激进** | 中 | 中 | 豁免有据可查；diff-cover 只检查 PR 变更行，不检查存量代码 |
| **Docker 多阶段构建增加构建时间** | 低 | 低 | Node.js 层有 npm cache，增量构建快 |

---

## 9. 过渡期策略

整个迁移过程中（Phase 0-7），**两条路径同时可用**：

| 路径 | 启动方式 | 用途 |
|------|---------|------|
| **旧版（legacy）** | `uv run uvicorn server.main:app --port 5001` | 始终可用，serve 原始 .js 文件 |
| **新版（dev）** | `cd src/source && npm run dev` | Vite HMR，TypeScript 即时编译 |

迁移完成后（Phase 7+）：
- 所有 `.js` 从 `js/` 目录删除
- `dist/` 成为生产部署的权威前端产物
- FastAPI 自动检测 `dist/` 目录存在 → 使用 Vite build；不存在 → 降级到源文件

---

## 10. 成功指标

### 定量指标

| 指标 | 当前 | 目标 |
|------|------|------|
| 前端构建管线 | 无 | Vite build ≤10s |
| TypeScript strict 模式 | 无 | `tsc --noEmit` 零错误 |
| 前端测试文件数 | 0 | ≥15 |
| 前端 diff-cover | N/A | 100% |
| 全局变量数 | 48 | 0（全部模块化） |
| npm 依赖 | 0 (CDN) | npm 管理（Leaflet 系列） |
| 开发 HMR | 无 | Vite <1s |

### 定性指标

- 新增一个前端功能只需修改相关 `.ts` 模块，不触及全局状态
- 纯计算逻辑（颜色映射、统计、坐标变换）可通过 `npm test` 在 2 秒内验证
- IDE 自动补全和类型检查覆盖所有模块接口
- PR 中任何未测试的前端代码被 CI 阻止合并

---

## 附录 A: 迁移顺序总览

| Phase | 内容 | 预计时间 | 风险 | 可独立合并 |
|-------|------|---------|------|-----------|
| 0 | 工程基建 | 0.5d | 低 | ✅ |
| 1 | 全局→ES Modules | 1d | **高** | ✅ (checkpoint) |
| 2 | 纯逻辑提取+首批测试 | 1d | 低 | ✅ |
| 3 | Core+Map+Panels TS 化 | 1.5d | 中 | ✅ |
| 4 | Features TS 化 | 2d | 中 | ✅ |
| 5 | onclick→事件委托 | 0.5d | 低 | ✅ |
| 6 | 测试补全+覆盖率 | 1d | 低 | ✅ |
| 7 | FastAPI 适配 | 0.5d | 中 | ✅ |
| 8 | CI 集成 | 0.5d | 低 | ✅ |
| 9 | 文档更新 | 0.25d | 低 | ✅ |
| **总计** | | **8.75 天** | | |

## 附录 B: 相关资源

- [TypeScript 官方文档](https://www.typescriptlang.org/docs/)
- [Vite 官方文档](https://vitejs.dev/)
- [Vitest 官方文档](https://vitest.dev/)
- [Leaflet TypeScript 支持](https://leafletjs.com/reference.html)
- [Aladin Lite v3 API](https://aladin.cds.unistra.fr/AladinLite/doc/API/)
