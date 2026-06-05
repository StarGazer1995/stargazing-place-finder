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
├── mountain_peak/         # Mountain peak finding & filtering
├── location_finder/       # Observatory & viewpoint discovery
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
| Run all tests | `uv run python src/test/run_src_tests.py` |
| Run single test | `uv run pytest src/<module>/test/test_*.py` |
| Start web app | `bash start.sh` (API + HTTP server on :8000) |
| Start API only | `uv run python src/light_pollution/light_pollution_api.py` |
| Generate maps | `uv run python src/utils/styled_map_generator.py` |
| CLI usage | `uv run stargazing-finder --center LAT LON RADIUS_KM` |
| Build package | `uv run python publish_to_pypi.py` |
| Lint | No linter configured; check with `ruff` if installed |

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
- Internal cross-module imports use `try/except ImportError` fallback pattern:
  ```python
  try:
      from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
  except ImportError:
      import sys, os
      sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))
      from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
  ```
- For new code, prefer `import` from the installed package when possible.

### Module Patterns
- Each module exposes a `public_api.py` with lazy-initialized global analyzer instances
- `__init__.py` files re-export key symbols for clean imports
- Dataclasses used for structured data (`@dataclass`)

### Testing
- Every source module must have a `test/` directory with `__init__.py` and `test_*.py`
- Tests run standalone (can be executed directly with `python test_*.py`)
- Use `FAST_TESTS` env var to gate slow tests
- Environment is patched so `src/` is on `PYTHONPATH`

### Naming
- `snake_case` for files, functions, variables
- `PascalCase` for classes
- Chinese comments and docstrings are acceptable (bilingual project)

## Key Design Decisions

1. **Unified Location model** — All location types (peaks, observatories, viewpoints) share a single `Location` dataclass. Older `Peak`, `Observatory`, `Viewpoint` are maintained as backward-compatible aliases.

2. **Lazy initialization** — Global analyzers (`LightPollutionAnalyzer`, `RoadConnectivityChecker`) are initialized on first use, not at import time. This avoids expensive setup for CLI tools that may not use all features.

3. **Package resource loading** — GeoTIFF data is bundled via `importlib.resources` / `setuptools` `package-data`, not relative file paths. See `light_pollution/public_api.py:_default_geotiff_path()`.

4. **Database is optional** — PostGIS-backed queries are behind a `PostGISClient` class. The system falls back to Overpass API when no database config is provided.

5. **Cache layer** — Geocoding and elevation lookups are cached on disk via `src/cache/` module (gitignored except `__init__.py` and `cache_config.py`).

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

1. If adding a new sub-analyzer, follow the pattern: `public_api.py` + lazy global init + `test/` directory
2. If changing the data model, update `utils/` unified dataclasses and all type aliases
3. Ensure backward compatibility — existing import paths should continue to work
4. Update `CHANGELOG.md` with the version bump and description
5. Version in `pyproject.toml` must match the changelog entry
6. Run full test suite before finalizing (`uv run python src/test/run_src_tests.py`)
