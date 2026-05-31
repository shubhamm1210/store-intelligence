#!/usr/bin/env python3
# detector.py — main pipeline entry point
#
# Usage:
#   python detector.py                          # uses config.py defaults
#   python detector.py --source input.mp4
#   python detector.py --source 0              # webcam
#   python detector.py --source input.mp4 --no-video  # skip writing output

import argparse
import cv2
import time
from pathlib import Path
from ultralytics import YOLO

import config
from event_store import init_db, emit
from counter import PersonCounter


# ── Colour palette for track IDs ────────────────────────────────────────────
PALETTE = [
    (255, 56,  56 ), (255, 157, 151), (255, 112, 31 ), (255, 178, 29 ),
    (207, 210, 49 ), (72,  249, 10 ), (146, 204, 23 ), (61,  219, 134),
    (26,  147, 52 ), (0,   212, 187), (44,  153, 168), (0,   194, 255),
    (52,  69,  147), (100, 115, 255), (0,   24,  236), (132, 56,  255),
    (82,  0,   133), (203, 56,  255), (255, 149, 200), (255, 55,  199),
]

ZONE_COLOURS = {
    "entrance":     (0,   255, 0  ),
    "skin_care":    (255, 180, 0  ),
    "makeup":       (255, 0,   180),
    "foh":          (0,   200, 255),
    "cash_counter": (0,   0,   255),
    "bottom_shelf": (180, 0,   255),
    "floor":        (200, 200, 200),
}


def track_colour(tid: int):
    return PALETTE[tid % len(PALETTE)]


def draw_overlay(frame, tracks_annotated, counter, fps_actual):
    h, w = frame.shape[:2]
    line_y = counter.line_y

    # counting line
    cv2.line(frame, (0, line_y), (w, line_y), (0, 255, 255), 2)
    cv2.putText(frame, "COUNTING LINE", (10, line_y - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # zone overlays (light transparent rectangles — drawn before boxes)
    overlay = frame.copy()
    for zone, (nx1, ny1, nx2, ny2) in config.ZONES.items():
        px1, py1 = int(nx1 * w), int(ny1 * h)
        px2, py2 = int(nx2 * w), int(ny2 * h)
        colour = ZONE_COLOURS.get(zone, (200, 200, 200))
        cv2.rectangle(overlay, (px1, py1), (px2, py2), colour, -1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

    # bounding boxes + labels
    for (tid, x1, y1, x2, y2, zone) in tracks_annotated:
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        col = track_colour(tid)
        cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
        label = f"#{tid} [{zone}]"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), col, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # HUD — stats panel
    stats = [
        f"Entries : {counter.total_entries}",
        f"Exits   : {counter.total_exits}",
        f"Inside  : {counter.currently_inside}",
        f"FPS     : {fps_actual:.1f}",
    ]
    panel_x, panel_y = 10, 10
    for i, line in enumerate(stats):
        y = panel_y + 22 * (i + 1)
        cv2.putText(frame, line, (panel_x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, line, (panel_x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

    return frame


def run(source, write_video: bool = True, max_frames: int = None):
    # ── Init ────────────────────────────────────────────────────────
    init_db()
    model = YOLO(config.MODEL_NAME)
    cap   = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {source}")

    fw  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    fh  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    counter = PersonCounter(frame_h=fh, frame_w=fw)

    writer = None
    if write_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(config.OUTPUT_VIDEO, fourcc, fps, (fw, fh))

    emit("pipeline_started", metadata={"source": str(source), "resolution": f"{fw}x{fh}"})

    frame_no  = 0
    t_prev    = time.time()
    fps_actual = fps

    print(f"[detector] Running on {fw}x{fh} @ {fps:.1f} fps — source: {source}")
    print(f"[detector] Counting line at y={counter.line_y}px  ({config.COUNTING_LINE_Y_RATIO*100:.0f}% of frame)")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if max_frames and frame_no >= max_frames:
                break

            # ── YOLOv8 track (ByteTrack built-in) ───────────────────
            results = model.track(
                frame,
                persist      = True,
                tracker      = "bytetrack.yaml",
                classes      = [0],           # 0 = person only
                conf         = config.CONFIDENCE,
                iou          = config.IOU,
                device       = config.DEVICE,
                verbose      = False,
            )

            # ── Extract tracks ───────────────────────────────────────
            raw_tracks = []
            if results[0].boxes.id is not None:
                for box, tid in zip(results[0].boxes.xyxy, results[0].boxes.id):
                    x1, y1, x2, y2 = box.tolist()
                    raw_tracks.append((int(tid), x1, y1, x2, y2))

            # ── Count + zone logic ───────────────────────────────────
            annotated = counter.update(raw_tracks, frame_no)

            # ── FPS calc ─────────────────────────────────────────────
            now = time.time()
            fps_actual = 1.0 / max(now - t_prev, 1e-6)
            t_prev = now

            # ── Draw + write ─────────────────────────────────────────
            vis = draw_overlay(frame, annotated, counter, fps_actual)
            if writer:
                writer.write(vis)

            frame_no += 1
            if frame_no % 100 == 0:
                print(f"[detector] frame={frame_no}  in={counter.total_entries}  "
                      f"out={counter.total_exits}  inside={counter.currently_inside}")

    finally:
        cap.release()
        if writer:
            writer.release()
        emit("pipeline_finished",
             total_entries=counter.total_entries,
             total_exits=counter.total_exits,
             frames_processed=frame_no)
        print(f"\n[detector] Done. frames={frame_no}  entries={counter.total_entries}  exits={counter.total_exits}")
        if write_video:
            print(f"[detector] Output saved → {config.OUTPUT_VIDEO}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Store Intelligence — Detection Pipeline")
    parser.add_argument("--source",    default=config.VIDEO_SOURCE, help="Video file or camera index")
    parser.add_argument("--no-video",  action="store_true",         help="Skip writing output video")
    parser.add_argument("--max-frames",type=int, default=None,      help="Stop after N frames (for testing)")
    args = parser.parse_args()

    src = int(args.source) if str(args.source).isdigit() else args.source
    run(src, write_video=not args.no_video, max_frames=args.max_frames)
