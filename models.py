"""
Shared Pydantic models for the HubSpot Job Scraper API.

This module defines the data models used across the FastAPI backend,
ensuring type safety and data validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


# Type aliases for clarity
CrawlState = Literal["idle", "running", "stopping", "error", "finished"]
EventLevel = Literal["info", "warning", "error"]
EventType = Literal[
    "domain_started",
    "domain_finished",
    "career_page_found",
    "job_extracted",
    "error",
    "log"
]
LogLevel = Literal["debug", "info", "warning", "error"]
RemoteType = Literal["remote", "hybrid", "office"]


class CrawlSummary(BaseModel):
    """Summary of the current crawl status and metrics."""
    
    state: CrawlState
    paused: bool = False
    last_run_started_at: Optional[datetime] = None
    last_run_finished_at: Optional[datetime] = None
    domains_total: int = 0
    domains_completed: int = 0
    jobs_found: int = 0
    errors_count: int = 0


class CrawlEvent(BaseModel):
    """Event emitted during crawling for timeline display."""
    
    id: str
    ts: datetime
    level: EventLevel
    type: EventType
    domain: Optional[str] = None
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobItem(BaseModel):
    """Represents a job posting extracted from a domain."""
    
    id: str
    domain: str
    title: str
    location: Optional[str] = None
    remote_type: Optional[RemoteType] = None
    url: str
    source_page: str
    ats: Optional[str] = None
    created_at: datetime


class DomainItem(BaseModel):
    """Represents a domain being scraped."""
    
    domain: str
    category: Optional[str] = None
    blacklisted: bool = False
    last_scraped_at: Optional[datetime] = None
    career_page: Optional[str] = None
    ats: Optional[str] = None
    jobs_count: int = 0
    status: Optional[str] = None


class ConfigSettings(BaseModel):
    """Configuration settings for the scraper."""
    
    dark_mode_default: Literal["system", "light", "dark"] = "dark"
    max_pages_per_domain: int = 10
    max_depth: int = 3
    blacklist_domains: List[str] = Field(default_factory=list)
    allowed_categories: List[str] = Field(default_factory=list)
    role_filters: List[str] = Field(default_factory=list)
    remote_only: bool = False


class LogLine(BaseModel):
    """Represents a single log line."""
    
    ts: datetime
    level: LogLevel
    message: str
    domain: Optional[str] = None
    source: Literal["crawler", "system"] = "crawler"


class StartCrawlRequest(BaseModel):
    """Request payload for starting a crawl."""
    
    role_filter: Optional[str] = None
    remote_only: Optional[bool] = None


class StartCrawlResponse(BaseModel):
    """Response from starting a crawl."""
    
    ok: bool
    reason: Optional[str] = None
    message: Optional[str] = None


class NavigationFlowStep(BaseModel):
    """Represents a step in the domain navigation flow."""
    
    step: int
    url: str
    type: str
    timestamp: Optional[datetime] = None
    screenshot: Optional[str] = None
    jobs_found: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScreenshotInfo(BaseModel):
    """Information about a screenshot."""
    
    filename: str
    url: str
    step: int
    timestamp: datetime
    description: Optional[str] = None
