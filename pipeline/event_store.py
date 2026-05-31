# event_store.py — write structured events to SQLite
# Simple replacement for Redis/Kafka at this scale.
# Can be swapped for a message broker later without changing the event schema.

import sqlite3
import json
import time
from datetime import datetime
from config import EVENTS_DB


def get_conn():
    conn = sqlite3.connect(EVENTS_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT    NOT NULL,
            track_id    INTEGER,
            zone        TEXT,
            timestamp   TEXT    NOT NULL,
            frame_no    INTEGER,
            metadata    TEXT            -- JSON blob for extra fields
        );

        CREATE TABLE IF NOT EXISTS zone_dwell (
            track_id    INTEGER NOT NULL,
            zone        TEXT    NOT NULL,
            entered_at  REAL    NOT NULL,   -- unix timestamp
            exited_at   REAL,
            PRIMARY KEY (track_id, zone, entered_at)
        );

        CREATE INDEX IF NOT EXISTS idx_events_type      ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_track     ON events(track_id);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
    """)
    conn.commit()
    conn.close()


def emit(event_type: str, track_id: int = None, zone: str = None,
         frame_no: int = None, **extra):
    """
    Persist one event and also print it as JSON to stdout.
    event_type examples: person_entered, person_exited,
                         zone_entered, zone_exited,
                         anomaly_crowd, anomaly_loiter, anomaly_queue
    """
    ts = datetime.utcnow().isoformat() + "Z"
    payload = {
        "event_type": event_type,
        "track_id":   track_id,
        "zone":       zone,
        "timestamp":  ts,
        "frame_no":   frame_no,
        **extra,
    }
    # stdout — useful for log pipelines / debugging
    print(json.dumps(payload))

    conn = get_conn()
    conn.execute(
        "INSERT INTO events (event_type, track_id, zone, timestamp, frame_no, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (event_type, track_id, zone, ts, frame_no, json.dumps(extra) if extra else None)
    )
    conn.commit()
    conn.close()


def update_dwell(track_id: int, zone: str, entered_at: float, exited_at: float = None):
    conn = get_conn()
    if exited_at is None:
        conn.execute(
            "INSERT OR IGNORE INTO zone_dwell (track_id, zone, entered_at) VALUES (?,?,?)",
            (track_id, zone, entered_at)
        )
    else:
        conn.execute(
            "UPDATE zone_dwell SET exited_at=? WHERE track_id=? AND zone=? AND entered_at=?",
            (exited_at, track_id, zone, entered_at)
        )
    conn.commit()
    conn.close()
