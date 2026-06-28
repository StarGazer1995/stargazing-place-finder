# AGENTS.md — Stargazing Place Finder

Guidance for AI coding agents working on this repository.

## Project Overview

A Python application for finding optimal stargazing locations using VIIRS DNB 2025 satellite light pollution data (GeoTIFF), geographic information analysis, and road connectivity detection. Targets Chinese geography but supports international expansion.

## Environment & Setup

- **Python**: 3.12 (`.python-version`), supports 3.9–3.12
- **Package manager**: `uv` (lockfile: `uv.lock`)
- **Virtual env**: `.venv/` (gitignored)
- **Install**: `uv sync`
- **Dev deps**: `uv sync --dev` (adds pytest, pytest-cov, build, twine, freezegun, etc.)

## Project Structure

```
src/
├── light_pollution/       # Light pollution analysis (VIIRS GeoTIFF backend)
│   └── resources/         # viirs_china_2025.tif (GeoTIFF data)
├── cache/                 # Unified cache configuration (disk + OSMnx)
├── road_connectivity/     # Road accessibility scoring
├── stargazing_analyzer/   # Main orchestrator: combines all modules
│   ├── cli.py             # CLI entry point (`stargazing-finder`)
│   └── public_api.py      # Public Python API
├── stargazingplacefinder/ # Top-level package re-exports
├── utils/                 # KML parser, map generator, unified dataclasses
└── test/                  # Test runners
```

Each module has a `test/` subdirectory with `test_*.py` files.

Packages are configured in `pyproject.toml` via `[tool.setuptools.packages.find]` with `where = ["src"]`.

## Build / Run / Test Commands

| Action | Command |
|--------|---------|
| Install deps | `uv sync` |
| Run all tests | `uv run pytest` |
| Run single test | `uv run pytest src/<module>/test/test_*.py` |
| Start web app | `bash start.sh` (API + HTTP server on :8000) |
| Start API only | `uv run python src/light_pollution/light_pollution_api.py` |
| Generate maps | `uv run python src/utils/styled_map_generator.py` |
| CLI usage | `uv run stargazing-finder --center LAT LON RADIUS_KM` |
| Build docs | `uv run sphinx-build -b html docs/sphinx/source docs/sphinx/build` |
| Build package | `uv run python publish_to_pypi.py` |
| Lint | `uv run ruff format --check src/ && uv run ruff check src/` |
| Security scan | `uv run bandit -r src/ -c pyproject.toml --severity-level-medium` |

Run tests with `FAST_TESTS=1` for a faster test mode that skips slow geospatial operations.

## Coding Conventions

### Style
- Python 3.9+ compatible (no `match`/`case` or PEP 695 generics)
- UTF-8 with `# -*- coding: utf-8 -*-` header
- Google-style docstrings (Args/Returns/Raises)
- Type hints on all public functions
- 4-space indentation

### Imports
- Standard library → third-party → first-party ordering
- **Legacy fallback pattern** (existing code only — do NOT use in new code):
  ```python
  try:
      from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
  except ImportError:
      import sys, os
      sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
      from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
  ```
  This pattern exists for historical reasons (supporting both `python -m` and direct script execution). New code must use normal package imports — the `pyproject.toml` `pythonpath = ["src"]` config and `uv run` handle path resolution.
- Clean up legacy import fallbacks when touching old files.

### Module Patterns
- Each module exposes a `public_api.py` with lazy-initialized global analyzer instances — thread-safe via `threading.RLock` double-checked locking
- `__init__.py` files re-export key symbols for clean imports
- **Pydantic v2 `BaseModel`** for all data transfer objects — use `Field()` validators, `model_dump()`, and type hints. Legacy `@dataclass` usage should be migrated to Pydantic when touching old files.

### Testing
- Every source module must have a `test/` directory with `__init__.py` and `test_*.py`
- Tests run standalone (can be executed directly with `python test_*.py`)
- Use `FAST_TESTS` env var to gate slow tests
- Environment is patched so `src/` is on `PYTHONPATH`
- **新加代码的差异覆盖度必须达到 100%** — `diff-cover --fail-under=100` 在 CI 中强制执行，覆盖所有新增/修改行

### Naming
- `snake_case` for files, functions, variables
- `PascalCase` for classes
- Chinese comments and docstrings are acceptable (bilingual project)

## Key Design Decisions

1. **Unified Location model** — All location types (peaks, observatories, viewpoints) share a single `Location` Pydantic v2 model (`src/models/location.py`). Older `Peak`, `Observatory`, `Viewpoint` are type aliases for backward compatibility. Distinguish by `location_type: Literal["mountain_peak", "observatory", "viewpoint"]`.

2. **Lazy initialization** — Global analyzers (`LightPollutionAnalyzer`, `RoadConnectivityChecker`) are initialized on first use, not at import time. Thread-safe via `threading.RLock` with double-checked locking. This avoids expensive setup for CLI tools that may not use all features.

3. **Package resource loading** — GeoTIFF data is bundled via `importlib.resources` / `setuptools` `package-data`, not relative file paths. See `light_pollution/public_api.py:_default_geotiff_path()`.

4. **Database is optional** — PostGIS-backed queries use `PostgisBackend` with `SimpleConnectionPool(1, 4)` for connection reuse. The system falls back to Overpass API via `OverpassBackend` when no database config is provided.

5. **Cache layer** — Two-level cache (memory dict + disk pickle) used for GIS queries (`GisQueryCache`) and road connectivity results (`RoadAccessInfoCache`). **Note:** neither implementation is thread-safe — no file locks or atomic writes. Avoid concurrent access to the same cache key.

## Dependencies

Core: `flask`, `flask-cors`, `folium`, `matplotlib`, `numpy`, `pillow`, `scipy`, `osmnx`, `networkx`, `geopy`, `psycopg2-binary`, `requests`, `rasterio`

Dev: `pytest`, `pytest-cov`, `requests-mock`, `responses`, `freezegun`, `build`, `twine`

## Documentation

- `docs/` contains per-module system design docs and usage guides
- README is bilingual (Chinese + English via `README.md` / `README_EN.md`)
- `CHANGELOG.md` tracks version history
- `PYPI_PUBLISH_GUIDE.md` covers PyPI publishing

## Environment Variables

- `STARGAZING_DB_CONFIG` — Path to PostGIS database config file (JSON)
- `FAST_TESTS=1` — Skip slow geospatial operations in tests

## When Making Changes

1. If adding a new sub-analyzer, follow the pattern: `public_api.py` + lazy global init (with `threading.RLock`) + `test/` directory
2. If changing the data model, update `src/models/` Pydantic v2 models and all type aliases
3. Use Pydantic v2 `BaseModel` (not `@dataclass`) for new data structures
4. Ensure backward compatibility — existing import paths should continue to work
5. Update `CHANGELOG.md` with the version bump and description
6. Version in `pyproject.toml` must match the changelog entry
7. Run full test suite before finalizing (`uv run pytest`)
8. See `CLAUDE.md` → Known Sharp Edges for current technical debt items to be aware of

## CI/CD & Release Workflow

### PyPI Publishing: OIDC Trusted Publishing (No API Token)

**Do NOT use `PYPI_API_TOKEN` or any API-token-based approach.** GitHub Secrets consistently resolved to empty strings in this repository's Actions environment — the root cause was never identified. Instead, use PyPI Trusted Publishing (OIDC):

- **Workflow file**: `.github/workflows/release.yml` (triggered by `v*` tags)
- **Permission required**: `id-token: write` at job level
- **Publisher action**: `pypa/gh-action-pypi-publish@release/v1` (no password/token config)
- **PyPI configuration**: On pypi.org → Publishing → Trusted Publisher Mgmt:
  - Owner: `StarGazer1995`
  - Repository: `stargazing-place-finder`
  - Workflow: `release.yml`

**How to release a new version:**
```bash
# 1. Create a release branch, bump version in pyproject.toml and CHANGELOG.md
git checkout -b release/vX.Y.Z
# ... edit pyproject.toml and CHANGELOG.md ...
git add -A && git commit -m "chore: bump version to vX.Y.Z"
git push origin release/vX.Y.Z
# 2. Create PR from release/vX.Y.Z → main, get it reviewed and merged
# 3. After merge, checkout main and tag the merge commit
git checkout main && git fetch origin && git reset --hard origin/main
git tag vX.Y.Z
git push origin vX.Y.Z
# CI will automatically build, verify, and publish to PyPI
# ⚠️ Push the tag ONLY ONCE — do not force-push or re-push the same tag.
```

### Copilot Code Review

GitHub Copilot automatic PR code review **requires a Business or Enterprise subscription**. It does NOT work with personal/individual Copilot plans, even if enabled in repository Rules settings. Do not attempt to set up `copilot-review.yml` workflows — they will not trigger.

## Commit Policy

### 只提交必要的文件

每次提交前必须确认只包含**必要的源代码文件**。以下文件类型不得提交：

| 类型 | 原因 | 示例 |
|------|------|------|
| **未完成的设计文档** | 草稿、计划、笔记等仅在本地保留 | `docs/performance_optimization_plan.md` |
| **本地配置** | 含密码、token 等敏感信息 | `config/postgis_config.*` |
| **字节码缓存** | `.gitignore` 已忽略 `__pycache__/` | `*.pyc` |
| **地图输出 / 可视化数据** | 生成物，非源码 | `map_output/`, `visualization_output/` |

**检查流程**：`git status` 确认只有预期的文件在变更列表中，再 `git add` 精确指定文件（不要用 `git add .` 或 `git add -A`）。

## Common Pitfalls

### GitHub Secrets Empty in Actions
- `secrets.PYPI_API_TOKEN` and similar repository secrets may resolve to empty strings in workflow runs with no visible error.
- Expression-based secrets (`${{ secrets.NAME }}`) are only available in expression context, not as automatic shell environment variables.
- **Workaround**: Use OIDC Trusted Publishing for PyPI instead of API tokens.

### `.gitignore` Glob Pitfalls
- Patterns like `*cache*` match directory paths, not just filenames.
- `src/cache/test/` was matched by `*cache*`, blocking test files from being tracked.
- **Fix**: Use negations like `!src/cache/**` to un-ignore specific directories.

### Branch Protection on `main`
- **ALL direct pushes to `main` are rejected** — every change must go through a Pull Request.
- Force push is also blocked.
- Workflow for any change: `git checkout -b <branch> → commit → push → create PR → merge → delete branch`.
- To sync local main after a merged PR: `git checkout main && git fetch origin && git reset --hard origin/main`.

### `LightPollutionAnalyzer` GeoTIFF Migration
- As of v0.4.0, the analyzer uses GeoTIFF data (not KML).
- Constructor takes `geotiff_path` (keyword arg, default `None` for lazy init).
- Old methods `_image_cache_dir` and `clear_image_cache()` no longer exist.
- Use `close()` to release resources.

### Tag Push Triggers Duplicate PyPI Publish
- PyPI **does not allow overwriting** a published version. Once `vX.Y.Z` is uploaded, any re-upload of the same version will fail with `400 File already exists`.
- If the tag `vX.Y.Z` is pushed twice (even force-pushed to a different commit), the second run will try to re-publish the same artifacts and fail.
- **Fix**: Push the release tag **exactly once** after the PR is merged. Do not force-push or re-push the same tag.
- Correct order: merge release PR into `main` → create tag on the merge commit → `git push origin vX.Y.Z` (one time only).

## Database Configuration

PostGIS database connection is configured via JSON or TOML:

```json
{
  "host": "192.168.1.8",
  "port": 5455,
  "database": "osm_db",
  "user": "postgres",
  "password": "your_password"
}
```

Config file path: set `STARGAZING_DB_CONFIG` env var, or place at `config/postgis_config.json` / `config/postgis_config.toml`.
