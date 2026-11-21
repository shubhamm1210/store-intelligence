# config.py — central place to tune all parameters

import os

VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "input.mp4")
OUTPUT_VIDEO = os.getenv("OUTPUT_VIDEO", "output.mp4")
EVENTS_DB = os.getenv("EVENTS_DB", "events.db")

# YOLOv8 settings
MODEL_NAME = os.getenv("MODEL_NAME", "yolov8n.pt")
CONFIDENCE = 0.4
IOU = 0.5
DEVICE = "cpu"

# Counting line
# Defined as a fraction of frame height (0.0 = top, 1.0 = bottom)
# People crossing this line trigger entry/exit events
COUNTING_LINE_Y_RATIO = 0.55

# Zone definitions (normalized x1,y1,x2,y2 — 0.0 to 1.0)
# Based on Brigade Road store layout
ZONES = {
    "entrance":     (0.0, 0.0, 0.15, 1.0),
    "skin_care":    (0.0, 0.0, 0.55, 0.45),
    "makeup":       (0.55, 0.0, 1.0, 0.45),
    "foh":          (0.2, 0.35, 0.75, 0.65),
    "cash_counter": (0.75, 0.3, 1.0, 0.75),
    "bottom_shelf": (0.0, 0.65, 1.0, 1.0),
}

# Anomaly thresholds
CROWD_THRESHOLD = 8
DWELL_SECONDS = 30
QUEUE_THRESHOLD = 3
