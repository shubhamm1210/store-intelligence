# config.py — central place to tune all parameters

VIDEO_SOURCE = "input.mp4"        # path to CCTV video file
OUTPUT_VIDEO = "output.mp4"       # path to annotated output video
EVENTS_DB    = "events.db"        # SQLite database file

# YOLOv8 settings
MODEL_NAME   = "yolov8n.pt"       # nano = fastest, CPU-friendly
CONFIDENCE   = 0.4                # detection confidence threshold
IOU          = 0.5                # NMS IOU threshold
DEVICE       = "cpu"              # "cpu" or "0" for GPU

# Counting line
# Defined as a fraction of frame height (0.0 = top, 1.0 = bottom)
# People crossing this line trigger entry/exit events
COUNTING_LINE_Y_RATIO = 0.55      # 55% down the frame

# Zone definitions (normalized x1,y1,x2,y2 — 0.0 to 1.0)
# Based on Brigade Road store layout
ZONES = {
    "entrance":     (0.0,  0.0,  0.15, 1.0),   # left side (door)
    "skin_care":    (0.0,  0.0,  0.55, 0.45),   # top-left shelf wall
    "makeup":       (0.55, 0.0,  1.0,  0.45),   # top-right shelf wall
    "foh":          (0.2,  0.35, 0.75, 0.65),   # centre floor / FOH
    "cash_counter": (0.75, 0.3,  1.0,  0.75),   # right — billing
    "bottom_shelf": (0.0,  0.65, 1.0,  1.0),    # bottom wall brands
}

# Anomaly thresholds
CROWD_THRESHOLD   = 8     # persons in frame simultaneously → overcrowding
DWELL_SECONDS     = 30    # seconds in one zone → loitering alert
QUEUE_THRESHOLD   = 3     # persons near cash counter → queue alert
