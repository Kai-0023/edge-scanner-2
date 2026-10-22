"""Tests for values intentionally hidden from the browser response."""

from logic.matchup_presentation import public_matchup_payload


def test_public_matchup_hides_provider_ids_and_verification_state() -> None:
    source = {
        "home": {
            "current_roster": {
                "team_id": "51",
                "verified": True,
                "count": 2,
                "players": [
                    {"id": "9", "name": "Player One", "position": "G"},
                    {"id": "10", "name": "Player Two", "position": "F"},
                ],
            },
            "historical_player_context": {"roster_verified": True, "players": []},
        },
        "away": {"current_roster": {"verified": False, "players": [{"id": "4", "name": "Wrong Team", "position": "C"}]}},
    }

    result = public_matchup_payload(source)

    assert result["home"]["current_roster"] == {
        "players": [{"name": "Player One", "position": "G"}, {"name": "Player Two", "position": "F"}]
    }
    assert result["away"]["current_roster"] == {"players": []}
    assert "roster_verified" not in result["home"]["historical_player_context"]
    assert source["home"]["current_roster"]["players"][0]["id"] == "9"
