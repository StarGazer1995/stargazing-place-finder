# -*- coding: utf-8 -*-
"""Real GDAL masks/non-finite samples must not become dark-sky values."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
import rasterio
from PIL import Image
from rasterio.transform import from_bounds

from light_pollution.light_pollution_analyzer import LightPollutionAnalyzer
from server import tile_renderer as tiles
from stargazing_analyzer.stargazing_location_analyzer import StargazingLocationAnalyzer
from stargazingplacefinder.models import Location, StargazingLocation


@pytest.fixture
def raster(tmp_path):
    opened = []
    north, south, east, west = tiles.tile_bounds(53, 26, 6)

    def make(data, nodata=None, mask=None, **kwargs):
        path = tmp_path / f"fixture-{len(opened)}.tif"
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                width=32,
                height=32,
                count=1,
                dtype="float32",
                crs="EPSG:4326",
                nodata=nodata,
                transform=from_bounds(west, south, east, north, 32, 32),
            ) as file:
                file.write(np.asarray(data, dtype="float32"), 1)
                if mask is not None:
                    file.write_mask(mask)
        analyzer = LightPollutionAnalyzer(geotiff_path=path, **kwargs)
        opened.append(analyzer)
        tiles.clear_tile_cache()
        return analyzer

    yield make
    for analyzer in opened:
        analyzer.close()
    tiles.clear_tile_cache()


def coordinate(analyzer, row=16, col=16):
    lon, lat = analyzer._src.xy(row, col)
    return lat, lon


def alpha(png):
    return np.asarray(Image.open(BytesIO(png)).convert("RGBA"))[:, :, 3]


@pytest.mark.parametrize(
    "value,nodata,masked",
    [
        (0, 0, False),
        (1000, 1000, False),
        (-9999, -9999, False),
        (np.nan, None, False),
        (np.inf, None, False),
        (-np.inf, None, False),
        (5, None, True),
    ],
)
def test_declared_missing_and_nonfinite_samples_remain_unknown(raster, value, nodata, masked):
    analyzer = raster(
        np.full((32, 32), value),
        nodata=nodata,
        mask=np.zeros((32, 32), dtype="uint8") if masked else None,
    )
    point = coordinate(analyzer)
    assert analyzer.get_raw_radiance(*point) is None
    assert analyzer.get_radiance(*point) is None
    assert analyzer.get_light_pollution_color(*point) is None
    batch = analyzer.batch_analyze_coordinates([point])
    assert batch[0]["success"] is False and batch[0]["pollution_info"] is None
    assert np.isnan(analyzer._skyglow_grid).all()  # No data is not a zero-radiance model.
    assert not np.any(alpha(tiles.render_tile(6, 53, 26, analyzer)))


def test_unmasked_zero_remains_a_valid_source_value(raster):
    analyzer = raster(np.zeros((32, 32)))
    point = coordinate(analyzer)
    assert analyzer.get_raw_radiance(*point) == 0
    assert analyzer.get_light_pollution_color(*point).bortle == 1
    assert analyzer.batch_analyze_coordinates([point])[0]["success"] is True
    assert np.all(alpha(tiles.render_tile(6, 53, 26, analyzer)) == 255)


@pytest.mark.parametrize("kind", ["nodata", "mask", "nan"])
def test_missing_samples_do_not_bias_neighbour_skyglow_or_gain_tile_opacity(raster, kind):
    data = np.full((32, 32), 5.0)
    mask = None
    nodata = None
    if kind == "nodata":
        data[:16, :16] = 1000
        nodata = 1000
    elif kind == "nan":
        data[:16, :16] = np.nan
    else:
        mask = np.full((32, 32), 255, dtype="uint8")
        mask[:16, :16] = 0
    analyzer = raster(data, nodata=nodata, mask=mask)
    missing, valid = coordinate(analyzer, 8, 8), coordinate(analyzer, 24, 24)
    assert analyzer.get_raw_radiance(*missing) is None
    assert analyzer.get_radiance(*missing) is None  # Do not impute raw data from neighbours.
    assert analyzer.get_raw_radiance(*valid) == 5
    assert analyzer._skyglow_grid == pytest.approx(np.full((2, 2), 5))
    assert analyzer.get_radiance(*valid) == pytest.approx(7)
    batch = analyzer.batch_analyze_coordinates([missing, valid])
    assert [p["success"] for p in batch] == [False, True]
    assert batch[1]["pollution_info"].radiance == pytest.approx(7)
    opacity = alpha(tiles.render_tile(6, 53, 26, analyzer))
    assert np.all(opacity[:128, :128] == 0)
    assert np.all(opacity[128:, 128:] == 255)


def test_mixed_row_batch_keeps_valid_points_and_original_order(raster, monkeypatch):
    data = np.full((32, 32), 5.0)
    data[8, 8], data[8, 9], data[8, 10] = 0, np.nan, np.inf
    analyzer = raster(data, nodata=0)
    points = [coordinate(analyzer, 8, col) for col in (8, 9, 10, 11)]
    read = MagicMock(wraps=analyzer._read_valid)
    monkeypatch.setattr(analyzer, "_read_valid", read)
    batch = analyzer.batch_analyze_coordinates(points)
    assert [p["coordinates"] for p in batch] == points
    assert [p["index"] for p in batch] == list(range(len(points)))
    assert [p["success"] for p in batch] == [False, False, False, True]
    assert batch[-1]["pollution_info"].radiance == pytest.approx(7)
    read.assert_called_once()  # Missing cells do not force per-point I/O.


@pytest.mark.parametrize("weight", [0.0, 0.4])
def test_invalid_correction_is_unknown_but_zero_weight_uses_raw(raster, monkeypatch, weight):
    analyzer = raster(np.full((32, 32), 5.0), skyglow_weight=weight)
    monkeypatch.setattr(analyzer, "_get_skyglow", lambda *_: np.nan)
    point = coordinate(analyzer)
    result = analyzer.get_radiance(*point)
    batch = analyzer.batch_analyze_coordinates([point])
    if weight == 0:
        assert result == 5 and batch[0]["pollution_info"].radiance == 5
        skyglow = MagicMock(return_value=np.full((256, 256), np.nan))
        monkeypatch.setattr(analyzer, "get_skyglow_for_window", skyglow)
        assert np.all(alpha(tiles.render_tile(6, 53, 26, analyzer)) == 255)
        skyglow.assert_not_called()
    else:
        assert result is None and batch[0]["success"] is False


def test_corrected_masked_arrays_are_not_compared_to_raw_nodata_again():
    source = SimpleNamespace(nodata=1000)
    raw = np.array([[1000, 5]], dtype="float32")
    assert alpha(tiles.render_tile_png(raw, source, "raw")).tolist() == [[0, 255]]
    corrected = np.ma.array(raw, mask=[[False, True]])
    assert alpha(tiles.render_tile_png(corrected, source, "masked")).tolist() == [[255, 0]]
    tiles.clear_tile_cache()


def test_missing_radiance_reaches_location_as_unknown_without_changing_score_formula(raster):
    analyzer = raster(np.zeros((32, 32)), nodata=0)
    lat, lon = coordinate(analyzer)
    fields = dict(
        name="Synthetic",
        lat=lat,
        lon=lon,
        elevation=1000,
        distance_to_nearest_town=0,
        nearest_town_name="Unknown",
        location_type="mountain_peak",
    )
    location, raw = StargazingLocation(**fields), Location(**fields)
    scorer = StargazingLocationAnalyzer.__new__(StargazingLocationAnalyzer)
    info = analyzer.batch_analyze_coordinates([(lat, lon)])[0]["pollution_info"]
    scorer._enrich_light_pollution(location, raw, {(lat, lon): info})
    assert location.light_pollution_bortle is None
    assert location.light_pollution_brightness is None
    assert scorer._score_light_pollution(location) == 18  # Existing neutral fallback, not verified quality.
    valid = raster(np.zeros((32, 32)))
    scorer._enrich_light_pollution(location, raw, {(lat, lon): valid.get_light_pollution_color(lat, lon)})
    assert location.light_pollution_bortle == 1
    assert scorer._score_light_pollution(location) == 35
