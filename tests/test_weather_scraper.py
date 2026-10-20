"""Tests for the Open-Meteo response adapter."""

import pytest

from scrapers.weather_scraper import WeatherProviderUnavailable, summarize_game_weather


def _forecast_payload() -> dict:
    return {
        "timezone": "America/Chicago",
        "utc_offset_seconds": -18000,
        "hourly": {
            "time": ["2026-10-20T18:00", "2026-10-20T19:00", "2026-10-20T20:00"],
            "temperature_2m": [72.0, 70.0, 69.0],
            "precipitation_probability": [5, 65, 60],
            "wind_speed_10m": [10.0, 17.0, 18.0],
            "wind_gusts_10m": [18.0, 28.0, 30.0],
            "weather_code": [1, 63, 63],
        },
    }


def test_weather_summary_returns_forecast_and_review_flags() -> None:
    summary = summarize_game_weather(_forecast_payload(), 29.9511, -90.0715, "2026-10-20T19:15")

    assert summary["conditions"]["temperature_f"] == 70.0
    assert summary["conditions"]["weather_description"] == "Moderate rain"
    assert len(summary["review_flags"]) == 3


def test_weather_summary_rejects_a_game_time_outside_forecast() -> None:
    with pytest.raises(WeatherProviderUnavailable):
        summarize_game_weather(_forecast_payload(), 29.9511, -90.0715, "2026-11-20T19:00")


def test_weather_summary_converts_an_upcoming_utc_event_time_to_venue_time() -> None:
    summary = summarize_game_weather(_forecast_payload(), 29.9511, -90.0715, "2026-10-21T00:15:00Z")

    assert summary["forecast_time_local"] == "2026-10-20T19:00"
