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
| `/api/telescope/optics` | POST | Compute optical parameters |
| `/api/telescope/targets` | POST | Match deep-sky targets |
| `/api/telescope/plan` | POST | Generate shooting plan |
| `/api/telescope/mosaic` | POST | Mosaic panel planning |

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
