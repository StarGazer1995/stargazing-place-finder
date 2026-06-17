# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also `AGENTS.md` for broader agent guidance including environment setup, coding conventions, and CI/CD details.

## Quick Commands

| Action | Command |
|--------|---------|
| Install deps | `uv sync` |
| Run all tests | `uv run pytest` |
| Run single test file | `uv run pytest src/<module>/test/test_*.py` |
| Run with fast mode | `FAST_TESTS=1 uv run pytest` |
| Lint + format check | `uv run ruff format --check src/ && uv run ruff check src/` |
| Security scan | `uv run bandit -r src/ -c pyproject.toml --severity-level medium` |
| Start full web app | `bash start.sh` (API :5001 + static server :8000) |
| Start API only | `uv run python -m light_pollution.light_pollution_api` |
| CLI | `uv run stargazing-finder --center LAT LON RADIUS_KM` |
| Build docs | `uv run sphinx-build -b html docs/sphinx/source docs/sphinx/build` |

## Architecture

```
User Layer:   CLI (stargazing-finder)  |  Web UI (Leaflet.js SPA)  |  REST API (Flask :5001)
                 \                          |                        /
Orchestrator:           StargazingLocationAnalyzer (stargazing_analyzer/)
                              /              \
Analysis:    LightPollutionAnalyzer     RoadConnectivityChecker
             (VIIRS GeoTIFF → Bortle)   (OSM road distance scoring)
                              \              /
Infra:       GisQueryService ──┬── PostgisBackend (fast, needs config)
                               └── OverpassBackend (slow fallback)
             ElevationBackend (4-level fallback: OSM tag → PostGIS → API → 0.0)
             Cache layer (disk + memory, MD5-keyed)
             Models (Pydantic v2 DTOs)
```

**Data flow**: CLI/API → `StargazingLocationAnalyzer.analyze_area()` → search locations → batch light pollution → preload road network → `ThreadPoolExecutor(max_workers=4)` parallel per-location pipeline (build → enrich → score) → filter/sort → results.

**Scoring** (0–100): light pollution 0–35, town isolation 0–20, road accessibility 0–20, elevation+prominence 0–15, location type 0–10.

## Key Source Layout

```
src/
├── stargazing_analyzer/    → orchestrator (analyzer, CLI, public_api)
├── light_pollution/        → VIIRS GeoTIFF analysis + Flask API server
│   └── resources/          → viirs_china_2025.tif (~100MB, from GitHub Release)
├── road_connectivity/      → road distance via OSMnx or PostGIS kNN
├── gis_service/            → unified GIS query (PostGIS/Overpass/Elevation backends)
├── models/                 → Pydantic v2 models + exception hierarchy
├── cache/                  → disk + memory cache layer
├── config/                 → StargazingConfig (Pydantic, extra="forbid")
├── utils/                  → KML, map gen, geo helpers
├── source/                 → web frontend static assets (HTML/JS/CSS)
└── stargazingplacefinder/  → top-level package re-exports
```

## Critical Design Patterns

1. **Lazy global singletons** — `public_api.py` modules hold module-level `_analyzer = None` variables, initialized on first use. No locks. Tests manually reset these. Be careful with concurrent access.

2. **try/except ImportError for cross-imports** — Many modules use this fallback to support both `python -m` and direct script execution. Prefer installed-package imports in new code.

3. **PostGIS is optional** — `GisQueryService` auto-detects config and falls back to Overpass API. No database config → pure Overpass mode.

4. **GeoTIFF via `importlib.resources`** — Not file paths. Use `importlib.resources.files("light_pollution")` to locate the tif.

5. **`Location` is the single data model** — `Peak`, `Observatory`, `Viewpoint` are just `Location` type aliases (not subclasses). Distinguish by `location_type` string field.

## Testing

- Config in `pyproject.toml`: `pythonpath = ["src"]`, `testpaths = ["src"]`
- Tests live in `test/` subdirectories next to source modules
- `src/conftest.py` has shared fixtures (`bbox_beijing`, `mock_gis_service`, `sample_stargazing_location`, etc.)
- CI enforces **100% diff-cover** on PRs (new/modified lines must be fully covered)
- Overall coverage floor: 60% (`fail_under`)
- Some older tests use `sys.path.insert(0, ...)` — ignore, `pyproject.toml` handles the path
- Some older tests use manual `run_all_tests()` runners with `print()` instead of pytest asserts — prefer rewriting to standard pytest when touching those files

## Known Sharp Edges

- **No PostGIS connection pool** — every query creates a new `psycopg2.connect()`. If adding batch operations, add a pool first.
- **Bare `except Exception` in ~5 places** — hides programming errors. Bandit BLE001 is suppressed with `# noqa`.
- **Frontend hides all UI controls on load** (`app.js` ~line 1332). Search, legend, language toggle all get `display: none`. Only the map + analysis toggle remain visible.
- **Frontend `generateMockData()` is dead code** but still referenced; real data path is `loadLightPollutionDataPoints()`.
- **`Ctrl+L` keyboard shortcut conflicts** with browser focus-address-bar.
- **Flask `app.run()` is dev-only** — no gunicorn/uwsgi config for production.
- **Duplicate functions**: `brightness_to_bortle()`, `bortle_to_sqm()`, `calculate_distance()` appear in 3 files. Fix bugs in all three.
- **TOML config parsing** is duplicated between `config/stargazing_config.py` and `gis_service/config.py`.
- **Tests share mutable disk state** (cache directory) — not fully isolated.
- **Tag push triggers PyPI publish** — push a `v*` tag only ONCE. PyPI does not allow overwriting versions.

## Commit Policy

- **Never commit internal planning documents** — code review findings, implementation plans, design drafts, or meeting notes stay local or in `.claude/plans/`. Only commit source code, docs, and config that are intended for the public repo.
- Use `git status` to verify only expected files are staged before committing.

## Environment Variables

- `STARGAZING_DB_CONFIG` — path to PostGIS config file (JSON or TOML)
- `FAST_TESTS=1` — skip slow geospatial operations in tests
- `WEB_PORT` / `API_PORT` — override defaults in `start.sh` (8000/5001)

## Release Process

1. Branch `release/vX.Y.Z`, bump version in `pyproject.toml` and `CHANGELOG.md`
2. PR → review → merge to `main`
3. `git checkout main && git fetch origin && git reset --hard origin/main`
4. `git tag vX.Y.Z && git push origin vX.Y.Z`
5. CI auto-publishes to PyPI via OIDC Trusted Publishing (no API token)
6. **Never** force-push or re-push the same tag.
