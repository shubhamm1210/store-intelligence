# zone_mapper.py — maps bounding box pixel coords → named store zones

from config import ZONES


def get_zone(cx: float, cy: float, frame_w: int, frame_h: int) -> str:
    """
    Given a centroid (cx, cy) in pixels and frame dimensions,
    return the name of the zone the person is standing in.
    Returns 'floor' if no zone matches.
    """
    nx = cx / frame_w   # normalise to 0–1
    ny = cy / frame_h

    for zone_name, (x1, y1, x2, y2) in ZONES.items():
        if x1 <= nx <= x2 and y1 <= ny <= y2:
            return zone_name

    return "floor"


def get_all_zones(cx: float, cy: float, frame_w: int, frame_h: int) -> list[str]:
    """Returns all zones the point falls into (zones can overlap)."""
    nx, ny = cx / frame_w, cy / frame_h
    matched = [
        name for name, (x1, y1, x2, y2) in ZONES.items()
        if x1 <= nx <= x2 and y1 <= ny <= y2
    ]
    return matched if matched else ["floor"]
