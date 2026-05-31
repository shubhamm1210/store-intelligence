# routes/zones.py — GET /zones/heatmap
# Per-zone traffic and average dwell time

from fastapi import APIRouter
from database import query

router = APIRouter()

ALL_ZONES = ["entrance", "skin_care", "makeup", "foh", "cash_counter", "bottom_shelf", "floor"]


@router.get("/zones/heatmap")
def get_zone_heatmap():
    # Visit counts per zone
    visits = query("""
        SELECT zone, COUNT(DISTINCT track_id) AS unique_visitors, COUNT(*) AS total_visits
        FROM events
        WHERE event_type = 'zone_entered' AND zone IS NOT NULL
        GROUP BY zone
        ORDER BY unique_visitors DESC
    """)

    # Avg dwell time per zone
    dwell = query("""
        SELECT zone,
               ROUND(AVG(exited_at - entered_at), 1)  AS avg_dwell_seconds,
               ROUND(MAX(exited_at - entered_at), 1)  AS max_dwell_seconds,
               COUNT(*)                                AS dwell_records
        FROM zone_dwell
        WHERE exited_at IS NOT NULL
        GROUP BY zone
        ORDER BY avg_dwell_seconds DESC
    """)

    # Merge into one response keyed by zone
    dwell_map = {r["zone"]: r for r in dwell}
    result = []
    for v in visits:
        z = v["zone"]
        d = dwell_map.get(z, {})
        result.append({
            "zone":               z,
            "unique_visitors":    v["unique_visitors"],
            "total_visits":       v["total_visits"],
            "avg_dwell_seconds":  d.get("avg_dwell_seconds", 0),
            "max_dwell_seconds":  d.get("max_dwell_seconds", 0),
        })

    return {"zones": result}
