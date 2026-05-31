# routes/funnel.py — GET /funnel
# Conversion funnel: entered → browsed → reached billing → converted
# Each stage is a subset of the previous — no double counting.

from fastapi import APIRouter
from database import query_one

router = APIRouter()


@router.get("/funnel")
def get_funnel():
    # Stage 1: entered store
    s1 = query_one("""
        SELECT COUNT(DISTINCT track_id) AS n
        FROM events WHERE event_type = 'person_entered'
    """)
    entered = s1["n"] or 0

    # Stage 2: browsed — spent time in at least one product zone
    # (skin_care, makeup, bottom_shelf, foh)
    s2 = query_one("""
        SELECT COUNT(DISTINCT track_id) AS n
        FROM events
        WHERE event_type = 'zone_entered'
          AND zone IN ('skin_care','makeup','bottom_shelf','foh')
    """)
    browsed = s2["n"] or 0

    # Stage 3: reached billing — visited cash_counter zone
    s3 = query_one("""
        SELECT COUNT(DISTINCT track_id) AS n
        FROM events
        WHERE event_type = 'zone_entered' AND zone = 'cash_counter'
    """)
    reached_billing = s3["n"] or 0

    # Stage 4: converted — reached billing AND their session ended
    # (proxy: track_id has both zone_entered cash_counter AND person_exited)
    s4 = query_one("""
        SELECT COUNT(DISTINCT e1.track_id) AS n
        FROM events e1
        JOIN events e2 ON e1.track_id = e2.track_id
        WHERE e1.event_type = 'zone_entered'  AND e1.zone = 'cash_counter'
          AND e2.event_type = 'person_exited'
    """)
    converted = s4["n"] or 0

    def drop(a, b):
        return round((1 - b / a) * 100, 1) if a > 0 else 0.0

    return {
        "stages": [
            {
                "stage":      "entered",
                "count":      entered,
                "drop_off_pct": 0.0,
            },
            {
                "stage":      "browsed",
                "count":      browsed,
                "drop_off_pct": drop(entered, browsed),
            },
            {
                "stage":      "reached_billing",
                "count":      reached_billing,
                "drop_off_pct": drop(browsed, reached_billing),
            },
            {
                "stage":      "converted",
                "count":      converted,
                "drop_off_pct": drop(reached_billing, converted),
            },
        ],
        "overall_conversion_pct": round((converted / entered * 100), 1) if entered > 0 else 0.0,
    }
