"""Tests for completed-game opponent-strength context."""

from logic.nfl_opponent_strength import nfl_opponent_strength_context


def _game(home: str, away: str, home_points: int, away_points: int) -> dict:
    return {
        "teams": {"home": {"id": home}, "away": {"id": away}},
        "scores": {"home": {"total": home_points}, "away": {"total": away_points}},
    }


def test_opponent_strength_compares_selected_team_against_stronger_and_weaker_groups() -> None:
    context = nfl_opponent_strength_context(
        [
            _game("A", "B", 20, 10),
            _game("B", "C", 10, 7),
            _game("B", "D", 10, 7),
            _game("A", "D", 24, 20),
            _game("C", "D", 28, 7),
            _game("A", "C", 21, 14),
        ],
        "A",
    )

    assert context["available"] is True
    assert context["offense"]["vs_stronger_defenses"]["games"] >= 1
    assert context["offense"]["vs_weaker_defenses"]["games"] >= 1
    assert context["defense"]["vs_premier_offenses"]["games"] >= 1
    assert context["method"].startswith("Season-to-date completed games")


def test_opponent_strength_waits_for_enough_league_data() -> None:
    context = nfl_opponent_strength_context([_game("A", "B", 20, 10)], "A")

    assert context["available"] is False
