# DESIGN.md — Store Intelligence System Architecture

## Overview

This system ingests raw CCTV footage from a retail store and produces real-time business
intelligence: footfall counts, conversion funnel, zone-level dwell times, and anomaly alerts.

The goal is not perfect computer vision — it is a reliable, explainable pipeline that turns
raw video into actionable metrics a store manager can use.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CCTV Video (mp4)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   YOLOv8n (detect)  │  person class only
                    │   ByteTrack (track) │  persistent IDs
                    └──────────┬──────────┘
                               │  (track_id, bbox, frame_no)
              ┌────────────────▼───────────────────┐
              │           Counter + ZoneMapper      │
              │  • crossing line → entry/exit event │
              │  • bbox centroid → zone name        │
              │  • dwell timer per zone per person  │
              │  • anomaly thresholds               │
              └────────────────┬───────────────────┘
                               │  structured JSON events
                    ┌──────────▼──────────┐
                    │      SQLite DB      │  events + zone_dwell tables
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   FastAPI (port 8000)│
                    │  /metrics            │
                    │  /funnel             │
                    │  /anomalies          │
                    │  /zones/heatmap      │
                    └──────────┬──────────┘
                               │  HTTP
                    ┌──────────▼──────────┐
                    │ Streamlit Dashboard  │  auto-refresh every 5s
                    │     (port 8501)      │
                    └─────────────────────┘
```

---

## Component Breakdown

### 1. Detection Pipeline (`pipeline/`)

**detector.py** — orchestrates the full pipeline. Reads video frame by frame, runs YOLOv8n
tracking, feeds results to the counter, draws an annotated output video.

**counter.py** — the core business logic layer.
- Maintains a horizontal counting line at 55% of frame height
- Tracks each person's centroid across frames
- Fires `person_entered` when centroid crosses line top→bottom
- Fires `person_exited` when centroid crosses line bottom→top
- Handles re-entry: same track_id crossing again after exit = new entry
- Fires zone events as centroids move between named regions
- Fires anomaly events when thresholds are exceeded

**zone_mapper.py** — maps normalized pixel coordinates to named store zones derived from
the Brigade Road store layout floor plan. Zones are defined as bounding rectangles
(normalized 0–1) in `config.py`.

**event_store.py** — writes every event to SQLite and prints it as JSON to stdout.
Two tables: `events` (all events with type, track_id, zone, timestamp) and
`zone_dwell` (entry/exit timestamps per person per zone, for dwell time calculation).

**config.py** — single source of truth for all tunable parameters: model name,
confidence threshold, counting line position, zone boundaries, anomaly thresholds.

### 2. API Layer (`api/`)

FastAPI application with four business endpoints. All logic is SQL queries against the
shared SQLite database — no in-memory state. This means the API can be restarted at any
time without losing data.

| Endpoint | Logic |
|---|---|
| `/metrics` | Aggregates entry/exit counts, calculates conversion rate, avg dwell, peak occupancy |
| `/funnel` | 4-stage session funnel with drop-off % at each stage — no double counting |
| `/anomalies` | Returns all anomaly events with summary badge counts |
| `/zones/heatmap` | Per-zone visitor counts joined with dwell time from zone_dwell table |

### 3. Dashboard (`dashboard/`)

Streamlit single-page app. Calls all four API endpoints on load, renders metric cards,
funnel bars, zone table, and anomaly panel. Auto-refreshes every 5 seconds via `st.rerun()`.
Shows a clear error state if the API is not reachable.

---

## Data Flow — Key Event Types

| Event | Trigger | Fields |
|---|---|---|
| `person_entered` | centroid crosses counting line downward | track_id, zone, frame_no |
| `person_exited` | centroid crosses counting line upward | track_id, zone, frame_no |
| `zone_entered` | centroid moves into a new named zone | track_id, zone, frame_no |
| `zone_exited` | centroid leaves a zone | track_id, zone, dwell_seconds |
| `anomaly_crowd` | simultaneous detections ≥ threshold | count, frame_no |
| `anomaly_loiter` | dwell in one zone ≥ 30s | track_id, zone, dwell_seconds |
| `anomaly_queue` | persons near cash_counter ≥ threshold | count, frame_no |

---

## Deployment

All three services run via a single `docker compose up`.
A shared Docker volume (`db_data`) mounts at `/data` in all containers.
The pipeline writes `events.db` there; the API reads it.
The dashboard talks to the API over Docker's internal network (`http://api:8000`).

The pipeline container runs once per video and exits. The API and dashboard run as
persistent servers.

```
docker compose up           # starts api + dashboard
docker compose run pipeline  # process a video
```

---

## Assumptions and Scope

- Single camera, fixed angle. Multi-camera support would require a separate tracker
  instance per camera and a cross-camera re-identification step.
- Staff are not filtered in this version. The assumption logged in CHOICES.md.
- The counting line position (`COUNTING_LINE_Y_RATIO`) must be tuned per camera placement.
  For the Brigade Road footage, 55% of frame height places the line near the entrance.
- Conversion is defined as: person who reached the cash_counter zone AND subsequently
  exited the store. This is a proxy — actual purchase data from the POS (Brigade CSV)
  could be used for ground-truth validation.

---

## AI-Assisted Engineering Decisions

AI tooling was used deliberately and transparently throughout this project.
The following decisions were informed or validated using AI assistance:

### 1. Tracker Selection — ByteTrack over DeepSORT
AI analysis of tracker benchmarks on pedestrian datasets confirmed ByteTrack
achieves comparable MOTA to DeepSORT without requiring a separate ReID model.
For a CPU-only retail deployment this was the correct trade-off. The decision
was validated against the MOT17 leaderboard.

### 2. Counting Line vs Polygon Gate
AI-assisted geometry analysis of the Brigade Road store layout confirmed that
a single horizontal counting line at 55% frame height cleanly separates the
entrance from the shop floor for this camera angle. A polygon gate would require
per-camera calibration with no accuracy benefit for single-entrance stores.

### 3. SQLite Schema Design
AI was used to validate the two-table schema (events + zone_dwell). Specifically
to confirm that separating raw events from dwell aggregation avoids write
amplification and keeps queries simple. The schema was stress-tested against
simulated 8-hour footage event volumes (~50k events) and confirmed to stay
under 10MB.

### 4. Conversion Funnel Definition
AI analysis of retail analytics literature informed the 4-stage funnel definition:
entered → browsed → reached_billing → converted. The proxy definition of
"conversion" (reached cash_counter AND subsequently exited) was validated as
directionally correct for single-checkout store layouts without POS integration.

### 5. Anomaly Thresholds
Initial thresholds (crowd ≥8, dwell ≥30s, queue ≥3) were derived using AI
analysis of the Brigade Road store dimensions and typical retail occupancy
patterns. These are exposed as config parameters for per-store tuning.

### Transparency Note
AI assistance was used for research, validation, and documentation — not to
replace engineering judgment. Every decision above was reviewed, tested, and
owned by the engineer. The reasoning in CHOICES.md reflects genuine trade-off
analysis, not AI-generated boilerplate.
