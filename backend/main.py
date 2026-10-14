"""FastAPI entry point, league router, and authorized odds comparison route."""

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from logic.nba_logic import nba_player_summary
from logic.nfl_logic import nfl_player_summary
from logic.projection_models import nfl_projection, nba_projection
from scrapers.odds_scraper import OddsProviderUnavailable, fetch_odds_comparison


app = FastAPI(title="Edge Scanner 2", version="0.2.0")

CACHE_SECONDS = 60
odds_cache: dict[tuple[str, str | None], tuple[float, dict[str, Any]]] = {}
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"

app.mount("/static", StaticFiles(directory=FRONTEND_DIRECTORY), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the local sportsbook-comparison dashboard."""

    return FileResponse(FRONTEND_DIRECTORY / "index.html")


class NbaTeamFactors(BaseModel):
    """Historical and availability factors for one NBA team."""

    offensive_rating: float = Field(description="Historical points scored per 100 possessions.")
    defensive_rating: float = Field(description="Historical points allowed per 100 possessions.")
    recent_net_rating: float = Field(default=0, description="Recent points-for minus points-against per 100 possessions.")
    pace: float = Field(default=100, description="Possessions per game.")
    rest_days: int = Field(default=1, ge=0, le=14)
    injury_adjustment: float = Field(default=0, description="Negative when absences hurt the team.")


class NbaProjectionRequest(BaseModel):
    home: NbaTeamFactors
    away: NbaTeamFactors


class NflTeamFactors(BaseModel):
    """Historical and availability factors for one NFL team."""

    offense_points: float = Field(description="Historical points scored per game.")
    defense_points_allowed: float = Field(description="Historical points allowed per game.")
    recent_rating: float = Field(default=0, description="A recent-performance point rating.")
    rest_days: int = Field(default=7, ge=0, le=21)
    qb_adjustment: float = Field(default=0, description="Point value of the current QB situation.")
    injury_adjustment: float = Field(default=0, description="Other player-availability point adjustment.")
    weather_adjustment: float = Field(default=0, description="Weather point adjustment for the team.")


class NflProjectionRequest(BaseModel):
    home: NflTeamFactors
    away: NflTeamFactors


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


@app.post("/projection/nba")
def project_nba_game(data: NbaProjectionRequest) -> dict[str, Any]:
    """Calculate a transparent NBA baseline projection from supplied factors."""

    return {
        "model": "NBA baseline efficiency, pace, form, rest, and injury model",
        "inputs_are_user_supplied": True,
        "projection": nba_projection(
            **{f"home_{key}": value for key, value in data.home.model_dump().items()},
            **{f"away_{key}": value for key, value in data.away.model_dump().items()},
        ),
    }


@app.post("/projection/nfl")
def project_nfl_game(data: NflProjectionRequest) -> dict[str, Any]:
    """Calculate a transparent NFL baseline projection from supplied factors."""

    return {
        "model": "NFL baseline performance, QB, injury, rest, and weather model",
        "inputs_are_user_supplied": True,
        "projection": nfl_projection(
            **{f"home_{key}": value for key, value in data.home.model_dump().items()},
            **{f"away_{key}": value for key, value in data.away.model_dump().items()},
        ),
    }


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
