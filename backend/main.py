"""FastAPI entry point, league router, and authorized odds comparison route."""

import time
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.database import (
    database_status,
    initialize_database,
    recent_tracking_entries,
    save_injuries,
    save_odds_events,
    save_projection,
    save_tracking_entry,
)
from logic.matchup_insights import nfl_matchup_insight, nba_matchup_insight
from logic.nba_logic import nba_player_summary
from logic.nfl_logic import nfl_player_summary
from logic.projection_models import nfl_projection, nba_projection
from logic.slip_ocr import OCRUnavailable, extract_bet_slip
from logic.venue_registry import home_venue, list_venues
from scrapers.odds_scraper import OddsProviderUnavailable, fetch_odds_comparison
from scrapers.api_sports_scraper import (
    ApiSportsUnavailable,
    fetch_injuries,
    fetch_nba_matchup_insights,
    fetch_nfl_matchup_insights,
)
from scrapers.weather_scraper import WeatherProviderUnavailable, fetch_game_weather
from scrapers.jurisdiction_lookup import DeviceJurisdictionUnavailable, lookup_device_jurisdiction


app = FastAPI(title="Edge Scanner 2", version="0.5.0")

CACHE_SECONDS = 60
odds_cache: dict[tuple[str, str | None], tuple[float, dict[str, Any]]] = {}
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIRECTORY = PROJECT_ROOT / "frontend"

initialize_database()
app.mount("/static", StaticFiles(directory=FRONTEND_DIRECTORY), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the local sportsbook-comparison dashboard."""

    return FileResponse(FRONTEND_DIRECTORY / "index.html")


class NbaTeamFactors(BaseModel):
    """Historical and availability factors for one NBA team."""

    team_name: str | None = Field(default=None, max_length=60, description="Optional display name used in the explanation.")
    offensive_rating: float = Field(description="Historical points scored per 100 possessions.")
    defensive_rating: float = Field(description="Historical points allowed per 100 possessions.")
    recent_net_rating: float = Field(default=0, description="Recent points-for minus points-against per 100 possessions.")
    pace: float = Field(default=100, description="Possessions per game.")
    rest_days: int = Field(default=1, ge=0, le=14)
    injury_adjustment: float = Field(default=0, description="Negative when absences hurt the team.")


class NbaProjectionRequest(BaseModel):
    game_id: str | None = Field(default=None, description="Optional provider game ID used to link stored snapshots.")
    home: NbaTeamFactors
    away: NbaTeamFactors


class NflTeamFactors(BaseModel):
    """Historical and availability factors for one NFL team."""

    team_name: str | None = Field(default=None, max_length=60, description="Optional display name used in the explanation.")
    offense_points: float = Field(description="Historical points scored per game.")
    defense_points_allowed: float = Field(description="Historical points allowed per game.")
    recent_rating: float = Field(default=0, description="A recent-performance point rating.")
    rest_days: int = Field(default=7, ge=0, le=21)
    qb_adjustment: float = Field(default=0, description="Point value of the current QB situation.")
    injury_adjustment: float = Field(default=0, description="Other player-availability point adjustment.")
    weather_adjustment: float = Field(default=0, description="Weather point adjustment for the team.")


class NflProjectionRequest(BaseModel):
    game_id: str | None = Field(default=None, description="Optional provider game ID used to link stored snapshots.")
    home: NflTeamFactors
    away: NflTeamFactors


class TrackingEntryRequest(BaseModel):
    """Fields a user has reviewed after manual entry or optional OCR."""

    league: Literal["nba", "nfl", "other"] = "other"
    event_name: str = Field(min_length=2, max_length=140)
    selection: str = Field(min_length=2, max_length=140)
    american_odds: int | None = Field(default=None, ge=-10000, le=10000)
    stake: float | None = Field(default=None, ge=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=500)
    source: Literal["manual", "ocr_confirmed"] = "manual"


class DeviceLocationRequest(BaseModel):
    """Approximate browser coordinates used once to suggest a U.S. state."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small response that confirms the API is running."""

    return {"status": "ok"}


@app.post("/jurisdiction/device")
async def device_jurisdiction(request: DeviceLocationRequest, response: Response) -> dict[str, str | bool]:
    """Suggest a state after an opt-in browser location request.

    Coordinates arrive in a POST body so they do not appear in the local
    server's request URL. They are not saved by Edge Scanner.
    """

    response.headers["Cache-Control"] = "no-store"
    try:
        state = await lookup_device_jurisdiction(request.latitude, request.longitude)
    except DeviceJurisdictionUnavailable as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {**state, "approximate": True, "coordinates_stored": False}


@app.get("/data/status")
def data_status() -> dict[str, int]:
    """Show how many local pipeline snapshots have been saved."""

    return database_status()


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

    model_name = "NBA baseline efficiency, pace, form, rest, and injury model"
    home = data.home.model_dump()
    away = data.away.model_dump()
    projection = nba_projection(
        **{f"home_{key}": value for key, value in home.items() if key != "team_name"},
        **{f"away_{key}": value for key, value in away.items() if key != "team_name"},
    )
    save_projection("nba", model_name, data.model_dump(), projection, data.game_id)
    return {
        "model": model_name,
        "inputs_are_user_supplied": True,
        "projection": projection,
        "matchup_insight": nba_matchup_insight(home, away, projection),
    }


@app.post("/projection/nfl")
def project_nfl_game(data: NflProjectionRequest) -> dict[str, Any]:
    """Calculate a transparent NFL baseline projection from supplied factors."""

    model_name = "NFL baseline performance, QB, injury, rest, and weather model"
    home = data.home.model_dump()
    away = data.away.model_dump()
    projection = nfl_projection(
        **{f"home_{key}": value for key, value in home.items() if key != "team_name"},
        **{f"away_{key}": value for key, value in away.items() if key != "team_name"},
    )
    save_projection("nfl", model_name, data.model_dump(), projection, data.game_id)
    return {
        "model": model_name,
        "inputs_are_user_supplied": True,
        "projection": projection,
        "matchup_insight": nfl_matchup_insight(home, away, projection),
    }


@app.get("/venues/{league}")
def venues(league: str) -> dict[str, Any]:
    """List all NBA or NFL teams and their home arena/stadium reference data."""

    try:
        return {"league": league.lower(), "location_basis": "home_team", "venues": list_venues(league)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/venue-context/{league}")
async def venue_context(
    league: str,
    home_team: str = Query(..., min_length=2, description="The designated home team from the matchup or bet."),
    away_team: str | None = Query(default=None, description="Optional display-only away team. It never determines the venue."),
    game_time_local: str | None = Query(default=None, description="Optional official game start time. Enables NFL venue weather."),
) -> dict[str, Any]:
    """Resolve a matchup's location from the home team and optionally add NFL weather."""

    normalized_league = league.lower()
    try:
        venue = home_venue(normalized_league, home_team)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result: dict[str, Any] = {
        "league": normalized_league,
        "home_team": home_team,
        "away_team": away_team,
        "location_basis": "home_team",
        "venue": venue,
    }
    if normalized_league == "nfl" and game_time_local:
        try:
            result["weather"] = await fetch_game_weather(
                venue["latitude"], venue["longitude"], game_time_local
            )
        except (ValueError, WeatherProviderUnavailable) as exc:
            result["weather_unavailable"] = str(exc)
    return result


@app.get("/insights/nfl")
async def nfl_team_insights(
    home_team: str = Query(..., min_length=2, description="Designated NFL home team from the selected odds event."),
    away_team: str = Query(..., min_length=2, description="Designated NFL away team from the selected odds event."),
    season: int = Query(..., ge=2020, le=2100, description="NFL season start year, such as 2026."),
) -> dict[str, Any]:
    """Return authorized season-to-date NFL context for one selected game.

    A missing key or plan coverage is reported as an available-in-app message so
    the dashboard never substitutes made-up performance statistics.
    """

    try:
        return await fetch_nfl_matchup_insights(home_team, away_team, season)
    except ApiSportsUnavailable as exc:
        return {
            "available": False,
            "source": "API-Sports NFL",
            "season": str(season),
            "reason": str(exc),
            "disclaimer": "No player or team efficiency values were estimated without an authorized stats response.",
        }


@app.get("/insights/nba")
async def nba_team_insights(
    home_team: str = Query(..., min_length=2, description="Designated NBA home team from the selected odds event."),
    away_team: str = Query(..., min_length=2, description="Designated NBA away team from the selected odds event."),
    season: int = Query(..., ge=2020, le=2100, description="NBA season start year, such as 2026."),
) -> dict[str, Any]:
    """Return authorized NBA team and notable-player context for one game."""

    try:
        return await fetch_nba_matchup_insights(home_team, away_team, season)
    except ApiSportsUnavailable as exc:
        return {
            "available": False,
            "source": "API-Sports NBA",
            "season": str(season),
            "reason": str(exc),
            "disclaimer": "No player, injury, or team values were estimated without an authorized stats response.",
        }


@app.post("/tracking/ocr")
async def scan_bet_slip(image: UploadFile = File(...)) -> dict[str, Any]:
    """Run optional in-memory OCR; a user must review every suggested field."""

    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload an image file, not a document or video.")
    image_bytes = await image.read()
    try:
        return extract_bet_slip(image_bytes)
    except OCRUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/tracking/entries", status_code=201)
def create_tracking_entry(data: TrackingEntryRequest) -> dict[str, Any]:
    """Save a reviewed local tracking entry, never the original image or OCR text."""

    return save_tracking_entry(data.model_dump())


@app.get("/tracking/entries")
def list_tracking_entries(limit: int = Query(default=8, ge=1, le=50)) -> dict[str, list[dict[str, Any]]]:
    """List recent local tracking entries for this app instance."""

    return {"entries": recent_tracking_entries(limit)}


@app.post("/sync/injuries/{league}")
async def sync_injuries(
    league: str,
    season: str | None = Query(default=None, description="Season start year, such as 2026."),
    week: int | None = Query(default=None, ge=0, le=25, description="NFL week number."),
) -> dict[str, Any]:
    """Fetch and timestamp authorized injury records in the local database."""

    try:
        injuries = await fetch_injuries(league, season, week)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ApiSportsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "league": league.lower(),
        "injuries_received": len(injuries),
        "snapshots_saved": save_injuries(league.lower(), injuries),
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

    saved = save_odds_events(normalized_league, result.get("events", []))
    odds_cache[cache_key] = (time.monotonic(), result)
    return {**result, "cached": False, "snapshots_saved": saved}
