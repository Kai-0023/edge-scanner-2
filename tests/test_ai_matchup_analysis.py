"""Tests for the Gemini request/response boundary without real network calls."""

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
