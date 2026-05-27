"""
api/server.py — GeoRisk Oracle FastAPI dashboard backend

Routes:
  GET /                    → dashboard HTML
  GET /api/status          → monitor status (last scan, next scan, models)
  GET /api/events?days=1   → recent analyzed events
  GET /api/alerts?days=7   → Telegram alerts sent
  GET /api/scans?days=1    → monitoring cycle history
  GET /api/insights        → latest Nemotron pattern analysis + outlook
  POST /api/scan           → trigger manual scan immediately
  POST /api/insight        → trigger manual insight generation
"""

import os
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from config.settings import get_settings

app = FastAPI(title="GeoRisk Oracle", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

settings = get_settings()

# Shared state (updated by watch loop in app.py)
monitor_state = {
    "running": False,
    "last_scan_at": None,
    "next_scan_at": None,
    "interval_minutes": int(os.getenv("WATCH_INTERVAL", "30")),
    "total_events_today": 0,
    "total_alerts_today": 0,
    "nim_model": settings.nim_model,
    "llama_model": settings.llama_model,
    "started_at": None,
}


def _serialize(obj):
    """Convert Firestore Timestamps and datetimes to ISO strings."""
    if obj is None:
        return None
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "_seconds"):          # Firestore Timestamp
        return datetime.fromtimestamp(obj._seconds, tz=timezone.utc).isoformat()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/status")
async def status():
    return JSONResponse(_serialize(monitor_state))


@app.get("/api/events")
async def events(days: int = 1, limit: int = 50):
    try:
        from db.firestore import get_events
        data = get_events(since_days=days, limit=limit)
        return JSONResponse({"events": _serialize(data), "count": len(data)})
    except Exception as e:
        return JSONResponse({"error": str(e), "events": []}, status_code=500)


@app.get("/api/alerts")
async def alerts(days: int = 7):
    try:
        from db.firestore import get_alerts
        data = get_alerts(since_days=days)
        return JSONResponse({"alerts": _serialize(data), "count": len(data)})
    except Exception as e:
        return JSONResponse({"error": str(e), "alerts": []}, status_code=500)


@app.get("/api/scans")
async def scans(days: int = 1):
    try:
        from db.firestore import get_scans, get_last_scan
        data = get_scans(since_days=days)
        last = get_last_scan()
        return JSONResponse({"scans": _serialize(data), "last_scan": _serialize(last)})
    except Exception as e:
        return JSONResponse({"error": str(e), "scans": []}, status_code=500)


@app.get("/api/insights")
async def insights(period: str = "weekly"):
    try:
        from db.firestore import get_latest_insight
        data = get_latest_insight(period=period)
        return JSONResponse(_serialize(data) or {"content": "No insights generated yet."})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/scan")
async def trigger_scan():
    """Trigger an immediate scan cycle."""
    try:
        import threading
        from app import run_one_cycle
        t = threading.Thread(target=run_one_cycle, daemon=True)
        t.start()
        return JSONResponse({"status": "scan triggered"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/insight")
async def trigger_insight():
    """Trigger immediate insight generation."""
    try:
        from agents.insight_agent import InsightAgent
        agent = InsightAgent(verbose=True)
        text = agent.generate(since_days=7, period="weekly")
        return JSONResponse({"status": "generated", "preview": text[:300]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
