# NBA Team Insights Guide

## Purpose

The NBA Team Insights view gives a quick, transparent research snapshot for a selected matchup. It combines current-season team data with a separate prior-season player reference so early preseason game logs do not hide established players who are resting or have not played yet.

This screen is for research. It does not guarantee an outcome, calculate a betting probability, or provide personalized betting advice.

## How to use it

1. Open **Odds & games** and choose an NBA event.
2. Select **Analyze matchup**.
3. Review the home and away team cards, then compare the transparent scoring context with the available market line.

The page uses the event's scheduled season. API responses are cached for 15 minutes to limit use of the authorized data plan.

## What the team cards show

### Current-season team data

The following measurements come from the current API-NBA season data:

- Points, field-goal percentage, three-point percentage, rebounds, assists, and turnovers per game
- Free-throw percentage and attempts per game
- Three-point attempts per game
- Offensive and defensive rebounds per game
- Assist-to-turnover ratio
- Points allowed, steals, blocks, and opponent field-goal percentage when available

The **Completed-game form** section uses only finished games returned by the provider. It shows the record, last five results, point differential per game, recent points scored, and recent points allowed.

### Current notable players

The **Notable players** section summarizes the highest-scoring player game logs returned for the selected season. An availability message is shown only when the provider returns an injury report; a missing injury report is not proof that a player is healthy or active.

During preseason, this group may be made up of players receiving preseason minutes rather than the team's usual stars.

### Established players from the prior season

The **Established players** section uses player production from the prior NBA season. It is included to provide context when a starter or superstar has not logged a preseason game.

- It shows prior-season points, rebounds, and assists per game.
- It is displayed separately from current-season results.
- It never changes the current season-to-date scoring blend.
- It does not establish that a player is on the current roster, healthy, active, or expected to play. Confirm the current roster and availability before relying on it.

For example, early in the 2026 preseason, the app can still display a player's 2025–26 production even if that player has no 2026 preseason game log.

## Matchup context and market comparison

The **Transparent matchup context** uses a simple current-season scoring blend:

- A team's points per game is averaged with its opponent's points allowed per game.
- The result is compared with the available consensus spread or total from the authorized odds provider.
- A large difference is labeled a **research lead**, not a recommendation or guarantee.

Historical player data is intentionally excluded from this blend so the displayed calculation remains clear and testable.

## Data sources and limits

The dashboard requests authorized API-Sports NBA data from the server. API keys stay in the local `.env` file and are never sent to browser JavaScript.

The quality of the view depends on the provider's returned records. In particular:

- Preseason samples are small and can differ substantially from regular-season performance.
- A player can be missing from current-season logs because they rested, did not play, or data was not returned.
- Prior-season data can include players who have since changed teams.
- Injury reporting can be incomplete or delayed.
- A line can change after the app retrieves odds.

Use this information with current roster, injury, and official game-status checks.

## API response

The underlying endpoint is:

```text
GET /insights/nba?home_team=Washington%20Wizards&away_team=Milwaukee%20Bucks&season=2026
```

Each team's response includes `offense`, `defense`, `form`, `notable_players`, and `historical_player_context`. The `historical_player_context` object contains the prior season label and up to three production leaders from that season.
