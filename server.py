import asyncio
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from playwright_crawler.runner import run_all, run_maps_radar, run_domain_cleanup
from playwright_crawler.state import get_registry, get_state

app = FastAPI(title="HubSpot Job Hunter (Playwright)")

STATIC_DIR = "static"

if os.path.exists(os.path.join(STATIC_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")


@app.on_event("startup")
async def startup():
    app.state.running_task: Optional[asyncio.Task] = None
    app.state.state = get_state()
    app.state.registry = get_registry()


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


@app.get("/results")
async def results():
    state = app.state.state
    return {"jobs": state.results(), "coverage": state.coverage()}


@app.get("/logs")
async def logs():
    state = app.state.state
    return {"logs": state.recent_logs()}


@app.get("/health")
async def health():
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z"}


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
