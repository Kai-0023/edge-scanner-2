# NFL Team Insights Guide

## Purpose

The NFL Team Insights view provides a season-to-date research snapshot for a selected game. It uses completed NFL game data from the authorized API-Sports provider and keeps the displayed figures separate from the app's simple scoring-context blend.

This screen is for research only. It does not guarantee an outcome, estimate a betting probability, or provide personalized betting advice.

## How to use it

1. Open **Odds & games** and choose an NFL event.
2. Select **Analyze matchup**.
3. Review the home and away cards before reviewing the transparent scoring-context comparison.

The app uses the event's scheduled NFL season and caches authorized provider responses for 15 minutes.

## Team statistics

Each team card uses only completed games returned by the provider and shows averages across the available sample:

- Points, passing yards, rushing yards, sacks allowed, and total touchdowns per game
- Red-zone touchdown rate: touchdowns divided by red-zone opportunities
- Points allowed, passing yards allowed, rushing yards allowed, defensive sacks, and interceptions per game
- Opponent red-zone touchdown rate

Team touchdowns are counted from the provider's scoring events rather than inferred from total points. This avoids incorrectly treating field goals or two-point conversions as touchdowns.

## Quarterback data

The quarterback section identifies quarterbacks from the team's roster and loads their authorized season statistics. The card displays the quarterback with the most passing yards in the returned season data, along with passing/rushing production, touchdowns, interceptions, and sacks taken.

If the provider has no season record for a listed quarterback, the app does not invent a value. A different quarterback may be shown when they have the largest available passing sample.

## Key availability

The **Key availability** tab requests the provider's NFL injury/availability response and surfaces notices for these tracked positions:

- Quarterback, running back, wide receiver, and tight end
- Defensive line, linebackers, cornerbacks, and safeties

The API does not provide a trustworthy universal "top player" ranking, so the app does not claim a listed player is the team's top player. It preserves the provider's reported status and reason when available and uses the authorized roster response only to identify a player's position when the injury response omits it.

An empty report does **not** prove every player is healthy or active. A report is also not a final game-day active/inactive designation. Availability notices are visible to the optional AI summary as factual context, but they are not converted into a point adjustment or included in the scoring blend. Confirm final status with official team or league reporting close to kickoff.

## Quarterback return-to-action context

The app reads at most the six most recent completed team games. For each game, it requests the provider's passing-stat group and identifies that game's primary passer by passing yards. A return-to-action pattern is shown only when the latest primary passer had no passing-stat record in one or more immediately prior completed games, and another primary passer was recorded during that gap.

When a pattern appears, the app shows the number of consecutive prior games without that passer's passing record, the other primary passer or passers, team points per game during the gap, and team points in the return game. The optional AI summary gets the same factual fields.

This is deliberately **not** called an injury absence: the provider's injury endpoint is current-only and does not preserve historical injury reports. The pattern could have another explanation, and one return game is not enough evidence that an offense is back to its normal level.

## Provider field mapping

API-Sports NFL uses a few field formats that require interpretation:

- Passing yards are read from the team's `passing.total` field.
- Rushing yards are read from `rushings.total`.
- Sacks allowed are read from the first number in `passing.sacks_yards_lost`, such as `4-27` for four sacks and 27 lost yards.
- Red-zone makes and attempts are read from `red_zone.made_att`, such as `2-3`.
- Team touchdowns are counted from events whose type is `TD` for that team.

The app parses these forms server-side and leaves a metric unavailable when the provider does not return usable data. It does not substitute estimates.

## Limits

- The sample is limited to the most recent completed games made available by the provider.
- Provider corrections, missing box scores, and delayed injury or roster updates can affect the display.
- Availability notices are limited to the provider response and selected positions; they are not a full injury report or an official active/inactive list.
- Return-to-action context uses a short game-stat sample. Missing player-stat data breaks the sequence rather than being counted as a missed game.
- Red-zone rates and other small-sample statistics can change quickly early in a season.
- The current scoring blend is descriptive and is not a validated prediction model.

Use current official injury reports, roster status, and game information alongside these statistics.

## API response

The underlying endpoint is:

```text
GET /insights/nfl?home_team=New%20Orleans%20Saints&away_team=Atlanta%20Falcons&season=2025
```

Each team object includes `quarterback`, `offense`, `defense`, `opponent_strength`, `availability`, and `quarterback_return_context`. The team `games` value identifies how many completed-game samples were used for the displayed team averages.
