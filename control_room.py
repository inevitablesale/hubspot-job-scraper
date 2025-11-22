"""
Enhanced FastAPI server for HubSpot Job Scraper Control Room.

Provides a modern UI and API endpoints for triggering and monitoring crawls.
"""

import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from logging_config import setup_logging, get_logger
from main import run_scraper, get_domains_file

# Setup logging
logger = setup_logging("control_room")

app = FastAPI(title="HubSpot Job Scraper Control Room")


class CrawlerState(str, Enum):
    """Crawler state enum."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class CrawlStatus:
    """Global crawl status manager."""
    
    def __init__(self):
        self.state: CrawlerState = CrawlerState.IDLE
        self.last_run_started_at: Optional[str] = None
        self.last_run_finished_at: Optional[str] = None
        self.domains_total: int = 0
        self.domains_processed: int = 0
        self.jobs_found: int = 0
        self.last_error: Optional[str] = None
        self.recent_jobs: List[Dict] = []
        self.log_buffer: deque = deque(maxlen=500)  # Keep last 500 log lines
    
    def reset_run(self):
        """Reset run-specific metrics."""
        self.domains_processed = 0
        self.jobs_found = 0
        self.last_error = None
        self.recent_jobs = []
    
    def to_dict(self) -> Dict:
        """Convert status to dictionary."""
        return {
            "state": self.state.value,
            "last_run_started_at": self.last_run_started_at,
            "last_run_finished_at": self.last_run_finished_at,
            "domains_total": self.domains_total,
            "domains_processed": self.domains_processed,
            "jobs_found": self.jobs_found,
            "last_error": self.last_error
        }


# Global status instance
crawl_status = CrawlStatus()


class StartCrawlRequest(BaseModel):
    """Request model for starting a crawl."""
    role_filter: Optional[str] = None
    remote_only: Optional[bool] = None


class LogCaptureHandler(logging.Handler):
    """Custom log handler that captures logs to a buffer."""
    
    def __init__(self, buffer: deque):
        super().__init__()
        self.buffer = buffer
    
    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.buffer.append({
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": msg
            })
        except Exception:
            self.handleError(record)


# Install log capture handler
root_logger = logging.getLogger()
log_capture = LogCaptureHandler(crawl_status.log_buffer)
log_capture.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
root_logger.addHandler(log_capture)


async def run_scraper_background(role_filter: Optional[str] = None, remote_only: Optional[bool] = None):
    """
    Background task to run the scraper.
    
    Args:
        role_filter: Optional role filter (comma-separated)
        remote_only: Optional remote-only filter
    """
    try:
        # Update state
        crawl_status.state = CrawlerState.RUNNING
        crawl_status.last_run_started_at = datetime.utcnow().isoformat() + "Z"
        crawl_status.reset_run()
        
        # Apply filters if provided
        env_overrides = {}
        if role_filter:
            env_overrides['ROLE_FILTER'] = role_filter
        if remote_only is not None:
            env_overrides['REMOTE_ONLY'] = "true" if remote_only else "false"
        
        # Temporarily set env vars
        old_env = {}
        for key, value in env_overrides.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        logger.info(
            "🎮 Control room triggered crawl",
            extra={
                "role_filter": role_filter,
                "remote_only": remote_only,
                "requested_by": "ui"
            }
        )
        
        try:
            # Get domains count
            domains_file = get_domains_file()
            from scraper_engine import load_domains
            domains = load_domains(domains_file)
            crawl_status.domains_total = len(domains)
            
            # Run scraper
            jobs = await run_scraper()
            
            # Update status
            crawl_status.jobs_found = len(jobs)
            crawl_status.recent_jobs = jobs[:50]  # Keep last 50
            crawl_status.state = CrawlerState.COMPLETED
            crawl_status.last_run_finished_at = datetime.utcnow().isoformat() + "Z"
            
            logger.info(
                "✅ Control room crawl completed successfully",
                extra={"jobs_found": len(jobs)}
            )
        
        finally:
            # Restore env vars
            for key, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value
    
    except Exception as e:
        crawl_status.state = CrawlerState.ERROR
        crawl_status.last_error = str(e)
        crawl_status.last_run_finished_at = datetime.utcnow().isoformat() + "Z"
        
        logger.error(
            "❌ Control room crawl failed",
            extra={"error": str(e)},
            exc_info=True
        )


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the control room UI."""
    static_dir = Path(__file__).parent / "static"
    
    # Try to serve the new control room UI first
    control_room_file = static_dir / "control-room.html"
    if control_room_file.exists():
        return FileResponse(control_room_file)
    
    # Fallback to old index.html
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    
    # Fallback: serve embedded minimal UI if static file doesn't exist
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HubSpot Job Scraper Control Room</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
        <h1>HubSpot Job Scraper Control Room</h1>
        <p>Loading...</p>
        <p>Note: Static UI files not found. Using fallback.</p>
        <div>
            <button id="startBtn">Start Crawl</button>
            <pre id="status"></pre>
        </div>
        <script>
            const statusEl = document.getElementById('status');
            const startBtn = document.getElementById('startBtn');
            
            async function refreshStatus() {
                const res = await fetch('/status');
                const data = await res.json();
                statusEl.textContent = JSON.stringify(data, null, 2);
            }
            
            startBtn.onclick = async () => {
                await fetch('/start', { method: 'POST' });
                refreshStatus();
            };
            
            setInterval(refreshStatus, 2000);
            refreshStatus();
        </script>
    </body>
    </html>
    """)


@app.get("/health")
async def health():
    """Health check endpoint for Render."""
    return {"status": "ok"}


@app.get("/status")
async def get_status():
    """
    Get current crawler status and metrics.
    
    Returns:
        JSON with state, metrics, and timing info
    """
    return JSONResponse(content=crawl_status.to_dict())


@app.post("/start")
async def start_crawl(
    request: Optional[StartCrawlRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Start a new crawl run.
    
    Args:
        request: Optional crawl configuration
        background_tasks: FastAPI background tasks
        
    Returns:
        JSON confirmation that crawl started
    """
    # Check if already running
    if crawl_status.state == CrawlerState.RUNNING:
        raise HTTPException(
            status_code=409,
            detail="Crawler is already running"
        )
    
    # Extract params
    role_filter = None
    remote_only = None
    if request:
        role_filter = request.role_filter
        remote_only = request.remote_only
    
    # Start background task
    background_tasks.add_task(
        run_scraper_background,
        role_filter=role_filter,
        remote_only=remote_only
    )
    
    logger.info("Crawl start requested from UI")
    
    return {
        "status": "started",
        "message": "Crawl initiated in background"
    }


@app.get("/logs")
async def get_logs(lines: int = 100):
    """
    Get recent log entries.
    
    Args:
        lines: Number of recent lines to return (max 500)
        
    Returns:
        JSON array of log entries
    """
    lines = min(lines, 500)
    recent_logs = list(crawl_status.log_buffer)[-lines:]
    return JSONResponse(content={"logs": recent_logs})


@app.get("/jobs")
async def get_jobs():
    """
    Get recent job results.
    
    Returns:
        JSON array of recent jobs
    """
    return JSONResponse(content={
        "jobs": crawl_status.recent_jobs,
        "count": len(crawl_status.recent_jobs)
    })


# Mount static files if directory exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
