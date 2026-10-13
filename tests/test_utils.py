"""Tests for shared calculation helpers."""

import pytest

from logic.utils import expected_value


def test_expected_value_for_even_odds() -> None:
    assert expected_value(0.5, 2.0) == 0


def test_expected_value_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError):
        expected_value(1.2, 2.0)
