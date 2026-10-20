"""Small local SQLite store for reproducible odds, injury, and model snapshots."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "edge_scanner.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def initialize_database() -> None:
    """Create the local tables used by the data pipeline."""

    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS odds_snapshots (
                id INTEGER PRIMARY KEY,
                league TEXT NOT NULL,
                event_id TEXT NOT NULL,
                home_team TEXT,
                away_team TEXT,
                captured_at TEXT NOT NULL,
                event_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS injury_snapshots (
                id INTEGER PRIMARY KEY,
                league TEXT NOT NULL,
                player_id TEXT,
                team TEXT,
                status TEXT,
                captured_at TEXT NOT NULL,
                injury_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS team_factor_snapshots (
                id INTEGER PRIMARY KEY,
                league TEXT NOT NULL,
                team TEXT NOT NULL,
                game_id TEXT,
                captured_at TEXT NOT NULL,
                factors_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projection_snapshots (
                id INTEGER PRIMARY KEY,
                league TEXT NOT NULL,
                game_id TEXT,
                model_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                inputs_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tracking_entries (
                id INTEGER PRIMARY KEY,
                league TEXT NOT NULL,
                event_name TEXT NOT NULL,
                selection TEXT NOT NULL,
                american_odds INTEGER,
                stake REAL,
                notes TEXT,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def save_odds_events(league: str, events: list[dict[str, Any]]) -> int:
    """Store each provider event exactly as it was seen at the captured time."""

    captured_at = _now()
    rows = [
        (
            league,
            str(event.get("id", "unknown")),
            event.get("home_team"),
            event.get("away_team"),
            captured_at,
            json.dumps(event),
        )
        for event in events
    ]
    if not rows:
        return 0
    with _connection() as connection:
        connection.executemany(
            """INSERT INTO odds_snapshots
            (league, event_id, home_team, away_team, captured_at, event_json)
            VALUES (?, ?, ?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def save_injuries(league: str, injuries: list[dict[str, Any]]) -> int:
    """Store raw authorized injury records with a timestamp."""

    captured_at = _now()
    rows = [
        (
            league,
            str(injury.get("PlayerID") or injury.get("PlayerId") or ""),
            injury.get("Team") or injury.get("TeamKey"),
            injury.get("Status") or injury.get("InjuryStatus"),
            captured_at,
            json.dumps(injury),
        )
        for injury in injuries
    ]
    if not rows:
        return 0
    with _connection() as connection:
        connection.executemany(
            """INSERT INTO injury_snapshots
            (league, player_id, team, status, captured_at, injury_json)
            VALUES (?, ?, ?, ?, ?, ?)""",
            rows,
        )
    return len(rows)


def save_projection(
    league: str, model_name: str, inputs: dict[str, Any], result: dict[str, Any], game_id: str | None = None
) -> None:
    """Save each model output with the inputs used to create it."""

    with _connection() as connection:
        connection.execute(
            """INSERT INTO projection_snapshots
            (league, game_id, model_name, created_at, inputs_json, result_json)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (league, game_id, model_name, _now(), json.dumps(inputs), json.dumps(result)),
        )


def save_tracking_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Store fields the user reviewed; images and raw OCR text are excluded."""

    created_at = _now()
    with _connection() as connection:
        cursor = connection.execute(
            """INSERT INTO tracking_entries
            (league, event_name, selection, american_odds, stake, notes, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["league"],
                entry["event_name"],
                entry["selection"],
                entry.get("american_odds"),
                entry.get("stake"),
                entry.get("notes"),
                entry["source"],
                created_at,
            ),
        )
    return {"id": cursor.lastrowid, "created_at": created_at, **entry}


def recent_tracking_entries(limit: int = 12) -> list[dict[str, Any]]:
    """Return recent locally saved, user-confirmed tracking entries."""

    with _connection() as connection:
        rows = connection.execute(
            """SELECT id, league, event_name, selection, american_odds, stake, notes, source, created_at
            FROM tracking_entries ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    fields = ["id", "league", "event_name", "selection", "american_odds", "stake", "notes", "source", "created_at"]
    return [dict(zip(fields, row)) for row in rows]


def database_status() -> dict[str, int]:
    """Return simple counts to show pipeline activity without exposing data."""

    with _connection() as connection:
        counts = {
            "odds_snapshots": connection.execute("SELECT COUNT(*) FROM odds_snapshots").fetchone()[0],
            "injury_snapshots": connection.execute("SELECT COUNT(*) FROM injury_snapshots").fetchone()[0],
            "projection_snapshots": connection.execute("SELECT COUNT(*) FROM projection_snapshots").fetchone()[0],
            "tracking_entries": connection.execute("SELECT COUNT(*) FROM tracking_entries").fetchone()[0],
        }
    return counts
