"""Licensed odds-provider integration point.

Do not scrape sportsbook websites. This module only permits API-based data access
after a user supplies credentials from a provider they are authorized to use.
"""


def live_odds_status(sport: str) -> dict[str, str]:
    """Return a safe response until a licensed provider is configured."""

    return {
        "sport": sport.lower(),
        "status": "Live odds are disabled.",
        "reason": "Add credentials for a licensed odds-data API before enabling this route.",
    }
