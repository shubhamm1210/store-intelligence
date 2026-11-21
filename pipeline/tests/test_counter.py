import sys
from pathlib import Path

import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE_DIR))

import counter  # noqa: E402


@pytest.fixture
def counter_instance(monkeypatch):
    monkeypatch.setattr(counter, "emit", lambda *args, **kwargs: None)
    monkeypatch.setattr(counter, "update_dwell", lambda *args, **kwargs: None)
    monkeypatch.setattr(counter, "get_zone", lambda *args, **kwargs: "skin_care")
    return counter.PersonCounter(frame_h=100, frame_w=100)


def track(track_id, cy):
    return (track_id, 10, cy - 5, 20, cy + 5)


def test_downward_crossing_counts_one_entry(counter_instance):
    pc = counter_instance
    pc.update([track(7, 40)], frame_no=1)
    pc.update([track(7, 60)], frame_no=2)
    assert pc.total_entries == 1
    assert pc.total_exits == 0
    assert pc.currently_inside == 1


def test_upward_crossing_counts_one_exit(counter_instance):
    pc = counter_instance
    pc.update([track(7, 40)], frame_no=1)
    pc.update([track(7, 60)], frame_no=2)
    pc.update([track(7, 40)], frame_no=3)
    assert pc.total_entries == 1
    assert pc.total_exits == 1
    assert pc.currently_inside == 0


def test_same_track_can_reenter_after_exit(counter_instance, monkeypatch):
    emitted = []
    monkeypatch.setattr(counter, "emit", lambda *args, **kwargs: emitted.append((args, kwargs)))
    pc = counter_instance
    pc.update([track(7, 40)], frame_no=1)
    pc.update([track(7, 60)], frame_no=2)
    pc.update([track(7, 40)], frame_no=3)
    pc.update([track(7, 60)], frame_no=4)

    entries = [event for event in emitted if event[0][0] == "person_entered"]
    assert len(entries) == 2
    assert entries[0][1].get("re_entry") is None
    assert entries[1][1]["re_entry"] is True
    assert pc.total_entries == 2
    assert pc.total_exits == 1
    assert pc.currently_inside == 1


def test_stationary_track_does_not_create_entries(counter_instance):
    pc = counter_instance
    for frame in range(5):
        pc.update([track(7, 40)], frame_no=frame)
    assert pc.total_entries == 0
    assert pc.total_exits == 0


def test_missing_active_track_is_counted_as_exit(counter_instance):
    pc = counter_instance
    pc.update([track(7, 40)], frame_no=1)
    pc.update([track(7, 60)], frame_no=2)
    pc.update([], frame_no=3)
    assert pc.total_exits == 1
    assert pc.currently_inside == 0
    assert 7 in pc.exited


def test_returns_zone_annotation(counter_instance):
    result = counter_instance.update([track(3, 20)], frame_no=1)
    assert result == [(3, 10, 15, 20, 25, "skin_care")]
