"""Tests for game-date and weather behavior in venue context responses."""

import asyncio

from backend.main import venue_context


def test_nba_venue_context_keeps_weather_out_of_the_response(monkeypatch) -> None:
    """NBA home venues can carry a game date without requesting weather."""

    weather_requested = False

    async def fake_weather(*_args: object) -> dict[str, object]:
        nonlocal weather_requested
        weather_requested = True
        return {"forecast_time_local": "2026-10-21T19:00"}

    monkeypatch.setattr("backend.main.fetch_game_weather", fake_weather)

    result = asyncio.run(
        venue_context("nba", "Boston Celtics", game_time_local="2026-10-21T19:00:00Z")
    )

    assert result["venue"]["venue"] == "TD Garden"
    assert "weather" not in result
    assert weather_requested is False


def test_nfl_venue_context_fetches_weather_for_the_official_game_time(monkeypatch) -> None:
    """NFL home venues request weather only when a game time is supplied."""

    received: tuple[float, float, str] | None = None

    async def fake_weather(latitude: float, longitude: float, game_time: str) -> dict[str, object]:
        nonlocal received
        received = (latitude, longitude, game_time)
        return {"forecast_time_local": "2026-10-21T19:00"}

    monkeypatch.setattr("backend.main.fetch_game_weather", fake_weather)

    result = asyncio.run(
        venue_context("nfl", "New Orleans Saints", game_time_local="2026-10-22T00:00:00Z")
    )

    assert result["weather"]["forecast_time_local"] == "2026-10-21T19:00"
    assert received == (29.9511, -90.0812, "2026-10-22T00:00:00Z")
