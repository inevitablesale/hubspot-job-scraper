import asyncio
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from playwright_crawler.runner import run_all, run_maps_radar, run_domain_cleanup
from playwright_crawler.state import DEFAULT_SETTINGS, get_registry, get_state, get_settings

app = FastAPI(title="HubSpot Job Hunter (Playwright)")

STATIC_DIR = "static"
BACKEND_VERSION = os.getenv("BACKEND_VERSION", "2025.11.21.1")

if os.path.exists(os.path.join(STATIC_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")


@app.on_event("startup")
async def startup():
    app.state.running_task: Optional[asyncio.Task] = None
    app.state.state = get_state()
    app.state.registry = get_registry()
    app.state.settings = get_settings()


@app.post("/run")
async def trigger_run():
    state = app.state.state
    if app.state.running_task and not app.state.running_task.done():
        raise HTTPException(status_code=409, detail="Crawler already running")

    async def _runner():
        try:
            await run_all()
        finally:
            pass

    state.add_log("INFO", "Run triggered via API")
    app.state.running_task = asyncio.create_task(_runner())
    return {"status": "started"}


@app.post("/run/maps")
async def trigger_maps_run(body: dict = None):
    body = body or {}
    queries = body.get("queries")
    limit = body.get("limit", 50)
    if app.state.running_task and not app.state.running_task.done():
        raise HTTPException(status_code=409, detail="Crawler already running")

    async def _runner():
        await run_maps_radar(queries=queries, limit=limit)

    app.state.state.add_log("INFO", "Maps radar triggered via API")
    app.state.running_task = asyncio.create_task(_runner())
    return {"status": "started", "mode": "maps"}


@app.post("/run/full")
async def trigger_full(body: dict = None):
    body = body or {}
    headless = body.get("headless", True)
    state = app.state.state
    if app.state.running_task and not app.state.running_task.done():
        raise HTTPException(status_code=409, detail="Crawler already running")

    async def _runner():
        await run_maps_radar(queries=body.get("queries"), limit=body.get("limit", 50), headless=headless)
        await run_all(headless=headless)

    state.add_log("INFO", "Full sweep (maps + jobs) triggered via API")
    app.state.running_task = asyncio.create_task(_runner())
    return {"status": "started", "mode": "full"}


@app.post("/stop")
async def stop_run():
    if not app.state.running_task or app.state.running_task.done():
        raise HTTPException(status_code=409, detail="No run in progress")
    app.state.running_task.cancel()
    return {"status": "cancelling"}


@app.get("/status")
async def status():
    state = app.state.state
    snapshot = state.snapshot()
    snapshot["coverage"] = state.coverage()
    return snapshot


@app.get("/state")
async def live_state():
    state = app.state.state
    registry = app.state.registry
    settings = app.state.settings
    return {
        "snapshot": state.snapshot(),
        "coverage": state.coverage(),
        "domains": registry.stats(),
        "history": state.history,
        "settings": settings.snapshot(),
    }


@app.get("/domains")
async def list_domains():
    registry = app.state.registry
    return {"domains": registry.get_all(), "stats": registry.stats()}


@app.get("/domains/changes")
async def domain_changes(hours: int = 24):
    registry = app.state.registry
    return registry.get_changes(hours=hours)


@app.delete("/domains/{domain}")
async def delete_domain(domain: str):
    registry = app.state.registry
    await registry.remove(domain)
    return {"ok": True, "domains": registry.get_all()}


@app.get("/schema")
async def schema():
    return {
        "modules": {
            "jobs": {"enabled": True, "route": "/run"},
            "maps": {"enabled": True, "route": "/run/maps"},
            "full": {"enabled": True, "route": "/run/full"},
        },
        "state": {
            "statusRoute": "/status",
            "stateRoute": "/state",
            "resultsRoute": "/results",
            "logsRoute": "/logs",
            "logStream": "/logs/stream",
            "domainRoute": "/domains",
        },
        "config": {
            "scoring": {"path": "/settings", "fields": list(DEFAULT_SETTINGS.keys())},
            "maps": {"path": "/run/maps", "fields": ["queries", "limit"]},
        },
        "version": {"route": "/version"},
    }


@app.get("/results")
async def results():
    state = app.state.state
    return {"jobs": state.results(), "coverage": state.coverage()}


@app.get("/settings")
async def settings():
    return get_settings().snapshot()


@app.post("/settings/update")
async def update_settings(payload: dict):
    settings_store = get_settings()
    settings_store.update(payload or {})
    return settings_store.snapshot()


@app.get("/logs")
async def logs():
    state = app.state.state
    return {"logs": state.recent_logs()}


@app.get("/logs/stream")
async def stream_logs():
    state = app.state.state
    queue = await state.log_broker.register()

    async def event_stream():
        try:
            for log in state.recent_logs():
                yield f"data: {json.dumps(log)}\n\n"
            while True:
                msg = await queue.get()
                yield f"data: {json.dumps(msg)}\n\n"
        finally:
            await state.log_broker.unregister(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z"}


@app.get("/version")
async def version():
    frontend = os.getenv("FRONTEND_VERSION", BACKEND_VERSION)
    return {"backendVersion": BACKEND_VERSION, "frontendVersion": frontend}


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    state = app.state.state
    queue = await state.log_broker.register()
    # send backlog
    for log in state.recent_logs():
        await websocket.send_json(log)
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        await state.log_broker.unregister(queue)
    except Exception:
        await state.log_broker.unregister(queue)


@app.get("/")
@app.head("/")
async def serve_index():
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"error": "Frontend not built"}


@app.get("/{full_path:path}")
async def react_app(full_path: str):
    index = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"error": "Frontend not built"}
