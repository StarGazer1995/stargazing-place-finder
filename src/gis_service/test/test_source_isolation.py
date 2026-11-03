# -*- coding: utf-8 -*-
"""Synthetic source changes exercise real configuration, cache and pool lifetimes."""

import json
from unittest.mock import MagicMock

import pytest

from gis_service.caching import GisQueryCache
from gis_service.query_service import GisQueryService
from stargazingplacefinder.models import LatLonBox


@pytest.fixture
def sources(tmp_path, monkeypatch):
    monkeypatch.delenv("STARGAZING_DB_CONFIG", raising=False)
    monkeypatch.delenv("DB_CONFIG_PATH", raising=False)
    monkeypatch.setattr("gis_service.caching.get_cache_dir", lambda _: tmp_path)
    pools = []

    def pool_factory(_minimum, _maximum, **settings):
        pool = MagicMock()
        cursor = pool.getconn.return_value.cursor.return_value
        cursor.fetchall.return_value = [
            (1, settings["host"], 119.5, 30.5, None, None, None, None, None, None, None, None, "peak", "1000")
        ]
        pools.append(pool)
        return pool

    monkeypatch.setattr("gis_service.backends.postgis_backend.SimpleConnectionPool", pool_factory)
    overpass = MagicMock(return_value=[{"tags": {"name": "overpass-fixture"}}])
    monkeypatch.setattr("gis_service.backends.overpass_backend.OverpassBackend.query_locations_in_bbox", overpass)
    return tmp_path, pools, overpass


def bbox():
    return LatLonBox(south=30, north=31, west=119, east=120)


@pytest.mark.parametrize(
    "first_source,second_source",
    [("a", "b"), ("a", "a"), ("a", None), (None, "b")],
)
def test_reconstructed_services_do_not_consume_another_db_context(sources, first_source, second_source):
    directory, pools, overpass = sources
    path = directory / "synthetic-db.json"
    for source in (first_source, second_source):
        if source is not None:
            path.write_text(json.dumps({"host": source}))
        service = GisQueryService(db_config_path=str(path) if source is not None else None)
        try:
            result = service.query_locations(bbox())
            assert result[0]["tags"]["name"] == (source or "overpass-fixture")
            assert service.query_locations(bbox()) == result  # In-instance reuse is retained.
        finally:
            service.close()
    assert len(pools) == sum(s is not None for s in (first_source, second_source))
    for pool in pools:
        assert pool.getconn.return_value.cursor.return_value.execute.call_count == 1
        pool.closeall.assert_called_once()
    assert overpass.call_count == sum(s is None for s in (first_source, second_source))


def test_overpass_ignores_legacy_unlabelled_entries_but_keeps_its_disk_reuse(sources):
    directory, pools, overpass = sources
    cache = GisQueryCache()
    bounds = bbox()
    legacy = cache._make_key("query_locations", (bounds.south, bounds.west, bounds.north, bounds.east), "peak", None)
    cache.set(legacy, [{"tags": {"name": "legacy-mixed-source"}}])
    first = GisQueryService()
    expected = [{"tags": {"name": "overpass-fixture"}}]
    assert first.query_locations(bbox()) == expected
    first.close()
    second = GisQueryService()
    assert second.query_locations(bbox()) == expected
    second.close()
    overpass.assert_called_once()
    assert pools == []
    assert len(list(directory.glob("*.pkl"))) == 2


def test_memory_only_cache_expiry_and_clear_never_touch_shared_disk(sources, monkeypatch):
    directory, _pools, _overpass = sources
    now = [1000.0]
    monkeypatch.setattr("gis_service.caching.time.time", lambda: now[0])
    disk = GisQueryCache()
    disk.set("same-key", ["old source"])
    memory = GisQueryCache(cache_expiry_hours=1, persist_to_disk=False)
    assert memory.get("same-key") is None
    memory.set("same-key", [])
    assert memory.get("same-key") == []
    now[0] = 4600.0
    assert memory.get("same-key") is None
    memory.set("same-key", ["new source"])
    memory.clear()
    assert memory.get("same-key") is None
    assert disk.get("same-key") == ["old source"]
    assert len(list(directory.glob("*.pkl"))) == 1


def test_public_analyzer_rebind_closes_old_pool_and_queries_the_new_connection(sources, monkeypatch):
    import stargazing_analyzer.public_api as api
    import stargazingplacefinder as spf

    directory, pools, _overpass = sources
    monkeypatch.setattr(api, "_sa_analyzer", None)
    monkeypatch.setattr("road_connectivity.road_connectivity_checker.get_cache_dir", lambda _: directory)
    monkeypatch.setattr("road_connectivity.road_connectivity_checker.setup_osmnx_cache", lambda: None)
    path = directory / "synthetic-db.json"
    try:
        for source in ("a", "b"):
            path.write_text(json.dumps({"host": source}))
            spf.init_stargazing_analyzer(geotiff_path=directory / "missing-fixture.tif", db_config_path=path)
            # Inspect the real resource graph created by the public initializer.
            gis = api._sa_analyzer.mountain_finder.gis_service
            assert gis.query_locations(bbox())[0]["tags"]["name"] == source
        assert len(pools) == 2
        pools[0].closeall.assert_called_once()
        pools[1].closeall.assert_not_called()
    finally:
        api.reset_analyzer()
    pools[1].closeall.assert_called_once()
