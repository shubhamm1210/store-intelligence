from fastapi import APIRouter
from database import query_one

router = APIRouter()


@router.get("/funnel")
def get_funnel():

    # Stage 1: entered store
    s1 = query_one("""
        SELECT COUNT(DISTINCT track_id) AS n
        FROM events
        WHERE event_type = 'person_entered'
    """)
    entered = s1["n"] or 0

    # Stage 2: browsed
    # Only count users who actually entered first
    s2 = query_one("""
        SELECT COUNT(DISTINCT e.track_id) AS n
        FROM events e
        WHERE e.event_type = 'zone_entered'
          AND e.zone IN ('skin_care','makeup','bottom_shelf','foh')
          AND e.track_id IN (
              SELECT DISTINCT track_id
              FROM events
              WHERE event_type = 'person_entered'
          )
    """)
    browsed = min(s2["n"] or 0, entered)

    # Stage 3: reached billing
    s3 = query_one("""
        SELECT COUNT(DISTINCT e.track_id) AS n
        FROM events e
        WHERE e.event_type = 'zone_entered'
          AND e.zone = 'cash_counter'
          AND e.track_id IN (
              SELECT DISTINCT track_id
              FROM events
              WHERE event_type = 'person_entered'
          )
    """)
    reached_billing = min(s3["n"] or 0, browsed)

    # Stage 4: converted
    s4 = query_one("""
        SELECT COUNT(DISTINCT e1.track_id) AS n
        FROM events e1
        JOIN events e2 ON e1.track_id = e2.track_id
        WHERE e1.event_type = 'zone_entered'
          AND e1.zone = 'cash_counter'
          AND e2.event_type = 'person_exited'
          AND e1.track_id IN (
              SELECT DISTINCT track_id
              FROM events
              WHERE event_type = 'person_entered'
          )
    """)
    converted = min(s4["n"] or 0, reached_billing)

    def drop(a, b):
        if a <= 0:
            return 0.0
        value = (1 - b / a) * 100
        return round(max(0.0, min(100.0, value)), 1)

    return {
        "stages": [
            {
                "stage": "entered",
                "count": entered,
                "drop_off_pct": 0.0,
            },
            {
                "stage": "browsed",
                "count": browsed,
                "drop_off_pct": drop(entered, browsed),
            },
            {
                "stage": "reached_billing",
                "count": reached_billing,
                "drop_off_pct": drop(browsed, reached_billing),
            },
            {
                "stage": "converted",
                "count": converted,
                "drop_off_pct": drop(reached_billing, converted),
            },
        ],
        "overall_conversion_pct":
            round((converted / entered) * 100, 1)
            if entered > 0 else 0.0,
    }