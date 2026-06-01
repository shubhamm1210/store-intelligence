# routes/anomalies.py — GET /anomalies
# Returns all detected anomaly events with context

from fastapi import APIRouter, Query
from database import query

router = APIRouter()

ANOMALY_TYPES = {"anomaly_crowd", "anomaly_loiter", "anomaly_queue"}


@router.get("/anomalies")
def get_anomalies(
    type: str = Query(None, description="Filter by type: crowd | loiter | queue"),
    limit: int = Query(50, ge=1, le=500),
):
    if type:
        event_type = f"anomaly_{type}"
        rows = query(
            "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            (event_type, limit),
        )
    else:
        rows = query(
            "SELECT * FROM events WHERE event_type LIKE 'anomaly_%' ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )

    # Summary counts
    summary = query("""
        SELECT event_type, COUNT(*) as count
        FROM events
        WHERE event_type LIKE 'anomaly_%'
        GROUP BY event_type
        ORDER BY count DESC
    """)

    return {
        "summary": summary,
        "events":  rows,
        "total":   len(rows),
    }
