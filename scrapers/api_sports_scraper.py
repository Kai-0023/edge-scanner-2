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
MAX_NFL_QUARTERBACKS = 8

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
        value = value.strip().replace("%", "").replace(",", "")
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
    short = str(
        _nested(game, "game", "status", "short")
        or _nested(game, "status", "short")
        or ""
    ).upper()
    long = str(
        _nested(game, "game", "status", "long")
        or _nested(game, "status", "long")
        or ""
    ).upper()
    return short in {"FT", "AOT", "FINAL", "3"} or long in {"FINISHED", "FINAL"}


def _team_id(record: dict[str, Any]) -> str | None:
    value = _nested(record, "team", "id") or record.get("team_id")
    return str(value) if value is not None else None


def _score_for_team(game: dict[str, Any], team_id: str) -> tuple[float | None, float | None]:
    teams = game.get("teams") if isinstance(game.get("teams"), dict) else {}
    scores = game.get("scores") if isinstance(game.get("scores"), dict) else {}
    for side, opponent_side in (("home", "away"), ("away", "home"), ("home", "visitors"), ("visitors", "home")):
        if opponent_side not in teams or opponent_side not in scores:
            continue
        current_team = teams.get(side) if isinstance(teams.get(side), dict) else {}
        if str(current_team.get("id")) != team_id:
            continue
        own = scores.get(side) if isinstance(scores.get(side), dict) else {}
        opponent = scores.get(opponent_side) if isinstance(scores.get(opponent_side), dict) else {}
        return _number(own.get("total") or own.get("points")), _number(opponent.get("total") or opponent.get("points"))
    return None, None


def _first_number(*values: float | None) -> float | None:
    """Return the first supplied numeric value, preserving valid zeros."""

    return next((value for value in values if value is not None), None)


def _stat_pair(value: Any) -> tuple[float | None, float | None]:
    """Parse paired provider values such as ``2-3`` or ``4/27``."""

    if not isinstance(value, str):
        return None, None
    numbers = [_number(part) for part in re.findall(r"\d+(?:\.\d+)?", value)]
    return (numbers[0] if len(numbers) >= 1 else None, numbers[1] if len(numbers) >= 2 else None)


def _team_stat_block(record: dict[str, Any]) -> dict[str, Any]:
    statistics = record.get("statistics")
    return statistics if isinstance(statistics, dict) else record


def _team_touchdowns(events: list[dict[str, Any]], team_id: str) -> float:
    """Count provider scoring events rather than guessing TDs from point totals."""

    return float(
        sum(
            str(_nested(event, "team", "id")) == team_id and str(event.get("type") or "").upper() == "TD"
            for event in events
        )
    )


def _nfl_stat_sample(
    game: dict[str, Any],
    team_id: str,
    records: list[dict[str, Any]],
    event_records: list[dict[str, Any]] | None = None,
) -> dict[str, float | None] | None:
    team_record = next((record for record in records if _team_id(record) == team_id), None)
    if not team_record:
        return None
    opponent_record = next((record for record in records if _team_id(record) != team_id), None)
    own_block = _team_stat_block(team_record)
    opponent_block = _team_stat_block(opponent_record or {})
    own_stats = _flatten_numbers(own_block)
    opponent_stats = _flatten_numbers(opponent_block)
    own_sacks_lost, _ = _stat_pair(_nested(own_block, "passing", "sacks_yards_lost"))
    opponent_sacks_lost, _ = _stat_pair(_nested(opponent_block, "passing", "sacks_yards_lost"))
    own_red_zone_made, own_red_zone_attempts = _stat_pair(_nested(own_block, "red_zone", "made_att"))
    opponent_red_zone_made, opponent_red_zone_attempts = _stat_pair(
        _nested(opponent_block, "red_zone", "made_att")
    )
    points_for, points_allowed = _score_for_team(game, team_id)
    return {
        "points_for": points_for,
        "points_allowed": points_allowed,
        "passing_yards": _first_number(
            _number(_nested(own_block, "passing", "total")),
            _find_number(own_stats, "passing", "yards"),
        ),
        "rushing_yards": _first_number(
            _number(_nested(own_block, "rushings", "total")),
            _number(_nested(own_block, "rushing", "total")),
            _find_number(own_stats, "rushing", "yards"),
        ),
        "sacks_allowed": _first_number(own_sacks_lost, _find_number(own_stats, "sacks", "lost")),
        "touchdowns": _team_touchdowns(event_records, team_id) if event_records is not None else None,
        "red_zone_attempts": _first_number(
            own_red_zone_attempts,
            _find_number(own_stats, "red", "zone", "attempt"),
        ),
        "red_zone_touchdowns": _first_number(
            own_red_zone_made,
            _find_number(own_stats, "red", "zone", "touchdown"),
        ),
        "passing_yards_allowed": _first_number(
            _number(_nested(opponent_block, "passing", "total")),
            _find_number(opponent_stats, "passing", "yards"),
        ),
        "rushing_yards_allowed": _first_number(
            _number(_nested(opponent_block, "rushings", "total")),
            _number(_nested(opponent_block, "rushing", "total")),
            _find_number(opponent_stats, "rushing", "yards"),
        ),
        "sacks": _first_number(
            _number(_nested(own_block, "sacks", "total")),
            _find_number(own_stats, "sacks"),
        ),
        "interceptions": _first_number(
            _number(_nested(own_block, "interceptions", "total")),
            _find_number(own_stats, "interceptions"),
        ),
        "red_zone_attempts_allowed": _first_number(
            opponent_red_zone_attempts,
            _find_number(opponent_stats, "red", "zone", "attempt"),
        ),
        "red_zone_touchdowns_allowed": _first_number(
            opponent_red_zone_made,
            _find_number(opponent_stats, "red", "zone", "touchdown"),
        ),
    }


def _player_name(record: dict[str, Any]) -> str:
    name = _text(record, ("player", "name"), ("name",), ("player", "display_name"))
    if name:
        return name
    player = record.get("player") if isinstance(record.get("player"), dict) else {}
    first_last = " ".join(
        str(part).strip()
        for part in [
            player.get("firstname") or record.get("firstname") or record.get("firstName"),
            player.get("lastname") or record.get("lastname") or record.get("lastName"),
        ]
        if part
    )
    return first_last or "Player unavailable"


def _player_id(record: dict[str, Any]) -> str | None:
    """Return the provider player identifier when the response includes one."""

    value = _nested(record, "player", "id") or record.get("player_id") or record.get("id")
    return str(value) if value is not None else None


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
                "sacks_taken": _first_number(
                    _find_number(values, "passing", "sacks"), _find_number(values, "sacks")
                ),
                "games": _first_number(
                    _find_number(values, "games", "played"), _find_number(values, "appearances")
                ),
                "passing_yards_per_game": _find_number(values, "passing", "yards", "per", "game"),
                "rushing_yards_per_game": _find_number(values, "rushing", "yards", "per", "game"),
            }
        )
    if not candidates:
        return None
    quarterback = max(candidates, key=lambda item: item["passing_yards"] or 0)
    games = quarterback["games"]
    quarterback["passing_yards_per_game"] = _first_number(
        quarterback["passing_yards_per_game"],
        _round(quarterback["passing_yards"] / games) if games and games > 0 else None,
    )
    quarterback["rushing_yards_per_game"] = _first_number(
        quarterback["rushing_yards_per_game"],
        _round(quarterback["rushing_yards"] / games) if games and games > 0 else None,
    )
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
    records: list[dict[str, Any]],
    injury_records: list[dict[str, Any]] | None,
    *,
    historical: bool = False,
    roster_membership: dict[str, set[str]] | None = None,
) -> list[dict[str, Any]]:
    injuries = _injury_map(injury_records)

    def included(record: dict[str, Any]) -> bool:
        if roster_membership is None:
            return True

        # A provider player ID is authoritative. Only use a normalized name when
        # one of the two responses does not include an ID.
        player_id = _player_id(record)
        roster_ids = roster_membership["ids"]
        if player_id and roster_ids:
            return player_id in roster_ids
        return _normalize(_player_name(record)) in roster_membership["names"]

    def availability(name: str) -> str | None:
        if historical:
            return None
        return injuries.get(
            _normalize(name),
            "No current injury report returned" if injury_records is not None else "Availability data unavailable",
        )

    game_logs = [
        record for record in records
        if included(record) and isinstance(record.get("game"), dict) and "points" in record
    ]
    if game_logs:
        aggregates: dict[str, dict[str, Any]] = {}
        for record in game_logs:
            name = _player_name(record)
            player = aggregates.setdefault(
                name,
                {
                    "name": name,
                    "position": str(record.get("pos") or "—"),
                    "games": 0,
                    "points": 0.0,
                    "rebounds": 0.0,
                    "assists": 0.0,
                },
            )
            player["games"] += 1
            player["points"] += _number(record.get("points")) or 0
            player["rebounds"] += _number(record.get("totReb")) or 0
            player["assists"] += _number(record.get("assists")) or 0
        players = [
            {
                "name": player["name"],
                "position": player["position"],
                "points_per_game": _round(player["points"] / player["games"]),
                "rebounds_per_game": _round(player["rebounds"] / player["games"]),
                "assists_per_game": _round(player["assists"] / player["games"]),
                "availability": availability(player["name"]),
            }
            for player in aggregates.values()
            if player["games"]
        ]
        return sorted(players, key=lambda player: player["points_per_game"] or 0, reverse=True)[:3]

    players: list[dict[str, Any]] = []
    for record in records:
        if not included(record):
            continue
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
                "availability": availability(name),
            }
        )
    return sorted(players, key=lambda player: player["points_per_game"] or 0, reverse=True)[:3]


def _roster_membership(
    records: list[dict[str, Any]] | None,
    expected_team_id: str | None,
) -> dict[str, set[str]] | None:
    """Return a provider-confirmed roster, rejecting an explicitly wrong team."""

    if records is None:
        return None

    # The NBA API normally scopes this endpoint by the requested team. Some
    # provider responses also include a team ID. When that ID is present, do
    # not accept records for a different team; it is safer to show no player
    # data than to label another team's players as the selected team.
    declared_team_ids = {_team_id(record) for record in records if _team_id(record) is not None}
    if expected_team_id and declared_team_ids and declared_team_ids != {expected_team_id}:
        return None

    scoped_records = [
        record
        for record in records
        if not expected_team_id or _team_id(record) in {None, expected_team_id}
    ]
    player_ids = {player_id for record in scoped_records if (player_id := _player_id(record))}
    player_names = {
        normalized
        for record in scoped_records
        if (normalized := _normalize(_player_name(record))) and normalized != _normalize("Player unavailable")
    }
    if not player_ids and not player_names:
        return None
    return {"ids": player_ids, "names": player_names}


def _nba_form(game_records: list[dict[str, Any]] | None, team_id: str | None) -> dict[str, Any]:
    """Create a small, completed-game form snapshot for an NBA team."""

    completed: list[tuple[str, float, float]] = []
    for game in game_records or []:
        if not team_id or not _completed_game(game):
            continue
        points_for, points_allowed = _score_for_team(game, team_id)
        if points_for is None or points_allowed is None:
            continue
        game_time = _text(game, ("date", "start"), ("game", "date", "start"), ("date",)) or ""
        completed.append((game_time, points_for, points_allowed))

    completed.sort(key=lambda item: item[0], reverse=True)
    wins = sum(points_for > points_allowed for _, points_for, points_allowed in completed)
    losses = sum(points_for < points_allowed for _, points_for, points_allowed in completed)
    recent = completed[:5]
    return {
        "wins": wins if completed else None,
        "losses": losses if completed else None,
        "win_percentage": _percentage(wins, wins + losses),
        "recent_form": [
            "W" if points_for > points_allowed else "L" if points_for < points_allowed else "T"
            for _, points_for, points_allowed in recent
        ],
        "point_differential_per_game": _average(
            points_for - points_allowed for _, points_for, points_allowed in completed
        ),
        "recent_points_per_game": _average(points_for for _, points_for, _ in recent),
        "recent_points_allowed_per_game": _average(points_allowed for _, _, points_allowed in recent),
    }


def summarize_nba_team(
    team_name: str,
    statistics: dict[str, Any],
    player_records: list[dict[str, Any]],
    injury_records: list[dict[str, Any]] | None,
    game_records: list[dict[str, Any]] | None = None,
    team_id: str | None = None,
    historical_player_records: list[dict[str, Any]] | None = None,
    historical_season: int | None = None,
    current_roster_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Normalize API-NBA season fields without inventing absent values."""

    values = _flatten_numbers(statistics)
    games = _find_number(values, "games", "played", "all") or _find_number(values, "games", "played")
    direct_game_count = _number(statistics.get("games")) if isinstance(statistics, dict) else None
    if direct_game_count is not None:
        games = direct_game_count
        points_total = _number(statistics.get("points"))
        field_goals_made = _number(statistics.get("fgm"))
        field_goals_attempted = _number(statistics.get("fga"))
        three_pointers_made = _number(statistics.get("tpm"))
        three_pointers_attempted = _number(statistics.get("tpa"))
        free_throws_made = _number(statistics.get("ftm"))
        free_throws_attempted = _number(statistics.get("fta"))
        offensive_rebounds_total = _number(statistics.get("offReb"))
        defensive_rebounds_total = _number(statistics.get("defReb"))
        rebounds_total = _number(statistics.get("totReb"))
        assists_total = _number(statistics.get("assists"))
        turnovers_total = _number(statistics.get("turnovers"))
        steals_total = _number(statistics.get("steals"))
        blocks_total = _number(statistics.get("blocks"))
        points_for = _round(points_total / games) if points_total is not None and games else None
        field_goal_percentage = _percentage(field_goals_made, field_goals_attempted) or _number(statistics.get("fgp"))
        three_point_percentage = _percentage(three_pointers_made, three_pointers_attempted) or _number(statistics.get("tpp"))
        free_throw_percentage = _percentage(free_throws_made, free_throws_attempted) or _number(statistics.get("ftp"))
        three_point_attempts_per_game = _round(three_pointers_attempted / games) if three_pointers_attempted is not None and games else None
        free_throw_attempts_per_game = _round(free_throws_attempted / games) if free_throws_attempted is not None and games else None
        offensive_rebounds_per_game = _round(offensive_rebounds_total / games) if offensive_rebounds_total is not None and games else None
        defensive_rebounds_per_game = _round(defensive_rebounds_total / games) if defensive_rebounds_total is not None and games else None
        rebounds_per_game = _round(rebounds_total / games) if rebounds_total is not None and games else None
        assists_per_game = _round(assists_total / games) if assists_total is not None and games else None
        turnovers_per_game = _round(turnovers_total / games) if turnovers_total is not None and games else None
        steals_per_game = _round(steals_total / games) if steals_total is not None and games else None
        blocks_per_game = _round(blocks_total / games) if blocks_total is not None and games else None
        assist_to_turnover_ratio = _round(assists_total / turnovers_total) if assists_total is not None and turnovers_total else None
    else:
        points_for = _stat_per_game(values, games, "points", "for")
        field_goal_percentage = _find_number(values, "field", "goal", "percentage")
        three_point_percentage = _find_number(values, "three", "point", "percentage")
        rebounds_per_game = _stat_per_game(values, games, "rebounds")
        assists_per_game = _stat_per_game(values, games, "assists")
        turnovers_per_game = _stat_per_game(values, games, "turnovers")
        steals_per_game = _stat_per_game(values, games, "steals")
        blocks_per_game = _stat_per_game(values, games, "blocks")
        free_throw_percentage = _find_number(values, "free", "throw", "percentage")
        three_point_attempts_per_game = _stat_per_game(values, games, "three", "point", "attempt")
        free_throw_attempts_per_game = _stat_per_game(values, games, "free", "throw", "attempt")
        offensive_rebounds_per_game = _stat_per_game(values, games, "offensive", "rebound")
        defensive_rebounds_per_game = _stat_per_game(values, games, "defensive", "rebound")
        assist_to_turnover_ratio = _round(assists_per_game / turnovers_per_game) if assists_per_game is not None and turnovers_per_game else None

    completed_scores = [
        _score_for_team(game, team_id)
        for game in game_records or []
        if team_id and _completed_game(game)
    ]
    scored_points = [opponent for _, opponent in completed_scores if opponent is not None]
    points_allowed = _average(scored_points) or _stat_per_game(values, games, "points", "against")
    current_roster = _roster_membership(current_roster_records, team_id)
    historical_context = None
    historical_players: list[dict[str, Any]] = []
    if historical_season is not None and historical_player_records is not None:
        historical_players = _notable_nba_players(
            historical_player_records,
            None,
            historical=True,
            roster_membership=current_roster,
        ) if current_roster is not None else []
        historical_context = {
            "season": str(historical_season),
            "players": historical_players,
            "roster_verified": current_roster is not None,
        }

    # Current-season player statistics can include old team associations around
    # trades or pre-season. Never display them until the current roster endpoint
    # confirms the same player belongs to this team.
    current_players = _notable_nba_players(
        player_records,
        injury_records,
        roster_membership=current_roster,
    ) if current_roster is not None else []
    current_injuries = _injury_map(injury_records)
    fallback_players = [
        {
            **player,
            "availability": current_injuries.get(_normalize(player["name"])),
        }
        for player in historical_players
    ]
    notable_players = current_players or fallback_players
    notable_players_source = (
        "current_season" if current_players
        else "previous_season_roster" if fallback_players
        else "unavailable"
    )

    return {
        "team": team_name,
        "games": games,
        "offense": {
            "points_per_game": points_for,
            "field_goal_percentage": field_goal_percentage,
            "three_point_percentage": three_point_percentage,
            "rebounds_per_game": rebounds_per_game,
            "assists_per_game": assists_per_game,
            "turnovers_per_game": turnovers_per_game,
            "free_throw_percentage": free_throw_percentage,
            "free_throw_attempts_per_game": free_throw_attempts_per_game,
            "three_point_attempts_per_game": three_point_attempts_per_game,
            "offensive_rebounds_per_game": offensive_rebounds_per_game,
            "defensive_rebounds_per_game": defensive_rebounds_per_game,
            "assist_to_turnover_ratio": assist_to_turnover_ratio,
        },
        "defense": {
            "points_allowed_per_game": points_allowed,
            "steals_per_game": steals_per_game,
            "blocks_per_game": blocks_per_game,
            "opponent_field_goal_percentage": _find_number(values, "opponent", "field", "goal", "percentage"),
        },
        "form": _nba_form(game_records, team_id),
        "notable_players": notable_players,
        "notable_players_source": notable_players_source,
        "historical_player_context": historical_context,
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
        stat_payloads, event_payloads, roster_payload = await asyncio.gather(
            asyncio.gather(
                *[_get("nfl", "games/statistics/teams", {"id": game_id}) for _, game_id in completed_with_ids],
                return_exceptions=True,
            ),
            asyncio.gather(
                *[_optional_get("nfl", "games/events", {"id": game_id}) for _, game_id in completed_with_ids],
                return_exceptions=True,
            ),
            _optional_get("nfl", "players", {"team": team_id, "season": season}),
            return_exceptions=True,
        )
        samples: list[dict[str, float | None]] = []
        first_error: ApiSportsUnavailable | None = None
        for (game, _), payload, events in zip(completed_with_ids, stat_payloads, event_payloads, strict=False):
            if isinstance(payload, ApiSportsUnavailable):
                first_error = first_error or payload
                continue
            if isinstance(payload, Exception):
                continue
            event_records = _records(events) if events is not None and not isinstance(events, Exception) else None
            sample = _nfl_stat_sample(game, team_id, _records(payload), event_records)
            if sample:
                samples.append(sample)
        if not samples:
            raise first_error or ApiSportsUnavailable(f"API-Sports returned no team box-score data for {name}.")
        quarterbacks = [
            player for player in _records(roster_payload)
            if str(player.get("position") or "").upper() in {"QB", "QUARTERBACK"}
        ][:MAX_NFL_QUARTERBACKS]
        quarterback_payloads = await asyncio.gather(
            *[_optional_get("nfl", "players/statistics", {"id": player["id"], "season": season}) for player in quarterbacks],
            return_exceptions=True,
        )
        quarterback_records: list[dict[str, Any]] = []
        for quarterback, payload in zip(quarterbacks, quarterback_payloads, strict=False):
            if isinstance(payload, Exception):
                continue
            for record in _records(payload):
                player = dict(record.get("player") or {})
                player["position"] = quarterback.get("position") or "QB"
                quarterback_records.append({**record, "player": player})
        return summarize_nfl_samples(name, samples, quarterback_records)

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
        stats, players, injuries, games, historical_players, current_roster = await asyncio.gather(
            _get("nba", "teams/statistics", {"id": team_id, "season": season}),
            _optional_get("nba", "players/statistics", {"team": team_id, "season": season}),
            _optional_get("nba", "injuries", {"team": team_id, "season": season}),
            _optional_get("nba", "games", {"team": team_id, "season": season}),
            _optional_get("nba", "players/statistics", {"team": team_id, "season": season - 1}),
            _optional_get("nba", "players", {"team": team_id, "season": season}),
        )
        records = _records(stats)
        if not records:
            raise ApiSportsUnavailable(f"API-Sports has no {season} NBA team statistics for {name} yet.")
        return summarize_nba_team(
            name,
            records[0],
            _records(players),
            _records(injuries),
            _records(games),
            team_id,
            _records(historical_players),
            season - 1,
            _records(current_roster) if current_roster is not None else None,
        )

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
