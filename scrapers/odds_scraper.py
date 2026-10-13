"""Licensed The Odds API integration for comparing authorized bookmaker data.

This module never scrapes sportsbook websites. It uses only the user's own
The Odds API key and should be enabled only when their plan permits the use.
"""

from typing import Any

import httpx

from backend.dependencies import settings


LEAGUE_KEYS = {
    "nba": "basketball_nba",
    "nfl": "americanfootball_nfl",
}
API_URL = "https://api.the-odds-api.com/v4/sports/{sport_key}/odds"


class OddsProviderUnavailable(RuntimeError):
    """Raised when the configured odds provider cannot return data."""


def live_odds_status(sport: str) -> dict[str, str]:
    """Return a safe response until a licensed provider is configured."""

    return {
        "league": sport.lower(),
        "status": "Live odds are disabled.",
        "reason": "Add THE_ODDS_API_KEY from a licensed The Odds API account to .env.",
    }


async def fetch_odds_comparison(
    league: str, bookmakers: str | None = None
) -> dict[str, Any]:
    """Fetch comparable moneyline, spread, and total lines from one licensed API.

    `bookmakers` is an optional comma-separated provider list such as
    ``draftkings,fanduel``. No request is made when no API key is configured.
    """

    normalized_league = league.lower()
    sport_key = LEAGUE_KEYS.get(normalized_league)
    if sport_key is None:
        raise ValueError("League must be 'nba' or 'nfl'.")
    if not settings.odds_api_key:
        return live_odds_status(normalized_league)

    params = {
        "apiKey": settings.odds_api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
    }
    if bookmakers:
        params["bookmakers"] = bookmakers

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(API_URL.format(sport_key=sport_key), params=params)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OddsProviderUnavailable("The configured odds provider is unavailable.") from exc

    try:
        events = response.json()
    except ValueError as exc:
        raise OddsProviderUnavailable("The odds provider returned invalid data.") from exc

    return {
        "league": normalized_league,
        "source": "The Odds API",
        "markets": ["h2h", "spreads", "totals"],
        "bookmaker_filter": bookmakers or "US region providers",
        "event_count": len(events),
        "events": events,
        "usage": {
            "requests_remaining": response.headers.get("x-requests-remaining"),
            "requests_used": response.headers.get("x-requests-used"),
            "last_request_cost": response.headers.get("x-requests-last"),
        },
    }
