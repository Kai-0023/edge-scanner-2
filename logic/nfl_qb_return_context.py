"""Evidence-limited NFL quarterback return-to-action context.

The injury endpoint describes only the current report, not historical absences.
This module therefore detects only a factual game-stat pattern: the latest
primary passer did not have a passing-stat record in consecutive immediately
previous completed games, then appears in the latest completed game.
"""

from __future__ import annotations

from typing import Any


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def quarterback_return_context(game_samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe a recent QB return-to-action pattern without inferring an injury.

    ``game_samples`` must be chronological and include a quarterback only when
    the provider returned a passing-stat record for that game. A blank or
    unavailable player-stat response breaks the sequence rather than becoming a
    made-up absence.
    """

    if len(game_samples) < 2:
        return {
            "available": False,
            "detected": False,
            "reason": "Not enough completed games are available to check recent quarterback continuity.",
        }

    latest = game_samples[-1]
    latest_quarterback = latest.get("quarterback")
    if not isinstance(latest_quarterback, dict) or not latest_quarterback.get("id"):
        return {
            "available": False,
            "detected": False,
            "reason": "The latest completed game's primary passer was unavailable from the provider.",
        }

    returner_id = str(latest_quarterback["id"])
    gap: list[dict[str, Any]] = []
    for sample in reversed(game_samples[:-1]):
        if not sample.get("passing_stats_available"):
            break
        quarterback = sample.get("quarterback")
        if not isinstance(quarterback, dict) or not quarterback.get("id"):
            break
        if str(quarterback["id"]) == returner_id:
            break
        gap.append(sample)

    if not gap:
        return {
            "available": True,
            "detected": False,
            "reason": (
                "No recent return-to-action pattern was found: the latest primary passer also had a passing-stat "
                "record in the immediately prior completed game, or the provider did not return a complete sequence."
            ),
            "method": (
                "Uses completed-game passing statistics only. It does not identify the reason for an absence or confirm "
                "a game-day role."
            ),
        }

    replacement_names: list[str] = []
    for sample in reversed(gap):
        quarterback = sample.get("quarterback")
        name = str(quarterback.get("name") or "Quarterback unavailable") if isinstance(quarterback, dict) else "Quarterback unavailable"
        if name not in replacement_names:
            replacement_names.append(name)
    gap_points = [float(sample["points_for"]) for sample in gap if isinstance(sample.get("points_for"), (int, float))]
    latest_points = latest.get("points_for")
    latest_points_number = float(latest_points) if isinstance(latest_points, (int, float)) else None
    average_gap_points = _mean(gap_points)

    return {
        "available": True,
        "detected": True,
        "quarterback": {"name": str(latest_quarterback.get("name") or "Quarterback unavailable")},
        "consecutive_prior_games_without_passing_record": len(gap),
        "replacement_quarterbacks": replacement_names,
        "return_game_date": latest.get("date"),
        "offense": {
            "points_per_game_during_gap": average_gap_points,
            "points_in_return_game": latest_points_number,
            "return_game_difference_from_gap": (
                round(latest_points_number - average_gap_points, 1)
                if latest_points_number is not None and average_gap_points is not None
                else None
            ),
        },
        "method": (
            "The latest primary passer had no passing-stat record in each immediately prior listed game. "
            "This is a return-to-action pattern, not proof that the player was injured or officially ruled out. "
            "One return game is not enough to conclude the offense is back to its normal level."
        ),
    }
