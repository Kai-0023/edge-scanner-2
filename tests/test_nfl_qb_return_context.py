"""Tests for evidence-limited quarterback return context."""

from logic.nfl_qb_return_context import quarterback_return_context


def _sample(
    date: str,
    points_for: int,
    quarterback_id: str | None,
    quarterback_name: str | None,
    *,
    available: bool = True,
) -> dict:
    return {
        "date": date,
        "points_for": points_for,
        "passing_stats_available": available,
        "quarterback": (
            {"id": quarterback_id, "name": quarterback_name}
            if quarterback_id is not None
            else None
        ),
    }


def test_quarterback_return_context_detects_consecutive_prior_passing_gap() -> None:
    context = quarterback_return_context(
        [
            _sample("2026-09-14", 21, "caleb", "Caleb Example"),
            _sample("2026-09-21", 14, "backup", "Backup Example"),
            _sample("2026-09-28", 10, "backup", "Backup Example"),
            _sample("2026-10-05", 27, "caleb", "Caleb Example"),
        ]
    )

    assert context["available"] is True
    assert context["detected"] is True
    assert context["quarterback"]["name"] == "Caleb Example"
    assert context["consecutive_prior_games_without_passing_record"] == 2
    assert context["replacement_quarterbacks"] == ["Backup Example"]
    assert context["offense"]["points_per_game_during_gap"] == 12
    assert context["offense"]["points_in_return_game"] == 27
    assert context["offense"]["return_game_difference_from_gap"] == 15
    assert "not proof" in context["method"]


def test_quarterback_return_context_does_not_turn_missing_provider_game_data_into_an_absence() -> None:
    context = quarterback_return_context(
        [
            _sample("2026-09-21", 14, None, None, available=False),
            _sample("2026-09-28", 27, "caleb", "Caleb Example"),
        ]
    )

    assert context["available"] is True
    assert context["detected"] is False
    assert "No recent return-to-action pattern" in context["reason"]
