import asyncio
import json
import logging
import os
import threading
import subprocess
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scraper_engine import JobScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="HubSpot Job Scraper Control")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    """Request model for /scrape/stream endpoint"""
    domains: List[str]


async def stream_scrape(domains: List[str]):
    """
    Stream scraping results in real-time using asyncio.as_completed.
    Each domain result is yielded as soon as it completes.
    
    Args:
        domains: List of domain URLs to scrape
        
    Yields:
        SSE-formatted messages with domain scraping results
    """
    scraper = JobScraper()
    
    try:
        # Initialize browser once for all domains
        await scraper.initialize()
        
        # Create tasks for all domains
        tasks = []
        for domain_url in domains:
            # Extract company name from domain
            company_name = domain_url.replace('https://', '').replace('http://', '').split('/')[0]
            task = asyncio.create_task(scrape_domain_wrapper(scraper, domain_url, company_name))
            tasks.append(task)
        
        # Stream results as they complete
        for finished_task in asyncio.as_completed(tasks):
            try:
                result = await finished_task
                logger.info("[STREAM] Finished %s", result['domain'])
                yield f"data: {json.dumps(result)}\n\n"
            except Exception as e:
                logger.error("[STREAM] Error processing domain: %s", e)
                error_result = {
                    "domain": "unknown",
                    "status": "error",
                    "error": str(e),
                    "jobs": []
                }
                yield f"data: {json.dumps(error_result)}\n\n"
    
    finally:
        # Clean up browser
        await scraper.shutdown()


async def scrape_domain_wrapper(scraper: JobScraper, domain_url: str, company_name: str) -> dict:
    """
    Wrapper function to scrape a single domain and return formatted result.
    
    Args:
        scraper: Initialized JobScraper instance
        domain_url: Domain URL to scrape
        company_name: Company name
        
    Returns:
        Dictionary with domain, status, and jobs
    """
    try:
        jobs = await scraper.scrape_domain(domain_url, company_name)
        return {
            "domain": domain_url,
            "status": "success",
            "jobs": jobs
        }
    except Exception as e:
        logger.error("Error scraping %s: %s", domain_url, e)
        return {
            "domain": domain_url,
            "status": "error",
            "error": str(e),
            "jobs": []
        }


@app.post("/scrape/stream")
async def scrape_stream_endpoint(request: ScrapeRequest):
    """
    SSE endpoint that streams scraping results in real-time.
    
    Accepts a list of domains and streams each result as soon as it completes,
    enabling parallel scraping without waiting for the full batch.
    
    Returns:
        StreamingResponse with text/event-stream content type
    """
    logger.info("Starting streaming scrape for %d domains", len(request.domains))
    return StreamingResponse(
        stream_scrape(request.domains),
        media_type="text/event-stream"
    )


@app.on_event("startup")
async def startup_event():
    app.state.loop = asyncio.get_event_loop()
    app.state.log_queue: asyncio.Queue[str] = asyncio.Queue()
    app.state.proc: Optional[subprocess.Popen] = None
    app.state.run_id = 0
    app.state.started_at: Optional[str] = None
    app.state.last_event_at: Optional[str] = None


def _enqueue_output(
    proc: subprocess.Popen,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue,
    state,
):
    assert proc.stdout is not None
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        state.last_event_at = datetime.utcnow().isoformat() + "Z"
        asyncio.run_coroutine_threadsafe(queue.put(line), loop)
    state.last_event_at = datetime.utcnow().isoformat() + "Z"
    asyncio.run_coroutine_threadsafe(queue.put("[crawler] process ended"), loop)


@app.post("/run")
async def trigger_run():
    if app.state.proc and app.state.proc.poll() is None:
        raise HTTPException(status_code=409, detail="Crawler already running")

    app.state.run_id += 1
    queue: asyncio.Queue = app.state.log_queue
    while not queue.empty():
        queue.get_nowait()

    app.state.started_at = datetime.utcnow().isoformat() + "Z"
    app.state.last_event_at = None

    env = os.environ.copy()
    proc = subprocess.Popen(
        ["python", "run_spider.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    app.state.proc = proc

    threading.Thread(
        target=_enqueue_output,
        args=(proc, app.state.loop, queue, app.state),
        daemon=True,
    ).start()

    return {"status": "started", "run_id": app.state.run_id}


@app.get("/status")
async def status():
    running = app.state.proc is not None and app.state.proc.poll() is None
    return {
        "running": running,
        "run_id": app.state.run_id,
        "started_at": app.state.started_at,
        "last_event_at": app.state.last_event_at,
    }


@app.get("/events")
async def stream_events():
    async def event_generator():
        queue: asyncio.Queue = app.state.log_queue
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=20)
                yield f"data: {line}\n\n"
                queue.task_done()
            except asyncio.TimeoutError:
                yield "data: [heartbeat]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/")
async def index():
    html = """
    <!doctype html>
    <html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <title>HubSpot Job Scraper</title>
        <script src=\"https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js\"></script>
        <style>
            :root {
                color-scheme: dark light;
            }
            * { box-sizing: border-box; }
            body {
                font-family: "Inter", "SF Pro Text", system-ui, -apple-system, sans-serif;
                margin: 0;
                min-height: 100vh;
                background: radial-gradient(circle at 20% 20%, #f59e0b22, transparent 25%),
                            radial-gradient(circle at 80% 0%, #6366f122, transparent 25%),
                            #0f172a;
                color: #e2e8f0;
            }
            header {
                padding: 32px clamp(24px, 3vw, 48px) 8px;
            }
            .wrap {
                padding: 0 clamp(24px, 3vw, 48px) 48px;
            }
            h1 { margin: 0; font-size: clamp(28px, 4vw, 40px); }
            p.lead { margin: 12px 0 0; color: #cbd5e1; }
            .panel {
                background: rgba(15, 23, 42, 0.8);
                border: 1px solid #1f2937;
                box-shadow: 0 25px 80px rgba(0,0,0,0.25);
                border-radius: 18px;
                padding: clamp(18px, 3vw, 24px);
                backdrop-filter: blur(10px);
            }
            .controls {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
                margin-top: 16px;
            }
            button.primary {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 12px 16px;
                font-weight: 600;
                font-size: 16px;
                border-radius: 12px;
                border: none;
                cursor: pointer;
                background: linear-gradient(90deg, #f59e0b, #f97316);
                color: #0f172a;
                box-shadow: 0 10px 30px rgba(249, 115, 22, 0.35);
                transition: transform 120ms ease, box-shadow 120ms ease, opacity 120ms ease;
            }
            button.primary:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                box-shadow: none;
            }
            button.primary:hover:not(:disabled) {
                transform: translateY(-1px);
                box-shadow: 0 14px 40px rgba(249, 115, 22, 0.45);
            }
            .status-pill {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 8px 12px;
                border-radius: 999px;
                background: rgba(99, 102, 241, 0.15);
                color: #c7d2fe;
                border: 1px solid rgba(99, 102, 241, 0.25);
                font-weight: 600;
            }
            .status-pill.running { background: rgba(52, 211, 153, 0.15); border-color: rgba(52, 211, 153, 0.35); color: #bbf7d0; }
            .status-pill.idle { background: rgba(148, 163, 184, 0.12); border-color: rgba(148, 163, 184, 0.3); color: #e2e8f0; }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
                gap: 16px;
                margin-top: 18px;
            }
            .grid-visual {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 18px;
                margin-top: 18px;
            }
            .card {
                padding: 14px 16px;
                border-radius: 14px;
                border: 1px solid #1f2937;
                background: rgba(30, 41, 59, 0.7);
            }
            .card.hero {
                background: radial-gradient(circle at 10% 10%, rgba(99,102,241,0.16), transparent 45%),
                            radial-gradient(circle at 90% 10%, rgba(56,189,248,0.18), transparent 45%),
                            rgba(15,23,42,0.9);
                border-color: rgba(99,102,241,0.35);
                box-shadow: 0 25px 90px rgba(56,189,248,0.12);
                min-height: 240px;
            }
            .metric { color: #cbd5e1; font-size: 14px; margin: 0 0 6px; }
            .value { font-size: 22px; font-weight: 700; margin: 0; color: #f8fafc; }
            .log-shell {
                margin-top: 18px;
                border-radius: 16px;
                background: #0b1021;
                border: 1px solid #111827;
                overflow: hidden;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
            }
            .log-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                color: #cbd5e1;
                background: linear-gradient(90deg, #111827, #0f172a);
                font-weight: 600;
            }
            #log {
                white-space: pre-wrap;
                color: #e2e8f0;
                padding: 16px;
                height: 420px;
                overflow-y: auto;
                font-family: "SFMono-Regular", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                font-size: 13px;
                line-height: 1.45;
            }
            #chart {
                width: 100%;
                height: 260px;
            }
            .chart-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 10px;
                color: #e2e8f0;
                font-weight: 600;
            }
            .line.error { color: #fca5a5; }
            .line.warn { color: #fbbf24; }
            .pulse {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: #22d3ee;
                position: relative;
                box-shadow: 0 0 0 rgba(34, 211, 238, 0.4);
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.35); }
                70% { box-shadow: 0 0 0 12px rgba(34, 211, 238, 0); }
                100% { box-shadow: 0 0 0 0 rgba(34, 211, 238, 0); }
            }
            .pill-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
            .chip { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; padding: 6px 10px; border-radius: 999px; font-size: 12px; }
            a { color: #38bdf8; }
        </style>
    </head>
    <body>
        <header>
            <div class=\"pill-row\">
                <div class=\"status-pill idle\" id=\"status-pill\"><span class=\"pulse\"></span><span id=\"status-label\">Idle</span></div>
                <span class=\"chip\">Live control room</span>
            </div>
            <h1>HubSpot Job Scraper</h1>
            <p class=\"lead\">Launch a crawl, track status, and watch events stream in real time.</p>
            <div class=\"controls\">
                <button class=\"primary\" id=\"run\">🚀 Start Crawl</button>
                <span id=\"status\">Ready</span>
            </div>
        </header>
        <div class=\"wrap\">
            <div class=\"panel\">
                <div class=\"grid\">
                    <div class=\"card\">
                        <p class=\"metric\">Run ID</p>
                        <p class=\"value\" id=\"run-id\">—</p>
                    </div>
                    <div class=\"card\">
                        <p class=\"metric\">Started</p>
                        <p class=\"value\" id=\"started-at\">—</p>
                    </div>
                    <div class=\"card\">
                        <p class=\"metric\">Last Event</p>
                        <p class=\"value\" id=\"last-event\">—</p>
                    </div>
                    <div class=\"card\">
                        <p class=\"metric\">Lines Streamed</p>
                        <p class=\"value\" id=\"line-count\">0</p>
                    </div>
                </div>
                <div class=\"grid-visual\">
                    <div class=\"card hero\">
                        <div class=\"chart-header\">
                            <span>Live Pulse</span>
                            <span style=\"font-size:12px; color:#94a3b8;\">ECharts real-time stream</span>
                        </div>
                        <div id=\"chart\"></div>
                    </div>
                    <div class=\"card\">
                        <p class=\"metric\">Interactive ideas</p>
                        <p class=\"value\" style=\"font-size:14px; font-weight:600; color:#cbd5e1; line-height:1.6;\">
                            • Animated pulse chart of log volume<br/>
                            • Color-coded live console<br/>
                            • Status pills that reflect crawler state in real time
                        </p>
                    </div>
                </div>
                <div class=\"log-shell\">
                    <div class=\"log-header\">
                        <span>Live Log</span>
                        <span id=\"sse-status\">Connecting…</span>
                    </div>
                    <div id=\"log\"></div>
                </div>
            </div>
        </div>
        <script>
            const logEl = document.getElementById('log');
            const statusEl = document.getElementById('status');
            const runBtn = document.getElementById('run');
            const statusLabel = document.getElementById('status-label');
            const statusPill = document.getElementById('status-pill');
            const runIdEl = document.getElementById('run-id');
            const startedEl = document.getElementById('started-at');
            const lastEventEl = document.getElementById('last-event');
            const lineCountEl = document.getElementById('line-count');
            const sseStatusEl = document.getElementById('sse-status');
            const chartEl = document.getElementById('chart');
            let lineCount = 0;
            let chart;
            let chartData = [];

            function initChart() {
                if (!chartEl || typeof echarts === 'undefined') return;
                chart = echarts.init(chartEl, null, { renderer: 'canvas' });
                chart.setOption({
                    animation: true,
                    textStyle: { color: '#e2e8f0' },
                    grid: { left: 10, right: 10, top: 20, bottom: 25, containLabel: true },
                    xAxis: {
                        type: 'category',
                        boundaryGap: false,
                        data: [],
                        axisLine: { lineStyle: { color: '#334155' } },
                        axisLabel: { color: '#cbd5e1' },
                    },
                    yAxis: {
                        type: 'value',
                        name: 'Lines',
                        axisLine: { lineStyle: { color: '#334155' } },
                        splitLine: { lineStyle: { color: 'rgba(148,163,184,0.2)' } },
                        axisLabel: { color: '#cbd5e1' },
                    },
                    series: [
                        {
                            name: 'Lines streamed',
                            type: 'line',
                            smooth: true,
                            showSymbol: false,
                            data: [],
                            areaStyle: {
                                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                    { offset: 0, color: 'rgba(56,189,248,0.55)' },
                                    { offset: 1, color: 'rgba(56,189,248,0.05)' },
                                ]),
                            },
                            lineStyle: { color: '#22d3ee', width: 3 },
                        },
                    ],
                    tooltip: { trigger: 'axis' },
                });
            }

            function updateChart() {
                if (!chart) return;
                const labels = chartData.map(d => d.label);
                const values = chartData.map(d => d.value);
                chart.setOption({
                    xAxis: { data: labels },
                    series: [{ data: values }],
                });
            }

            function setRunningState(running) {
                if (running) {
                    statusLabel.textContent = 'Running';
                    statusPill.classList.add('running');
                    statusPill.classList.remove('idle');
                    runBtn.disabled = true;
                } else {
                    statusLabel.textContent = 'Idle';
                    statusPill.classList.add('idle');
                    statusPill.classList.remove('running');
                    runBtn.disabled = false;
                }
            }

            function classify(line) {
                const lower = line.toLowerCase();
                if (lower.includes('error')) return 'error';
                if (lower.includes('warn')) return 'warn';
                return '';
            }

            function renderLine(line) {
                const div = document.createElement('div');
                div.className = 'line ' + classify(line);
                div.textContent = line;
                logEl.appendChild(div);
                lineCount += 1;
                lineCountEl.textContent = lineCount;
                logEl.scrollTop = logEl.scrollHeight;
                const now = new Date();
                chartData.push({ label: now.toLocaleTimeString(), value: lineCount });
                if (chartData.length > 50) chartData.shift();
                updateChart();
            }

            async function refreshStatus() {
                try {
                    const res = await fetch('/status');
                    if (!res.ok) throw new Error('status failed');
                    const data = await res.json();
                    setRunningState(data.running);
                    runIdEl.textContent = data.run_id ?? '—';
                    startedEl.textContent = data.started_at ?? '—';
                    lastEventEl.textContent = data.last_event_at ?? '—';
                    statusEl.textContent = data.running ? 'Crawler active' : 'Ready';
                } catch (err) {
                    statusEl.textContent = 'Status unavailable';
                }
            }

            runBtn.onclick = async () => {
                statusEl.textContent = 'Starting…';
                try {
                    const res = await fetch('/run', { method: 'POST' });
                    if (res.ok) {
                        const data = await res.json();
                        statusEl.textContent = `Run ${data.run_id} launched`;
                        runIdEl.textContent = data.run_id;
                        startedEl.textContent = new Date().toISOString();
                        setRunningState(true);
                    } else {
                        const err = await res.json();
                        statusEl.textContent = err.detail || 'Failed to start';
                    }
                } catch (err) {
                    statusEl.textContent = 'Network error while starting';
                }
            };

            function startStream() {
                const evt = new EventSource('/events');
                evt.onopen = () => { sseStatusEl.textContent = 'Live'; };
                evt.onerror = () => { sseStatusEl.textContent = 'Reconnecting…'; };
                evt.onmessage = (e) => {
                    if (e.data === '[heartbeat]') return;
                    renderLine(e.data);
                    refreshStatus();
                };
            }

            startStream();
            refreshStatus();
            setInterval(refreshStatus, 4000);
            initChart();
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
