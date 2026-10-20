"""Home-venue reference data for current NBA and NFL teams.

Venue context is determined only from the designated home team.  The registry is
kept in source control so the application does not need to transmit a user's
location or depend on a third-party lookup for every team selection.
"""

from __future__ import annotations

import re
from typing import Any


class VenueNotFound(ValueError):
    """Raised when a team does not have a home venue in this registry."""


VENUES: dict[str, list[dict[str, Any]]] = {
    "nfl": [
        {"team": "Arizona Cardinals", "venue": "State Farm Stadium", "city": "Glendale, AZ", "latitude": 33.5276, "longitude": -112.2626},
        {"team": "Atlanta Falcons", "venue": "Mercedes-Benz Stadium", "city": "Atlanta, GA", "latitude": 33.7554, "longitude": -84.4008},
        {"team": "Baltimore Ravens", "venue": "M&T Bank Stadium", "city": "Baltimore, MD", "latitude": 39.2780, "longitude": -76.6227},
        {"team": "Buffalo Bills", "venue": "Highmark Stadium", "city": "Orchard Park, NY", "latitude": 42.7738, "longitude": -78.7870},
        {"team": "Carolina Panthers", "venue": "Bank of America Stadium", "city": "Charlotte, NC", "latitude": 35.2258, "longitude": -80.8528},
        {"team": "Chicago Bears", "venue": "Soldier Field", "city": "Chicago, IL", "latitude": 41.8623, "longitude": -87.6167},
        {"team": "Cincinnati Bengals", "venue": "Paycor Stadium", "city": "Cincinnati, OH", "latitude": 39.0954, "longitude": -84.5160},
        {"team": "Cleveland Browns", "venue": "Huntington Bank Field", "city": "Cleveland, OH", "latitude": 41.5061, "longitude": -81.6995},
        {"team": "Dallas Cowboys", "venue": "AT&T Stadium", "city": "Arlington, TX", "latitude": 32.7473, "longitude": -97.0945},
        {"team": "Denver Broncos", "venue": "Empower Field at Mile High", "city": "Denver, CO", "latitude": 39.7439, "longitude": -105.0201},
        {"team": "Detroit Lions", "venue": "Ford Field", "city": "Detroit, MI", "latitude": 42.3400, "longitude": -83.0456},
        {"team": "Green Bay Packers", "venue": "Lambeau Field", "city": "Green Bay, WI", "latitude": 44.5013, "longitude": -88.0622},
        {"team": "Houston Texans", "venue": "NRG Stadium", "city": "Houston, TX", "latitude": 29.6847, "longitude": -95.4107},
        {"team": "Indianapolis Colts", "venue": "Lucas Oil Stadium", "city": "Indianapolis, IN", "latitude": 39.7601, "longitude": -86.1639},
        {"team": "Jacksonville Jaguars", "venue": "EverBank Stadium", "city": "Jacksonville, FL", "latitude": 30.3239, "longitude": -81.6373},
        {"team": "Kansas City Chiefs", "venue": "GEHA Field at Arrowhead Stadium", "city": "Kansas City, MO", "latitude": 39.0489, "longitude": -94.4839},
        {"team": "Las Vegas Raiders", "venue": "Allegiant Stadium", "city": "Las Vegas, NV", "latitude": 36.0909, "longitude": -115.1833},
        {"team": "Los Angeles Chargers", "venue": "SoFi Stadium", "city": "Inglewood, CA", "latitude": 33.9535, "longitude": -118.3392, "aliases": ["LA Chargers"]},
        {"team": "Los Angeles Rams", "venue": "SoFi Stadium", "city": "Inglewood, CA", "latitude": 33.9535, "longitude": -118.3392, "aliases": ["LA Rams"]},
        {"team": "Miami Dolphins", "venue": "Hard Rock Stadium", "city": "Miami Gardens, FL", "latitude": 25.9580, "longitude": -80.2389},
        {"team": "Minnesota Vikings", "venue": "U.S. Bank Stadium", "city": "Minneapolis, MN", "latitude": 44.9738, "longitude": -93.2576},
        {"team": "New England Patriots", "venue": "Gillette Stadium", "city": "Foxborough, MA", "latitude": 42.0909, "longitude": -71.2643},
        {"team": "New Orleans Saints", "venue": "Caesars Superdome", "city": "New Orleans, LA", "latitude": 29.9511, "longitude": -90.0812},
        {"team": "New York Giants", "venue": "MetLife Stadium", "city": "East Rutherford, NJ", "latitude": 40.8135, "longitude": -74.0745},
        {"team": "New York Jets", "venue": "MetLife Stadium", "city": "East Rutherford, NJ", "latitude": 40.8135, "longitude": -74.0745},
        {"team": "Philadelphia Eagles", "venue": "Lincoln Financial Field", "city": "Philadelphia, PA", "latitude": 39.9008, "longitude": -75.1675},
        {"team": "Pittsburgh Steelers", "venue": "Acrisure Stadium", "city": "Pittsburgh, PA", "latitude": 40.4468, "longitude": -80.0158},
        {"team": "San Francisco 49ers", "venue": "Levi's Stadium", "city": "Santa Clara, CA", "latitude": 37.4033, "longitude": -121.9700},
        {"team": "Seattle Seahawks", "venue": "Lumen Field", "city": "Seattle, WA", "latitude": 47.5952, "longitude": -122.3316},
        {"team": "Tampa Bay Buccaneers", "venue": "Raymond James Stadium", "city": "Tampa, FL", "latitude": 27.9759, "longitude": -82.5033, "aliases": ["Tampa Bay Bucs"]},
        {"team": "Tennessee Titans", "venue": "Nissan Stadium", "city": "Nashville, TN", "latitude": 36.1665, "longitude": -86.7713},
        {"team": "Washington Commanders", "venue": "Northwest Stadium", "city": "Landover, MD", "latitude": 38.9078, "longitude": -76.8644},
    ],
    "nba": [
        {"team": "Atlanta Hawks", "venue": "State Farm Arena", "city": "Atlanta, GA", "latitude": 33.7573, "longitude": -84.3963},
        {"team": "Boston Celtics", "venue": "TD Garden", "city": "Boston, MA", "latitude": 42.3662, "longitude": -71.0621},
        {"team": "Brooklyn Nets", "venue": "Barclays Center", "city": "Brooklyn, NY", "latitude": 40.6826, "longitude": -73.9754},
        {"team": "Charlotte Hornets", "venue": "Spectrum Center", "city": "Charlotte, NC", "latitude": 35.2251, "longitude": -80.8392},
        {"team": "Chicago Bulls", "venue": "United Center", "city": "Chicago, IL", "latitude": 41.8807, "longitude": -87.6742},
        {"team": "Cleveland Cavaliers", "venue": "Rocket Arena", "city": "Cleveland, OH", "latitude": 41.4965, "longitude": -81.6882},
        {"team": "Dallas Mavericks", "venue": "American Airlines Center", "city": "Dallas, TX", "latitude": 32.7905, "longitude": -96.8103},
        {"team": "Denver Nuggets", "venue": "Ball Arena", "city": "Denver, CO", "latitude": 39.7487, "longitude": -105.0077},
        {"team": "Detroit Pistons", "venue": "Little Caesars Arena", "city": "Detroit, MI", "latitude": 42.3410, "longitude": -83.0550},
        {"team": "Golden State Warriors", "venue": "Chase Center", "city": "San Francisco, CA", "latitude": 37.7680, "longitude": -122.3877},
        {"team": "Houston Rockets", "venue": "Toyota Center", "city": "Houston, TX", "latitude": 29.7508, "longitude": -95.3621},
        {"team": "Indiana Pacers", "venue": "Gainbridge Fieldhouse", "city": "Indianapolis, IN", "latitude": 39.7639, "longitude": -86.1555},
        {"team": "Los Angeles Clippers", "venue": "Intuit Dome", "city": "Inglewood, CA", "latitude": 33.9458, "longitude": -118.3382, "aliases": ["LA Clippers"]},
        {"team": "Los Angeles Lakers", "venue": "Crypto.com Arena", "city": "Los Angeles, CA", "latitude": 34.0430, "longitude": -118.2673, "aliases": ["LA Lakers"]},
        {"team": "Memphis Grizzlies", "venue": "FedExForum", "city": "Memphis, TN", "latitude": 35.1382, "longitude": -90.0505},
        {"team": "Miami Heat", "venue": "Kaseya Center", "city": "Miami, FL", "latitude": 25.7814, "longitude": -80.1880},
        {"team": "Milwaukee Bucks", "venue": "Fiserv Forum", "city": "Milwaukee, WI", "latitude": 43.0451, "longitude": -87.9172},
        {"team": "Minnesota Timberwolves", "venue": "Target Center", "city": "Minneapolis, MN", "latitude": 44.9795, "longitude": -93.2760},
        {"team": "New Orleans Pelicans", "venue": "Smoothie King Center", "city": "New Orleans, LA", "latitude": 29.9490, "longitude": -90.0821},
        {"team": "New York Knicks", "venue": "Madison Square Garden", "city": "New York, NY", "latitude": 40.7505, "longitude": -73.9934},
        {"team": "Oklahoma City Thunder", "venue": "Paycom Center", "city": "Oklahoma City, OK", "latitude": 35.4634, "longitude": -97.5151},
        {"team": "Orlando Magic", "venue": "Kia Center", "city": "Orlando, FL", "latitude": 28.5392, "longitude": -81.3839},
        {"team": "Philadelphia 76ers", "venue": "Xfinity Mobile Arena", "city": "Philadelphia, PA", "latitude": 39.9012, "longitude": -75.1720},
        {"team": "Phoenix Suns", "venue": "Mortgage Matchup Center", "city": "Phoenix, AZ", "latitude": 33.4457, "longitude": -112.0712},
        {"team": "Portland Trail Blazers", "venue": "Moda Center", "city": "Portland, OR", "latitude": 45.5316, "longitude": -122.6668},
        {"team": "Sacramento Kings", "venue": "Golden 1 Center", "city": "Sacramento, CA", "latitude": 38.5802, "longitude": -121.4997},
        {"team": "San Antonio Spurs", "venue": "Frost Bank Center", "city": "San Antonio, TX", "latitude": 29.4270, "longitude": -98.4375},
        {"team": "Toronto Raptors", "venue": "Scotiabank Arena", "city": "Toronto, ON", "latitude": 43.6435, "longitude": -79.3791},
        {"team": "Utah Jazz", "venue": "Delta Center", "city": "Salt Lake City, UT", "latitude": 40.7683, "longitude": -111.9011},
        {"team": "Washington Wizards", "venue": "Capital One Arena", "city": "Washington, DC", "latitude": 38.8981, "longitude": -77.0209},
    ],
}


def _normalize(team: str) -> str:
    return re.sub(r"[^a-z0-9]", "", team.lower())


def list_venues(league: str) -> list[dict[str, Any]]:
    """Return a copy of the league's team-to-home-venue reference data."""

    normalized_league = league.lower()
    if normalized_league not in VENUES:
        raise ValueError("League must be 'nba' or 'nfl'.")
    return [{key: value for key, value in venue.items() if key != "aliases"} for venue in VENUES[normalized_league]]


def home_venue(league: str, home_team: str) -> dict[str, Any]:
    """Resolve an event's venue from its home team, never its away team."""

    target = _normalize(home_team)
    for venue in list_venues(league):
        aliases = next(
            raw.get("aliases", []) for raw in VENUES[league.lower()] if raw["team"] == venue["team"]
        )
        if target in {_normalize(venue["team"]), *(_normalize(alias) for alias in aliases)}:
            return venue
    raise VenueNotFound(f"No {league.upper()} home venue is configured for '{home_team}'.")
