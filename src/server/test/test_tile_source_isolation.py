# -*- coding: utf-8 -*-
"""Real synthetic TIFF/handle/HTTP tests; no satellite observations or live services."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from unittest.mock import MagicMock

import numpy as np
import pytest
import rasterio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from rasterio.transform import from_bounds

from light_pollution import public_api as api
from server import tile_renderer as tiles
from server.routes.tiles import router


def pixels(png):
    return Image.open(BytesIO(png)).convert("RGBA").tobytes()


@pytest.fixture
def raster(tmp_path):
    path = tmp_path / "synthetic.tif"
    north, south, east, west = tiles.tile_bounds(53, 26, 6)

    def replace(value, *, nodata=None, masked=False):
        replacement = tmp_path / "replacement.tif"
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(
                replacement,
                "w",
                driver="GTiff",
                width=32,
                height=32,
                count=1,
                dtype="float32",
                crs="EPSG:4326",
                nodata=nodata,
                transform=from_bounds(west, south, east, north, 32, 32),
            ) as output:
                output.write(np.full((32, 32), value, dtype="float32"), 1)
                if masked:
                    output.write_mask(np.zeros((32, 32), dtype="uint8"))
        os.replace(replacement, path)

    api.reset_analyzer()
    tiles.clear_tile_cache()
    replace(1)
    try:
        yield path, replace, (north + south) / 2, (east + west) / 2
    finally:
        api.reset_analyzer()
        tiles.clear_tile_cache()


def test_public_reinit_rebuilds_handle_model_and_tile_pixels(raster):
    path, replace, lat, lon = raster
    old = api.init_light_pollution_analyzer(geotiff_path=path)
    handle = old._src
    # Unlabelled legacy keys cannot supply a tile from an unknown source.
    tiles.set_tile_cache("6/53/26", b"legacy-source")
    first = tiles.render_tile(6, 53, 26, old)
    assert old.get_raw_radiance(lat, lon) == 1
    assert api.analyze_coordinate(lat, lon)["data"]["light_pollution"]["radiance"] == pytest.approx(1.4)
    replace(100)
    current = api.init_light_pollution_analyzer(geotiff_path=path)
    assert handle.closed
    assert current.get_raw_radiance(lat, lon) == 100
    assert api.analyze_coordinate(lat, lon)["data"]["light_pollution"]["radiance"] == pytest.approx(140)
    fresh = tiles.render_tile(6, 53, 26, current)
    assert pixels(fresh) != pixels(first)
    tiles.clear_tile_cache()
    assert pixels(tiles.render_tile(6, 53, 26, current)) == pixels(fresh)


def test_http_route_resolves_current_handle_before_cache_hit(raster):
    path, replace, _lat, _lon = raster
    api.init_light_pollution_analyzer(geotiff_path=path)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        first = client.get("/api/light_pollution/tiles/6/53/26.png")
        assert first.status_code == 200
        replace(100)
        api.init_light_pollution_analyzer(geotiff_path=path)
        fresh = client.get("/api/light_pollution/tiles/6/53/26.png")
    assert fresh.status_code == 200
    assert fresh.headers["content-type"] == "image/png"
    assert fresh.headers["cache-control"] == "public, max-age=3600"
    assert pixels(fresh.content) != pixels(first.content)


@pytest.mark.parametrize("known_revision", [True, False])
def test_same_handle_reuses_tiles_and_untracked_handles_bypass_cache(raster, monkeypatch, known_revision):
    path, _replace, _lat, _lon = raster
    analyzer = api.init_light_pollution_analyzer(geotiff_path=path)
    if not known_revision:
        del analyzer._tile_cache_revision
    read = MagicMock(wraps=tiles.read_tile_window)
    monkeypatch.setattr(tiles, "read_tile_window", read)
    first = tiles.render_tile(6, 53, 26, analyzer)
    assert tiles.render_tile(6, 53, 26, analyzer) == first
    assert read.call_count == (1 if known_revision else 2)


@pytest.mark.parametrize("close_analyzer", [True, False])
def test_closed_handle_cannot_serve_its_old_cached_pixels(raster, close_analyzer):
    path, _replace, _lat, _lon = raster
    analyzer = api.init_light_pollution_analyzer(geotiff_path=path)
    first = tiles.render_tile(6, 53, 26, analyzer)
    if close_analyzer:
        analyzer.close()
    else:
        analyzer._src.close()
    closed = tiles.render_tile(6, 53, 26, analyzer)
    assert closed == tiles.empty_tile_png()
    assert pixels(closed) != pixels(first)


@pytest.mark.parametrize("new_missing", [False, True])
def test_late_old_tile_publication_cannot_overwrite_rebuilt_source(raster, monkeypatch, new_missing):
    path, replace, _lat, _lon = raster
    old = api.init_light_pollution_analyzer(geotiff_path=path)
    old_key = f"{old._tile_cache_revision}:6/53/26"
    waiting, release = threading.Event(), threading.Event()
    publish = tiles.set_tile_cache

    def delayed(key, png):
        if key == old_key:
            waiting.set()  # Bytes and source metadata have already been read.
            assert release.wait(5)
        publish(key, png)

    monkeypatch.setattr(tiles, "set_tile_cache", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(tiles.render_tile, 6, 53, 26, old)
        try:
            assert waiting.wait(5)
            replace(0 if new_missing else 100, nodata=0 if new_missing else None)
            current = api.init_light_pollution_analyzer(geotiff_path=path)
            fresh = tiles.render_tile(6, 53, 26, current)
        finally:
            release.set()
        assert pixels(pending.result(5)) != pixels(fresh)
    assert tiles.render_tile(6, 53, 26, current) == fresh


@pytest.mark.parametrize("kind", ["nodata", "mask", "nan"])
@pytest.mark.parametrize("first_missing", [False, True])
def test_http_reinit_replaces_cached_validity_in_both_directions(raster, kind, first_missing):
    path, replace, lat, lon = raster
    value = {"nodata": 0, "mask": 5, "nan": np.nan}[kind]
    app = FastAPI()
    app.include_router(router)
    previous = None
    with TestClient(app) as client:
        for missing in (first_missing, not first_missing):
            replace(
                value if missing else 0,
                nodata=0 if missing and kind == "nodata" else None,
                masked=missing and kind == "mask",
            )
            analyzer = api.init_light_pollution_analyzer(geotiff_path=path)
            if previous is not None:
                assert previous.closed  # A real new handle, not a renamed cache token.
            previous = analyzer._src
            raw = analyzer.get_raw_radiance(lat, lon)
            assert raw is None if missing else raw == 0
            batch = analyzer.batch_analyze_coordinates([(lat, lon)])
            assert batch[0]["success"] is not missing
            response = client.get("/api/light_pollution/tiles/6/53/26.png")
            assert response.status_code == 200
            rgba = np.asarray(Image.open(BytesIO(response.content)).convert("RGBA"))
            assert np.all(rgba[:, :, 3] == (0 if missing else 255))
            assert client.get("/api/light_pollution/tiles/6/53/26.png").content == response.content
