"""Tests for transparent matchup explanations."""

from logic.matchup_insights import nba_matchup_insight, nfl_matchup_insight


def test_nba_insight_names_the_favored_team_and_is_not_labeled_ml() -> None:
    insight = nba_matchup_insight(
        {
            "team_name": "Home",
            "offensive_rating": 118,
            "defensive_rating": 110,
            "recent_net_rating": 6,
            "pace": 100,
            "rest_days": 2,
            "injury_adjustment": 0,
        },
        {
            "team_name": "Away",
            "offensive_rating": 108,
            "defensive_rating": 116,
            "recent_net_rating": -2,
            "pace": 99,
            "rest_days": 1,
            "injury_adjustment": -1,
        },
        {"projected_home_margin": 8.2, "home_win_probability": 0.72},
    )

    assert "Home by 8.2" in insight["summary"]
    assert "not trained ML" in insight["method"]
    assert insight["drivers"][0]["favors"] == "Home"


def test_nfl_insight_handles_an_away_favorite() -> None:
    insight = nfl_matchup_insight(
        {
            "offense_points": 20,
            "defense_points_allowed": 27,
            "recent_rating": -3,
            "rest_days": 5,
            "qb_adjustment": -1,
            "injury_adjustment": -1,
            "weather_adjustment": 0,
        },
        {
            "team_name": "Away",
            "offense_points": 28,
            "defense_points_allowed": 19,
            "recent_rating": 4,
            "rest_days": 8,
            "qb_adjustment": 1,
            "injury_adjustment": 0,
            "weather_adjustment": 0,
        },
        {"projected_home_margin": -7.0, "home_win_probability": 0.25},
    )

    assert "Away by 7.0" in insight["summary"]
    assert insight["league"] == "nfl"
