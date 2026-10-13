"""NBA-specific starter calculations."""


def pace_adjusted_projection(player_average: float, team_pace: float, league_pace: float) -> float:
    """Adjust a player average for expected game pace."""

    if league_pace <= 0:
        raise ValueError("league_pace must be greater than 0")
    return player_average * (team_pace / league_pace)


def nba_player_summary(player: str) -> dict[str, str]:
    """Return a placeholder until the NBA data pipeline is connected."""

    return {
        "league": "nba",
        "player": player,
        "status": "Starter route is ready; connect nba_scraper.py to add live data.",
    }
