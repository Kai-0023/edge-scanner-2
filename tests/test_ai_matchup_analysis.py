"""Tests for the Gemini request/response boundary without real network calls."""

import asyncio

import logic.ai_matchup_analysis as ai_matchup_analysis
from logic.ai_matchup_analysis import _extract_output_text, build_analysis_input


def test_build_analysis_input_keeps_prompt_grounded_in_selected_facts() -> None:
    prompt = build_analysis_input(
        "nba",
        {
            "league": "nba",
            "season": "2026",
            "source": "API-Sports NBA",
            "home": {"team": "Home", "offense": {"points_per_game": 111}, "quarterback_return_context": {"detected": True}},
            "away": {"team": "Away", "defense": {"points_allowed_per_game": 108}},
        },
    )

    assert "using only the factual API response" in prompt
    assert "Do not say what someone should bet" in prompt
    assert "return-to-action pattern" in prompt
    assert '"team":"Home"' in prompt
    assert '"quarterback_return_context":{"detected":true}' in prompt
    assert '"team":"Away"' in prompt


def test_extract_output_text_reads_documented_convenience_field() -> None:
    assert _extract_output_text({"output_text": "  Grounded analysis.  "}) == "Grounded analysis."


def test_extract_output_text_uses_text_content_fallback() -> None:
    response = {"output": [{"type": "text", "text": "First factor."}, {"type": "text", "text": "Second factor."}]}
    assert _extract_output_text(response) == "First factor.\nSecond factor."


def test_generate_analysis_sends_selected_facts_to_gemini_and_returns_its_text(monkeypatch) -> None:
    """The server submits the selected API-Sports facts, not a fixed summary."""

    captured: dict[str, object] = {}

    class FakeResponse:
        is_error = False
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"output_text": "Gemini found that the home team scores more while the away defense allows fewer points."}

    class FakeClient:
        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResponse()

    def fake_async_client(*, timeout: int) -> FakeClient:
        captured["timeout"] = timeout
        return FakeClient()

    monkeypatch.setattr(ai_matchup_analysis.httpx, "AsyncClient", fake_async_client)
    monkeypatch.setattr(ai_matchup_analysis.settings, "gemini_api_key", "test-server-key")
    monkeypatch.setattr(ai_matchup_analysis.settings, "gemini_model", "test-gemini-model")

    result = asyncio.run(
        ai_matchup_analysis.generate_ai_matchup_analysis(
            "nba",
            {
                "league": "nba",
                "season": 2026,
                "source": "API-Sports NBA",
                "home": {"team": "Selected Home", "offense": {"points_per_game": 112.4}},
                "away": {"team": "Selected Away", "defense": {"points_allowed_per_game": 108.1}},
                "matchup_summary": {"estimated_home_points": 112.4, "estimated_away_points": 108.1},
                "disclaimer": "Provider facts only.",
            },
        )
    )

    body = captured["body"]
    assert captured["url"] == ai_matchup_analysis.GEMINI_INTERACTIONS_URL
    assert captured["timeout"] == 30
    assert captured["headers"] == {"x-goog-api-key": "test-server-key", "Content-Type": "application/json"}
    assert isinstance(body, dict)
    assert body["model"] == "test-gemini-model"
    assert '"team":"Selected Home"' in str(body["input"])
    assert '"team":"Selected Away"' in str(body["input"])
    assert result["available"] is True
    assert result["analysis"].startswith("Gemini found")
    assert result["source"] == "Google AI Studio Gemini (test-gemini-model)"
