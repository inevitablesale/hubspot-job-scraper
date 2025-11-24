"""
Database models for Supabase integration.

This module defines Pydantic models that match the exact Supabase schema
as specified in the problem statement. These models are used for data
validation and type safety when interacting with the database.

DO NOT modify table or column names - they must match Supabase exactly.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class Company(BaseModel):
    """Represents a company in the companies table."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    domain: str
    source_url: str
    logo_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Job(BaseModel):
    """Represents a job posting in the jobs table."""
    id: UUID = Field(default_factory=uuid4)
    company_id: UUID
    job_title: str
    job_url: str
    department: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    hash: str  # For deduplication
    active: bool = True
    ats_provider: Optional[str] = None


class JobMetadata(BaseModel):
    """Represents additional job metadata in the job_metadata table."""
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    seniority: Optional[str] = None
    employment_type: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    technologies: Optional[List[str]] = None
    raw_json: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ATSSource(BaseModel):
    """Represents ATS detection information in the ats_sources table."""
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    provider: str
    raw_html: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class ScrapeRun(BaseModel):
    """Represents a scraping run in the scrape_runs table."""
    id: UUID = Field(default_factory=uuid4)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    total_companies: int = 0
    total_jobs: int = 0
    errors: Optional[Dict[str, Any]] = None


class JobHistory(BaseModel):
    """Represents a job snapshot in the job_history table."""
    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    snapshot: Dict[str, Any]
    captured_at: datetime = Field(default_factory=datetime.utcnow)
