# counter.py — entry / exit detection using a horizontal counting line
#
# Logic:
#   Each tracked person has a centroid (cy) each frame.
#   We remember their cy from the PREVIOUS frame.
#   If they cross the counting line (prev above, now below) → ENTRY
#   If they cross the other way                             → EXIT
#
# Edge cases handled:
#   - Re-entry: same track_id seen again after exit → counted as new entry
#   - Staff: we do NOT filter staff here (staff filtering is a CHOICES.md decision)
#   - Partial occlusion: ByteTrack handles ID continuity

import time
from event_store import emit, update_dwell
from zone_mapper import get_zone
from config import COUNTING_LINE_Y_RATIO, DWELL_SECONDS, CROWD_THRESHOLD, QUEUE_THRESHOLD


class PersonCounter:
    def __init__(self, frame_h: int, frame_w: int):
        self.line_y     = int(frame_h * COUNTING_LINE_Y_RATIO)
        self.frame_h    = frame_h
        self.frame_w    = frame_w

        self.prev_cy: dict[int, float] = {}     # track_id → last cy
        self.active:  set[int]         = set()  # currently inside store
        self.exited:  set[int]         = set()  # ever exited (for re-entry)

        self.total_entries = 0
        self.total_exits   = 0

        # Zone dwell tracking: track_id → {zone: entered_at_unix}
        self.zone_entry_time: dict[int, dict[str, float]] = {}
        self.current_zone:    dict[int, str]              = {}

        # Anomaly state
        self._last_crowd_alert  = 0.0
        self._last_queue_alert  = 0.0

    def update(self, tracks: list, frame_no: int):
        """
        tracks: list of (track_id, x1, y1, x2, y2)
        Returns annotated list with zone info added.
        """
        now       = time.time()
        seen_ids  = set()
        annotated = []

        cash_counter_count = 0

        for (tid, x1, y1, x2, y2) in tracks:
            seen_ids.add(tid)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            zone = get_zone(cx, cy, self.frame_w, self.frame_h)
            if zone == "cash_counter":
                cash_counter_count += 1

            # ── Entry / Exit detection ──────────────────────────────
            prev = self.prev_cy.get(tid)
            if prev is not None:
                crossed_down = prev < self.line_y <= cy   # top→bottom = entry
                crossed_up   = prev > self.line_y >= cy   # bottom→top = exit

                if crossed_down and tid not in self.active:
                    self.active.add(tid)
                    self.total_entries += 1
                    emit("person_entered", track_id=tid, zone=zone, frame_no=frame_no)

                elif crossed_up and tid in self.active:
                    self.active.discard(tid)
                    self.exited.add(tid)
                    self.total_exits += 1
                    emit("person_exited", track_id=tid, zone=zone, frame_no=frame_no)

                # Re-entry: was exited, crossed line downward again
                elif crossed_down and tid in self.exited:
                    self.active.add(tid)
                    self.exited.discard(tid)
                    self.total_entries += 1
                    emit("person_entered", track_id=tid, zone=zone,
                         frame_no=frame_no, re_entry=True)

            self.prev_cy[tid] = cy

            # ── Zone dwell tracking ─────────────────────────────────
            prev_zone = self.current_zone.get(tid)
            if prev_zone != zone:
                # exited previous zone
                if prev_zone and tid in self.zone_entry_time:
                    entered_at = self.zone_entry_time[tid].pop(prev_zone, None)
                    if entered_at:
                        dwell = now - entered_at
                        update_dwell(tid, prev_zone, entered_at, now)
                        emit("zone_exited", track_id=tid, zone=prev_zone,
                             frame_no=frame_no, dwell_seconds=round(dwell, 1))
                        if dwell >= DWELL_SECONDS:
                            emit("anomaly_loiter", track_id=tid, zone=prev_zone,
                                 frame_no=frame_no, dwell_seconds=round(dwell, 1))

                # entered new zone
                self.current_zone[tid] = zone
                self.zone_entry_time.setdefault(tid, {})[zone] = now
                update_dwell(tid, zone, now)
                emit("zone_entered", track_id=tid, zone=zone, frame_no=frame_no)

            annotated.append((tid, x1, y1, x2, y2, zone))

        # ── Handle tracks that disappeared this frame ───────────────
        vanished = set(self.prev_cy.keys()) - seen_ids
        for tid in vanished:
            if tid in self.active:
                # treat disappearance near exit as implicit exit
                self.active.discard(tid)
                self.total_exits += 1
                emit("person_exited", track_id=tid, zone=self.current_zone.get(tid, "unknown"),
                     frame_no=frame_no, reason="track_lost")
            del self.prev_cy[tid]
            self.current_zone.pop(tid, None)

        # ── Crowd anomaly ───────────────────────────────────────────
        if len(tracks) >= CROWD_THRESHOLD and now - self._last_crowd_alert > 10:
            emit("anomaly_crowd", frame_no=frame_no, count=len(tracks))
            self._last_crowd_alert = now

        # ── Queue anomaly ───────────────────────────────────────────
        if cash_counter_count >= QUEUE_THRESHOLD and now - self._last_queue_alert > 15:
            emit("anomaly_queue", frame_no=frame_no, count=cash_counter_count,
                 zone="cash_counter")
            self._last_queue_alert = now

        return annotated

    @property
    def currently_inside(self) -> int:
        return len(self.active)
