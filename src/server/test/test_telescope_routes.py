"""Tests for the /api/telescope/* endpoints."""

import pytest
from fastapi.testclient import TestClient

from server.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestTelescopePresets:
    def test_get_presets_returns_dict(self, client: TestClient) -> None:
        resp = client.get("/api/telescope/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert len(data) >= 15
        assert "seestar-s50" in data
        assert data["seestar-s50"]["focal_length_mm"] == 250

    def test_preset_has_expected_fields(self, client: TestClient) -> None:
        resp = client.get("/api/telescope/presets")
        seestar = resp.json()["seestar-s50"]
        for key in (
            "focal_length_mm",
            "sensor_width_mm",
            "sensor_height_mm",
            "aperture_mm",
            "sensor_pixel_size_um",
            "mount_type",
        ):
            assert key in seestar, f"Missing field: {key}"


class TestTelescopeOptics:
    def test_compute_optics_returns_fov(self, client: TestClient) -> None:
        cfg = {
            "focal_length_mm": 250,
            "sensor_width_mm": 7.6,
            "sensor_height_mm": 5.7,
            "aperture_mm": 50,
            "sensor_pixel_size_um": 2.9,
            "mount_type": "altaz",
        }
        resp = client.post("/api/telescope/optics", json=cfg)
        assert resp.status_code == 200
        data = resp.json()
        assert data["fov_width_deg"] == pytest.approx(1.74, abs=0.05)
        assert data["fov_height_deg"] == pytest.approx(1.31, abs=0.05)
        assert data["effective_focal_length_mm"] == 250

    def test_compute_optics_validation_error(self, client: TestClient) -> None:
        resp = client.post(
            "/api/telescope/optics",
            json={
                "focal_length_mm": -1,
                "sensor_width_mm": 7.6,
                "sensor_height_mm": 5.7,
            },
        )
        assert resp.status_code == 422

    def test_compute_optics_visual_only(self, client: TestClient) -> None:
        resp = client.post(
            "/api/telescope/optics",
            json={
                "focal_length_mm": 1200,
                "aperture_mm": 200,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fov_width_deg"] is None
        assert data["limiting_magnitude"] is not None


class TestTelescopeTargets:
    def test_get_targets_returns_structure(self, client: TestClient, monkeypatch) -> None:
        """Targets endpoint returns expected response shape."""
        from server.routes import telescope

        mock_result = [
            {
                "name": "M 31",
                "ra": 10.68,
                "dec": 41.27,
                "type": "Gx",
                "magnitude": 3.4,
                "surface_brightness": 13.5,
                "angular_size_arcmin": 199.5,
                "altitude": 45.0,
                "azimuth": 180.0,
                "fov_fill_ratio": 0.5,
                "fov_fit_score": 1.0,
                "surface_brightness_score": 0.8,
                "filter_match_score": 1.0,
                "altitude_score": 0.5,
                "suitability_score": 85.0,
                "mosaic_recommended": True,
                "catalog": "Messier",
            }
        ]
        monkeypatch.setattr(
            telescope,
            "match_telescope_targets",
            lambda *a, **kw: {
                "targets": mock_result,
                "moon": {
                    "illumination": 0.5,
                    "phase": "First Quarter",
                    "altitude_curve": [],
                    "always_down": False,
                    "always_up": False,
                    "dark_fraction": 0.4,
                },
            },
        )

        body = {
            "focal_length_mm": 250,
            "sensor_width_mm": 23.5,
            "sensor_height_mm": 15.7,
            "lon": 116.4,
            "lat": 39.9,
            "time": "2024-01-25T22:00:00",
            "time_zone": "Asia/Shanghai",
            "limit": 5,
        }
        resp = client.post("/api/telescope/targets", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["targets"]) == 1
        assert data["targets"][0]["name"] == "M 31"
        assert "config" in data

    def test_get_targets_defaults(self, client: TestClient, monkeypatch) -> None:
        """Targets endpoint applies defaults for time_zone and limit."""
        from server.routes import telescope

        monkeypatch.setattr(
            telescope,
            "match_telescope_targets",
            lambda *a, **kw: {"targets": [], "moon": {}},
        )

        body = {
            "focal_length_mm": 250,
            "lon": 0,
            "lat": 51,
            "time": "2024-01-25T22:00:00",
        }
        resp = client.post("/api/telescope/targets", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["targets"] == []

    def test_get_targets_fallback_timezone(self, client: TestClient, monkeypatch) -> None:
        """Targets endpoint falls back to direct Time parse for invalid tz."""
        from server.routes import telescope

        monkeypatch.setattr(
            telescope,
            "match_telescope_targets",
            lambda *a, **kw: {"targets": [], "moon": {}},
        )

        body = {
            "focal_length_mm": 250,
            "lon": 0,
            "lat": 51,
            "time": "2024-01-25T22:00:00",
            "time_zone": "Mars/Olympus",
        }
        resp = client.post("/api/telescope/targets", json=body)
        assert resp.status_code == 200
