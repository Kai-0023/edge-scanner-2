"""Shared calculation helpers."""


def expected_value(win_probability: float, decimal_odds: float) -> float:
    """Return expected profit for a one-unit wager.

    ``win_probability`` must be between 0 and 1 and decimal odds must exceed 1.
    """

    if not 0 <= win_probability <= 1:
        raise ValueError("win_probability must be between 0 and 1")
    if decimal_odds <= 1:
        raise ValueError("decimal_odds must be greater than 1")

    return (win_probability * (decimal_odds - 1)) - (1 - win_probability)
