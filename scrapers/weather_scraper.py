"""Open-Meteo forecast lookup for public game-venue coordinates.

Weather is returned as NFL venue context only. The app never changes a
projection automatically; the person using the app must decide whether it is
relevant.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherProviderUnavailable(RuntimeError):
    """Raised when the weather provider cannot return a usable forecast."""


def _nearest_hour_index(
    hourly_times: list[str], game_time_local: str, utc_offset_seconds: int = 0
) -> int:
    """Find the closest provider hour to a local venue time within two hours.

    The odds provider supplies event times as ISO timestamps with an offset. The
    weather provider's hourly times are venue-local, so offset timestamps are
    converted to the venue timezone before matching.
    """

    try:
        target = datetime.fromisoformat(game_time_local.replace("Z", "+00:00"))
        if target.tzinfo is not None:
            target = target.astimezone(timezone(timedelta(seconds=utc_offset_seconds))).replace(tzinfo=None)
        candidates = [datetime.fromisoformat(value) for value in hourly_times]
    except ValueError as exc:
        raise ValueError("game_time_local must be an ISO date-time, such as 2026-10-20T19:00 or 2026-10-21T00:00:00Z.") from exc

    index = min(range(len(candidates)), key=lambda item: abs(candidates[item] - target))
    if abs(candidates[index] - target).total_seconds() > 2 * 60 * 60:
        raise WeatherProviderUnavailable("That game time is outside the available forecast window.")
    return index


def summarize_game_weather(
    payload: dict[str, Any], latitude: float, longitude: float, game_time_local: str
) -> dict[str, Any]:
    """Extract a nearest-hour forecast and flag conditions worth reviewing."""

    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    required_fields = ["temperature_2m", "precipitation_probability", "wind_speed_10m", "wind_gusts_10m", "weather_code"]
    if not times or any(not hourly.get(field) for field in required_fields):
        raise WeatherProviderUnavailable("The weather provider did not return a complete hourly forecast.")

    index = _nearest_hour_index(times, game_time_local, int(payload.get("utc_offset_seconds", 0)))
    weather_code = hourly["weather_code"][index]
    temperature = hourly["temperature_2m"][index]
    precipitation_probability = hourly["precipitation_probability"][index]
    wind_speed = hourly["wind_speed_10m"][index]
    wind_gusts = hourly["wind_gusts_10m"][index]
    review_flags: list[str] = []
    if precipitation_probability >= 50:
        review_flags.append("Precipitation probability is elevated.")
    if wind_speed >= 15 or wind_gusts >= 25:
        review_flags.append("Wind conditions may be meaningful for passing and kicking.")
    if weather_code >= 51:
        review_flags.append("The forecast includes precipitation or a severe-weather condition.")
    if not review_flags:
        review_flags.append("No high-level weather flag was triggered by this simple screen.")

    return {
        "source": "Open-Meteo",
        "venue_coordinates": {"latitude": latitude, "longitude": longitude},
        "forecast_time_local": times[index],
        "timezone": payload.get("timezone"),
        "conditions": {
            "temperature_f": temperature,
            "precipitation_probability_percent": precipitation_probability,
            "wind_speed_mph": wind_speed,
            "wind_gusts_mph": wind_gusts,
            "weather_code": weather_code,
            "weather_description": WEATHER_CODES.get(weather_code, "Unclassified condition"),
        },
        "review_flags": review_flags,
        "model_note": (
            "Use this as current context for the NFL weather input. "
            "Edge Scanner does not automatically change a projection from this forecast."
        ),
    }


async def fetch_game_weather(latitude: float, longitude: float, game_time_local: str) -> dict[str, Any]:
    """Request the hourly forecast for a public venue, with no API key required."""

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,wind_gusts_10m,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": 16,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPEN_METEO_FORECAST_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise WeatherProviderUnavailable("Open-Meteo is unavailable right now.") from exc

    return summarize_game_weather(payload, latitude, longitude, game_time_local)
