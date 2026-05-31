# routes/metrics.py — GET /metrics
# Core business KPIs derived from pipeline events

from fastapi import APIRouter
from database import query, query_one

router = APIRouter()


@router.get("/metrics")
def get_metrics():
    # Total entries and exits
    counts = query_one("""
        SELECT
            SUM(CASE WHEN event_type = 'person_entered' THEN 1 ELSE 0 END) AS total_entries,
            SUM(CASE WHEN event_type = 'person_exited'  THEN 1 ELSE 0 END) AS total_exits
        FROM events
    """)

    total_entries = counts["total_entries"] or 0
    total_exits   = counts["total_exits"]   or 0
    currently_inside = max(0, total_entries - total_exits)

    # Avg dwell time per person (seconds) from zone_dwell table
    dwell = query_one("""
        SELECT AVG(exited_at - entered_at) AS avg_dwell
        FROM zone_dwell
        WHERE exited_at IS NOT NULL
    """)
    avg_dwell_seconds = round(dwell["avg_dwell"] or 0, 1)

    # Conversion rate — persons who reached cash_counter / total entries
    # A "conversion" = track_id that had a zone_entered event for cash_counter
    converters = query_one("""
        SELECT COUNT(DISTINCT track_id) AS converted
        FROM events
        WHERE event_type = 'zone_entered' AND zone = 'cash_counter'
    """)
    converted = converters["converted"] or 0
    conversion_rate = round((converted / total_entries * 100), 1) if total_entries > 0 else 0.0

    # Peak occupancy (max people inside at any point)
    # Approximated by counting running total of entries - exits over time
    events = query("""
        SELECT event_type FROM events
        WHERE event_type IN ('person_entered', 'person_exited')
        ORDER BY timestamp
    """)
    peak = inside = 0
    for e in events:
        inside += 1 if e["event_type"] == "person_entered" else -1
        peak = max(peak, inside)

    # Zone popularity — top zones by visit count
    zone_visits = query("""
        SELECT zone, COUNT(*) AS visits
        FROM events
        WHERE event_type = 'zone_entered' AND zone IS NOT NULL
        GROUP BY zone
        ORDER BY visits DESC
    """)

    return {
        "total_entries":       total_entries,
        "total_exits":         total_exits,
        "currently_inside":    currently_inside,
        "peak_occupancy":      peak,
        "avg_dwell_seconds":   avg_dwell_seconds,
        "conversion_rate_pct": conversion_rate,
        "converted_count":     converted,
        "zone_popularity":     zone_visits,
    }
