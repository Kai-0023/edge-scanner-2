"""Client-safe presentation fields for internal matchup research data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def public_matchup_payload(matchup: dict[str, Any]) -> dict[str, Any]:
    """Remove internal roster identity and verification details from the client.

    API-Sports player and team IDs are still used on the server to prevent
    cross-team player records. The browser needs only a safe roster display.
    """

    payload = deepcopy(matchup)
    for side in ("home", "away"):
        team = payload.get(side)
        if not isinstance(team, dict):
            continue
        roster = team.get("current_roster")
        if isinstance(roster, dict):
            safe_players = []
            if roster.get("verified"):
                for player in roster.get("players", []):
                    if not isinstance(player, dict) or not player.get("name"):
                        continue
                    safe_players.append({"name": str(player["name"]), "position": str(player.get("position") or "—")})
            team["current_roster"] = {"players": safe_players}

        historical = team.get("historical_player_context")
        if isinstance(historical, dict):
            historical.pop("roster_verified", None)
    return payload
