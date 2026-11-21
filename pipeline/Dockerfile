FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Keep model weights in the image rather than the Git repository.
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

CMD ["python", "detector.py"]
