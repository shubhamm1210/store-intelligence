import sqlite3
import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from routes import funnel  # noqa: E402


@pytest.fixture
def event_database(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE events (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            track_id INTEGER,
            zone TEXT,
            timestamp TEXT,
            frame_no INTEGER,
            metadata TEXT
        )
        """
    )

    def query_one(sql, params=()):
        row = connection.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    monkeypatch.setattr(funnel, "query_one", query_one)
    yield connection
    connection.close()


def add_event(db, event_type, track_id, zone=None):
    db.execute(
        """
        INSERT INTO events (event_type, track_id, zone, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (event_type, track_id, zone, "2026-01-01T00:00:00Z"),
    )
    db.commit()


def test_funnel_deduplicates_tracker_ids_and_caps_later_stages(event_database):
    db = event_database

    # Track 1 enters, browses repeatedly, reaches billing, and exits.
    add_event(db, "person_entered", 1)
    add_event(db, "person_entered", 1)  # duplicate event for the same tracker
    add_event(db, "zone_entered", 1, "skin_care")
    add_event(db, "zone_entered", 1, "makeup")
    add_event(db, "zone_entered", 1, "cash_counter")
    add_event(db, "person_exited", 1)

    # Track 2 enters and reaches billing, but never browses.
    add_event(db, "person_entered", 2)
    add_event(db, "zone_entered", 2, "cash_counter")
    add_event(db, "person_exited", 2)

    # Track 3 has downstream events but never entered; it must be excluded.
    add_event(db, "zone_entered", 3, "skin_care")
    add_event(db, "zone_entered", 3, "cash_counter")
    add_event(db, "person_exited", 3)

    result = funnel.get_funnel()
    stages = {stage["stage"]: stage for stage in result["stages"]}

    assert stages["entered"]["count"] == 2
    assert stages["browsed"]["count"] == 1
    assert stages["reached_billing"]["count"] == 1
    assert stages["converted"]["count"] == 1
    assert result["overall_conversion_pct"] == 50.0


def test_empty_event_table_returns_zero_counts(event_database):
    result = funnel.get_funnel()

    assert [stage["count"] for stage in result["stages"]] == [0, 0, 0, 0]
    assert result["overall_conversion_pct"] == 0.0
