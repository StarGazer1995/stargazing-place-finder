"""Tests for the /api/weather/* endpoints."""

from unittest import mock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from server.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _mock_reader():
    """Create a mock OmWeatherReader with valid metadata and data."""
    reader = mock.MagicMock()
    reader.model.value = "dwd_icon"
    reader.reference_time = "2026-07-09T00:00:00Z"
    reader.valid_times = [f"2026-07-09T{i:02d}:00Z" for i in range(24)]
    reader.available_variables = [
        "cloud_cover",
        "cloud_cover_low",
        "precipitation",
        "temperature_2m",
    ]

    def _fake_read(variable, north=None, south=None, east=None, west=None, shape=None, valid_time_index=0):
        h, w = shape if shape else (256, 256)
        return np.full((h, w), 30.0, dtype=np.float32)

    reader.read_window.side_effect = _fake_read
    return reader


@pytest.fixture(autouse=True)
def mock_weather_reader():
    """Patch OmWeatherReader so tests don't need network access."""
    r = _mock_reader()
    _valid_vars = {"cloud_cover", "cloud_cover_low", "precipitation", "temperature_2m"}

    def _fake_weather_var(value):
        if value not in _valid_vars:
            raise ValueError(f"Unknown variable: {value}")
        m = mock.MagicMock()
        m.value = value
        return m

    with (
        mock.patch(
            "stargazing_core.OmWeatherReader",
            return_value=r,
        ),
        mock.patch(
            "server.routes.weather_tiles.OmWeatherReader",
            return_value=r,
        ),
        mock.patch(
            "server.routes.weather_tiles.WeatherModel",
        ),
        mock.patch(
            "server.routes.weather_tiles.WeatherVariable",
            side_effect=_fake_weather_var,
        ),
    ):
        yield r


class TestWeatherMeta:
    def test_meta_returns_model_info(self, client: TestClient) -> None:
        resp = client.get("/api/weather/meta")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model"] == "dwd_icon"
        assert data["total_steps"] == 24
        assert len(data["valid_times"]) == 24

    def test_meta_returns_available_variables(self, client: TestClient) -> None:
        resp = client.get("/api/weather/meta")
        assert "cloud_cover" in resp.json()["variables"]


class TestWeatherTile:
    def test_tile_returns_png(self, client: TestClient) -> None:
        resp = client.get("/api/weather/tiles/6/52/22.png?variable=cloud_cover&model=dwd_icon")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert len(resp.content) > 0
        # Validate PNG signature
        assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_tile_with_time_index(self, client: TestClient) -> None:
        resp = client.get("/api/weather/tiles/6/52/22.png?time_index=5")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    def test_tile_cached_on_repeat(self, client: TestClient) -> None:
        url = "/api/weather/tiles/6/52/22.png"
        r1 = client.get(url)
        r2 = client.get(url)
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Cache hit should return same content
        assert r1.content == r2.content

    def test_tile_invalid_variable_returns_400(self, client: TestClient) -> None:
        resp = client.get("/api/weather/tiles/6/52/22.png?variable=invalid_var")
        assert resp.status_code == 400

    def test_tile_default_parameters(self, client: TestClient) -> None:
        resp = client.get("/api/weather/tiles/3/3/1.png")
        assert resp.status_code == 200

    def test_tile_cache_expiry_evicts_entry(self, client: TestClient) -> None:
        """When cache TTL expires, the entry should be evicted and re-rendered."""
        import server.routes.weather_tiles as wt

        url = "/api/weather/tiles/6/52/22.png"
        # First call — cache miss
        r1 = client.get(url)
        assert r1.status_code == 200
        # Expire the cache entry
        for key in list(wt._tile_cache):
            wt._tile_cache[key] = (wt._tile_cache[key][0], 0)  # created_at=0 → expired
        # Second call — cache hit but expired → re-render
        r2 = client.get(url)
        assert r2.status_code == 200

    def test_tile_oserror_returns_empty_png(self, client: TestClient) -> None:
        """When read_window raises OSError, return a transparent empty tile."""
        bad_reader = _mock_reader()
        bad_reader.read_window.side_effect = OSError("S3 unavailable")

        with mock.patch(
            "server.routes.weather_tiles._get_reader",
            return_value=bad_reader,
        ):
            resp = client.get("/api/weather/tiles/6/52/22.png")
        assert resp.status_code == 200
        assert len(resp.content) > 0
        # Should be a valid PNG
        assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_meta_error_returns_error_dict(self, client: TestClient) -> None:
        """When _get_reader raises, meta should return error dict."""
        with mock.patch(
            "server.routes.weather_tiles._get_reader",
            side_effect=OSError("network down"),
        ):
            resp = client.get("/api/weather/meta")
        assert resp.status_code == 200
        assert "error" in resp.json()
