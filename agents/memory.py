"""Small local SQLite memory store for user preferences, trip drafts and events.

All persistence remains on the user's machine unless they deploy the app elsewhere.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def db_path() -> Path:
    configured = os.getenv("VOYAGEWISE_DB_PATH", "").strip()
    return Path(configured).expanduser() if configured else ROOT / "data" / "voyagewise.sqlite3"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS profile_memory (
            memory_key TEXT PRIMARY KEY,
            memory_value TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            request_json TEXT NOT NULL,
            itinerary_json TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            updated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER,
            agent_name TEXT NOT NULL,
            event TEXT NOT NULL,
            detail TEXT NOT NULL,
            created_at_utc TEXT NOT NULL,
            FOREIGN KEY(trip_id) REFERENCES trips(id)
        );
        """)


def save_profile(memory: dict[str, Any]) -> None:
    if not memory:
        return
    init_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        for key, value in memory.items():
            conn.execute("""INSERT INTO profile_memory(memory_key,memory_value,updated_at_utc)
                VALUES(?,?,?) ON CONFLICT(memory_key) DO UPDATE SET
                memory_value=excluded.memory_value, updated_at_utc=excluded.updated_at_utc""",
                (str(key), json.dumps(value, ensure_ascii=False), now))


def load_profile() -> dict[str, Any]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT memory_key,memory_value FROM profile_memory").fetchall()
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["memory_key"]] = json.loads(row["memory_value"])
        except ValueError:
            continue
    return result


def save_trip(request: dict[str, Any], itinerary: dict[str, Any], trip_id: int | None = None) -> int:
    init_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    title = f"{request.get('origin_city', 'Trip')} → {request.get('destination', 'Destination')}"
    status = str(itinerary.get("approval_status", "Pending approval"))
    req_json = json.dumps(request, ensure_ascii=False, default=str)
    it_json = json.dumps(itinerary, ensure_ascii=False, default=str)
    with _connect() as conn:
        if trip_id is None:
            cursor = conn.execute("INSERT INTO trips(title,status,request_json,itinerary_json,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",
                                  (title, status, req_json, it_json, now, now))
            return int(cursor.lastrowid)
        conn.execute("UPDATE trips SET title=?,status=?,request_json=?,itinerary_json=?,updated_at_utc=? WHERE id=?",
                     (title, status, req_json, it_json, now, int(trip_id)))
        return int(trip_id)


def list_trips(limit: int = 30) -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT id,title,status,request_json,itinerary_json,created_at_utc,updated_at_utc FROM trips ORDER BY updated_at_utc DESC LIMIT ?",
                            (max(1, min(limit, 100)),)).fetchall()
    output = []
    for row in rows:
        try:
            output.append({"id": row["id"], "title": row["title"], "status": row["status"],
                           "request": json.loads(row["request_json"]), "itinerary": json.loads(row["itinerary_json"]),
                           "created_at_utc": row["created_at_utc"], "updated_at_utc": row["updated_at_utc"]})
        except ValueError:
            continue
    return output


def log_events(events: list[dict[str, Any]], trip_id: int | None = None) -> None:
    if not events:
        return
    init_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        conn.executemany("INSERT INTO agent_events(trip_id,agent_name,event,detail,created_at_utc) VALUES(?,?,?,?,?)",
                         [(trip_id, str(e.get("agent", "System")), str(e.get("status", "info")), str(e.get("detail", "")), now) for e in events])


def list_events(limit: int = 100) -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT trip_id,agent_name,event,detail,created_at_utc FROM agent_events ORDER BY id DESC LIMIT ?",
                            (max(1, min(limit, 500)),)).fetchall()
    return [dict(row) for row in rows]


def clear_memory() -> None:
    """Explicit user-invoked reset for local preference memory and trip history."""
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM profile_memory")
        conn.execute("DELETE FROM trips")
        conn.execute("DELETE FROM agent_events")
