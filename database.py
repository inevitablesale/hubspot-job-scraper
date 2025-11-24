"""
Database layer for persisting jobs to Supabase.

This module handles all database operations including:
- Connecting to Supabase
- Saving jobs to the database
- Loading jobs from the database
- Querying jobs with filters
"""

import logging
import os
from datetime import datetime
from typing import List, Optional
from supabase import create_client, Client

from models import JobItem

logger = logging.getLogger(__name__)


class SupabaseDatabase:
    """
    Database client for Supabase operations.
    """
    
    def __init__(self):
        """Initialize Supabase client with environment variables."""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.client: Optional[Client] = None
        self.enabled = bool(self.url and self.key)
        
        if not self.url:
            logger.warning("SUPABASE_URL not set. Database persistence disabled.")
            return
        
        if not self.key:
            logger.warning("SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY not set. Database persistence disabled.")
            return
        
        if self.enabled:
            try:
                self.client = create_client(self.url, self.key)
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.enabled = False
    
    async def save_job(self, job: JobItem) -> bool:
        """
        Save a job to the database.
        
        Args:
            job: JobItem to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Convert JobItem to dict for Supabase
            job_data = {
                "id": job.id,
                "domain": job.domain,
                "title": job.title,
                "location": job.location,
                "remote_type": job.remote_type,
                "url": job.url,
                "source_page": job.source_page,
                "ats": job.ats,
                "created_at": job.created_at.isoformat() if job.created_at else datetime.utcnow().isoformat()
            }
            
            # Upsert (insert or update) the job
            self.client.table("jobs").upsert(job_data).execute()
            logger.debug(f"Saved job {job.id} to database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save job {job.id}: {e}")
            return False
    
    async def save_jobs(self, jobs: List[JobItem]) -> int:
        """
        Save multiple jobs to the database.
        
        Args:
            jobs: List of JobItems to save
            
        Returns:
            Number of jobs successfully saved
        """
        if not self.enabled:
            return 0
        
        saved_count = 0
        for job in jobs:
            if await self.save_job(job):
                saved_count += 1
        
        logger.info(f"Saved {saved_count}/{len(jobs)} jobs to database")
        return saved_count
    
    async def load_jobs(self, limit: int = 1000) -> List[JobItem]:
        """
        Load jobs from the database.
        
        Args:
            limit: Maximum number of jobs to load
            
        Returns:
            List of JobItems
        """
        if not self.enabled:
            return []
        
        try:
            # Query jobs from database, ordered by created_at descending
            response = self.client.table("jobs").select("*").order("created_at", desc=True).limit(limit).execute()
            
            jobs = []
            for row in response.data:
                try:
                    # Parse datetime string
                    created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                    
                    job = JobItem(
                        id=row["id"],
                        domain=row["domain"],
                        title=row["title"],
                        location=row.get("location"),
                        remote_type=row.get("remote_type"),
                        url=row["url"],
                        source_page=row["source_page"],
                        ats=row.get("ats"),
                        created_at=created_at
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Failed to parse job from database: {e}")
                    continue
            
            logger.info(f"Loaded {len(jobs)} jobs from database")
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to load jobs from database: {e}")
            return []
    
    async def query_jobs(
        self,
        domain: Optional[str] = None,
        remote_only: bool = False,
        limit: int = 1000
    ) -> List[JobItem]:
        """
        Query jobs with filters.
        
        Args:
            domain: Filter by specific domain
            remote_only: Show only remote jobs
            limit: Maximum number of jobs to return
            
        Returns:
            List of JobItems matching the filters
        """
        if not self.enabled:
            return []
        
        try:
            query = self.client.table("jobs").select("*")
            
            if domain:
                query = query.eq("domain", domain)
            
            if remote_only:
                query = query.eq("remote_type", "remote")
            
            query = query.order("created_at", desc=True).limit(limit)
            response = query.execute()
            
            jobs = []
            for row in response.data:
                try:
                    created_at = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
                    
                    job = JobItem(
                        id=row["id"],
                        domain=row["domain"],
                        title=row["title"],
                        location=row.get("location"),
                        remote_type=row.get("remote_type"),
                        url=row["url"],
                        source_page=row["source_page"],
                        ats=row.get("ats"),
                        created_at=created_at
                    )
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Failed to parse job from database: {e}")
                    continue
            
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to query jobs: {e}")
            return []


# Global database instance
db = SupabaseDatabase()
