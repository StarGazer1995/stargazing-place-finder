"""Catalog-first name lookup must work when every remote service is down."""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from server.main import app
from server.routes import name_resolution as resolver


@pytest.fixture
def client():
    return TestClient(app)


def mock_remote(monkeypatch, handler):
    client_class = httpx.AsyncClient
    monkeypatch.setattr(
        resolver.httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handler), **kwargs),
    )


@pytest.mark.parametrize(
    "name,canonical", [("M42", "M 42"), (" m 42 ", "M 42"), ("NGC7000", "NGC 7000"), ("ic434", "IC 434")]
)
def test_catalog_ids_work_without_remote_network(client, monkeypatch, name, canonical):
    def fail_remote(**kwargs):
        raise AssertionError("Catalog search must never use the network")

    monkeypatch.setattr(resolver.httpx, "AsyncClient", fail_remote)
    response = client.get("/api/telescope/resolve", params={"name": name})
    assert response.status_code == 200
    target = response.json()
    assert target["name"] == canonical
    assert target["source"] == "local_catalog"
    obj = next(obj for obj in resolver.load_objects() if obj["name"] == canonical)
    assert target["ra"] == obj["ra"]
    assert target["dec"] == obj["dec"]
    assert set(target) == {"name", "ra", "dec", "source"}


@pytest.mark.parametrize("params", [{}, {"name": ""}, {"name": "  "}, {"name": "x" * 121}])
def test_invalid_names(client, params):
    assert client.get("/api/telescope/resolve", params=params).status_code == 422


def test_remote_fails_over_and_encodes_name(client, monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(200, text="%J 10.5 -20.25 = coordinates")

    mock_remote(monkeypatch, handler)
    response = client.get("/api/telescope/resolve", params={"name": "unknown & star"})
    assert response.status_code == 200
    assert response.json() == {"name": "unknown & star", "ra": 10.5, "dec": -20.25, "source": "Harvard"}
    assert str(requests[0].url).endswith("?unknown%20%26%20star")


@pytest.mark.parametrize("body", ["garbage", "%J 999 91", "%J 1..2 3", "%J NaN inf"])
def test_malformed_remote_data_is_unavailable_not_absent(client, monkeypatch, body):
    mock_remote(monkeypatch, lambda request: httpx.Response(200, text=body))
    response = client.get("/api/telescope/resolve", params={"name": "unknown"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "RESOLVER_UNAVAILABLE"


@pytest.mark.parametrize("failure", ["http", "timeout"])
def test_remote_failures_are_not_not_found(client, monkeypatch, failure):
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        return httpx.Response(502)

    mock_remote(monkeypatch, handler)
    assert client.get("/api/telescope/resolve", params={"name": "unknown"}).status_code == 503


def test_authoritative_not_found(client, monkeypatch):
    mock_remote(monkeypatch, lambda request: httpx.Response(200, text="#!E Nothing found"))
    response = client.get("/api/telescope/resolve", params={"name": "no such object"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "OBJECT_NOT_FOUND"


def test_overall_remote_deadline(client, monkeypatch):
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, text="%J 10 20")

    mock_remote(monkeypatch, handler)
    monkeypatch.setattr(resolver, "REMOTE_DEADLINE_SECONDS", 0.01)
    assert client.get("/api/telescope/resolve", params={"name": "unknown"}).status_code == 503
