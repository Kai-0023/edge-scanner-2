"""Transparent starter projections for NBA and NFL games.

These formulas are a baseline for testing ideas, not a trained betting model or a
guarantee of an outcome. Every adjustment should be validated against historical
games before relying on it.
"""

from math import exp


def win_probability(projected_margin: float, scale: float = 6.5) -> float:
    """Convert a projected home-team margin into a simple win probability."""

    return round(1 / (1 + exp(-projected_margin / scale)), 4)


def nba_projection(
    home_offensive_rating: float, home_defensive_rating: float,
    home_recent_net_rating: float, home_pace: float, home_rest_days: int,
    home_injury_adjustment: float, away_offensive_rating: float,
    away_defensive_rating: float, away_recent_net_rating: float,
    away_pace: float, away_rest_days: int, away_injury_adjustment: float,
) -> dict[str, float]:
    """Project an NBA score from efficiency, pace, form, rest, and injuries."""

    expected_possessions = (home_pace + away_pace) / 2
    home_base = ((home_offensive_rating + away_defensive_rating) / 2) * expected_possessions / 100
    away_base = ((away_offensive_rating + home_defensive_rating) / 2) * expected_possessions / 100
    margin = (
        home_base - away_base + 1.75
        + 0.4 * (home_rest_days - away_rest_days)
        + 0.2 * (home_recent_net_rating - away_recent_net_rating)
        + home_injury_adjustment - away_injury_adjustment
    )
    total = home_base + away_base + home_injury_adjustment + away_injury_adjustment
    return {
        "projected_home_margin": round(margin, 1),
        "projected_total": round(total, 1),
        "home_win_probability": win_probability(margin),
        "expected_possessions": round(expected_possessions, 1),
    }


def nfl_projection(
    home_offense_points: float, home_defense_points_allowed: float,
    home_recent_rating: float, home_rest_days: int, home_qb_adjustment: float,
    home_injury_adjustment: float, home_weather_adjustment: float,
    away_offense_points: float, away_defense_points_allowed: float,
    away_recent_rating: float, away_rest_days: int, away_qb_adjustment: float,
    away_injury_adjustment: float, away_weather_adjustment: float,
) -> dict[str, float]:
    """Project an NFL margin using performance, QB, injury, rest, and weather."""

    home_base = (home_offense_points + away_defense_points_allowed) / 2
    away_base = (away_offense_points + home_defense_points_allowed) / 2
    margin = (
        home_base - away_base + 1.5
        + 0.25 * (home_rest_days - away_rest_days)
        + 0.15 * (home_recent_rating - away_recent_rating)
        + home_qb_adjustment + home_injury_adjustment
        - away_qb_adjustment - away_injury_adjustment
        + home_weather_adjustment - away_weather_adjustment
    )
    total = home_base + away_base + home_injury_adjustment + away_injury_adjustment
    return {
        "projected_home_margin": round(margin, 1),
        "projected_total": round(total, 1),
        "home_win_probability": win_probability(margin),
    }
