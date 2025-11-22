"""
State management for the HubSpot Job Scraper.

This module manages the global state of the crawler, including:
- Crawler status and metrics
- Event bus for real-time updates
- Log buffer
- Configuration settings
"""

import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4

from models import (
    CrawlSummary, CrawlEvent, JobItem, DomainItem,
    ConfigSettings, LogLine, CrawlState, NavigationFlowStep, ScreenshotInfo
)


logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus for real-time event streaming via SSE.
    Implements a simple pub-sub pattern using asyncio queues.
    """
    
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
    
    def subscribe(self) -> asyncio.Queue:
        """Subscribe to events. Returns a queue to receive events from."""
        queue = asyncio.Queue(maxsize=1000)
        self._subscribers.add(queue)
        logger.debug(f"New subscriber. Total subscribers: {len(self._subscribers)}")
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from events."""
        self._subscribers.discard(queue)
        logger.debug(f"Subscriber removed. Total subscribers: {len(self._subscribers)}")
    
    async def publish(self, event):
        """Publish an event to all subscribers."""
        if not self._subscribers:
            return
        
        # Remove disconnected subscribers
        dead_queues = set()
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full, dropping event")
            except Exception as e:
                logger.error(f"Error publishing to subscriber: {e}")
                dead_queues.add(queue)
        
        # Clean up dead queues
        for queue in dead_queues:
            self._subscribers.discard(queue)


class LogsBuffer:
    """
    Circular buffer for storing recent log lines.
    """
    
    def __init__(self, maxlen: int = 1000):
        self._buffer: deque = deque(maxlen=maxlen)
    
    def append(self, log_line: LogLine):
        """Add a log line to the buffer."""
        self._buffer.append(log_line)
    
    def tail(self, limit: int = 500) -> List[LogLine]:
        """Get the most recent log lines."""
        limit = min(limit, len(self._buffer))
        return list(self._buffer)[-limit:] if limit > 0 else []
    
    def clear(self):
        """Clear all log lines."""
        self._buffer.clear()


class CrawlerState:
    """
    Global state manager for the crawler.
    Tracks status, metrics, jobs, domains, and provides helper methods.
    """
    
    def __init__(self):
        # State tracking
        self._state: CrawlState = "idle"
        self._last_run_started_at: Optional[datetime] = None
        self._last_run_finished_at: Optional[datetime] = None
        
        # Metrics
        self._domains_total: int = 0
        self._domains_completed: int = 0
        self._jobs_found: int = 0
        self._errors_count: int = 0
        
        # Data storage
        self._jobs: List[JobItem] = []
        self._domains: List[DomainItem] = []
        self._navigation_flows: Dict[str, List[NavigationFlowStep]] = {}
        self._screenshots: Dict[str, List[ScreenshotInfo]] = {}
        
        # Background task reference
        self._current_task: Optional[asyncio.Task] = None
        self._stop_requested: bool = False
    
    def is_running(self) -> bool:
        """Check if crawler is currently running."""
        return self._state == "running"
    
    def summary(self) -> CrawlSummary:
        """Get current crawl summary."""
        return CrawlSummary(
            state=self._state,
            last_run_started_at=self._last_run_started_at,
            last_run_finished_at=self._last_run_finished_at,
            domains_total=self._domains_total,
            domains_completed=self._domains_completed,
            jobs_found=self._jobs_found,
            errors_count=self._errors_count
        )
    
    def request_stop(self):
        """Request the crawler to stop."""
        if self._state == "running":
            self._stop_requested = True
            self._state = "stopping"
            logger.info("Stop requested for crawler")
    
    def start_run(self, domains_total: int):
        """Mark the start of a crawl run."""
        self._state = "running"
        self._last_run_started_at = datetime.utcnow()
        self._domains_total = domains_total
        self._domains_completed = 0
        self._jobs_found = 0
        self._errors_count = 0
        self._stop_requested = False
        logger.info(f"Crawl run started with {domains_total} domains")
    
    def finish_run(self, success: bool = True):
        """Mark the end of a crawl run."""
        self._last_run_finished_at = datetime.utcnow()
        if success:
            self._state = "finished"
        else:
            self._state = "error"
        logger.info(f"Crawl run finished. State: {self._state}")
    
    def add_job(self, job: JobItem):
        """Add a job to the results."""
        self._jobs.append(job)
        self._jobs_found = len(self._jobs)
    
    def add_domain(self, domain: DomainItem):
        """Add or update a domain."""
        # Remove existing domain with same name if present
        self._domains = [d for d in self._domains if d.domain != domain.domain]
        self._domains.append(domain)
    
    def increment_completed(self):
        """Increment the completed domains counter."""
        self._domains_completed += 1
    
    def increment_errors(self):
        """Increment the errors counter."""
        self._errors_count += 1
    
    def query_jobs(
        self,
        q: Optional[str] = None,
        domain: Optional[str] = None,
        remote_only: bool = False
    ) -> List[JobItem]:
        """Query jobs with filters."""
        results = self._jobs
        
        if q:
            q_lower = q.lower()
            results = [
                job for job in results
                if q_lower in job.title.lower() or q_lower in job.domain.lower()
            ]
        
        if domain:
            results = [job for job in results if job.domain == domain]
        
        if remote_only:
            results = [job for job in results if job.remote_type == "remote"]
        
        return results
    
    def get_job(self, job_id: str) -> Optional[JobItem]:
        """Get a specific job by ID."""
        for job in self._jobs:
            if job.id == job_id:
                return job
        return None
    
    def list_domains(self) -> List[DomainItem]:
        """List all domains."""
        return self._domains
    
    def get_domain(self, domain: str) -> Optional[DomainItem]:
        """Get a specific domain."""
        for d in self._domains:
            if d.domain == domain:
                return d
        return None
    
    def get_navigation_flow(self, domain: str) -> List[NavigationFlowStep]:
        """Get the navigation flow for a domain."""
        return self._navigation_flows.get(domain, [])
    
    def set_navigation_flow(self, domain: str, flow: List[NavigationFlowStep]):
        """Set the navigation flow for a domain."""
        self._navigation_flows[domain] = flow
    
    def get_screenshots(self, domain: str) -> List[ScreenshotInfo]:
        """Get screenshots for a domain."""
        return self._screenshots.get(domain, [])
    
    def add_screenshot(self, domain: str, screenshot: ScreenshotInfo):
        """Add a screenshot for a domain."""
        if domain not in self._screenshots:
            self._screenshots[domain] = []
        self._screenshots[domain].append(screenshot)
    
    async def run_crawl_job(self):
        """Placeholder for actual crawl job execution."""
        # This would be implemented with the actual scraper logic
        # For now, it's a stub that can be overridden
        logger.warning("run_crawl_job called but not implemented")
        pass


class ConfigState:
    """
    Configuration state manager.
    Handles loading and saving configuration settings.
    """
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self._config: ConfigSettings = self._load()
    
    def _load(self) -> ConfigSettings:
        """Load configuration from file or use defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return ConfigSettings(**data)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        # Return defaults
        return ConfigSettings()
    
    def _save(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config.model_dump(), f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self) -> ConfigSettings:
        """Get current configuration."""
        return self._config
    
    def update(self, settings: ConfigSettings):
        """Update configuration."""
        self._config = settings
        self._save()


# Global instances
events_bus = EventBus()
logs_buffer = LogsBuffer()
crawler_state = CrawlerState()
config_state = ConfigState()
