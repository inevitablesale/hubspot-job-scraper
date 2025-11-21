import asyncio
import os
import threading
import subprocess
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI(title="HubSpot Job Scraper Control")


@app.on_event("startup")
async def startup_event():
    app.state.loop = asyncio.get_event_loop()
    app.state.log_queue: asyncio.Queue[str] = asyncio.Queue()
    app.state.proc: Optional[subprocess.Popen] = None
    app.state.run_id = 0


def _enqueue_output(proc: subprocess.Popen, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
    assert proc.stdout is not None
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        asyncio.run_coroutine_threadsafe(queue.put(line), loop)
    asyncio.run_coroutine_threadsafe(queue.put("[crawler] process ended"), loop)


@app.post("/run")
async def trigger_run():
    if app.state.proc and app.state.proc.poll() is None:
        raise HTTPException(status_code=409, detail="Crawler already running")

    app.state.run_id += 1
    queue: asyncio.Queue = app.state.log_queue
    while not queue.empty():
        queue.get_nowait()

    env = os.environ.copy()
    env.setdefault("SCRAPY_SETTINGS_MODULE", "scrapy_project.settings")
    proc = subprocess.Popen(
        ["python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    app.state.proc = proc

    threading.Thread(
        target=_enqueue_output,
        args=(proc, app.state.loop, queue),
        daemon=True,
    ).start()

    return {"status": "started", "run_id": app.state.run_id}


@app.get("/status")
async def status():
    running = app.state.proc is not None and app.state.proc.poll() is None
    return {"running": running, "run_id": app.state.run_id}


@app.get("/events")
async def stream_events():
    async def event_generator():
        queue: asyncio.Queue = app.state.log_queue
        while True:
            line = await queue.get()
            yield f"data: {line}\n\n"
            queue.task_done()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/")
async def index():
    html = """
    <!doctype html>
    <html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <title>HubSpot Job Scraper</title>
        <style>
            body { font-family: system-ui, sans-serif; margin: 2rem; }
            button { padding: 0.6rem 1rem; font-size: 1rem; }
            #log { white-space: pre-wrap; background: #0b1021; color: #f1f3f7; padding: 1rem; border-radius: 8px; height: 400px; overflow-y: auto; }
        </style>
    </head>
    <body>
        <h1>HubSpot Job Scraper</h1>
        <p>Trigger a crawl and watch stdout in real time.</p>
        <button id=\"run\">Start Crawl</button>
        <span id=\"status\"></span>
        <h2>Live Log</h2>
        <div id=\"log\"></div>
        <script>
            const logEl = document.getElementById('log');
            const statusEl = document.getElementById('status');
            document.getElementById('run').onclick = async () => {
                statusEl.textContent = ' starting...';
                const res = await fetch('/run', {method: 'POST'});
                if (res.ok) {
                    const data = await res.json();
                    statusEl.textContent = ` run ${data.run_id} started`;
                } else {
                    const err = await res.json();
                    statusEl.textContent = ` ${err.detail || 'failed'}`;
                }
            };
            const evt = new EventSource('/events');
            evt.onmessage = (e) => {
                logEl.textContent += e.data + '\n';
                logEl.scrollTop = logEl.scrollHeight;
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.head("/")
async def index_head():
    """Lightweight response for platform health checks that send HEAD requests."""
    return HTMLResponse(content="", status_code=200)


@app.get("/health")
async def health():
    """Simple health endpoint for uptime checks."""
    return {"status": "ok"}
