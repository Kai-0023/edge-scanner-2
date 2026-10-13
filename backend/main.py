"""FastAPI entry point, league router, and authorized odds comparison route."""

import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query

from logic.nba_logic import nba_player_summary
from logic.nfl_logic import nfl_player_summary
from scrapers.odds_scraper import OddsProviderUnavailable, fetch_odds_comparison


app = FastAPI(title="Edge Scanner 2", version="0.2.0")

CACHE_SECONDS = 60
odds_cache: dict[tuple[str, str | None], tuple[float, dict[str, Any]]] = {}


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small response that confirms the API is running."""

    return {"status": "ok"}


@app.get("/analyze/{league}")
def analyze(
    league: str,
    player: str = Query(..., min_length=2, description="Player name to analyze"),
) -> dict[str, str]:
    """Route an analysis request to the selected sport-specific module."""

    normalized_league = league.lower()
    if normalized_league == "nba":
        return nba_player_summary(player)
    if normalized_league == "nfl":
        return nfl_player_summary(player)

    raise HTTPException(status_code=400, detail="League must be 'nba' or 'nfl'.")


@app.get("/live/{league}")
async def live_odds(
    league: str,
    bookmakers: str | None = Query(
        default=None,
        description="Optional comma-separated bookmaker keys, e.g. draftkings,fanduel",
    ),
) -> dict[str, Any]:
    """Return legal API-sourced odds for comparing listed sportsbooks.

    Results are cached for 60 seconds to limit API-credit use. This route does
    not scrape sportsbook websites.
    """

    normalized_league = league.lower()
    if normalized_league not in {"nba", "nfl"}:
        raise HTTPException(status_code=400, detail="League must be 'nba' or 'nfl'.")

    cache_key = (normalized_league, bookmakers)
    cached = odds_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return {**cached[1], "cached": True}

    try:
        result = await fetch_odds_comparison(normalized_league, bookmakers)
    except OddsProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    odds_cache[cache_key] = (time.monotonic(), result)
    return {**result, "cached": False}
