"""Authorized SportsDataIO injury-feed connector.

No request is made unless the user supplies an authorized SPORTS_DATA_IO_API_KEY.
"""

from typing import Any

import httpx

from backend.dependencies import settings


NBA_INJURIES_URL = "https://api.sportsdata.io/v3/nba/projections/json/InjuredPlayers"
NFL_INJURIES_URL = "https://api.sportsdata.io/v3/nfl/stats/json/Injuries/{season}/{week}"


class SportsDataUnavailable(RuntimeError):
    """Raised when SportsDataIO cannot provide the requested authorized data."""


async def fetch_injuries(league: str, season: str | None = None, week: int | None = None) -> list[dict[str, Any]]:
    """Fetch authorized NBA or NFL injury records from SportsDataIO."""

    if not settings.sportsdata_api_key:
        raise SportsDataUnavailable("Add SPORTS_DATA_IO_API_KEY from an authorized SportsDataIO plan first.")

    normalized_league = league.lower()
    if normalized_league == "nba":
        url = NBA_INJURIES_URL
    elif normalized_league == "nfl":
        if not season or week is None:
            raise ValueError("NFL injury sync requires season and week values.")
        url = NFL_INJURIES_URL.format(season=season, week=week)
    else:
        raise ValueError("League must be 'nba' or 'nfl'.")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers={"Ocp-Apim-Subscription-Key": settings.sportsdata_api_key},
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SportsDataUnavailable("The authorized injury provider is unavailable.") from exc
