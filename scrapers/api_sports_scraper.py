"""Server-side API-Sports connectors for NFL and NBA matchup research.

The module deliberately keeps provider keys on the server and caches expensive
lookups. It reports data that the authorized provider actually returns rather
than filling missing values with estimates.
"""

from __future__ import annotations

import asyncio
import math
import re
import time
from collections.abc import Iterable
from typing import Any

import httpx

from backend.dependencies import settings
from logic.nfl_game_analysis import matchup_summary


NFL_BASE_URL = "https://v1.american-football.api-sports.io"
NBA_BASE_URL = "https://v2.nba.api-sports.io"
CACHE_SECONDS = 15 * 60
MAX_NFL_COMPLETED_GAMES = 18

_cache: dict[str, tuple[float, Any]] = {}


class ApiSportsUnavailable(RuntimeError):
    """Raised when the configured API-Sports subscription cannot supply data."""


def _normalize(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _number(value: object) -> float | None:
    """Return a finite number from a provider value, including percent strings."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip().replace("%", "")
        if not value:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _round(value: float | None, digits: int = 1) -> float | None:
    return round(value, digits) if value is not None else None


def _average(values: Iterable[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    return _round(sum(usable) / len(usable)) if usable else None


def _percentage(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return _round(numerator / denominator * 100)


def _flatten_numbers(value: Any, prefix: str = "") -> dict[str, float]:
    """Flatten provider statistic payloads while retaining descriptive paths."""

    flattened: dict[str, float] = {}
    if isinstance(value, dict):
        label = value.get("name") or value.get("type") or value.get("label")
        labelled_prefix = f"{prefix}.{label}" if prefix and label else str(label or prefix)
        for key, item in value.items():
            if key in {"name", "type", "label"}:
                continue
            path = f"{labelled_prefix}.{key}" if labelled_prefix else str(key)
            numeric = _number(item)
            if numeric is not None:
                flattened[path] = numeric
            elif isinstance(item, (dict, list)):
                flattened.update(_flatten_numbers(item, path))
        return flattened
    if isinstance(value, list):
        for item in value:
            flattened.update(_flatten_numbers(item, prefix))
    return flattened


def _find_number(flattened: dict[str, float], *required_terms: str) -> float | None:
    """Find the shortest stat path containing every requested semantic token."""

    normalized_terms = tuple(_normalize(term) for term in required_terms)
    candidates = [
        (len(_normalize(path)), value)
        for path, value in flattened.items()
        if all(term in _normalize(path) for term in normalized_terms)
    ]
    return min(candidates, default=(0, None))[1]


def _nested(value: Any, *path: str) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _text(value: Any, *paths: tuple[str, ...]) -> str | None:
    for path in paths:
        candidate = _nested(value, *path)
        if candidate not in (None, ""):
            return str(candidate)
    return None


def _provider_key(league: str) -> str | None:
    if league == "nfl":
        return settings.api_sports_nfl_key or settings.api_sports_key
    if league == "nba":
        return settings.api_sports_nba_key or settings.api_sports_key
    return None


def _provider_base_url(league: str) -> str:
    if league == "nfl":
        return NFL_BASE_URL
    if league == "nba":
        return NBA_BASE_URL
    raise ValueError("League must be 'nfl' or 'nba'.")


def _cache_key(league: str, endpoint: str, params: dict[str, Any]) -> str:
    rendered_params = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return f"{league}:{endpoint}:{rendered_params}"


def _provider_error(payload: dict[str, Any]) -> str | None:
    errors = payload.get("errors")
    if not errors:
        return None
    if isinstance(errors, dict):
        message = "; ".join(str(item) for item in errors.values() if item)
    elif isinstance(errors, list):
        message = "; ".join(str(item) for item in errors if item)
    else:
        message = str(errors)
    return message or None


async def _get(league: str, endpoint: str, params: dict[str, Any], *, ttl: int = CACHE_SECONDS) -> Any:
    """Fetch one authorized API-Sports response and retain a short local cache."""

    api_key = _provider_key(league)
    if not api_key:
        variable = "API_SPORTS_NFL_KEY" if league == "nfl" else "API_SPORTS_NBA_KEY"
        raise ApiSportsUnavailable(f"Add {variable} to .env before loading {league.upper()} insights.")

    key = _cache_key(league, endpoint, params)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < ttl:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{_provider_base_url(league)}/{endpoint}",
                params=params,
                headers={"x-apisports-key": api_key},
            )
            payload = response.json()
            response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        raise ApiSportsUnavailable(
            f"The authorized API-Sports {league.upper()} service could not be reached."
        ) from exc

    if not isinstance(payload, dict):
        raise ApiSportsUnavailable("The authorized stats provider returned an unexpected response.")
    if message := _provider_error(payload):
        raise ApiSportsUnavailable(f"API-Sports could not supply this data: {message}")

    result = payload.get("response")
    if result is None:
        raise ApiSportsUnavailable("The authorized stats provider returned no response data.")
    _cache[key] = (time.monotonic(), result)
    return result


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return [value] if isinstance(value, dict) else []


async def _resolve_team(league: str, team_name: str, season: int) -> dict[str, Any]:
    params: dict[str, Any] = {"league": 1, "season": season} if league == "nfl" else {"league": "standard"}
    candidates = _records(await _get(league, "teams", params, ttl=24 * 60 * 60))
    target = _normalize(team_name)
    for team in candidates:
        names = [
            team.get("name"),
            team.get("full_name"),
            team.get("nickname"),
            " ".join(part for part in [str(team.get("city") or ""), str(team.get("nickname") or "")] if part),
        ]
        if any(_normalize(name) == target for name in names):
            if team.get("id") is not None:
                return team
    raise ApiSportsUnavailable(f"API-Sports could not match the team '{team_name}'.")


def _game_id(game: dict[str, Any]) -> str | None:
    value = game.get("id") or _nested(game, "game", "id")
    return str(value) if value is not None else None


def _game_status(game: dict[str, Any]) -> str:
    return str(
        _nested(game, "game", "status", "short")
        or _nested(game, "status", "short")
        or _nested(game, "game", "status", "long")
        or _nested(game, "status", "long")
        or ""
    ).upper()


def _completed_game(game: dict[str, Any]) -> bool:
    return _game_status(game) in {"FT", "AOT", "FINISHED", "FINAL"}


def _team_id(record: dict[str, Any]) -> str | None:
    value = _nested(record, "team", "id") or record.get("team_id")
    return str(value) if value is not None else None


def _score_for_team(game: dict[str, Any], team_id: str) -> tuple[float | None, float | None]:
    teams = game.get("teams") if isinstance(game.get("teams"), dict) else {}
    scores = game.get("scores") if isinstance(game.get("scores"), dict) else {}
    for side, opponent_side in (("home", "away"), ("away", "home")):
        current_team = teams.get(side) if isinstance(teams.get(side), dict) else {}
        if str(current_team.get("id")) != team_id:
            continue
        own = scores.get(side) if isinstance(scores.get(side), dict) else {}
        opponent = scores.get(opponent_side) if isinstance(scores.get(opponent_side), dict) else {}
        return _number(own.get("total") or own.get("points")), _number(opponent.get("total") or opponent.get("points"))
    return None, None


def _nfl_stat_sample(game: dict[str, Any], team_id: str, records: list[dict[str, Any]]) -> dict[str, float | None] | None:
    team_record = next((record for record in records if _team_id(record) == team_id), None)
    if not team_record:
        return None
    opponent_record = next((record for record in records if _team_id(record) != team_id), None)
    own_stats = _flatten_numbers(team_record.get("statistics", team_record))
    opponent_stats = _flatten_numbers((opponent_record or {}).get("statistics", opponent_record or {}))
    points_for, points_allowed = _score_for_team(game, team_id)
    return {
        "points_for": points_for,
        "points_allowed": points_allowed,
        "passing_yards": _find_number(own_stats, "passing", "yards"),
        "rushing_yards": _find_number(own_stats, "rushing", "yards"),
        "sacks_allowed": _find_number(own_stats, "sacks", "lost"),
        "touchdowns": _find_number(own_stats, "touchdowns"),
        "red_zone_attempts": _find_number(own_stats, "red", "zone", "attempt"),
        "red_zone_touchdowns": _find_number(own_stats, "red", "zone", "touchdown"),
        "passing_yards_allowed": _find_number(opponent_stats, "passing", "yards"),
        "rushing_yards_allowed": _find_number(opponent_stats, "rushing", "yards"),
        "sacks": _find_number(own_stats, "sacks"),
        "interceptions": _find_number(own_stats, "interceptions"),
        "red_zone_attempts_allowed": _find_number(opponent_stats, "red", "zone", "attempt"),
        "red_zone_touchdowns_allowed": _find_number(opponent_stats, "red", "zone", "touchdown"),
    }


def _player_name(record: dict[str, Any]) -> str:
    return str(
        _text(record, ("player", "name"), ("name",), ("player", "display_name")) or "Player unavailable"
    )


def _quarterback_summary(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for record in records:
        position = _text(record, ("player", "position"), ("position",)) or ""
        if position.upper() not in {"QB", "QUARTERBACK"}:
            continue
        values = _flatten_numbers(record)
        passing_yards = _find_number(values, "passing", "yards")
        candidates.append(
            {
                "name": _player_name(record),
                "passing_yards": passing_yards,
                "passing_touchdowns": _find_number(values, "passing", "touchdown"),
                "passing_interceptions": _find_number(values, "passing", "interception"),
                "rushing_yards": _find_number(values, "rushing", "yards"),
                "rushing_touchdowns": _find_number(values, "rushing", "touchdown"),
                "sacks_taken": _find_number(values, "sacks"),
                "games": _find_number(values, "games", "played") or _find_number(values, "appearances"),
            }
        )
    if not candidates:
        return None
    quarterback = max(candidates, key=lambda item: item["passing_yards"] or 0)
    games = quarterback["games"]
    quarterback["passing_yards_per_game"] = _round(quarterback["passing_yards"] / games) if games and games > 0 else None
    quarterback["rushing_yards_per_game"] = _round(quarterback["rushing_yards"] / games) if games and games > 0 else None
    return quarterback


def summarize_nfl_samples(team_name: str, samples: list[dict[str, float | None]], players: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize completed NFL game samples into the Team Insights contract."""

    def mean(key: str) -> float | None:
        return _average(sample.get(key) for sample in samples)

    red_zone_made = sum(sample.get("red_zone_touchdowns") or 0 for sample in samples)
    red_zone_attempts = sum(sample.get("red_zone_attempts") or 0 for sample in samples)
    red_zone_allowed_made = sum(sample.get("red_zone_touchdowns_allowed") or 0 for sample in samples)
    red_zone_allowed_attempts = sum(sample.get("red_zone_attempts_allowed") or 0 for sample in samples)
    return {
        "team": team_name,
        "games": len(samples),
        "quarterback": _quarterback_summary(players),
        "offense": {
            "points_per_game": mean("points_for"),
            "passing_yards_per_game": mean("passing_yards"),
            "rushing_yards_per_game": mean("rushing_yards"),
            "sacks_allowed_per_game": mean("sacks_allowed"),
            "touchdowns_per_game": mean("touchdowns"),
            "red_zone_touchdown_rate": _percentage(red_zone_made, red_zone_attempts),
        },
        "defense": {
            "points_allowed_per_game": mean("points_allowed"),
            "passing_yards_allowed_per_game": mean("passing_yards_allowed"),
            "rushing_yards_allowed_per_game": mean("rushing_yards_allowed"),
            "sacks_per_game": mean("sacks"),
            "interceptions_per_game": mean("interceptions"),
            "red_zone_touchdown_rate_allowed": _percentage(red_zone_allowed_made, red_zone_allowed_attempts),
        },
    }


def _stat_per_game(flattened: dict[str, float], games: float | None, *terms: str) -> float | None:
    average = _find_number(flattened, *terms, "average")
    if average is not None:
        return _round(average)
    total = _find_number(flattened, *terms, "total") or _find_number(flattened, *terms)
    return _round(total / games) if total is not None and games and games > 0 else None


def _injury_map(records: list[dict[str, Any]] | None) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for record in records or []:
        name = _text(record, ("player", "name"), ("player", "firstname"), ("name",))
        if not name:
            continue
        detail = _text(record, ("status",), ("type",), ("description",), ("reason",))
        mapped[_normalize(name)] = f"Injury reported{f': {detail}' if detail else ''}"
    return mapped


def _notable_nba_players(
    records: list[dict[str, Any]], injury_records: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    injuries = _injury_map(injury_records)
    players: list[dict[str, Any]] = []
    for record in records:
        values = _flatten_numbers(record)
        points = _find_number(values, "points", "average")
        if points is None:
            games = _find_number(values, "games", "played") or _find_number(values, "appearances")
            total = _find_number(values, "points", "total")
            points = _round(total / games) if total is not None and games and games > 0 else None
        name = _player_name(record)
        players.append(
            {
                "name": name,
                "position": _text(record, ("player", "position"), ("position",)) or "—",
                "points_per_game": points,
                "rebounds_per_game": _stat_per_game(values, _find_number(values, "games", "played"), "rebounds"),
                "assists_per_game": _stat_per_game(values, _find_number(values, "games", "played"), "assists"),
                "availability": injuries.get(
                    _normalize(name),
                    "No current injury report returned" if injury_records is not None else "Availability data unavailable",
                ),
            }
        )
    return sorted(players, key=lambda player: player["points_per_game"] or 0, reverse=True)[:3]


def summarize_nba_team(
    team_name: str,
    statistics: dict[str, Any],
    player_records: list[dict[str, Any]],
    injury_records: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Normalize API-NBA season fields without inventing absent values."""

    values = _flatten_numbers(statistics)
    games = _find_number(values, "games", "played", "all") or _find_number(values, "games", "played")
    points_for = _stat_per_game(values, games, "points", "for")
    points_allowed = _stat_per_game(values, games, "points", "against")
    return {
        "team": team_name,
        "games": games,
        "offense": {
            "points_per_game": points_for,
            "field_goal_percentage": _find_number(values, "field", "goal", "percentage"),
            "three_point_percentage": _find_number(values, "three", "point", "percentage"),
            "rebounds_per_game": _stat_per_game(values, games, "rebounds"),
            "assists_per_game": _stat_per_game(values, games, "assists"),
            "turnovers_per_game": _stat_per_game(values, games, "turnovers"),
        },
        "defense": {
            "points_allowed_per_game": points_allowed,
            "steals_per_game": _stat_per_game(values, games, "steals"),
            "blocks_per_game": _stat_per_game(values, games, "blocks"),
            "opponent_field_goal_percentage": _find_number(values, "opponent", "field", "goal", "percentage"),
        },
        "notable_players": _notable_nba_players(player_records, injury_records),
    }


async def _optional_get(league: str, endpoint: str, params: dict[str, Any]) -> Any | None:
    try:
        return await _get(league, endpoint, params)
    except ApiSportsUnavailable:
        return None


async def fetch_nfl_matchup_insights(home_team: str, away_team: str, season: int) -> dict[str, Any]:
    """Build NFL team context from completed team box scores and season QB stats."""

    home, away = await asyncio.gather(
        _resolve_team("nfl", home_team, season), _resolve_team("nfl", away_team, season)
    )

    async def team_context(team: dict[str, Any], name: str) -> dict[str, Any]:
        team_id = str(team["id"])
        games = _records(await _get("nfl", "games", {"league": 1, "season": season, "team": team_id}))
        completed = [game for game in games if _completed_game(game)]
        completed = completed[-MAX_NFL_COMPLETED_GAMES:]
        if not completed:
            raise ApiSportsUnavailable(f"API-Sports has no completed {season} NFL games for {name} yet.")
        completed_with_ids = [(game, _game_id(game)) for game in completed]
        completed_with_ids = [(game, game_id) for game, game_id in completed_with_ids if game_id]
        stat_payloads = await asyncio.gather(
            *[_get("nfl", "games/statistics/teams", {"id": game_id}) for _, game_id in completed_with_ids],
            return_exceptions=True,
        )
        samples: list[dict[str, float | None]] = []
        first_error: ApiSportsUnavailable | None = None
        for (game, _), payload in zip(completed_with_ids, stat_payloads, strict=False):
            if isinstance(payload, ApiSportsUnavailable):
                first_error = first_error or payload
                continue
            if isinstance(payload, Exception):
                continue
            sample = _nfl_stat_sample(game, team_id, _records(payload))
            if sample:
                samples.append(sample)
        if not samples:
            raise first_error or ApiSportsUnavailable(f"API-Sports returned no team box-score data for {name}.")
        players = _records(
            await _get("nfl", "players/statistics", {"team": team_id, "season": season})
        )
        return summarize_nfl_samples(name, samples, players)

    home_context, away_context = await asyncio.gather(team_context(home, home_team), team_context(away, away_team))
    return {
        "available": True,
        "source": "API-Sports NFL",
        "season": str(season),
        "cache_minutes": CACHE_SECONDS // 60,
        "home": home_context,
        "away": away_context,
        "matchup_summary": matchup_summary(home_context, away_context),
    }


async def fetch_nba_matchup_insights(home_team: str, away_team: str, season: int) -> dict[str, Any]:
    """Build NBA team and notable-player context from the API-NBA subscription."""

    home, away = await asyncio.gather(
        _resolve_team("nba", home_team, season), _resolve_team("nba", away_team, season)
    )

    async def team_context(team: dict[str, Any], name: str) -> dict[str, Any]:
        team_id = str(team["id"])
        stats, players, injuries = await asyncio.gather(
            _get("nba", "teams/statistics", {"id": team_id, "season": season}),
            _optional_get("nba", "players/statistics", {"team": team_id, "season": season}),
            _optional_get("nba", "injuries", {"team": team_id, "season": season}),
        )
        records = _records(stats)
        if not records:
            raise ApiSportsUnavailable(f"API-Sports has no {season} NBA team statistics for {name} yet.")
        return summarize_nba_team(name, records[0], _records(players), _records(injuries))

    home_context, away_context = await asyncio.gather(team_context(home, home_team), team_context(away, away_team))
    return {
        "available": True,
        "source": "API-Sports NBA",
        "season": str(season),
        "cache_minutes": CACHE_SECONDS // 60,
        "home": home_context,
        "away": away_context,
        "matchup_summary": matchup_summary(home_context, away_context),
    }


async def fetch_injuries(league: str, season: str | None = None, week: int | None = None) -> list[dict[str, Any]]:
    """Fetch currently reported provider injuries for optional local snapshots."""

    normalized = league.lower()
    if normalized not in {"nfl", "nba"}:
        raise ValueError("League must be 'nba' or 'nfl'.")
    if not season or not re.fullmatch(r"\d{4}(?:REG|PRE|POST)?", season):
        raise ValueError("Use a four-digit season, optionally followed by REG, PRE, or POST.")
    season_year = int(season[:4])
    params: dict[str, Any] = {"season": season_year}
    if normalized == "nfl":
        params["league"] = 1
        if week is not None:
            params["week"] = week
    else:
        params["league"] = "standard"
    return _records(await _get(normalized, "injuries", params))
