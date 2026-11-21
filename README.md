# Store Intelligence System

AI-powered retail analytics platform built for the **Purplle Tech Challenge 2026**.

The system processes retail CCTV footage and generates footfall, dwell-time, zone-traffic, conversion-funnel, and anomaly analytics. The current implementation processes a video source frame by frame; the analytics dashboard refreshes from the API.

## Features

### Computer vision pipeline
- YOLOv8 person detection
- ByteTrack multi-object tracking
- Configurable entry/exit counting line
- Zone mapping and dwell-time tracking
- Crowd, queue, and loitering anomaly events

### Analytics API
- Footfall and occupancy metrics
- Four-stage conversion funnel
- Zone traffic and dwell-time summaries
- Anomaly summaries and filtered event retrieval
- FastAPI OpenAPI/Swagger documentation

### Dashboard
- KPI monitoring
- Conversion-funnel visualization
- Zone-level analytics
- Anomaly alerts

## Architecture

```text
CCTV video
    ↓
YOLOv8 person detection + ByteTrack tracking
    ↓
PersonCounter + zone mapping
    ↓
Structured events
    ↓
SQLite event store
    ↓
FastAPI analytics endpoints
    ↓
Streamlit dashboard
```

## Repository structure

```text
store-intelligence/
├── api/
│   ├── Dockerfile
│   ├── routes/
│   ├── database.py
│   └── main.py
├── dashboard/
│   ├── Dockerfile
│   └── app.py
├── pipeline/
│   ├── Dockerfile
│   ├── config.py
│   ├── counter.py
│   ├── detector.py
│   ├── event_store.py
│   └── zone_mapper.py
├── .github/workflows/
├── CHOICES.md
├── DESIGN.md
└── docker-compose.yml
```

## API endpoints

| Endpoint | Purpose |
|---|---|
| `/health` | Service health check |
| `/metrics` | Store KPIs and analytics |
| `/funnel` | Entry, browsing, billing, and conversion stages |
| `/zones/heatmap` | Zone traffic and dwell-time analysis |
| `/anomalies` | Crowd, queue, and loitering events |
| `/docs` | Interactive Swagger documentation |

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/shubhamm1210/store-intelligence.git
cd store-intelligence
```

### 2. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install pipeline dependencies

```bash
pip install -r pipeline/requirements.txt
```

The detector loads the model specified by `MODEL_NAME` in `pipeline/config.py`. If the model file is not present, Ultralytics can download the named pretrained weight on first use when network access is available. For offline execution, provide the model file locally.

### 4. Run the video pipeline

```bash
cd pipeline
python detector.py --source "path/to/video.mp4" --max-frames 200
```

Use `--no-video` to skip writing the annotated output.

### 5. Run the API

In a separate terminal:

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for interactive API documentation.

### 6. Run the dashboard

In another terminal:

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

Dashboard: `http://localhost:8501`.

## Docker Compose

The repository includes separate Docker build configurations for the pipeline, API, and dashboard. The pipeline and API use a shared named volume for SQLite.

Place your video at `video/input.mp4`, then run:

```bash
docker compose up --build -d api dashboard
docker compose run --rm pipeline
```

The API is available at `http://localhost:8000/docs` and the dashboard at `http://localhost:8501`.

## Tests

The counter tests use fake bounding-box tracks and mock event/database side effects. The funnel tests run the actual SQL against a temporary in-memory SQLite database. Neither test suite needs CCTV footage or pretrained model weights.

```bash
python -m pip install -r api/requirements.txt
python -m pip install -r api/requirements-dev.txt pipeline/requirements-dev.txt
python -m pytest -q pipeline/tests api/tests
```

GitHub Actions runs these checks on pushes and pull requests.

## Funnel semantics and validation status

The current funnel counts **distinct tracker IDs** at each stage and caps later stages so they cannot exceed the preceding stage. This avoids repeated zone events inflating a track's count, but it is not a visit/session-level funnel: if a tracker ID represents multiple visits, those visits are currently merged.

Performance benchmarks and POS transaction-alignment figures are not published yet. They require representative CCTV footage, the corresponding POS export, and a specified test machine. No FPS, latency, or conversion-accuracy number is assumed here.

## Screenshots

### Detection pipeline
![Detection pipeline](https://github.com/user-attachments/assets/fb2171b3-6a2b-4fa9-9879-3f33807bdbab)

### Dashboard
![Dashboard](https://github.com/user-attachments/assets/29b9e538-b6e8-40d7-88e8-c0cd540eb1f1)

### Swagger API documentation
![Swagger API documentation](https://github.com/user-attachments/assets/b8f5b806-483d-410d-9dda-16ae32ffe715)

## Scope and limitations

- The current configuration targets a single fixed camera view.
- Staff are not classified separately.
- Conversion is a behavioral proxy based on reaching the cash-counter zone and exiting; it is not a verified POS transaction.
- Counting-line position and zone boundaries must be tuned for a different camera angle.

See [DESIGN.md](DESIGN.md) and [CHOICES.md](CHOICES.md) for architectural decisions and trade-offs.

## Author

**Shubham Kumar** · [GitHub](https://github.com/shubhamm1210) · [LinkedIn](https://www.linkedin.com/in/shubhamkumar1210/)
