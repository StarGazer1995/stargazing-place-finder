# 多仓库管理方案 — Stargazing 项目族

> **状态**: Draft  
> **日期**: 2026-07-13  
> 📋 **Notion 追踪**: [Stargazing 项目任务板](https://app.notion.com/p/39ab3b0281c481e684d0dbc5ecd41805) — 筛选 `Module = MCP_server` 查看多仓库工具类任务  
> **关联文档**: [前端重构计划](./frontend_refactoring_plan.md) · [项目管理面板](https://github.com/StarGazer1995/stargazing-place-finder/wiki/Project-Dashboard)

---

## 目录

1. [现状概述](#1-现状概述)
2. [当前工作流痛点](#2-当前工作流痛点)
3. [方案对比](#3-方案对比)
4. [推荐方案：多仓库 + 轻量编排](#4-推荐方案多仓库--轻量编排)
5. [工具配置指南](#5-工具配置指南)
6. [跨仓库发布流程](#6-跨仓库发布流程)
7. [FAQ](#7-faq)

---

## 1. 现状概述

Stargazing 项目由 **3 个独立 Git 仓库** 组成，它们之间存在严格的线性依赖关系：

```
┌──────────────────────┐
│   stargazing-core    │  ← PyPI: stargazing-core
│   共享数据模型 / Schema │     数据模型、枚举、工具函数
│   Python 3.9+        │
└──────────┬───────────┘
           │ 依赖 (PyPI)
┌──────────▼───────────┐
│ stargazing-place-    │  ← PyPI: stargazing-place-finder
│ finder               │     光污染分析、GIS、Web 前端
│ Python 3.9–3.12      │     FastAPI + Leaflet SPA
└──────────┬───────────┘
           │ 依赖 (PyPI)
┌──────────▼───────────┐
│   mcp-stargazing     │  ← PyPI: mcp-stargazing
│   MCP 协议服务层      │     FastMCP 包装，15 个工具
│   Python 3.13+       │
└──────────────────────┘
```

| 仓库 | GitHub | PyPI 包名 | 主要语言 |
|------|--------|-----------|----------|
| stargazing-core | `StarGazer1995/stargazing-core` | `stargazing-core` | Python |
| stargazing-place-finder | `StarGazer1995/stargazing-place-finder` | `stargazing-place-finder` | Python + JS/CSS |
| mcp-stargazing | `StarGazer1995/mcp-stargazing` | `mcp-stargazing` | Python |

### 现有联合管理机制

已有一个 VS Code 多根工作区文件（位于 `stargazing-core` 仓库根目录）：

```json
// mcp-stargazing.code-workspace
{
    "folders": [
        { "path": "../mcp-stargazing" },
        { "path": "../stargazing-place-finder" },
        { "path": "." }
    ]
}
```

这个工作区文件可以同时打开三个仓库，但仅此而已——没有统一的任务、脚本或状态管理。

---

## 2. 当前工作流痛点

### 痛点 A: 跨仓库变更的 "多米诺骨牌"

当 `stargazing-core` 新增一个字段时：

```
1. 修改 stargazing-core → PR → merge → 等 PyPI 发布
2. 修改 stargazing-place-finder → 更新 core 版本依赖 → PR → merge → 等 PyPI 发布
3. 修改 mcp-stargazing → 更新 spf 版本依赖 → PR → merge → 等 PyPI 发布
```

每一步都是独立的 PR+review+发布周期，一个简单的字段新增可能需要 3 天才能在所有下游生效。

### 痛点 B: 多仓库状态不可见

```bash
# 想知道三个仓库各自在哪个分支、是否有未提交的更改
cd ~/workspace/stargazing-core && git status    # 手动
cd ~/workspace/stargazing-place-finder && git status  # 手动
cd ~/workspace/mcp-stargazing && git status     # 手动
```

无法一目了然地看到三个仓库的全局状态。

### 痛点 C: 关联功能分支命名不一致

```
stargazing-core:     feature/weather-tile-overlay
stargazing-place-finder: feature/weather-tile-overlay  ← 手动保持同名
mcp-stargazing:      (不需要改)
```

当跨仓库特性需要同时修改两个仓库时，没有机制保证分支命名一致或关联。

### 痛点 D: 统一的测试/检查不可行

```bash
# 想在所有仓库运行测试 —— 没有统一命令
# 只能逐个 cd 进去执行
```

### 痛点 E: 上游变更后下游忘记更新

`stargazing-core` 发布了 `0.5.0`，但 `mcp-stargazing` 的 `pyproject.toml` 还在依赖 `0.4.0`，直到 CI 报错才发现。

---

## 3. 方案对比

### 方案 A: 合并为 Monorepo

将三个仓库合并为一个大仓库，使用 `uv` workspace 管理包间依赖。

**目录结构：**
```
stargazing/
├── packages/
│   ├── core/           # 原 stargazing-core
│   ├── place-finder/   # 原 stargazing-place-finder
│   └── mcp/            # 原 mcp-stargazing
├── pyproject.toml      # workspace 根配置
└── .github/workflows/  # 统一的 CI/CD
```

**优点：**
- 一次 PR 覆盖所有相关包
- 统一的版本号、lint、test
- 本地路径依赖 `"stargazing-core = { path = "../core" }"` 即时生效

**缺点：**
- 破坏现有的 PyPI OIDC 发布流程（每个包分别发布）
- CI 需要 "affected" 检测（只构建/测试变更的包），否则每次跑全量太慢
- Python monorepo 工具链不如 JS 成熟（`uv workspaces` 还在 beta）
- 三个仓库的 Python 版本要求不同（core: 3.9+, MCP: 3.13+），不好统一
- **迁移成本高**：需要合并 Git 历史、重写 CI/CD、重新配置 PyPI Trusted Publishing

**结论：** 对当前规模（3 个包，1 个开发者）来说，迁移 monorepo 的**固定成本太高，边际收益太薄**。不推荐。

---

### 方案 B: 保持多仓库，不加工具

维持现状，不做任何变化。

**优点：** 零成本。

**缺点：** 痛点 A–E 持续存在。随着功能增长（如 telescope 模式、天气图层等跨仓库特性），摩擦会越来越大。

**结论：** 短期可行，但不是长期方案。

---

### 方案 C: 多仓库 + 轻量编排工具 ✅ 推荐

保持三个独立仓库，引入轻量级工具来统一日常操作。

**优点：**
- 不改变仓库结构、CI/CD、PyPI 发布流程
- 渐进式引入——工具是可选的，不影响现有工作流
- 低成本（1 天内可完成配置）

**缺点：**
- 无法做到 monorepo 的原子提交（但可以用脚本缓解）
- 多一个工具需要学习

**结论：** 最适合当前场景的方案。

---

## 4. 推荐方案：多仓库 + 轻量编排

### 4.1 工具选型

| 用途 | 推荐工具 | 理由 |
|------|----------|------|
| **多仓库状态一览** | [gita](https://github.com/nosarthur/gita) | Python 编写，pip 安装，彩色输出，支持自定义命令 |
| **多仓库批量命令** | gita + 自定义 shell 脚本 | `gita` 的 `--cmd` 模式支持在分组仓库执行相同命令 |
| **IDE 工作区** | VS Code Multi-root Workspace | 已有，需增强 tasks 和 settings |
| **跨仓库分支管理** | 自定义脚本 `repo-sync` | 轻量，10 行 shell |
| **跨仓库发布** | 自定义脚本 `release-chain` | 串联 core → SPF → MCP 发布流程 |

### 4.2 为什么不选其他工具

| 工具 | 淘汰理由 |
|------|----------|
| Git Submodules | 易出错，detached HEAD 问题，对新手不友好 |
| Git Subtree | 合并历史复杂，不适合需要独立发布到 PyPI 的场景 |
| Turborepo / Nx / Lerna | 面向 JS/TS 生态，Python 项目完全不适用 |
| Bazel / Buck2 | 配置复杂度远超当前项目规模的需要 |
| myrepos (mr) | 功能强大但 Perl 依赖，Python 项目用 Python 工具更自然 |
| ggman | Go 编写，需要 Go 工具链，用 Python 工具更自然 |

---

## 5. 工具配置指南

### 5.1 gita — 多仓库状态管理

#### 安装

```bash
pip install gita
# 或
uv tool install gita
```

#### 配置

```bash
# 在 ~/workspace/ 下初始化
cd ~/workspace
gita init

# 添加三个仓库（gita 自动检测已有 git 仓库）
gita add stargazing-core
gita add stargazing-place-finder  
gita add mcp-stargazing

# 创建分组（按依赖层级）
gita group add upstream stargazing-core
gita group add midstream stargazing-place-finder
gita group add downstream mcp-stargazing
```

#### 日常使用

```bash
gita ll           # 彩色一览表：所有仓库的分支、状态、ahead/behind

# 输出示例：
# stargazing-core            main      [✓]  ← clean
# stargazing-place-finder    feature/weather-tile-overlay  [M]  ← 有未提交修改
# mcp-stargazing             main      [↑2]  ← 领先远程 2 个提交

gita fetch        # 批量 fetch
gita pull         # 批量 pull（仅 fast-forward）

# 在指定分组执行命令
gita -g upstream exec "uv sync && uv run pytest"
gita -g midstream exec "uv sync"
gita -g downstream exec "uv sync && uv run pytest -v tests/"
```

### 5.2 VS Code 工作区增强

更新 `mcp-stargazing.code-workspace` 为完整的工作区配置：

```json
{
    "folders": [
        { "name": "MCP Stargazing", "path": "../mcp-stargazing" },
        { "name": "SPF (Place Finder)", "path": "../stargazing-place-finder" },
        { "name": "Stargazing Core", "path": "." }
    ],
    "settings": {
        "python.testing.pytestEnabled": true,
        "python.testing.cwd": "${workspaceFolder}",
        "editor.formatOnSave": true,
        "python.linting.enabled": true,
        // 搜索排除 node_modules
        "search.exclude": {
            "**/node_modules": true,
            "**/dist": true,
            "**/.venv": true
        }
    },
    "tasks": [
        {
            "label": "🔧 All: Install Dependencies",
            "type": "shell",
            "command": "gita exec 'uv sync'",
            "problemMatcher": []
        },
        {
            "label": "🧪 All: Run Tests",
            "type": "shell",
            "command": "gita exec 'uv run pytest'",
            "problemMatcher": []
        },
        {
            "label": "🔍 All: Lint Check",
            "type": "shell",
            "command": "gita exec 'uv run ruff format --check src/ tests/ && uv run ruff check src/ tests/'",
            "problemMatcher": []
        },
        {
            "label": "🧹 All: Format Code",
            "type": "shell",
            "command": "gita exec 'uv run ruff format src/ tests/ && uv run ruff check --fix src/ tests/'",
            "problemMatcher": []
        }
    ]
}
```

### 5.3 跨仓库分支同步脚本

创建 `~/workspace/repo-sync.sh`（可放在任一仓库的 `scripts/` 中）：

```bash
#!/usr/bin/env bash
# repo-sync.sh — 跨仓库创建同名分支、统一状态检查
# 用法:
#   repo-sync branch feat/new-feature  → 三个仓库都创建 feat/new-feature 分支
#   repo-sync status                   → 显示所有仓库状态
#   repo-sync exec "uv sync"           → 在所有仓库执行命令

set -e

REPOS=(
    "$HOME/workspace/stargazing-core"
    "$HOME/workspace/stargazing-place-finder"
    "$HOME/workspace/mcp-stargazing"
)

case "${1:-}" in
    branch)
        BRANCH="${2:-}"
        if [ -z "$BRANCH" ]; then
            echo "Usage: repo-sync branch <branch-name>"
            exit 1
        fi
        for repo in "${REPOS[@]}"; do
            echo "→ $(basename $repo): git checkout -b $BRANCH"
            (cd "$repo" && git checkout main && git pull --ff-only origin main && git checkout -b "$BRANCH")
        done
        ;;
    status)
        for repo in "${REPOS[@]}"; do
            echo "=== $(basename $repo) ==="
            (cd "$repo" && git status --short --branch)
            echo
        done
        ;;
    exec)
        shift
        CMD="$*"
        for repo in "${REPOS[@]}"; do
            echo "→ $(basename $repo): $CMD"
            (cd "$repo" && eval "$CMD") || echo "  ⚠️  failed (continuing)"
        done
        ;;
    *)
        echo "Usage: repo-sync {branch|status|exec} [args...]"
        ;;
esac
```

---

## 6. 跨仓库发布流程

当一个变更跨越多个仓库时，使用以下标准化流程：

### 场景 1: 底层变更（Core → 向上传播）

```
stargazing-core 新增/修改数据模型
        │
        ▼
1. stargazing-core PR → merge → 发布 v0.X.0 到 PyPI
        │
        ▼
2. stargazing-place-finder: uv add "stargazing-core>=0.X.0"
   → 适配代码 → PR → merge → 发布 v0.Y.0 到 PyPI
        │
        ▼
3. mcp-stargazing: uv add "stargazing-place-finder>=0.Y.0"
   → 适配代码（如需要）→ PR → merge → 发布 v0.Z.0
```

**加速策略：** 步骤 1 merge 后，**不等 PyPI 发布**，步骤 2 和 3 可以同时准备 PR：
- SPF 使用 `uv add stargazing-core@git+https://github.com/StarGazer1995/stargazing-core@main` 临时指向 Git commit
- 等 PyPI 发布完成后再切回版本号依赖
- 这个策略可以将 3 天的链路压缩到 1 天内完成

### 场景 2: 中层变更（SPF）

```
stargazing-place-finder 新增 API 或前端功能
        │
        ▼
1. SPF PR → merge → 发布到 PyPI
        │
        ▼
2. mcp-stargazing: uv add "stargazing-place-finder>=0.Y.0"
   → 注册新的 MCP 工具（如需要）→ PR → merge
```

### 场景 3: 顶层变更（MCP）

```
mcp-stargazing 新增工具或修复
        │
        ▼
1. MCP PR → merge → 发布到 PyPI → Docker 构建
   （不涉及上游）
```

### 自动化发布脚本

```bash
#!/usr/bin/env bash
# release-chain.sh — 串联跨仓库发布检查
# 在发布前运行，验证依赖链是否一致

echo "=== 依赖链一致性检查 ==="

# 检查 stargazing-core 的 PyPI 最新版本
CORE_PYPI=$(curl -s https://pypi.org/pypi/stargazing-core/json | jq -r '.info.version')
CORE_PYPROJECT=$(grep 'version' ~/workspace/stargazing-core/pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
echo "stargazing-core:  PyPI=$CORE_PYPI  pyproject.toml=$CORE_PYPROJECT"

# 检查 SPF 依赖的 core 版本
SPF_DEPS_CORE=$(grep 'stargazing-core' ~/workspace/stargazing-place-finder/pyproject.toml)
echo "stargazing-place-finder → core: $SPF_DEPS_CORE"

# 检查 MCP 依赖的 SPF 版本
MCP_DEPS_SPF=$(grep 'stargazing-place-finder' ~/workspace/mcp-stargazing/pyproject.toml)
echo "mcp-stargazing → SPF: $MCP_DEPS_SPF"

echo "=== 检查完成 ==="
```

---

## 7. FAQ

### Q: 为什么不直接用 Git Submodules？

Git Submodules 的核心问题是：
- 子模块指向特定 commit，不会自动更新到最新版本（detached HEAD）
- `git clone --recursive` 容易被遗忘
- merge 冲突处理复杂
- 与 PyPI 发布流程不兼容（PyPI 需要版本号依赖，不是 git commit 依赖）

### Q: 如果未来团队扩大到 5 人以上呢？

如果团队扩大且跨仓库变更频繁，可以考虑迁移到 Monorepo。但建议在以下条件达成时才考虑：
1. 团队 ≥5 人
2. 跨仓库 PR 占 PR 总数的 30% 以上
3. `uv workspaces` 达到 stable 状态

### Q: gita 和 VS Code 工作区怎么选？

两者互补，不是互斥：
- **gita** → 命令行操作：一键看状态、批量跑命令
- **VS Code 工作区** → IDE 操作：跨仓库搜索、统一调试、GUI 文件树

推荐同时使用。

### Q: 这些工具会影响现有的 CI/CD 吗？

完全不影响。gita、repo-sync 等工具完全在本地运行，不改变任何仓库的结构、Git 历史或 CI 配置。

---

## 附录 A: 一键设置脚本

```bash
#!/usr/bin/env bash
# setup-multi-repo.sh — 一键配置多仓库管理工具

set -e

echo "🔧 设置 Stargazing 多仓库管理工具..."

# 安装 gita
pip install gita

# 初始化 gita
cd ~/workspace
gita init
gita add stargazing-core
gita add stargazing-place-finder
gita add mcp-stargazing

# 创建分组
gita group add upstream stargazing-core
gita group add midstream stargazing-place-finder
gita group add downstream mcp-stargazing

# 安装 repo-sync 脚本
cp ~/workspace/stargazing-place-finder/scripts/repo-sync.sh /usr/local/bin/repo-sync 2>/dev/null || \
    echo "⚠️  repo-sync 脚本需手动复制（需要 sudo）"

echo "✅ 设置完成！"
echo ""
echo "常用命令:"
echo "  gita ll          # 查看所有仓库状态"
echo "  gita fetch       # 批量 fetch"
echo "  repo-sync status # 详细状态"
echo "  repo-sync branch feat/xxx  # 跨仓库创建分支"
```

## 附录 B: 相关资源

- [gita GitHub](https://github.com/nosarthur/gita)
- [VS Code Multi-root Workspaces](https://code.visualstudio.com/docs/editor/multi-root-workspaces)
- [uv Workspaces (beta)](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [monorepo.tools](https://monorepo.tools) — Monorepo 工具对比
