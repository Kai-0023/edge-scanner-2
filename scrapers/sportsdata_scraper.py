"""Authorized SportsDataIO connectors for injuries and NFL matchup research.

No request is made unless the user supplies an authorized SPORTS_DATA_IO_API_KEY.
"""

import asyncio
import re
import time
from typing import Any

import httpx

from backend.dependencies import settings
from logic.nfl_game_analysis import matchup_summary, summarize_team


NBA_INJURIES_URL = "https://api.sportsdata.io/v3/nba/projections/json/InjuredPlayers"
NFL_INJURIES_URL = "https://api.sportsdata.io/v3/nfl/stats/json/Injuries/{season}/{week}"
NFL_TEAMS_URL = "https://api.sportsdata.io/v3/nfl/scores/json/Teams"
NFL_TEAM_SEASON_STATS_URL = "https://api.sportsdata.io/v3/nfl/scores/json/TeamSeasonStats/{season}"
NFL_PLAYER_SEASON_STATS_URL = "https://api.sportsdata.io/v3/nfl/stats/json/PlayerSeasonStatsByTeam/{season}/{team_key}"
STATS_CACHE_SECONDS = 15 * 60
_stats_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


class SportsDataUnavailable(RuntimeError):
    """Raised when SportsDataIO cannot provide the requested authorized data."""


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


async def _authorized_json(url: str, cache_key: str) -> list[dict[str, Any]]:
    """Fetch and cache one authorized SportsDataIO list response."""

    if not settings.sportsdata_api_key:
        raise SportsDataUnavailable("Add SPORTS_DATA_IO_API_KEY from an authorized SportsDataIO plan first.")

    cached = _stats_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < STATS_CACHE_SECONDS:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                url,
                headers={"Ocp-Apim-Subscription-Key": settings.sportsdata_api_key},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SportsDataUnavailable(
            "The authorized SportsDataIO provider is unavailable or the selected plan does not cover this feed."
        ) from exc

    if not isinstance(payload, list):
        raise SportsDataUnavailable("The authorized stats provider returned an unexpected response.")
    records = [item for item in payload if isinstance(item, dict)]
    _stats_cache[cache_key] = (time.monotonic(), records)
    return records


def _find_team_key(teams: list[dict[str, Any]], team_name: str) -> str:
    target = _normalize(team_name)
    for team in teams:
        candidates = [
            str(team.get("FullName") or ""),
            str(team.get("Name") or ""),
            " ".join(part for part in [str(team.get("City") or ""), str(team.get("Name") or "")] if part),
        ]
        if any(_normalize(candidate) == target for candidate in candidates):
            key = str(team.get("Key") or "")
            if key:
                return key
    raise SportsDataUnavailable(f"SportsDataIO could not match the NFL team '{team_name}'.")


def _find_team_season_record(
    records: list[dict[str, Any]], team_key: str, team_name: str
) -> dict[str, Any]:
    for record in records:
        if str(record.get("Team") or "").upper() == team_key.upper():
            return record
        names = [str(record.get("TeamName") or ""), str(record.get("Name") or "")]
        if any(_normalize(name) == _normalize(team_name) for name in names):
            return record
    raise SportsDataUnavailable(f"SportsDataIO has no season totals for '{team_name}' yet.")


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


async def fetch_nfl_matchup_insights(
    home_team: str, away_team: str, season: str
) -> dict[str, Any]:
    """Fetch season-to-date NFL team and QB context for a selected matchup.

    The provider response is cached for 15 minutes to reduce both request volume
    and plan usage. No odds or personal data is sent to SportsDataIO.
    """

    teams, team_seasons = await asyncio.gather(
        _authorized_json(NFL_TEAMS_URL, "nfl:teams"),
        _authorized_json(NFL_TEAM_SEASON_STATS_URL.format(season=season), f"nfl:team-season:{season}"),
    )
    home_key = _find_team_key(teams, home_team)
    away_key = _find_team_key(teams, away_team)
    home_players, away_players = await asyncio.gather(
        _authorized_json(
            NFL_PLAYER_SEASON_STATS_URL.format(season=season, team_key=home_key),
            f"nfl:player-season:{season}:{home_key}",
        ),
        _authorized_json(
            NFL_PLAYER_SEASON_STATS_URL.format(season=season, team_key=away_key),
            f"nfl:player-season:{season}:{away_key}",
        ),
    )
    home = summarize_team(
        _find_team_season_record(team_seasons, home_key, home_team), home_players, home_team
    )
    away = summarize_team(
        _find_team_season_record(team_seasons, away_key, away_team), away_players, away_team
    )
    return {
        "available": True,
        "source": "SportsDataIO",
        "season": season,
        "cache_minutes": STATS_CACHE_SECONDS // 60,
        "home": home,
        "away": away,
        "matchup_summary": matchup_summary(home, away),
    }
