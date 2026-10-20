"""Tests for conservative, user-reviewable OCR suggestions."""

from logic.slip_ocr import parse_slip_text


def test_parse_slip_text_suggests_odds_and_stake_only() -> None:
    suggestions = parse_slip_text("Lakers moneyline +125 Stake: $20.50")

    assert suggestions == {"american_odds": 125, "stake": 20.5, "selection": None}


def test_parse_slip_text_leaves_unknown_fields_empty() -> None:
    suggestions = parse_slip_text("Receipt unavailable")

    assert suggestions["american_odds"] is None
    assert suggestions["stake"] is None
