"""Optional Gemini-written research summaries for already-authorized game data.

Gemini receives only the API-Sports matchup response selected by the user. It
does not fetch sports data, replace provider values, or send a key to the
browser.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from backend.dependencies import settings
from logic.matchup_presentation import public_matchup_payload


GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MAX_ANALYSIS_CHARACTERS = 2_400


class AiAnalysisUnavailable(RuntimeError):
    """Raised when a Gemini summary cannot be generated safely."""


def _matchup_context(matchup: dict[str, Any]) -> dict[str, Any]:
    """Keep the model context factual, compact, and limited to this matchup."""

    matchup = public_matchup_payload(matchup)

    def team_context(team: object) -> dict[str, Any]:
        if not isinstance(team, dict):
            return {}
        return {
            "team": team.get("team"),
            "offense": team.get("offense"),
            "defense": team.get("defense"),
            "form": team.get("form"),
            "quarterback": team.get("quarterback"),
            "availability": team.get("availability"),
            "quarterback_return_context": team.get("quarterback_return_context"),
            "opponent_strength": team.get("opponent_strength"),
            "notable_players": team.get("notable_players"),
            "notable_players_source": team.get("notable_players_source"),
            "current_roster": team.get("current_roster"),
        }

    return {
        "league": matchup.get("league"),
        "season": matchup.get("season"),
        "source": matchup.get("source"),
        "home": team_context(matchup.get("home")),
        "away": team_context(matchup.get("away")),
        "matchup_summary": matchup.get("matchup_summary"),
        "provider_disclaimer": matchup.get("disclaimer"),
    }


def build_analysis_input(league: str, matchup: dict[str, Any]) -> str:
    """Create a grounded task that does not ask Gemini to invent live facts."""

    facts = json.dumps(_matchup_context(matchup), separators=(",", ":"), ensure_ascii=True)
    return (
        f"Write a short {league.upper()} matchup research summary using only the factual API response below. "
        "State 2-4 concrete matchup factors and call out meaningful missing or stale data. "
        "For NFL, if quarterback_return_context reports a return-to-action pattern, state the exact prior-game gap and "
        "team-scoring sample. Do not call that pattern an injury absence, an official inactive status, or proof the offense "
        "is fully back to speed. "
        "Do not invent rosters, injuries, player availability, statistics, betting lines, or news. "
        "Do not say what someone should bet, guarantee an outcome, or personalize the response. "
        "Use plain language, with short paragraphs or bullets.\n\n"
        f"FACTUAL API RESPONSE:\n{facts}"
    )


def _extract_output_text(payload: dict[str, Any]) -> str:
    """Read the documented convenience field, with a small safe fallback."""

    direct_text = payload.get("output_text")
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    collected: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") == "text" and isinstance(value.get("text"), str):
                collected.append(value["text"])
                return
            for key in ("output", "steps", "content", "parts"):
                if key in value:
                    visit(value[key])
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return "\n".join(item.strip() for item in collected if item.strip()).strip()


async def generate_ai_matchup_analysis(league: str, matchup: dict[str, Any]) -> dict[str, Any]:
    """Generate an optional, clearly labeled Gemini interpretation of API facts."""

    if not settings.gemini_api_key:
        raise AiAnalysisUnavailable(
            "AI summary is not configured. Add GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_AI_STUDIO_API_KEY to .env, then restart the local app."
        )

    request_body = {
        "model": settings.gemini_model,
        "system_instruction": (
            "You are a careful sports research assistant. Treat the supplied API data as the only source of facts. "
            "Clearly separate data limits from analysis and never provide betting instructions."
        ),
        "input": build_analysis_input(league, matchup),
        "generation_config": {"thinking_level": "low", "max_output_tokens": 450},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                GEMINI_INTERACTIONS_URL,
                headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
                json=request_body,
            )
    except httpx.HTTPError as exc:
        raise AiAnalysisUnavailable("The AI summary service could not be reached. Try again shortly.") from exc

    if response.is_error:
        # Provider errors can include sensitive implementation details. The
        # app needs only a useful status, not Google’s full response body.
        if response.status_code in {401, 403}:
            message = "Google AI Studio rejected the configured key or model. Confirm the key and enabled model, then restart the app."
        elif response.status_code == 429:
            message = "Google AI Studio rate limit reached. Try the summary again later."
        else:
            message = "Google AI Studio could not create a summary for this matchup. Try again shortly."
        raise AiAnalysisUnavailable(message)

    try:
        output = _extract_output_text(response.json())
    except ValueError as exc:
        raise AiAnalysisUnavailable("Google AI Studio returned an unreadable summary response.") from exc
    if not output:
        raise AiAnalysisUnavailable("Google AI Studio returned no written summary for this matchup.")

    return {
        "available": True,
        "source": f"Google AI Studio Gemini ({settings.gemini_model})",
        "analysis": output[:MAX_ANALYSIS_CHARACTERS],
        "disclaimer": (
            "AI-generated research summary based only on the displayed API-Sports response. "
            "It is not a live-data replacement, prediction, instruction, or guarantee."
        ),
    }
