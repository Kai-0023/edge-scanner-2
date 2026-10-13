"""FastAPI entry point and league router."""

from fastapi import FastAPI, HTTPException, Query

from logic.nba_logic import nba_player_summary
from logic.nfl_logic import nfl_player_summary

app = FastAPI(title="Edge Scanner 2", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a small response that confirms the API is running."""

    return {"status": "ok"}


@app.get("/analyze/{league}")
def analyze(
    league: str,
    player: str = Query(..., min_length=2, description="Player name to analyze"),
) -> dict[str, str]:
    """Route an analysis request to the selected sport-specific module."""

    normalized_league = league.lower()
    if normalized_league == "nba":
        return nba_player_summary(player)
    if normalized_league == "nfl":
        return nfl_player_summary(player)

    raise HTTPException(status_code=400, detail="League must be 'nba' or 'nfl'.")
