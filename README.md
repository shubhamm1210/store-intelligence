# Store Intelligence System

AI-powered retail analytics platform built for the **Purplle Tech Challenge 2026**.

This system processes raw CCTV footage from retail stores and generates real-time business intelligence including footfall tracking, dwell-time analytics, zone heatmaps, conversion funnel metrics, and anomaly detection.

The project combines **Computer Vision**, **Real-Time Analytics**, **FastAPI**, and **Streamlit** into a modular production-style pipeline.

---

# Features

## Computer Vision Pipeline

* YOLOv8-based person detection
* Multi-object tracking
* Entry/exit monitoring
* Zone mapping and movement analysis
* Dwell time tracking

## Real-Time Analytics

* Footfall metrics
* Conversion funnel
* Zone popularity analysis
* Peak occupancy monitoring
* Revenue-oriented behavioral analytics

## API Layer

* FastAPI analytics backend
* Auto-generated OpenAPI/Swagger docs
* Structured JSON responses
* Modular route architecture

## Dashboard

* Live KPI monitoring
* Conversion funnel visualization
* Zone heatmap insights
* Anomaly alerts
* Real-time occupancy monitoring

---

# System Architecture

CCTV Footage
↓
YOLOv8 Person Detection
↓
Object Tracking + Zone Mapping
↓
Structured Event Generation
↓
SQLite Event Store
↓
FastAPI Analytics Engine
↓
Streamlit Dashboard

---

# Tech Stack

| Layer            | Technology     |
| ---------------- | -------------- |
| Detection        | YOLOv8         |
| Tracking         | ByteTrack      |
| Video Processing | OpenCV         |
| Backend API      | FastAPI        |
| Dashboard        | Streamlit      |
| Database         | SQLite         |
| Containerization | Docker Compose |

---

# Project Structure

```text
store-intelligence/
├── api/
│   ├── routes/
│   ├── main.py
│   └── database.py
│
├── dashboard/
│   └── app.py
│
├── pipeline/
│   ├── detector.py
│   ├── zone_mapper.py
│   ├── event_store.py
│   └── config.py
│
├── DESIGN.md
├── CHOICES.md
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

# API Endpoints

| Endpoint         | Description                   |
| ---------------- | ----------------------------- |
| `/metrics`       | Store KPIs and analytics      |
| `/funnel`        | Customer conversion funnel    |
| `/zones/heatmap` | Zone traffic analysis         |
| `/anomalies`     | Crowd and dwell anomalies     |
| `/docs`          | Swagger/OpenAPI documentation |

---

# Local Setup

## 1. Clone Repository

```bash
git clone <your-repository-url>
cd store-intelligence
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

---

# Run Detection Pipeline

```bash
cd pipeline
pip install -r requirements.txt

python detector.py --source "CAM 2.mp4" --max-frames 200
```

Generated outputs:

* `output.mp4`
* `events.db`

---

# Run FastAPI Backend

```bash
cd api
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Swagger/OpenAPI docs:

```text
http://localhost:8000/docs
```

---

# Run Dashboard

```bash
cd dashboard
pip install -r requirements.txt

streamlit run app.py
```

Dashboard:

```text
http://localhost:8501
```

---

# Screenshots

## Detection Pipeline
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/fb2171b3-6a2b-4fa9-9879-3f33807bdbab" />



## Dashboard
<img width="1920" height="1080" alt="Screenshot (809)" src="https://github.com/user-attachments/assets/29b9e538-b6e8-40d7-88e8-c0cd540eb1f1" />


## Swagger API Documentation
<img width="1920" height="1080" alt="Screenshot (813)" src="https://github.com/user-attachments/assets/b8f5b806-483d-410d-9dda-16ae32ffe715" />



---

# Engineering Decisions

* **YOLOv8n** chosen for lightweight real-time inference.
* **SQLite** selected for simplicity and reduced operational overhead.
* **FastAPI** used for high-performance APIs and automatic Swagger documentation.
* **Streamlit** used for rapid dashboard prototyping and visualization.
* Modular architecture used for separation of concerns and scalability.

Detailed technical reasoning is available in:

* `DESIGN.md`
* `CHOICES.md`

---

# Notes

* Dataset and CCTV footage are excluded from repository as per challenge guidelines.
* System outputs dynamically vary based on video input.
* Built during the Purplle Tech Challenge 2026.

---

# Future Improvements

* Multi-camera identity re-identification
* GPU acceleration
* Kafka/Redis event streaming
* Advanced behavioral analytics
* Cloud-native deployment

---

# Author

Shubham Kumar
Purplle Tech Challenge 2026
