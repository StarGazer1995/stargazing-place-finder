"""Ranking intent, missing evidence, and conservative SHO recommendations."""

from types import SimpleNamespace

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation
from astropy.time import Time
from fastapi.testclient import TestClient

from server.main import app
from server.routes import telescope
from server.routes import telescope_advice as advice


@pytest.mark.parametrize(
    "kind,status",
    [
        ("HII", "consider"),
        ("emission nebula", "consider"),
        ("SNR", "verify"),
        ("PN", "verify"),
        ("Gx", "not_primary"),
        ("AGN", "not_primary"),
        ("RNe", "not_primary"),
        ("OpC", "verify"),
        ("GlC", "not_primary"),
        ("Cl+N", "verify"),
        ("", "verify"),
        ("unknown", "verify"),
        (None, "verify"),
    ],
)
@pytest.mark.parametrize("camera", ["color", "mono", "unknown"])
def test_sho_never_invents_sii_or_requires_a_mono_camera(kind, status, camera):
    result = advice.sho_advice(kind, camera)
    assert result.status == status
    assert result.sii_strength is None
    assert result.basis == "catalog_type_only"
    assert result.camera_note
    if camera == "color":
        assert "配对双窄带" in result.camera_note
        assert "缺少独立 SII" in result.camera_note


def test_total_and_continuous_windows_are_distinct_and_clip_elapsed_time():
    result = advice.summarize_windows([0, 900, 1800, 2700, 3600, 4500], [True, True, True, False, True, True], 300)
    assert result.total_minutes == 40  # (1800-300 + 4500-3600) / 60
    assert result.longest_minutes == 25
    assert result.available_now is True
    assert [(window.start, window.end) for window in result.windows] == [(300, 1800), (3600, 4500)]
    assert advice.summarize_windows([0, 900], [True, True], 1000).total_minutes == 0
    assert advice.summarize_windows([0, 3600], [True, True], 0).total_minutes == 0


def candidate(name, total, longest, start, end, ready, fov=0.5, score=50):
    return {
        "name": name,
        "fov_fit_score": fov,
        "suitability_score": score,
        "visibility": {
            "total_minutes": total,
            "longest_minutes": longest,
            "available_now": ready,
            "windows": [{"start": start, "end": end}] if start is not None else [],
        },
    }


def test_sorting_intents_do_not_confuse_duration_urgency_framing_and_reference_score():
    unknown = candidate("unknown", None, None, None, None, None, score=100)
    soon = candidate("soon", 60, 60, 0, 3600, True, fov=1, score=10)
    long = candidate("long", 240, 120, 0, 7200, True, score=20)
    later = candidate("later", 180, 180, 900, 11700, False, score=80)
    short = candidate("short", 5, 5, 0, 300, True)
    targets = [unknown, later, soon, long, short]

    def names(mode):
        return [target["name"] for target in advice.sort_targets(targets, mode)]

    assert names("imaging_time") == ["long", "later", "soon", "unknown"]
    assert names("setting_soon") == ["soon", "long", "later", "unknown"]
    assert names("fov")[0] == "soon"
    assert names("heuristic")[0] == "unknown"
    assert targets[0] is unknown  # No in-place mutation.


def target(name="test", **changes):
    return {
        "name": name,
        "type": "HII",
        "ra": 10,
        "dec": 20,
        "altitude_curve": [{"time": 900, "alt": 30}, {"time": 1800, "alt": 35}, {"time": 2700, "alt": 40}],
        **changes,
    }


def test_batch_visibility_uses_darkness_and_keeps_bad_or_missing_evidence_unknown(monkeypatch):
    monkeypatch.setattr(
        advice,
        "get_sun",
        lambda grid: SimpleNamespace(
            transform_to=lambda frame: SimpleNamespace(alt=SimpleNamespace(deg=np.array([-19, -19, -19])))
        ),
    )
    items = [
        target(),
        target("missing", altitude_curve=[]),
        target("nan", ra=float("nan")),
        target("gap", altitude_curve=[{"time": 0, "alt": 30}, {"time": 3600, "alt": 30}]),
        target("bad", ra="oops"),
        target("dec", dec=91),
        target("keys", altitude_curve=[{}, {}]),
    ]
    result = advice.explain_targets(
        items, {"illumination": 0}, EarthLocation(lat=0 * u.deg, lon=0 * u.deg), Time(900, format="unix"), "color"
    )
    assert result[0]["visibility"]["total_minutes"] == 30
    assert all(item["visibility"]["total_minutes"] is None for item in result[1:])
    assert "visibility" not in items[0]
    for illumination in [None, "missing", float("nan"), 2]:
        assert (
            advice.explain_targets(
                [target()],
                {"illumination": illumination},
                EarthLocation(lat=0 * u.deg, lon=0 * u.deg),
                Time(900, format="unix"),
                "unknown",
            )[0]["visibility"]["total_minutes"]
            is None
        )


def test_moon_separation_applies_only_when_the_moon_is_up(monkeypatch):
    monkeypatch.setattr(
        advice,
        "get_sun",
        lambda grid: SimpleNamespace(
            transform_to=lambda frame: SimpleNamespace(alt=SimpleNamespace(deg=np.array([-19, -19, -19])))
        ),
    )

    class Moon:
        def __getitem__(self, index):
            return SimpleNamespace(alt=SimpleNamespace(deg=[20, -5, 20][index]))

    monkeypatch.setattr(advice, "get_body", lambda *args, **kwargs: SimpleNamespace(transform_to=lambda frame: Moon()))
    monkeypatch.setattr(
        advice,
        "SkyCoord",
        lambda *args: SimpleNamespace(
            transform_to=lambda frame: SimpleNamespace(separation=lambda moon: SimpleNamespace(deg=np.array([10, 40])))
        ),
    )
    result = advice.explain_targets(
        [target("near"), target("far")],
        {"illumination": 0.5},
        EarthLocation(lat=0 * u.deg, lon=0 * u.deg),
        Time(900, format="unix"),
        "mono",
    )
    assert result[0]["visibility"]["total_minutes"] == 0
    assert result[1]["visibility"]["total_minutes"] == 30


def test_api_sorts_the_full_candidate_pool_before_limit(monkeypatch):
    calls = []
    monkeypatch.setattr(telescope, "load_objects", lambda: [None] * 500)

    def match(config, observer, time, limit):
        calls.append(limit)
        return {
            "targets": [
                candidate("legacy-best", 60, 60, 0, 3600, True, score=100),
                candidate("time-best", 180, 180, 0, 10800, True, score=10),
            ],
            "moon": {},
        }

    monkeypatch.setattr(telescope, "match_telescope_targets", match)
    monkeypatch.setattr(telescope, "explain_targets", lambda items, *args: items)
    response = TestClient(app).post(
        "/api/telescope/targets",
        json={
            "focal_length_mm": 280,
            "lon": 120,
            "lat": 30,
            "time": "2024-01-01T20:00:00",
            "sort_by": "imaging_time",
            "camera_type": "color",
            "limit": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["targets"][0]["name"] == "time-best"
    assert response.json()["total_available"] == 2
    assert calls == [500]


@pytest.mark.parametrize("change", [{"sort_by": "invalid"}, {"camera_type": "invalid"}, {"limit": 101}])
def test_api_rejects_invalid_display_options(change):
    response = TestClient(app).post(
        "/api/telescope/targets",
        json={"focal_length_mm": 280, "lon": 120, "lat": 30, "time": "2024-01-01T20:00:00", **change},
    )
    assert response.status_code == 422


def test_rounding_a_short_window_does_not_make_it_eligible():
    item = candidate("short", 30, 30, 0, 1799, True)
    assert advice.sort_targets([item], "imaging_time") == []


def test_equal_time_prefers_framing_without_reintroducing_composite_weights():
    small = candidate("a", 120, 120, 0, 7200, True, fov=0.1, score=100)
    fits = candidate("z", 120, 120, 0, 7200, True, fov=1, score=1)
    assert advice.sort_targets([small, fits], "imaging_time")[0] is fits
