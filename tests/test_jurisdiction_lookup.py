"""Tests for the privacy-aware device jurisdiction response parser."""

import asyncio

from fastapi import Response

from backend.main import DeviceLocationRequest, device_jurisdiction
from scrapers.jurisdiction_lookup import state_from_census_response


def test_state_from_census_response_maps_louisiana_to_the_dashboard_code() -> None:
    payload = {"result": {"geographies": {"States": [{"STATE": "22", "NAME": "Louisiana"}]}}}

    assert state_from_census_response(payload) == {"code": "LA", "name": "Louisiana"}


def test_state_from_census_response_returns_none_for_an_unusable_response() -> None:
    assert state_from_census_response({"result": {"geographies": {}}}) is None


def test_device_jurisdiction_does_not_cache_the_location_response(monkeypatch) -> None:
    async def fake_lookup(latitude: float, longitude: float) -> dict[str, str]:
        assert (latitude, longitude) == (29.951, -90.072)
        return {"code": "LA", "name": "Louisiana"}

    monkeypatch.setattr("backend.main.lookup_device_jurisdiction", fake_lookup)
    response = Response()

    result = asyncio.run(device_jurisdiction(DeviceLocationRequest(latitude=29.951, longitude=-90.072), response))

    assert result["code"] == "LA"
    assert result["coordinates_stored"] is False
    assert response.headers["cache-control"] == "no-store"
