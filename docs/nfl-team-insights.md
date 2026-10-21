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
- Red-zone rates and other small-sample statistics can change quickly early in a season.
- The current scoring blend is descriptive and is not a validated prediction model.

Use current official injury reports, roster status, and game information alongside these statistics.

## API response

The underlying endpoint is:

```text
GET /insights/nfl?home_team=New%20Orleans%20Saints&away_team=Atlanta%20Falcons&season=2025
```

Each team object includes `quarterback`, `offense`, and `defense`. The team `games` value identifies how many completed-game samples were used for the displayed team averages.
