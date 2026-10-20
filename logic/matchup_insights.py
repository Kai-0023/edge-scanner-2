"""Plain-language explanations for the transparent starter projections.

The app deliberately keeps these explanations deterministic. They describe the
same factors used by ``projection_models`` and are not a trained machine-learning
model, a betting recommendation, or a guarantee of an outcome.
"""

from __future__ import annotations

from typing import Any


def _team_name(factors: dict[str, Any], fallback: str) -> str:
    return factors.get("team_name") or fallback


def _driver(label: str, impact: float, home_name: str, away_name: str) -> dict[str, Any]:
    """Describe which side a positive model contribution favors."""

    return {
        "factor": label,
        "model_impact_points": round(impact, 2),
        "favors": home_name if impact >= 0 else away_name,
    }


def _signal_strength(home_win_probability: float) -> str:
    """Label separation from 50% without presenting it as calibrated confidence."""

    distance_from_even = abs(home_win_probability - 0.5)
    if distance_from_even >= 0.22:
        return "strong baseline signal"
    if distance_from_even >= 0.1:
        return "moderate baseline signal"
    return "limited baseline signal"


def _base_response(
    league: str,
    home_name: str,
    away_name: str,
    projection: dict[str, float],
    drivers: list[dict[str, Any]],
) -> dict[str, Any]:
    margin = projection["projected_home_margin"]
    probability = projection["home_win_probability"]
    favored_team = home_name if margin >= 0 else away_name
    return {
        "method": "Transparent rule-based explanation (not trained ML)",
        "baseline_signal": _signal_strength(probability),
        "summary": (
            f"The baseline projects {favored_team} by {abs(margin):.1f} points. "
            f"It assigns {home_name} a {probability:.0%} home-win probability based on the supplied factors."
        ),
        "drivers": sorted(drivers, key=lambda driver: abs(driver["model_impact_points"]), reverse=True),
        "disclaimer": (
            "This is an explanation of user-supplied inputs, not financial advice or a guarantee. "
            "Validate inputs and local requirements before making any decision."
        ),
        "league": league,
    }


def nba_matchup_insight(
    home: dict[str, Any], away: dict[str, Any], projection: dict[str, float]
) -> dict[str, Any]:
    """Explain the NBA baseline using the exact adjustment categories in its formula."""

    home_name = _team_name(home, "Home team")
    away_name = _team_name(away, "Away team")
    possessions = (home["pace"] + away["pace"]) / 2
    home_base = (home["offensive_rating"] + away["defensive_rating"]) / 2 * possessions / 100
    away_base = (away["offensive_rating"] + home["defensive_rating"]) / 2 * possessions / 100
    drivers = [
        _driver("baseline efficiency", home_base - away_base, home_name, away_name),
        _driver("recent net rating", 0.2 * (home["recent_net_rating"] - away["recent_net_rating"]), home_name, away_name),
        _driver("rest", 0.4 * (home["rest_days"] - away["rest_days"]), home_name, away_name),
        _driver("injury adjustment", home["injury_adjustment"] - away["injury_adjustment"], home_name, away_name),
    ]
    return _base_response("nba", home_name, away_name, projection, drivers)


def nfl_matchup_insight(
    home: dict[str, Any], away: dict[str, Any], projection: dict[str, float]
) -> dict[str, Any]:
    """Explain the NFL baseline using the exact adjustment categories in its formula."""

    home_name = _team_name(home, "Home team")
    away_name = _team_name(away, "Away team")
    home_base = (home["offense_points"] + away["defense_points_allowed"]) / 2
    away_base = (away["offense_points"] + home["defense_points_allowed"]) / 2
    drivers = [
        _driver("baseline offense and defense", home_base - away_base, home_name, away_name),
        _driver("recent rating", 0.15 * (home["recent_rating"] - away["recent_rating"]), home_name, away_name),
        _driver("rest", 0.25 * (home["rest_days"] - away["rest_days"]), home_name, away_name),
        _driver("quarterback adjustment", home["qb_adjustment"] - away["qb_adjustment"], home_name, away_name),
        _driver("injury adjustment", home["injury_adjustment"] - away["injury_adjustment"], home_name, away_name),
        _driver("weather adjustment", home["weather_adjustment"] - away["weather_adjustment"], home_name, away_name),
    ]
    return _base_response("nfl", home_name, away_name, projection, drivers)
