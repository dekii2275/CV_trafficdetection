import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.path.join(ROOT, "data")
RUNTIME_DIR = os.path.join(DATA_DIR, "runtime")
STATS_FILE = os.path.join(RUNTIME_DIR, "stats.json")

app = FastAPI(title="Traffic Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/stats")
def get_stats():
    if not os.path.exists(STATS_FILE):
        return JSONResponse({"timestamp": None, "fps": 0, "counts": {}, "total": 0})
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return JSONResponse(json.load(f))
    except Exception:
        return JSONResponse({"timestamp": None, "fps": 0, "counts": {}, "total": 0})


@app.get("/api/video")
def get_video():
    # Trả về file video input cho UI phát
    cfg_video = os.path.join(DATA_DIR, "input.webm")
    fallback_mp4 = os.path.join(DATA_DIR, "input.mp4")
    if os.path.exists(cfg_video):
        return FileResponse(cfg_video, media_type="video/webm")
    if os.path.exists(fallback_mp4):
        return FileResponse(fallback_mp4, media_type="video/mp4")
    return JSONResponse({"error": "No input video found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


