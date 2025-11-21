import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from playwright_crawler.runner import run_all
from playwright_crawler.state import get_state

app = FastAPI(title="HubSpot Job Hunter (Playwright)")


@app.on_event("startup")
async def startup():
    app.state.running_task: Optional[asyncio.Task] = None
    app.state.state = get_state()


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


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <head><title>HubSpot Job Hunter</title></head>
        <body style='font-family: sans-serif;'>
            <h1>HubSpot Job Hunter (Playwright)</h1>
            <p>POST to <code>/run</code> to start a crawl. Check <code>/status</code> for progress.</p>
            <p>Live logs available at <code>/ws/logs</code>. Results at <code>/results</code>.</p>
        </body>
    </html>
    """
