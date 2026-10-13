"""NFL-specific starter calculations."""


def injury_adjusted_projection(projection: float, availability: float) -> float:
    """Apply an availability weight from 0 to 1 to a projection."""

    if not 0 <= availability <= 1:
        raise ValueError("availability must be between 0 and 1")
    return projection * availability


def nfl_player_summary(player: str) -> dict[str, str]:
    """Return a placeholder until the NFL data pipeline is connected."""

    return {
        "league": "nfl",
        "player": player,
        "status": "Starter route is ready; connect nfl_scraper.py to add live data.",
    }
