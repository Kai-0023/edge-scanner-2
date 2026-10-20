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
- `POST /projection/nba` and `POST /projection/nfl` return a transparent matchup explanation that identifies the supplied factors driving the baseline result. It is not a trained ML prediction.
- `POST /compliance/location-research` returns a research-only notice for a user-confirmed state code. It does not receive or store device coordinates and does not verify eligibility, legality, or provider availability.
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
- `POST /sync/injuries/nba` pulls and stores authorized NBA injury records after `SPORTS_DATA_IO_API_KEY` is configured.
- `POST /sync/injuries/nfl?season=2026REG&week=1` does the same for NFL, using the required season and week.

Add `SPORTS_DATA_IO_API_KEY` only after purchasing or otherwise obtaining authorized access to the NBA/NFL data feeds. Do not send the key to chat or commit it to GitHub.

## Baseline projections

The API includes transparent starter models. They do **not** fetch historical or injury data automatically yet. Instead, they calculate a projection from factors you supply, so their assumptions stay visible and testable.

- `POST /projection/nba` uses offensive/defensive rating, recent net rating, pace, rest, and a point-based injury adjustment.
- `POST /projection/nfl` uses points scored/allowed, recent performance, rest, quarterback adjustment, injury adjustment, and weather adjustment.

Use `/docs` to enter test values. An injury adjustment is a point estimate: negative when an absence hurts that team and positive when its opponent is missing a key player. Validate all factors against historical games before relying on model outputs.

## Mobile tools and privacy

The dashboard includes optional device-location confirmation and a camera/image upload control for slip tracking.

- Browser GPS only confirms location on the device. The app asks the user to enter a two-letter state code separately, and does not send or save browser coordinates.
- Location research is not a legal or sportsbook-availability check. Users must confirm requirements directly with the relevant jurisdiction and provider.
- The tracker stores only user-reviewed fields such as the event, selection, odds, and stake in the local SQLite database. It does not store slip images or raw OCR text.
- OCR requires the Python packages in `requirements.txt` and the [Tesseract executable](https://github.com/tesseract-ocr/tesseract) installed on the server. If it is unavailable, manual entry remains available.
