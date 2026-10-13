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

The scraper modules are intentionally safe placeholders. Add the provider-specific requests only after you have the appropriate API credentials and have reviewed that provider's terms.
