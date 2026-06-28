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

1. **Lazy global singletons** — `public_api.py` modules hold module-level `_analyzer = None` variables, initialized on first use. Thread-safe via `threading.RLock` with double-checked locking (`_require_analyzer()` pattern). Tests use `reset_analyzer()` for teardown between cases.

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

### Real issues (verified 2026-06-28)

- **Two `except (XError, Exception)` redundancies** — `stargazing_location_analyzer.py:251` and `road_connectivity_checker.py:373`. Both catch `(SpecificError, Exception)` where `SpecificError` is an `Exception` subclass, making this functionally `except Exception`. Both silently return `[]` or `None` without re-raising, which masks programming bugs like `TypeError` or `AttributeError`. Fix by removing `Exception` from the tuple.
- **Cache implementations are not thread-safe** — `RoadAccessInfoCache` (`road_connectivity_checker.py`) and `GisQueryCache` (`gis_service/caching.py`) both write pickle files directly without file locks or atomic temp-file+rename. `RoadAccessInfoCache` has a TOCTOU race: reads old cache → merges new data → writes back, and concurrent callers silently overwrite each other. Both also lack in-memory locking for their `dict`-backed caches.
- **Flask `app.run()` is dev-only** — no gunicorn/uwsgi/waitress config, no Dockerfile. `start.sh` runs Flask's single-process dev server and Python's `http.server` as background processes. Not suitable for production concurrency.
- **`calculate_distance` has a standalone duplicate** in `light_pollution/light_pollution_api.py` — identical Haversine algorithm but takes `(lat1, lon1, lat2, lon2)` floats instead of `(GeoCoordinate, GeoCoordinate)`. The version in `gis_service/parsers.py` is the canonical one; the `stargazing_place_finder.py` version is a thin delegate wrapper. Consolidate the API version to delegate to `parsers.py` by constructing temporary `GeoCoordinate` objects.
- **TOML import boilerplate duplicated** — the 4-line `try: import tomllib except ImportError: import tomli as tomllib` stanza appears identically in `config/__init__.py` and `gis_service/config.py`. Extract a shared `_load_toml(path) -> dict` helper.
- **`BatchElevationQuery.get_statistics()`** (deprecated module) still uses raw `psycopg2.connect()` — the only remaining non-pool connection in production code. Migrate to `PostgisBackend.get_elevation_statistics()` or remove the deprecated module.
- **Tests share mutable disk state** (cache directory) — not fully isolated between test runs.
- **Tag push triggers PyPI publish** — push a `v*` tag only ONCE. PyPI does not allow overwriting versions.

### Things previously listed that are no longer true

- ~~No PostGIS connection pool~~ → `PostgisBackend` uses `SimpleConnectionPool(1, 4)` since at least v0.6.x.
- ~~Bare except Exception in ~5 places~~ → Only 2 remain (listed above). All other 57 except blocks catch specific exception types.
- ~~Frontend hides all UI controls on load~~ → Only loading overlay and empty data panels are hidden on init — search, legend, language toggle, and mode toggle are all visible. Standard UX pattern.
- ~~`generateMockData()` dead code~~ → Does not exist anywhere in the codebase.
- ~~`brightness_to_bortle()` / `bortle_to_sqm()` duplicated~~ → Each defined exactly once in `gis_service/parsers.py`.

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
