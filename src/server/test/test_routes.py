"""Tests for the /api/analyze_stargazing_area endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.main import app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _mock_analyzer() -> None:
    """Prevent real analysis from running — no DB or GeoTIFF needed."""
    with patch(
        "server.routes.stargazing.analyze_stargazing_area",
        return_value=[],
    ):
        yield


class TestStargazingRoute:
    """Test the /api/analyze_stargazing_area POST endpoint."""

    def test_post_accepts_minimal_body(self, client: TestClient) -> None:
        """The endpoint should accept a minimal valid request body."""
        body = {
            "bbox": {"south": 39.9, "west": 116.3, "north": 40.0, "east": 116.5},
            "max_locations": 30,
            "network_type": "drive",
            "include_light_pollution": True,
            "include_road_connectivity": True,
            "road_radius_km": 10.0,
            "max_distance_to_road_km": 0.2,
        }
        response = client.post("/api/analyze_stargazing_area", json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 0

    def test_post_defaults_for_optional_fields(self, client: TestClient) -> None:
        """Omitting optional fields should use defaults without error."""
        body = {
            "bbox": {"south": 39.9, "west": 116.3, "north": 40.0, "east": 116.5},
        }
        response = client.post("/api/analyze_stargazing_area", json=body)
        assert response.status_code == 200

    def test_post_default_max_distance_to_road(self, client: TestClient) -> None:
        """When max_distance_to_road_km is omitted, default 0.2 is used."""
        body = {
            "bbox": {"south": 39.9, "west": 116.3, "north": 40.0, "east": 116.5},
            "road_radius_km": 0.2,
        }
        response = client.post("/api/analyze_stargazing_area", json=body)
        assert response.status_code == 200

    def test_post_rejects_negative_max_distance(self, client: TestClient) -> None:
        """Negative max_distance_to_road_km must be rejected (ge=0)."""
        body = {
            "bbox": {"south": 39.9, "west": 116.3, "north": 40.0, "east": 116.5},
            "max_distance_to_road_km": -1.0,
        }
        response = client.post("/api/analyze_stargazing_area", json=body)
        assert response.status_code == 422

    def test_get_accepts_new_param(self, client: TestClient) -> None:
        """The GET endpoint accepts max_distance_to_road_km as query param."""
        response = client.get(
            "/api/analyze_stargazing_area",
            params={
                "south": 39.9,
                "west": 116.3,
                "north": 40.0,
                "east": 116.5,
                "max_locations": 10,
                "road_radius_km": 0.2,
                "max_distance_to_road_km": 0.2,
            },
        )
        assert response.status_code == 200
