"""
Database service for Supabase operations.

This module provides all database operations for storing and retrieving
job scraping data in Supabase. It follows the exact schema defined in
the problem statement.

Key principles:
- Use company.domain to dedupe companies
- Use jobs.hash to dedupe jobs
- Insert into job_metadata only when data is present
- Insert ATS detections into ats_sources
- Log each run in scrape_runs
- Save job snapshots into job_history after updates
"""

import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from uuid import UUID
from supabase_client import get_supabase_client
from db_models import Company, Job, JobMetadata, ATSSource, ScrapeRun, JobHistory
from logging_config import get_logger

logger = get_logger(__name__)


class DatabaseService:
    """Service for all Supabase database operations."""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.enabled = self.client is not None
        
        if not self.enabled:
            logger.warning("DatabaseService initialized but Supabase is not configured")
    
    def _is_enabled(self) -> bool:
        """Check if database operations are enabled."""
        return self.enabled
    
    # ==================== COMPANY OPERATIONS ====================
    
    def get_or_create_company(
        self,
        name: str,
        domain: str,
        source_url: str,
        logo_url: Optional[str] = None
    ) -> Optional[UUID]:
        """
        Get existing company by domain or create a new one.
        
        Uses domain for deduplication as per requirements.
        
        Args:
            name: Company name
            domain: Company domain (used for deduplication)
            source_url: Source URL where company was found
            logo_url: Optional logo URL
            
        Returns:
            Company UUID or None if database is not configured
        """
        if not self._is_enabled():
            logger.debug("Skipping company upsert - database not configured")
            return None
        
        try:
            # Check if company exists by domain
            result = self.client.table("companies").select("id").eq("domain", domain).execute()
            
            if result.data and len(result.data) > 0:
                company_id = result.data[0]["id"]
                logger.debug(f"Found existing company: {name} (domain: {domain})")
                
                # Update updated_at timestamp
                self.client.table("companies").update({
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", company_id).execute()
                
                return UUID(company_id)
            else:
                # Create new company
                company = Company(
                    name=name,
                    domain=domain,
                    source_url=source_url,
                    logo_url=logo_url
                )
                
                insert_result = self.client.table("companies").insert({
                    "id": str(company.id),
                    "name": company.name,
                    "domain": company.domain,
                    "source_url": company.source_url,
                    "logo_url": company.logo_url,
                    "created_at": company.created_at.isoformat(),
                    "updated_at": company.updated_at.isoformat()
                }).execute()
                
                logger.info(f"Created new company: {name} (domain: {domain})")
                return company.id
                
        except Exception as e:
            logger.error(f"Error in get_or_create_company for {domain}: {e}")
            return None
    
    # ==================== JOB OPERATIONS ====================
    
    def _calculate_job_hash(self, job_title: str, company_id: UUID, job_url: str) -> str:
        """
        Calculate hash for job deduplication.
        
        Args:
            job_title: Job title
            company_id: Company UUID
            job_url: Job URL
            
        Returns:
            SHA256 hash string
        """
        data = f"{company_id}:{job_title}:{job_url}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get_or_create_job(
        self,
        company_id: UUID,
        job_title: str,
        job_url: str,
        department: Optional[str] = None,
        location: Optional[str] = None,
        remote_type: Optional[str] = None,
        description: Optional[str] = None,
        posted_at: Optional[datetime] = None,
        ats_provider: Optional[str] = None
    ) -> Optional[tuple[UUID, bool]]:
        """
        Get existing job by hash or create a new one.
        
        Uses jobs.hash for deduplication as per requirements.
        
        Args:
            company_id: Company UUID
            job_title: Job title
            job_url: Job URL
            department: Optional department
            location: Optional location
            remote_type: Optional remote type (remote/hybrid/office)
            description: Optional job description
            posted_at: Optional posting date
            ats_provider: Optional ATS provider name
            
        Returns:
            Tuple of (job_id, is_new) or None if database not configured
        """
        if not self._is_enabled():
            logger.debug("Skipping job upsert - database not configured")
            return None
        
        try:
            # Calculate hash
            job_hash = self._calculate_job_hash(job_title, company_id, job_url)
            
            # Check if job exists by hash
            result = self.client.table("jobs").select("id, active").eq("hash", job_hash).execute()
            
            if result.data and len(result.data) > 0:
                job_id = result.data[0]["id"]
                is_active = result.data[0]["active"]
                
                # If job was inactive, reactivate it
                if not is_active:
                    self.client.table("jobs").update({
                        "active": True,
                        "scraped_at": datetime.utcnow().isoformat()
                    }).eq("id", job_id).execute()
                    logger.info(f"Reactivated job: {job_title}")
                    return (UUID(job_id), False)
                else:
                    logger.debug(f"Found existing active job: {job_title}")
                    return (UUID(job_id), False)
            else:
                # Create new job
                job = Job(
                    company_id=company_id,
                    job_title=job_title,
                    job_url=job_url,
                    department=department,
                    location=location,
                    remote_type=remote_type,
                    description=description,
                    posted_at=posted_at,
                    hash=job_hash,
                    ats_provider=ats_provider
                )
                
                insert_data = {
                    "id": str(job.id),
                    "company_id": str(job.company_id),
                    "job_title": job.job_title,
                    "job_url": job.job_url,
                    "department": job.department,
                    "location": job.location,
                    "remote_type": job.remote_type,
                    "description": job.description,
                    "scraped_at": job.scraped_at.isoformat(),
                    "hash": job.hash,
                    "active": job.active,
                    "ats_provider": job.ats_provider
                }
                
                if job.posted_at:
                    insert_data["posted_at"] = job.posted_at.isoformat()
                
                self.client.table("jobs").insert(insert_data).execute()
                
                logger.info(f"Created new job: {job_title}")
                return (job.id, True)
                
        except Exception as e:
            logger.error(f"Error in get_or_create_job for {job_title}: {e}")
            return None
    
    # ==================== JOB METADATA OPERATIONS ====================
    
    def insert_job_metadata(
        self,
        job_id: UUID,
        seniority: Optional[str] = None,
        employment_type: Optional[str] = None,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        technologies: Optional[List[str]] = None,
        raw_json: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Insert job metadata.
        
        Only inserts when data is present as per requirements.
        
        Args:
            job_id: Job UUID
            seniority: Seniority level
            employment_type: Employment type (full-time, part-time, etc.)
            salary_min: Minimum salary
            salary_max: Maximum salary
            technologies: List of technologies
            raw_json: Raw JSON data
            
        Returns:
            True if successful, False otherwise
        """
        if not self._is_enabled():
            return False
        
        # Only insert if we have meaningful data
        has_data = any([
            seniority,
            employment_type,
            salary_min is not None,
            salary_max is not None,
            technologies,
            raw_json
        ])
        
        if not has_data:
            logger.debug(f"Skipping job_metadata insert for {job_id} - no data")
            return True
        
        try:
            metadata = JobMetadata(
                job_id=job_id,
                seniority=seniority,
                employment_type=employment_type,
                salary_min=salary_min,
                salary_max=salary_max,
                technologies=technologies,
                raw_json=raw_json
            )
            
            self.client.table("job_metadata").insert({
                "id": str(metadata.id),
                "job_id": str(metadata.job_id),
                "seniority": metadata.seniority,
                "employment_type": metadata.employment_type,
                "salary_min": metadata.salary_min,
                "salary_max": metadata.salary_max,
                "technologies": metadata.technologies,
                "raw_json": metadata.raw_json,
                "created_at": metadata.created_at.isoformat()
            }).execute()
            
            logger.debug(f"Inserted job_metadata for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting job_metadata for {job_id}: {e}")
            return False
    
    # ==================== ATS SOURCE OPERATIONS ====================
    
    def insert_ats_source(
        self,
        job_id: UUID,
        provider: str,
        raw_html: Optional[str] = None
    ) -> bool:
        """
        Insert ATS detection information.
        
        Args:
            job_id: Job UUID
            provider: ATS provider name
            raw_html: Optional raw HTML from ATS page
            
        Returns:
            True if successful, False otherwise
        """
        if not self._is_enabled():
            return False
        
        try:
            ats_source = ATSSource(
                job_id=job_id,
                provider=provider,
                raw_html=raw_html
            )
            
            self.client.table("ats_sources").insert({
                "id": str(ats_source.id),
                "job_id": str(ats_source.job_id),
                "provider": ats_source.provider,
                "raw_html": ats_source.raw_html,
                "detected_at": ats_source.detected_at.isoformat()
            }).execute()
            
            logger.debug(f"Inserted ATS source for job {job_id}: {provider}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting ATS source for {job_id}: {e}")
            return False
    
    # ==================== SCRAPE RUN OPERATIONS ====================
    
    def create_scrape_run(self) -> Optional[UUID]:
        """
        Create a new scrape run record.
        
        Returns:
            Scrape run UUID or None if database not configured
        """
        if not self._is_enabled():
            return None
        
        try:
            scrape_run = ScrapeRun()
            
            self.client.table("scrape_runs").insert({
                "id": str(scrape_run.id),
                "started_at": scrape_run.started_at.isoformat(),
                "total_companies": scrape_run.total_companies,
                "total_jobs": scrape_run.total_jobs,
                "errors": scrape_run.errors
            }).execute()
            
            logger.info(f"Created scrape run: {scrape_run.id}")
            return scrape_run.id
            
        except Exception as e:
            logger.error(f"Error creating scrape run: {e}")
            return None
    
    def update_scrape_run(
        self,
        run_id: UUID,
        total_companies: int,
        total_jobs: int,
        errors: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update scrape run with final metrics.
        
        Args:
            run_id: Scrape run UUID
            total_companies: Total companies scraped
            total_jobs: Total jobs found
            errors: Optional error information
            
        Returns:
            True if successful, False otherwise
        """
        if not self._is_enabled():
            return False
        
        try:
            self.client.table("scrape_runs").update({
                "finished_at": datetime.utcnow().isoformat(),
                "total_companies": total_companies,
                "total_jobs": total_jobs,
                "errors": errors
            }).eq("id", str(run_id)).execute()
            
            logger.info(f"Updated scrape run {run_id}: {total_companies} companies, {total_jobs} jobs")
            return True
            
        except Exception as e:
            logger.error(f"Error updating scrape run {run_id}: {e}")
            return False
    
    # ==================== JOB HISTORY OPERATIONS ====================
    
    def insert_job_history(
        self,
        job_id: UUID,
        snapshot: Dict[str, Any]
    ) -> bool:
        """
        Insert job history snapshot.
        
        Args:
            job_id: Job UUID
            snapshot: Job data snapshot
            
        Returns:
            True if successful, False otherwise
        """
        if not self._is_enabled():
            return False
        
        try:
            job_history = JobHistory(
                job_id=job_id,
                snapshot=snapshot
            )
            
            self.client.table("job_history").insert({
                "id": str(job_history.id),
                "job_id": str(job_history.job_id),
                "snapshot": job_history.snapshot,
                "captured_at": job_history.captured_at.isoformat()
            }).execute()
            
            logger.debug(f"Inserted job history for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting job history for {job_id}: {e}")
            return False
    
    # ==================== BULK OPERATIONS ====================
    
    def save_scraped_job(
        self,
        company_name: str,
        company_domain: str,
        company_source_url: str,
        job_data: Dict[str, Any],
        save_history: bool = True
    ) -> Optional[UUID]:
        """
        Save a complete scraped job with all related data.
        
        This is a convenience method that handles:
        1. Company creation/retrieval
        2. Job creation/retrieval
        3. Job metadata insertion (if present)
        4. ATS source insertion (if detected)
        5. Job history snapshot (if requested)
        
        Args:
            company_name: Company name
            company_domain: Company domain
            company_source_url: Company source URL
            job_data: Dictionary with job information
            save_history: Whether to save job history snapshot
            
        Returns:
            Job UUID or None if failed
        """
        if not self._is_enabled():
            return None
        
        try:
            # 1. Get or create company
            company_id = self.get_or_create_company(
                name=company_name,
                domain=company_domain,
                source_url=company_source_url
            )
            
            if not company_id:
                logger.error(f"Failed to get/create company: {company_name}")
                return None
            
            # 2. Get or create job
            job_result = self.get_or_create_job(
                company_id=company_id,
                job_title=job_data.get("title", ""),
                job_url=job_data.get("url", ""),
                department=job_data.get("department"),
                location=job_data.get("location"),
                remote_type=job_data.get("remote_type") or job_data.get("location_type"),
                description=job_data.get("summary") or job_data.get("description"),
                ats_provider=job_data.get("ats")
            )
            
            if not job_result:
                logger.error(f"Failed to get/create job: {job_data.get('title')}")
                return None
            
            job_id, is_new = job_result
            
            # 3. Insert job metadata if present
            self.insert_job_metadata(
                job_id=job_id,
                seniority=job_data.get("seniority"),
                employment_type=job_data.get("employment_type"),
                technologies=job_data.get("technologies"),
                raw_json=job_data
            )
            
            # 4. Insert ATS source if detected
            if job_data.get("ats"):
                self.insert_ats_source(
                    job_id=job_id,
                    provider=job_data.get("ats")
                )
            
            # 5. Save job history snapshot if requested
            if save_history:
                self.insert_job_history(
                    job_id=job_id,
                    snapshot=job_data
                )
            
            return job_id
            
        except Exception as e:
            logger.error(f"Error in save_scraped_job: {e}")
            return None
