import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from playwright_crawler.runner import run_all

app = FastAPI(title="HubSpot Job Hunter (Playwright)")


@app.on_event("startup")
async def startup():
    app.state.running = False
    app.state.last_run: Optional[str] = None


@app.post("/run")
async def trigger_run():
    if app.state.running:
        raise HTTPException(status_code=409, detail="Crawler already running")

    app.state.running = True
    app.state.last_run = datetime.utcnow().isoformat() + "Z"

    async def _runner():
        try:
            await run_all()
        finally:
            app.state.running = False

    asyncio.create_task(_runner())
    return {"status": "started"}


@app.get("/status")
async def status():
    return {"running": app.state.running, "last_run": app.state.last_run}


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <head><title>HubSpot Job Hunter</title></head>
        <body style='font-family: sans-serif;'>
            <h1>HubSpot Job Hunter (Playwright)</h1>
            <p>POST to <code>/run</code> to start a crawl. Check <code>/status</code> for progress.</p>
        </body>
    </html>
    """
