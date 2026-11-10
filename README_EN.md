# Stargazing Place Finder

English | [中文](README.md)

## Overview

An application for stargazing enthusiasts to find optimal observation locations in China, combining light pollution analysis, road accessibility, and telescope-aware target matching.

## Features

### Location Discovery
- **Smart recommendations**: VIIRS light pollution data + PostGIS elevation + OSM road network, multi-dimensional scoring
- **Light pollution analysis**: VIIRS DNB radiance → sky-glow correction → Bortle class + SQM
- **Road connectivity**: PostGIS `planet_osm_line` graph + OSMnx fallback
- **Elevation filtering**: Prioritize high-altitude, open-view locations

Raster validity: the analyzer honors GeoTIFF NoData and GDAL masks and treats NaN/infinity as missing.
Missing pixels return `None` for point queries, `success=False` in batch results, and transparent tiles;
finite zero values without a missing-data declaration remain valid. The skyglow model normalizes over
valid samples and remains unknown without valid support; it does not impute missing raw radiance.
This is not field calibration. Legacy Web/grid display defaults still require checking source markers.
The location scoring formula is unchanged: unknown light pollution retains its existing 18-point fallback,
which is not evidence of verified observing conditions.

### Telescope & Imaging
- **Equipment presets**: Seestar S50, RedCat 51, Askar FRA300, and more
- **Target matching**: Ranked Messier/NGC objects by FOV fit, surface brightness, and filter match
- **Shooting plan**: Minute-by-minute single-night schedule with meridian flip warnings + moon separation
- **Mosaic planning**: Multi-panel grid for large targets with adjustable overlap (5–40%)

### Sky Chart & Moon
- **Interactive sky chart**: Aladin Lite with real-time RA/Dec + FOV overlay
- **Altitude curves**: All-night height profiles with suitability scoring
- **Moon phase overlay**: Real-time sun/moon positions on map

### Map & Visualization
- **Light pollution tiles**: Leaflet multi-layer (Bortle / SQM / radiance)
- **Candidate markers**: Clustered display with detail popups
- **Elevation heatmap**: Regional elevation distribution

## Quick Start

Map PNG tiles use a process-local cache (3600 seconds, up to 500 LRU entries), scoped to
the actual opened analyzer/skyglow lifetime and tile coordinates. Explicit public analyzer
reinitialization opens a new handle/model and isolates its tiles from old cached results,
including late publications. Closed/uninitialized handles cannot reuse old tiles; custom
handles without a known identity render without sharing the cache.

Reinitialization also replaces cached pixel validity in both directions: valid zero can
become declared missing, and missing can become valid zero. Late PNG publication from
the previous handle cannot overwrite the replacement's validity.

This identity is not dataset age/version validation. Replacing a file alone does not reload
it or invalidate MCP results, other analyzers or browser/CDN responses. The existing HTTP
`max-age=3600` remains; clients may still reuse old responses. Concurrent close/read resource
leases and broader source-age rules remain unverified.

GIS location queries cache PostGIS results only in the current service instance's memory
(24 hours by default; reads do not renew it). Reconstructing the service queries its actual
connection again. Overpass keeps memory/disk reuse with a backend-specific key; unlabelled
legacy entries are ignored. Clearing a database service's cache leaves shared disk files intact.
Database service reconstruction therefore loses cross-instance disk reuse; deployed performance
has not been measured. This is not configuration watching, dataset age validation or automatic
invalidation of callers' result caches. Database content, config files and GeoTIFF lifetimes
still need coordinated resource rebuilding; unknown source ages remain unknown.

```bash
uv sync
uv run uvicorn server.main:app --host 0.0.0.0 --port 5001 --reload
```

| URL | Description |
|-----|-------------|
| `http://localhost:5001/` | Web UI (Leaflet SPA) |
| `http://localhost:5001/docs` | Swagger API docs |

### Docker

```bash
docker run -p 3001:3001 -p 5001:5001 mcp-stargazing
```

## API Endpoints

### Location Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/light_pollution` | GET | Light pollution data (Bortle/SQM/radiance) |
| `/api/light_pollution/tiles/{z}/{x}/{y}.png` | GET | Light pollution raster tiles |
| `/api/coordinate_analysis` | GET | Single-point analysis |
| `/api/analyze_stargazing_area` | GET/POST | Area search (paginated + sorted) |

### Telescope

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/telescope/presets` | GET | Telescope presets |
| `/api/telescope/resolve?name=M42` | GET | Resolve ICRS coordinates in degrees from the bundled catalog first, with bounded remote lookup for other names |
| `/api/telescope/optics` | POST | Compute optical parameters |
| `/api/telescope/targets` | POST | Match deep-sky targets |
| `/api/telescope/plan` | POST | Generate shooting plan |
| `/api/telescope/mosaic` | POST | Mosaic panel planning |

The shared search field resolves locations in map/analysis mode and sky objects
in telescope mode. Exact M/NGC/IC IDs ignore whitespace and case; bundled catalog
hits return `name`, `ra`, `dec`, and `source: local_catalog` without remote lookup.
Other names have a five-second remote deadline: confirmed absence is HTTP 404
(`OBJECT_NOT_FOUND`); network failures or invalid replies are HTTP 503
(`RESOLVER_UNAVAILABLE`). Positioning is independent of survey image loading.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Web framework** | FastAPI + Uvicorn |
| **Frontend** | Leaflet.js + Aladin Lite + vanilla JS |
| **Light pollution** | rasterio + VIIRS DNB GeoTIFF |
| **Road network** | OSMnx + NetworkX + PostGIS |
| **Database** | PostGIS (elevation + spatial query) |
| **Shared library** | stargazing-core ≥ 0.1.0 (PyPI) |
| **Package manager** | uv |

## Dependency

```
stargazing-place-finder
└── stargazing-core>=0.1.0  (PyPI)
    ├── TelescopeConfig, match_telescope_targets
    ├── ShootingPlan, generate_shooting_schedule
    └── CelestialPosition, MoonInfo, GeoPoint, ...
```

## License

MIT

### Equipment and imaging ranking

The browser loads `/api/telescope/presets` from the shared core catalog and forwards
complete selected configurations to matching, plans and mosaics. The existing HOPE
D60 + ASI2600MC Air configuration is included with core 0.2.3. Custom optics remain
available if the catalog request fails; manual edits clear preset-only parameters.
Imaging requires 30 continuous sampled minutes above 25° in astronomical darkness;
midnight/dawn gates and visual magnitude limits no longer remove imaging candidates.
The base 40/30/20/10 weights cover FOV, surface brightness, filter and usable-sample
mean altitude, with a continuous-window factor and target-specific Moon penalty.
Oversized targets incur a coverage penalty. Pure open clusters use attributed
OpenNGC optical sizes, without replacing nebula extents. These remain heuristics,
not weather, exposure or success predictions.


### SPF ordering and SHO guidance (0.9.6)

The page explicitly requests `sort_by=imaging_time`: remaining geometric imaging
minutes, then longest continuous window, then FOV fit. Other modes are `setting_soon`
(currently available targets whose current window ends first, followed by future
windows), `fov`, and the legacy `heuristic` reference score. All modes order
the full candidate pool before limiting results. Time modes reject known remaining
windows shorter than 30 minutes. Unknown evidence stays null and sorts last.

Cards show total versus continuous time and camera-aware SHO guidance. Geometry
uses 15-minute samples, target altitude >=25 degrees, Sun <=-18 degrees, and Moon
separation >=15 degrees when illumination >0.1 and the Moon is up. Elapsed time and
missing-sample gaps are excluded; weather, terrain and equipment overhead are not modeled.
These inherited thresholds are not yet configurable in the page.

SHO advice is catalog-type guidance only, never measured emission-line strength:
HII targets are conditional; SNR, planetary nebulae and ambiguous open-cluster fields
need verification; galaxies, reflection nebulae and globular-cluster subjects favor
broadband. SII strength remains null. The existing HOPE MC Air preset is marked color;
other unverified cameras stay unknown, with a manual color/mono/unknown selector.
Color SHO requires independently acquired SII/Ha/OIII (for example paired dual-band
filters); a single ordinary Ha/OIII dual-band filter lacks SII.

REST `/api/telescope/targets` accepts top-level `sort_by`, `camera_type`, and `limit`
(1-100). Omitted sorting keeps legacy heuristic order for compatibility; camera type
defaults to unknown. Responses add `total_available`, sorting/camera metadata, per-target
`visibility` and `sho_advice`. Presets include camera display metadata; plans include
SHO guidance but retain their separate scheduling algorithm. Changing controls clears
stale target results and requires a new match. No public MCP schema was changed.
