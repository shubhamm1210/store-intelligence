# main.py — FastAPI application
# Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.metrics   import router as metrics_router
from routes.funnel    import router as funnel_router
from routes.anomalies import router as anomalies_router
from routes.zones     import router as zones_router

app = FastAPI(
    title="Store Intelligence API",
    description="Real-time analytics from CCTV-based person detection pipeline",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dashboard on same docker network
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metrics_router,   tags=["Metrics"])
app.include_router(funnel_router,    tags=["Funnel"])
app.include_router(anomalies_router, tags=["Anomalies"])
app.include_router(zones_router,     tags=["Zones"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "service": "Store Intelligence API",
        "docs":    "/docs",
        "endpoints": ["/metrics", "/funnel", "/anomalies", "/zones/heatmap", "/health"],
    }
