"""Tests for the API-Sports normalization layer without live provider calls."""

from scrapers.api_sports_scraper import _nfl_stat_sample, summarize_nba_team, summarize_nfl_samples


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


def test_nfl_box_score_shape_maps_all_displayed_team_statistics() -> None:
    sample = _nfl_stat_sample(
        {
            "teams": {"home": {"id": 27}, "away": {"id": 8}},
            "scores": {"home": {"total": 20}, "away": {"total": 16}},
        },
        "27",
        [
            {
                "team": {"id": 27},
                "statistics": {
                    "passing": {"total": 232, "sacks_yards_lost": "4-27"},
                    "rushings": {"total": 108},
                    "red_zone": {"made_att": "2-3"},
                    "sacks": {"total": 4},
                    "interceptions": {"total": 1},
                },
            },
            {
                "team": {"id": 8},
                "statistics": {
                    "passing": {"total": 180, "sacks_yards_lost": "2-15"},
                    "rushings": {"total": 49},
                    "red_zone": {"made_att": "1-2"},
                    "sacks": {"total": 2},
                    "interceptions": {"total": 0},
                },
            },
        ],
        [
            {"team": {"id": 27}, "type": "TD"},
            {"team": {"id": 27}, "type": "TD"},
            {"team": {"id": 8}, "type": "TD"},
        ],
    )

    assert sample == {
        "points_for": 20,
        "points_allowed": 16,
        "passing_yards": 232,
        "rushing_yards": 108,
        "sacks_allowed": 4,
        "touchdowns": 2,
        "red_zone_attempts": 3,
        "red_zone_touchdowns": 2,
        "passing_yards_allowed": 180,
        "rushing_yards_allowed": 49,
        "sacks": 4,
        "interceptions": 1,
        "red_zone_attempts_allowed": 2,
        "red_zone_touchdowns_allowed": 1,
    }


def test_nfl_quarterback_summary_supports_provider_season_shape() -> None:
    result = summarize_nfl_samples(
        "New Orleans Saints",
        [{"points_for": 20, "points_allowed": 16}],
        [
            {
                "player": {"name": "Tyler Example", "position": "QB"},
                "teams": [
                    {
                        "groups": [
                            {
                                "name": "Passing",
                                "statistics": [
                                    {"name": "yards", "value": "2,384"},
                                    {"name": "yards per game", "value": "216.7"},
                                    {"name": "passing touchdowns", "value": "10"},
                                    {"name": "interceptions", "value": "6"},
                                    {"name": "sacks", "value": "31"},
                                ],
                            },
                            {
                                "name": "Rushing",
                                "statistics": [
                                    {"name": "yards", "value": "186"},
                                    {"name": "yards per game", "value": "16.9"},
                                    {"name": "rushing touchdowns", "value": "3"},
                                ],
                            },
                        ]
                    }
                ],
            }
        ],
    )

    assert result["quarterback"]["name"] == "Tyler Example"
    assert result["quarterback"]["passing_yards"] == 2384
    assert result["quarterback"]["passing_yards_per_game"] == 216.7
    assert result["quarterback"]["rushing_yards"] == 186
    assert result["quarterback"]["rushing_yards_per_game"] == 16.9
    assert result["quarterback"]["sacks_taken"] == 31


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
            "ftm": 164,
            "fta": 205,
            "offReb": 98,
            "defReb": 342,
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
                "date": {"start": "2026-10-01T00:00:00+00:00"},
                "teams": {"home": {"id": 23}, "visitors": {"id": 24}},
                "scores": {"home": {"points": 112}, "visitors": {"points": 107}},
            },
            {
                "status": {"short": 3, "long": "Finished"},
                "date": {"start": "2026-10-02T00:00:00+00:00"},
                "teams": {"home": {"id": 24}, "visitors": {"id": 23}},
                "scores": {"home": {"points": 110}, "visitors": {"points": 105}},
            }
        ],
        "23",
        [
            {
                "player": {"firstname": "Historical", "lastname": "Star"},
                "game": {"id": 10},
                "pos": "G",
                "points": 30,
                "totReb": 6,
                "assists": 8,
            }
        ],
        2025,
        [{"name": "Historical Star"}],
    )

    assert result["games"] == 10
    assert result["offense"]["points_per_game"] == 112
    assert result["offense"]["field_goal_percentage"] == 48.1
    assert result["offense"]["three_point_percentage"] == 37.2
    assert result["offense"]["free_throw_percentage"] == 80
    assert result["offense"]["offensive_rebounds_per_game"] == 9.8
    assert result["offense"]["assist_to_turnover_ratio"] == 2
    assert result["offense"]["rebounds_per_game"] == 44
    assert result["defense"]["points_allowed_per_game"] == 108.5
    assert result["form"]["recent_form"] == ["L", "W"]
    assert result["form"]["wins"] == 1
    assert result["form"]["losses"] == 1
    assert result["notable_players"][0]["name"] == "Player Example"
    assert result["notable_players"][0]["points_per_game"] == 23
    assert result["historical_player_context"]["season"] == "2025"
    assert result["historical_player_context"]["roster_verified"] is True
    assert result["historical_player_context"]["players"][0]["name"] == "Historical Star"
    assert result["historical_player_context"]["players"][0]["availability"] is None


def test_nba_historical_players_exclude_players_no_longer_on_the_current_roster() -> None:
    result = summarize_nba_team(
        "Example Team",
        {"games": 1, "points": 100, "fgm": 40, "fga": 80, "tpm": 10, "tpa": 30, "ftm": 10, "fta": 12},
        [],
        [],
        historical_player_records=[
            {"player": {"name": "Former Player"}, "game": {"id": 1}, "points": 30, "totReb": 5, "assists": 4},
            {"player": {"name": "Returning Player"}, "game": {"id": 2}, "points": 18, "totReb": 7, "assists": 6},
        ],
        historical_season=2025,
        current_roster_records=[{"firstname": "Returning", "lastname": "Player"}],
    )

    historical = result["historical_player_context"]
    assert historical["roster_verified"] is True
    assert [player["name"] for player in historical["players"]] == ["Returning Player"]
