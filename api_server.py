"""
Enhanced FastAPI server implementing the proposed API architecture.

This server provides a comprehensive API for managing and monitoring the
HubSpot job scraper with real-time updates via Server-Sent Events (SSE).
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CrawlSummary, CrawlEvent, JobItem, DomainItem,
    ConfigSettings, LogLine, StartCrawlRequest, StartCrawlResponse,
    NavigationFlowStep, ScreenshotInfo
)
from state import crawler_state, config_state, events_bus, logs_buffer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="HubSpot Job Scraper Control Room",
    description="Control room API for managing job scraping operations",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------- System / Dashboard --------

@app.get("/api/system/summary", response_model=CrawlSummary)
async def get_summary():
    """
    Get current system summary including crawler state and metrics.
    
    This endpoint provides the high-level overview used by the dashboard.
    """
    return crawler_state.summary()


# -------- Crawl Control --------

@app.post("/api/crawl/start", response_model=StartCrawlResponse)
async def start_crawl(
    background_tasks: BackgroundTasks,
    request: Optional[StartCrawlRequest] = None
):
    """
    Start a new crawl job.
    
    Returns an error if a crawl is already running.
    The crawl runs in the background and emits events via SSE.
    """
    if crawler_state.is_running():
        return StartCrawlResponse(
            ok=False,
            reason="already_running",
            message="Crawler is already running"
        )
    
    # Start the crawl in the background
    background_tasks.add_task(crawler_state.run_crawl_job)
    
    logger.info("Crawl started via API")
    
    # Emit start event
    await events_bus.publish(CrawlEvent(
        id=f"evt_{datetime.utcnow().timestamp()}",
        ts=datetime.utcnow(),
        level="info",
        type="log",
        message="Crawl started",
        metadata={"triggered_by": "api"}
    ))
    
    return StartCrawlResponse(
        ok=True,
        message="Crawl started successfully"
    )


@app.post("/api/crawl/stop", response_model=StartCrawlResponse)
async def stop_crawl():
    """
    Request the crawler to stop.
    
    The crawler will finish the current domain and then stop gracefully.
    """
    if not crawler_state.is_running():
        return StartCrawlResponse(
            ok=False,
            reason="not_running",
            message="Crawler is not running"
        )
    
    crawler_state.request_stop()
    
    logger.info("Crawl stop requested via API")
    
    # Emit stop event
    await events_bus.publish(CrawlEvent(
        id=f"evt_{datetime.utcnow().timestamp()}",
        ts=datetime.utcnow(),
        level="warning",
        type="log",
        message="Crawl stop requested",
        metadata={"triggered_by": "api"}
    ))
    
    return StartCrawlResponse(
        ok=True,
        message="Stop requested"
    )


@app.post("/api/crawl/pause", response_model=StartCrawlResponse)
async def pause_crawl():
    """
    Request the crawler to pause.
    
    The crawler will pause after finishing the current domain.
    """
    if not crawler_state.is_running():
        return StartCrawlResponse(
            ok=False,
            reason="not_running",
            message="Crawler is not running"
        )
    
    crawler_state.request_pause()
    
    logger.info("Crawl pause requested via API")
    
    # Emit pause event
    await events_bus.publish(CrawlEvent(
        id=f"evt_{datetime.utcnow().timestamp()}",
        ts=datetime.utcnow(),
        level="info",
        type="log",
        message="Crawl pause requested",
        metadata={"triggered_by": "api"}
    ))
    
    return StartCrawlResponse(
        ok=True,
        message="Pause requested"
    )


@app.post("/api/crawl/resume", response_model=StartCrawlResponse)
async def resume_crawl():
    """
    Request the crawler to resume.
    
    The crawler will resume from the paused state.
    """
    if not crawler_state.is_running():
        return StartCrawlResponse(
            ok=False,
            reason="not_running",
            message="Crawler is not running"
        )
    
    if not crawler_state.is_paused():
        return StartCrawlResponse(
            ok=False,
            reason="not_paused",
            message="Crawler is not paused"
        )
    
    crawler_state.request_resume()
    
    logger.info("Crawl resume requested via API")
    
    # Emit resume event
    await events_bus.publish(CrawlEvent(
        id=f"evt_{datetime.utcnow().timestamp()}",
        ts=datetime.utcnow(),
        level="info",
        type="log",
        message="Crawl resume requested",
        metadata={"triggered_by": "api"}
    ))
    
    return StartCrawlResponse(
        ok=True,
        message="Resume requested"
    )


@app.get("/api/crawl/status", response_model=CrawlSummary)
async def crawl_status():
    """
    Get current crawl status.
    
    This is the same as /api/system/summary but provided for API consistency.
    """
    return crawler_state.summary()


# -------- Events (Timeline + UI updates) --------

@app.get("/api/events/stream")
async def events_stream(request: Request):
    """
    Server-Sent Events (SSE) endpoint for real-time updates.
    
    Streams three types of events:
    - CrawlEvent: For timeline display (domain started, job found, etc.)
    - LogLine: For console/log display
    - State changes: When crawler state changes
    
    The frontend can listen to this endpoint to get real-time updates.
    """
    
    async def event_generator():
        # Subscribe to the event bus
        queue = events_bus.subscribe()
        
        try:
            # Send initial connection confirmation
            yield f"event: connected\n"
            yield f"data: {{'timestamp': '{datetime.utcnow().isoformat()}Z'}}\n\n"
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.debug("Client disconnected from SSE stream")
                    break
                
                try:
                    # Wait for event with timeout for heartbeat
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Determine event type and format
                    if isinstance(event, CrawlEvent):
                        event_type = "event"
                        payload = event.model_dump_json()
                    elif isinstance(event, LogLine):
                        event_type = "log"
                        payload = event.model_dump_json()
                    else:
                        event_type = "meta"
                        payload = "{}"
                    
                    # Send SSE formatted message
                    yield f"event: {event_type}\n"
                    yield f"data: {payload}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"event: heartbeat\n"
                    yield f"data: {{'timestamp': '{datetime.utcnow().isoformat()}Z'}}\n\n"
                
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
        finally:
            # Unsubscribe when client disconnects
            events_bus.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in nginx
        }
    )


# -------- Logs (for initial load / non-SSE) --------

@app.get("/api/logs", response_model=List[LogLine])
async def get_logs(limit: int = 500):
    """
    Get recent log lines.
    
    This is used for initial page load. Real-time logs should use
    the SSE endpoint (/api/events/stream).
    """
    return logs_buffer.tail(limit)


# -------- Jobs --------

@app.get("/api/jobs", response_model=List[JobItem])
async def list_jobs(
    q: Optional[str] = None,
    domain: Optional[str] = None,
    remote_only: bool = False
):
    """
    List and filter jobs.
    
    Args:
        q: Search query for title or domain
        domain: Filter by specific domain
        remote_only: Show only remote jobs
    """
    return crawler_state.query_jobs(q=q, domain=domain, remote_only=remote_only)


@app.get("/api/jobs/{job_id}", response_model=JobItem)
async def job_detail(job_id: str):
    """
    Get details for a specific job.
    """
    job = crawler_state.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# -------- Domains --------

@app.get("/api/domains", response_model=List[DomainItem])
async def list_domains():
    """
    List all domains.
    """
    return crawler_state.list_domains()


@app.get("/api/domains/{domain}", response_model=DomainItem)
async def domain_detail(domain: str):
    """
    Get details for a specific domain.
    """
    domain_item = crawler_state.get_domain(domain)
    if not domain_item:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain_item


@app.get("/api/domains/{domain}/flow", response_model=List[NavigationFlowStep])
async def domain_flow(domain: str):
    """
    Get the extraction tree / navigation flow for a domain.
    
    Returns the step-by-step navigation path taken during scraping,
    useful for debugging and understanding the scraper's behavior.
    """
    flow = crawler_state.get_navigation_flow(domain)
    if not flow:
        # Return empty list if no flow recorded
        return []
    return flow


@app.get("/api/domains/{domain}/screenshots", response_model=List[ScreenshotInfo])
async def domain_screenshots(domain: str):
    """
    Get metadata about screenshots taken for a domain.
    
    Returns URLs to the actual screenshot files which can be
    accessed via the /static/screenshots/ endpoint.
    """
    screenshots = crawler_state.get_screenshots(domain)
    return screenshots


# -------- Config --------

@app.get("/api/config", response_model=ConfigSettings)
async def get_config():
    """
    Get current configuration settings.
    """
    return config_state.get()


@app.put("/api/config", response_model=ConfigSettings)
async def update_config(settings: ConfigSettings):
    """
    Update configuration settings.
    
    Settings are persisted to disk and take effect immediately.
    """
    config_state.update(settings)
    
    logger.info("Configuration updated via API")
    
    # Emit config change event
    await events_bus.publish(LogLine(
        ts=datetime.utcnow(),
        level="info",
        message="Configuration updated",
        source="system"
    ))
    
    return settings


# -------- Health Check --------

@app.get("/health")
async def health():
    """
    Health check endpoint for monitoring and deployment.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0"
    }


# -------- Static Files and UI --------

@app.get("/")
async def index():
    """
    Serve the main UI.
    """
    static_dir = Path(__file__).parent / "static"
    control_room_file = static_dir / "control-room.html"
    
    if control_room_file.exists():
        return FileResponse(control_room_file)
    
    # Fallback
    return JSONResponse(
        content={
            "message": "HubSpot Job Scraper API",
            "version": "2.0.0",
            "docs": "/docs"
        }
    )


# Mount static files if directory exists
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
