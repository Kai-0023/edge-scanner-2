# Edge Scanner 2

Edge Scanner 2 is a starter API for analyzing NBA and NFL betting inputs. The project separates the API layer, sport-specific logic, data collection, and local data storage so each part can grow independently.

## Project layout

- `backend/` - FastAPI endpoints and environment settings
- `logic/` - shared and sport-specific calculations
- `scrapers/` - starter modules for NBA, NFL, and odds data
- `data/` - local raw and processed data; its contents are ignored by Git
- `tests/` - calculation tests

## Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to view the API documentation.

## Environment variables

Copy `.env.example` to `.env` and add your own key when you are ready to connect an odds provider. Do not commit `.env`.

## Current starter endpoints

- `GET /health` verifies that the API is running.
- `GET /analyze/nba?player=LeBron%20James` or `GET /analyze/nfl?player=...` routes a request to the selected sport.
- `GET /live/nba` and `GET /live/nfl` compare available U.S. sportsbook lines through The Odds API after you configure your own key. Responses are cached for 60 seconds to preserve API credits.
- The dashboard uses each authorized odds event's `commence_time`, home team, and away team to populate an upcoming-game selector. Choosing a game automatically applies its home venue and official start time.
- `POST /projection/nba` and `POST /projection/nfl` return a transparent matchup explanation that identifies the supplied factors driving the baseline result. It is not a trained ML prediction.
- `GET /venues/nba` and `GET /venues/nfl` list all configured home arenas and stadiums.
- `GET /venue-context/{league}?home_team=...` resolves the location from the home team only. For NFL, add `game_time_local` to include Open-Meteo venue weather.
- `GET /insights/nfl?home_team=...&away_team=...&season=2026` returns authorized season-to-date NFL QB, offense, defense, and red-zone context.
- `GET /insights/nba?home_team=...&away_team=...&season=2026` returns authorized NBA team averages, completed-game form, current notable-player statistics, and a separately labeled prior-season player reference.
- `POST /tracking/ocr` reads a slip image in memory when local OCR is installed. `POST /tracking/entries` stores only fields the user reviews and confirms.

## Live-data note

The live routes are intentionally disabled until you add a licensed odds-data provider and its API key in `.env`. Do not scrape sportsbook websites. Only use an API if your account and the provider's terms authorize the intended use, and follow its rate limits.

To enable the legal comparison route, create an authorized The Odds API account and add its key locally:

```text
THE_ODDS_API_KEY=your_key_here
```

Then try one of these URLs after starting FastAPI:

```text
http://127.0.0.1:8000/live/nba
http://127.0.0.1:8000/live/nfl?bookmakers=draftkings,fanduel
```

The second URL requests only the named bookmakers when they are included in your provider's coverage. Check the provider terms before publicly redistributing raw odds data.

## Local data pipeline

Edge Scanner now creates a local SQLite database at `data/processed/edge_scanner.db`. It is ignored by Git and stores timestamped odds, injury, and projection snapshots. Saving snapshots makes it possible to test the model using only information that was available before a game.

- Every non-cached `/live/nba` or `/live/nfl` request saves the returned event data locally.
- `GET /data/status` shows counts of saved snapshots.
- `POST /sync/injuries/nba?season=2026` pulls and stores authorized NBA injury records after the NBA API-Sports key is configured.
- `POST /sync/injuries/nfl?season=2026&week=1` does the same for NFL, using the season and optional week.

API-Sports subscriptions for NBA and NFL can have separate keys. Add the keys locally; do not send them to chat or commit them to GitHub:

```text
API_SPORTS_NFL_KEY=your_nfl_key
API_SPORTS_NBA_KEY=your_nba_key
```

If one API-Sports key is authorized for both subscriptions, use `API_SPORTS_KEY` instead. The dashboard sends these keys only from the FastAPI server to the corresponding API-Sports endpoint; browser JavaScript never receives them.

### Team insights

From an NFL event, choose **Analyze matchup** to review season-to-date quarterback passing/rushing, team scoring, pass/rush production, sacks, interceptions, and red-zone touchdown rates. From an NBA event, the same action shows current team averages, completed-game form, current player logs, and availability only when the provider returns it. It also shows a clearly separate prior-season player reference so established players who are resting or absent from preseason game logs are not hidden. Prior-season data does not affect the current-season scoring blend and must not be treated as a current roster or availability confirmation. Both feeds are cached for 15 minutes to reduce API usage.

Read the [NBA Team Insights Guide](docs/nba-team-insights.md) for definitions, data limits, and the API response structure.

The tab calculates a transparent scoring-context blend from each team's points per game and its opponent's points allowed per game. If a consensus spread or total is available from The Odds API, it highlights only the largest model-to-market difference as a research lead. It is not a probability, a validated model, or a guaranteed/personalized betting recommendation.

## Baseline projections

The API includes transparent starter models. They do **not** fetch historical or injury data automatically yet. Instead, they calculate a projection from factors you supply, so their assumptions stay visible and testable.

- `POST /projection/nba` uses offensive/defensive rating, recent net rating, pace, rest, and a point-based injury adjustment.
- `POST /projection/nfl` uses points scored/allowed, recent performance, rest, quarterback adjustment, injury adjustment, and weather adjustment.

Use `/docs` to enter test values. An injury adjustment is a point estimate: negative when an absence hurts that team and positive when its opponent is missing a key player. Validate all factors against historical games before relying on model outputs.

## Mobile venue and tracking tools

The dashboard resolves game location from the home team and includes a camera/image upload control for slip tracking.

- Every configured NBA and NFL team has a home arena/stadium, city, and venue coordinates in the source-controlled registry. The away team and device location are never used to determine venue.
- Once live odds are connected, the upcoming-game selector lists the provider's scheduled events by date. A selected event uses its home team to resolve venue; for NFL, its ISO start time is converted to the venue timezone for weather matching.
- The NFL venue-weather tool sends the selected stadium's reference coordinates and a venue-local game time to Open-Meteo. It returns temperature, precipitation probability, wind, gusts, weather code, and review flags.
- The tracker stores only user-reviewed fields such as the event, selection, odds, and stake in the local SQLite database. It does not store slip images or raw OCR text.
- OCR requires the Python packages in `requirements.txt` and the [Tesseract executable](https://github.com/tesseract-ocr/tesseract) installed on the server. If it is unavailable, manual entry remains available.
