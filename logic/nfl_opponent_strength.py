"""Opponent-strength context from completed NFL game scores.

This is a descriptive comparison of what a team scored or allowed relative to
its opponents' season-to-date norms. It is intentionally separate from the
app's transparent scoring blend and does not produce a betting recommendation.
"""

from __future__ import annotations

from typing import Any


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _third_cutoff(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def _game_result(game: dict[str, Any]) -> tuple[str, str, float, float] | None:
    teams = game.get("teams")
    scores = game.get("scores")
    if not isinstance(teams, dict) or not isinstance(scores, dict):
        return None
    home = teams.get("home")
    away = teams.get("away")
    home_score = scores.get("home")
    away_score = scores.get("away")
    if not all(isinstance(value, dict) for value in (home, away, home_score, away_score)):
        return None
    home_id = home.get("id")
    away_id = away.get("id")
    home_points = _number(home_score.get("total"))
    away_points = _number(away_score.get("total"))
    if home_id is None or away_id is None or home_points is None or away_points is None:
        return None
    return str(home_id), str(away_id), home_points, away_points


def _group_summary(samples: list[tuple[float, float]]) -> dict[str, float | int | None]:
    """Return actual PPG, opponent norm, and the difference for one group."""

    actual = _mean([sample[0] for sample in samples])
    opponent_norm = _mean([sample[1] for sample in samples])
    return {
        "games": len(samples),
        "points_per_game": actual,
        "opponent_norm_points_per_game": opponent_norm,
        "delta_from_opponent_norm": round(actual - opponent_norm, 1) if actual is not None and opponent_norm is not None else None,
    }


def nfl_opponent_strength_context(completed_games: list[dict[str, Any]], team_id: str) -> dict[str, Any]:
    """Compare a team's output against top- and bottom-third opponents.

    Stronger defenses have lower points allowed per game; premier offenses have
    higher points scored per game. Every value is season-to-date and includes
    only completed games passed into this function.
    """

    team_totals: dict[str, dict[str, float]] = {}
    results: list[tuple[str, str, float, float]] = []
    for game in completed_games:
        result = _game_result(game)
        if result is None:
            continue
        home_id, away_id, home_points, away_points = result
        results.append(result)
        for current_id, scored, allowed in ((home_id, home_points, away_points), (away_id, away_points, home_points)):
            totals = team_totals.setdefault(current_id, {"games": 0, "scored": 0, "allowed": 0})
            totals["games"] += 1
            totals["scored"] += scored
            totals["allowed"] += allowed

    team_rates = {
        current_id: {
            "points_per_game": round(totals["scored"] / totals["games"], 1),
            "points_allowed_per_game": round(totals["allowed"] / totals["games"], 1),
        }
        for current_id, totals in team_totals.items()
        if totals["games"]
    }
    if str(team_id) not in team_rates or len(team_rates) < 4:
        return {
            "available": False,
            "reason": "Not enough completed league games to compare opponent strength yet.",
        }

    defensive_allowances = [rate["points_allowed_per_game"] for rate in team_rates.values()]
    scoring_rates = [rate["points_per_game"] for rate in team_rates.values()]
    stronger_defense_cutoff = _third_cutoff(defensive_allowances, 1 / 3)
    weaker_defense_cutoff = _third_cutoff(defensive_allowances, 2 / 3)
    premier_offense_cutoff = _third_cutoff(scoring_rates, 2 / 3)
    weaker_offense_cutoff = _third_cutoff(scoring_rates, 1 / 3)
    if None in {stronger_defense_cutoff, weaker_defense_cutoff, premier_offense_cutoff, weaker_offense_cutoff}:
        return {"available": False, "reason": "Opponent strength thresholds are unavailable."}

    offense_vs_stronger: list[tuple[float, float]] = []
    offense_vs_weaker: list[tuple[float, float]] = []
    defense_vs_premier: list[tuple[float, float]] = []
    defense_vs_weaker: list[tuple[float, float]] = []
    for home_id, away_id, home_points, away_points in results:
        if str(team_id) == home_id:
            opponent_id, own_points, points_allowed = away_id, home_points, away_points
        elif str(team_id) == away_id:
            opponent_id, own_points, points_allowed = home_id, away_points, home_points
        else:
            continue
        opponent = team_rates.get(opponent_id)
        if opponent is None:
            continue
        if opponent["points_allowed_per_game"] <= stronger_defense_cutoff:
            offense_vs_stronger.append((own_points, opponent["points_allowed_per_game"]))
        if opponent["points_allowed_per_game"] >= weaker_defense_cutoff:
            offense_vs_weaker.append((own_points, opponent["points_allowed_per_game"]))
        if opponent["points_per_game"] >= premier_offense_cutoff:
            # Positive defensive delta means this team held the opponent below its normal scoring rate.
            defense_vs_premier.append((opponent["points_per_game"] - points_allowed, opponent["points_per_game"]))
        if opponent["points_per_game"] <= weaker_offense_cutoff:
            defense_vs_weaker.append((opponent["points_per_game"] - points_allowed, opponent["points_per_game"]))

    def defense_summary(samples: list[tuple[float, float]]) -> dict[str, float | int | None]:
        delta = _mean([sample[0] for sample in samples])
        opponent_norm = _mean([sample[1] for sample in samples])
        return {
            "games": len(samples),
            "points_allowed_per_game": round(opponent_norm - delta, 1) if delta is not None and opponent_norm is not None else None,
            "opponent_norm_points_per_game": opponent_norm,
            "delta_from_opponent_norm": delta,
        }

    return {
        "available": True,
        "method": (
            "Season-to-date completed games. Stronger/weaker defenses and premier/weaker offenses are based on "
            "the top or bottom third of qualifying teams by points allowed or points scored per game."
        ),
        "offense": {
            "vs_stronger_defenses": _group_summary(offense_vs_stronger),
            "vs_weaker_defenses": _group_summary(offense_vs_weaker),
        },
        "defense": {
            "vs_premier_offenses": defense_summary(defense_vs_premier),
            "vs_weaker_offenses": defense_summary(defense_vs_weaker),
        },
    }
