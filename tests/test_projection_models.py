from logic.projection_models import nfl_projection, nba_projection


def test_nba_away_injury_increases_home_probability() -> None:
    neutral = nba_projection(114, 114, 0, 100, 1, 0, 114, 114, 0, 100, 1, 0)
    injured_away = nba_projection(114, 114, 0, 100, 1, 0, 114, 114, 0, 100, 1, -4)
    assert injured_away["home_win_probability"] > neutral["home_win_probability"]


def test_nfl_qb_adjustment_changes_margin() -> None:
    baseline = nfl_projection(22, 22, 0, 7, 0, 0, 0, 22, 22, 0, 7, 0, 0, 0)
    upgraded_qb = nfl_projection(22, 22, 0, 7, 3, 0, 0, 22, 22, 0, 7, 0, 0, 0)
    assert upgraded_qb["projected_home_margin"] > baseline["projected_home_margin"]
