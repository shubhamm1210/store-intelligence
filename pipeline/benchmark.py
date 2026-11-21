#!/usr/bin/env python3
"""Benchmark YOLOv8 + ByteTrack inference and optional running API endpoints.

Inference FPS measures model.track() time only. It excludes video decoding,
event/database writes, overlay drawing, and video encoding.
"""

import argparse
import json
import math
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cv2
from ultralytics import YOLO

import config


def parse_source(value: str):
    return int(value) if value.isdigit() else value


def infer(model, frame):
    return model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0],
        conf=config.CONFIDENCE,
        iou=config.IOU,
        device=config.DEVICE,
        verbose=False,
    )


def benchmark_inference(source, max_frames: int, warmup_frames: int):
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video source: {source}")

    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        source_fps = capture.get(cv2.CAP_PROP_FPS) or None
        model = YOLO(config.MODEL_NAME)

        warmed = 0
        while warmed < warmup_frames:
            ok, frame = capture.read()
            if not ok:
                break
            infer(model, frame)
            warmed += 1

        processed = 0
        inference_seconds = 0.0
        while processed < max_frames:
            ok, frame = capture.read()
            if not ok:
                break

            started = time.perf_counter()
            infer(model, frame)
            inference_seconds += time.perf_counter() - started
            processed += 1

        if processed == 0 or inference_seconds <= 0:
            raise RuntimeError(
                "No benchmark frames were processed. Reduce --warmup or check the video."
            )

        return {
            "source": str(source),
            "resolution": f"{width}x{height}",
            "source_fps": source_fps,
            "device": config.DEVICE,
            "warmup_frames": warmed,
            "measured_frames": processed,
            "inference_seconds": round(inference_seconds, 4),
            "inference_fps": round(processed / inference_seconds, 2),
            "scope": (
                "YOLO + ByteTrack inference only; excludes decoding, event persistence, "
                "overlay drawing, and video encoding"
            ),
        }
    finally:
        capture.release()


def percentile(values, fraction: float):
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def benchmark_api(base_url: str, request_count: int):
    endpoints = [
        "/health",
        "/metrics",
        "/funnel",
        "/zones/heatmap",
        "/anomalies?limit=50",
    ]
    results = {}

    for endpoint in endpoints:
        samples_ms = []
        status_code = None
        url = base_url.rstrip("/") + endpoint

        for _ in range(request_count):
            request = Request(url, headers={"Accept": "application/json"})
            started = time.perf_counter()
            try:
                with urlopen(request, timeout=15) as response:
                    response.read()
                    status_code = response.status
            except (HTTPError, URLError, TimeoutError) as error:
                raise RuntimeError(f"API benchmark failed for {endpoint}: {error}") from error
            samples_ms.append((time.perf_counter() - started) * 1000)

        results[endpoint] = {
            "status_code": status_code,
            "requests": request_count,
            "mean_ms": round(statistics.mean(samples_ms), 2),
            "p50_ms": round(percentile(samples_ms, 0.50), 2),
            "p95_ms": round(percentile(samples_ms, 0.95), 2),
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark Store Intelligence inference and API latency.")
    parser.add_argument("--source", default=config.VIDEO_SOURCE, help="Video file path or camera index")
    parser.add_argument("--max-frames", type=int, default=300, help="Number of measured frames")
    parser.add_argument("--warmup", type=int, default=10, help="Warm-up frames excluded from timing")
    parser.add_argument("--api-base", help="Optional running API base URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--api-requests", type=int, default=20, help="Requests per API endpoint")
    args = parser.parse_args()

    if args.max_frames < 1 or args.warmup < 0 or args.api_requests < 1:
        parser.error("--max-frames and --api-requests must be positive; --warmup cannot be negative")

    result = {
        "inference": benchmark_inference(
            parse_source(args.source),
            max_frames=args.max_frames,
            warmup_frames=args.warmup,
        )
    }

    if args.api_base:
        result["api_latency"] = benchmark_api(args.api_base, args.api_requests)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
