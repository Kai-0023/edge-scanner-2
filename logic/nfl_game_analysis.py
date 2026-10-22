"""Normalize authorized NFL team and quarterback stats for matchup research.

The helpers in this module deliberately produce descriptive, season-to-date
context. They do not estimate a probability of winning or guarantee a wager.
"""

from __future__ import annotations

from typing import Any


def _number(record: dict[str, Any], *keys: str) -> float | None:
    """Return the first usable numeric field from a provider record."""

    for key in keys:
        value = record.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _per_game(value: float | None, games: float | None) -> float | None:
    if value is None or games is None or games <= 0:
        return None
    return round(value / games, 1)


def _percentage(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return round(numerator / denominator * 100, 1)


def _player_name(player: dict[str, Any]) -> str:
    return str(
        player.get("Name")
        or " ".join(part for part in [player.get("FirstName"), player.get("LastName")] if part)
        or "Quarterback unavailable"
    )


def _leading_quarterback(players: list[dict[str, Any]]) -> dict[str, Any] | None:
    quarterbacks = [player for player in players if str(player.get("Position", "")).upper() == "QB"]
    if not quarterbacks:
        return None
    return max(quarterbacks, key=lambda player: _number(player, "PassingYards") or 0)


def summarize_team(team: dict[str, Any], players: list[dict[str, Any]], team_name: str) -> dict[str, Any]:
    """Return only the offensive, defensive, and QB fields shown in the app."""

    games = _number(team, "Games", "GamesPlayed")
    quarterback = _leading_quarterback(players)
    quarterback_games = _number(quarterback or {}, "Games", "GamesPlayed")

    qb_summary: dict[str, Any] | None = None
    if quarterback:
        passing_yards = _number(quarterback, "PassingYards")
        rushing_yards = _number(quarterback, "RushingYards")
        qb_summary = {
            "name": _player_name(quarterback),
            "games": quarterback_games,
            "passing_yards": passing_yards,
            "passing_yards_per_game": _per_game(passing_yards, quarterback_games),
            "passing_touchdowns": _number(quarterback, "PassingTouchdowns"),
            "passing_interceptions": _number(quarterback, "PassingInterceptions"),
            "rushing_yards": rushing_yards,
            "rushing_yards_per_game": _per_game(rushing_yards, quarterback_games),
            "rushing_touchdowns": _number(quarterback, "RushingTouchdowns"),
            "sacks_taken": _number(quarterback, "PassingSacks"),
        }

    points = _number(team, "Score", "Points")
    points_allowed = _number(team, "PointsAllowed", "OpponentScore", "OpponentPoints")
    passing_yards = _number(team, "PassingYards")
    rushing_yards = _number(team, "RushingYards")
    touchdowns = _number(team, "Touchdowns", "OffensiveTouchdowns")
    red_zone_attempts = _number(team, "RedZoneAttempts")
    red_zone_touchdowns = _number(team, "RedZoneConversions")
    opponent_red_zone_attempts = _number(team, "OpponentRedZoneAttempts")
    opponent_red_zone_touchdowns = _number(team, "OpponentRedZoneConversions")

    return {
        "team": team_name,
        "games": games,
        "quarterback": qb_summary,
        "offense": {
            "points_per_game": _per_game(points, games),
            "passing_yards_per_game": _per_game(passing_yards, games),
            "rushing_yards_per_game": _per_game(rushing_yards, games),
            "sacks_allowed_per_game": _per_game(_number(team, "TimesSacked"), games),
            "touchdowns_per_game": _per_game(touchdowns, games),
            "red_zone_touchdown_rate": _percentage(red_zone_touchdowns, red_zone_attempts),
        },
        "defense": {
            "points_allowed_per_game": _per_game(points_allowed, games),
            "passing_yards_allowed_per_game": _per_game(_number(team, "OpponentPassingYards"), games),
            "rushing_yards_allowed_per_game": _per_game(_number(team, "OpponentRushingYards"), games),
            "sacks_per_game": _per_game(_number(team, "Sacks"), games),
            "interceptions_per_game": _per_game(_number(team, "Interceptions"), games),
            "red_zone_touchdown_rate_allowed": _percentage(
                opponent_red_zone_touchdowns, opponent_red_zone_attempts
            ),
        },
    }


def _average(first: float | None, second: float | None) -> float | None:
    if first is None or second is None:
        return None
    return round((first + second) / 2, 1)


def matchup_summary(home: dict[str, Any], away: dict[str, Any]) -> dict[str, Any]:
    """Create a transparent scoring-context estimate from season per-game rates."""

    home_points = _average(
        home["offense"]["points_per_game"], away["defense"]["points_allowed_per_game"]
    )
    away_points = _average(
        away["offense"]["points_per_game"], home["defense"]["points_allowed_per_game"]
    )
    projected_total = round(home_points + away_points, 1) if home_points is not None and away_points is not None else None
    projected_home_margin = round(home_points - away_points, 1) if home_points is not None and away_points is not None else None

    return {
        "method": "Season-to-date scoring blend: each team's points per game averaged with the opponent's points allowed per game.",
        "estimated_home_points": home_points,
        "estimated_away_points": away_points,
        "estimated_total": projected_total,
        "estimated_home_margin": projected_home_margin,
        "opponent_strength_note": (
            "Opponent-strength results are shown separately and are not added to this scoring blend. "
            "A positive offensive delta means a team scored above its opponents' usual allowance; a positive defensive delta means it held opponents below their usual scoring."
        ),
        "availability_note": (
            "Reported QB, skill-position, and defensive-player availability notices are shown separately. "
            "They are not confirmation of game-day active status and are not added to this scoring blend."
        ),
        "disclaimer": "This is descriptive season-to-date context, not a validated prediction, probability, or guaranteed bet.",
    }
