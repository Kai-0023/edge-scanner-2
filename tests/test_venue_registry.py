"""Tests for home-team venue resolution."""

import pytest

from logic.venue_registry import VenueNotFound, home_venue, list_venues


def test_registry_includes_every_current_nba_and_nfl_team() -> None:
    assert len(list_venues("nba")) == 30
    assert len(list_venues("nfl")) == 32


def test_home_team_determines_the_shared_stadium() -> None:
    chargers = home_venue("nfl", "Los Angeles Chargers")
    rams = home_venue("nfl", "LA Rams")

    assert chargers["venue"] == "SoFi Stadium"
    assert rams["venue"] == "SoFi Stadium"
    assert chargers["city"] == "Inglewood, CA"


def test_unknown_team_is_not_assigned_an_away_or_device_location() -> None:
    with pytest.raises(VenueNotFound):
        home_venue("nba", "Not A Team")
