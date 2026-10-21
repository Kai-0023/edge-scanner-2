"""Tests for the API-Sports normalization layer without live provider calls."""

from scrapers.api_sports_scraper import summarize_nba_team, summarize_nfl_samples


def test_nfl_samples_create_per_game_context_and_quarterback_summary() -> None:
    result = summarize_nfl_samples(
        "New Orleans Saints",
        [
            {
                "points_for": 24,
                "points_allowed": 17,
                "passing_yards": 245,
                "rushing_yards": 110,
                "sacks_allowed": 2,
                "touchdowns": 3,
                "red_zone_attempts": 4,
                "red_zone_touchdowns": 3,
                "passing_yards_allowed": 210,
                "rushing_yards_allowed": 92,
                "sacks": 3,
                "interceptions": 1,
                "red_zone_attempts_allowed": 3,
                "red_zone_touchdowns_allowed": 1,
            },
            {
                "points_for": 20,
                "points_allowed": 21,
                "passing_yards": 215,
                "rushing_yards": 95,
                "sacks_allowed": 1,
                "touchdowns": 2,
                "red_zone_attempts": 3,
                "red_zone_touchdowns": 2,
                "passing_yards_allowed": 235,
                "rushing_yards_allowed": 105,
                "sacks": 2,
                "interceptions": 2,
                "red_zone_attempts_allowed": 4,
                "red_zone_touchdowns_allowed": 3,
            },
        ],
        [
            {
                "player": {"name": "Jordan Example", "position": "QB"},
                "statistics": {
                    "games": {"played": 2},
                    "passing": {"yards": 460, "touchdowns": 4, "interceptions": 1},
                    "rushing": {"yards": 41, "touchdowns": 1},
                    "sacks": 3,
                },
            }
        ],
    )

    assert result["games"] == 2
    assert result["quarterback"]["name"] == "Jordan Example"
    assert result["quarterback"]["passing_yards_per_game"] == 230
    assert result["offense"]["points_per_game"] == 22
    assert result["offense"]["red_zone_touchdown_rate"] == 71.4
    assert result["defense"]["points_allowed_per_game"] == 19
    assert result["defense"]["red_zone_touchdown_rate_allowed"] == 57.1


def test_nba_summary_keeps_unavailable_injury_data_distinct_from_no_injuries() -> None:
    result = summarize_nba_team(
        "New Orleans Pelicans",
        {
            "games": {"played": {"all": 10}},
            "points": {"for": {"average": 113.4}, "against": {"average": 108.2}},
            "field_goals": {"percentage": 48.1},
            "three_points": {"percentage": 37.2},
            "rebounds": {"total": 440},
            "assists": {"total": 270},
            "turnovers": {"total": 138},
            "steals": {"total": 76},
            "blocks": {"total": 51},
            "opponent": {"field_goals": {"percentage": 45.5}},
        },
        [
            {
                "player": {"name": "Player Example", "position": "F"},
                "statistics": {
                    "games": {"played": 10},
                    "points": {"average": 26.4},
                    "rebounds": {"total": 74},
                    "assists": {"total": 59},
                },
            }
        ],
        None,
    )

    assert result["offense"]["points_per_game"] == 113.4
    assert result["offense"]["rebounds_per_game"] == 44
    assert result["defense"]["points_allowed_per_game"] == 108.2
    assert result["notable_players"][0]["name"] == "Player Example"
    assert result["notable_players"][0]["availability"] == "Availability data unavailable"


def test_nba_direct_stat_and_game_log_shape_is_normalized() -> None:
    result = summarize_nba_team(
        "New Orleans Pelicans",
        {
            "games": 10,
            "points": 1120,
            "fgm": 481,
            "fga": 1000,
            "tpm": 372,
            "tpa": 1000,
            "totReb": 440,
            "assists": 270,
            "turnovers": 138,
            "steals": 76,
            "blocks": 51,
        },
        [
            {
                "player": {"firstname": "Player", "lastname": "Example"},
                "game": {"id": 1},
                "pos": "F",
                "points": 25,
                "totReb": 7,
                "assists": 6,
            },
            {
                "player": {"firstname": "Player", "lastname": "Example"},
                "game": {"id": 2},
                "pos": "F",
                "points": 21,
                "totReb": 5,
                "assists": 4,
            },
        ],
        [],
        [
            {
                "status": {"short": 3, "long": "Finished"},
                "teams": {"home": {"id": 23}, "visitors": {"id": 24}},
                "scores": {"home": {"points": 112}, "visitors": {"points": 107}},
            }
        ],
        "23",
    )

    assert result["games"] == 10
    assert result["offense"]["points_per_game"] == 112
    assert result["offense"]["field_goal_percentage"] == 48.1
    assert result["offense"]["three_point_percentage"] == 37.2
    assert result["offense"]["rebounds_per_game"] == 44
    assert result["defense"]["points_allowed_per_game"] == 107
    assert result["notable_players"][0]["name"] == "Player Example"
    assert result["notable_players"][0]["points_per_game"] == 23
