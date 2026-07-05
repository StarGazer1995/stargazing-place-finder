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
