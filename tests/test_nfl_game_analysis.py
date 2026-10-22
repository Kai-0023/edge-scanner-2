"""Tests for NFL season-stat summaries used in the team insights tab."""

from logic.nfl_game_analysis import matchup_summary, summarize_team


def _team_record() -> dict:
    return {
        "Games": 5,
        "Score": 125,
        "PointsAllowed": 110,
        "PassingYards": 1_150,
        "RushingYards": 620,
        "TimesSacked": 10,
        "Touchdowns": 15,
        "RedZoneAttempts": 20,
        "RedZoneConversions": 12,
        "OpponentPassingYards": 1_000,
        "OpponentRushingYards": 500,
        "Sacks": 14,
        "Interceptions": 7,
        "OpponentRedZoneAttempts": 18,
        "OpponentRedZoneConversions": 8,
    }


def _quarterbacks() -> list[dict]:
    return [
        {"Name": "Backup QB", "Position": "QB", "PassingYards": 100, "Games": 2},
        {
            "Name": "Starter QB",
            "Position": "QB",
            "PassingYards": 1_250,
            "PassingTouchdowns": 10,
            "PassingInterceptions": 3,
            "RushingYards": 175,
            "RushingTouchdowns": 2,
            "PassingSacks": 9,
            "Games": 5,
        },
    ]


def test_team_summary_selects_the_leading_quarterback_and_normalizes_rates() -> None:
    summary = summarize_team(_team_record(), _quarterbacks(), "Example Team")

    assert summary["quarterback"]["name"] == "Starter QB"
    assert summary["quarterback"]["passing_yards_per_game"] == 250.0
    assert summary["offense"]["points_per_game"] == 25.0
    assert summary["offense"]["red_zone_touchdown_rate"] == 60.0
    assert summary["defense"]["sacks_per_game"] == 2.8
    assert summary["defense"]["red_zone_touchdown_rate_allowed"] == 44.4


def test_matchup_summary_blends_each_offense_with_opponent_defense() -> None:
    home = summarize_team(_team_record(), _quarterbacks(), "Home")
    away_record = _team_record() | {"Score": 100, "PointsAllowed": 130}
    away = summarize_team(away_record, _quarterbacks(), "Away")

    summary = matchup_summary(home, away)

    assert summary["estimated_home_points"] == 25.5
    assert summary["estimated_away_points"] == 21.0
    assert summary["estimated_total"] == 46.5
    assert summary["estimated_home_margin"] == 4.5
    assert "not added to this scoring blend" in summary["opponent_strength_note"]
    assert "not confirmation of game-day active status" in summary["availability_note"]
