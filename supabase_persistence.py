# supabase_persistence.py
import hashlib
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from supabase import Client

from supabase_client import get_supabase_client
from logging_config import get_logger

logger = get_logger(__name__)

# Track if we've already attempted to add run_id column
_RUN_ID_COLUMN_CHECKED = False


def _ensure_run_id_column(client: Client) -> None:
    """
    Placeholder for run_id column check.
    The actual column will be added manually via Supabase UI or automatically
    handled by the insert/update logic which gracefully falls back if column doesn't exist.
    """
    global _RUN_ID_COLUMN_CHECKED
    _RUN_ID_COLUMN_CHECKED = True


def _compute_job_hash(company_id: str, title: str, url: str) -> str:
    raw = f"{company_id}:{title}:{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_or_create_company(
    client: Client,
    name: str,
    domain: str,
    source_url: Optional[str] = None,
) -> Optional[str]:
    """
    Upserts a company by domain and returns its id.
    """
    resp = (
        client.table("companies")
        .select("id")
        .eq("domain", domain)
        .execute()
    )

    if resp.data:
        return resp.data[0]["id"]

    insert_data = {
        "name": name,
        "domain": domain,
        "source_url": source_url,
    }

    resp = client.table("companies").insert(insert_data).execute()
    return resp.data[0]["id"] if resp.data else None


def create_scrape_run() -> Optional[str]:
    """
    Create a new scrape run record in Supabase.
    
    Uses schema: id (uuid), hash (text), active (bool), ats_provider (text)
    
    Returns:
        run_id (UUID as string) if successful, None otherwise
    """
    client = get_supabase_client()
    if client is None:
        return None
    
    try:
        run_id = str(uuid.uuid4())
        random_hash = hashlib.sha256(run_id.encode()).hexdigest()[:16]
        
        insert_data = {
            "id": run_id,
            "hash": random_hash,
            "active": True,
            "ats_provider": "hubspot",
        }
        resp = client.table("scrape_runs").insert(insert_data).execute()
        
        if resp.data:
            logger.info(f"Created scrape run: run_id={run_id}")
            return run_id
        return None
    except Exception as e:
        logger.error(f"Failed to create scrape run: {e}")
        return None


def update_scrape_run(run_id: str, fields: dict) -> None:
    """
    Update a scrape run with arbitrary fields.
    
    Args:
        run_id: The scrape run ID
        fields: Dictionary of fields to update
    """
    client = get_supabase_client()
    if client is None:
        return
    
    try:
        if fields:
            client.table("scrape_runs").update(fields).eq("id", run_id).execute()
            logger.debug(f"Updated scrape run {run_id}: {fields}")
    except Exception as e:
        logger.error(f"Failed to update scrape run {run_id}: {e}")


def save_jobs_for_domain(
    run_id: str,
    company_id: str,
    jobs: List[Dict],
) -> None:
    """
    Persist all jobs for a given domain into Supabase.
    
    ALWAYS inserts new rows (never upserts or updates).

    Args:
        run_id: Scrape run ID to associate jobs with (REQUIRED)
        company_id: Company UUID (REQUIRED)
        jobs: List of job dictionaries with guaranteed fields:
              - job_title
              - job_url
              - department
              - location
              - remote_type
              - description
              - posted_at (optional)
              - scraped_at (optional)
              - hash
              - active
              - ats_provider
    """
    client = get_supabase_client()
    if client is None:
        # Supabase not configured, silently skip
        return

    if not run_id or not company_id:
        logger.error("run_id and company_id are required for save_jobs_for_domain")
        return

    jobs_inserted = 0
    for job in jobs:
        # Extract guaranteed fields from job dict
        job_title = job.get("job_title") or job.get("title") or ""
        job_url = job.get("job_url") or job.get("url") or ""
        department = job.get("department")
        location = job.get("location")
        remote_type = job.get("remote_type")
        description = job.get("description") or ""
        posted_at = job.get("posted_at")
        scraped_at = job.get("scraped_at")
        job_hash = job.get("hash")
        active = job.get("active", True)
        ats_provider = job.get("ats_provider") or job.get("ats")

        # Normalize timestamps to ISO or None
        if isinstance(posted_at, datetime):
            posted_at_iso = posted_at.isoformat()
        else:
            posted_at_iso = posted_at or None
        
        if isinstance(scraped_at, datetime):
            scraped_at_iso = scraped_at.isoformat()
        else:
            scraped_at_iso = scraped_at or datetime.utcnow().isoformat()

        # If hash not provided, compute it
        if not job_hash:
            job_hash = _compute_job_hash(company_id, job_title, job_url)

        # Build insert data with all required fields
        insert_data = {
            "company_id": company_id,
            "run_id": run_id,
            "job_title": job_title,
            "job_url": job_url,
            "department": department,
            "location": location,
            "remote_type": remote_type,
            "description": description,
            "posted_at": posted_at_iso,
            "scraped_at": scraped_at_iso,
            "hash": job_hash,
            "active": active,
            "ats_provider": ats_provider,
        }
        
        try:
            resp = client.table("jobs").insert(insert_data).execute()
            job_id = resp.data[0]["id"] if resp.data else None
            
            if job_id:
                jobs_inserted += 1
                # Insert job_metadata if present
                _save_job_metadata(client, job_id, job)
        except Exception as e:
            logger.error(f"Failed to insert job: {e}")
    
    # Log insertion summary as per requirements
    if jobs_inserted > 0:
        logger.info(f"Saved {jobs_inserted} jobs for run_id={run_id}, company_id={company_id}")


def _save_job_metadata(client: Client, job_id: str, job: Dict) -> None:
    """
    Save optional metadata into job_metadata if available on the job object.
    """
    seniority = job.get("seniority")
    employment_type = job.get("employment_type")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    technologies = job.get("technologies")
    raw_json = job.get("raw_json")

    if not any([seniority, employment_type, salary_min, salary_max, technologies, raw_json]):
        return

    insert_data = {
        "job_id": job_id,
        "seniority": seniority,
        "employment_type": employment_type,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "technologies": technologies,
        "raw_json": raw_json,
    }

    client.table("job_metadata").insert(insert_data).execute()


def get_jobs_for_run(run_id: str) -> List[Dict]:
    """
    Retrieve all jobs for a specific scrape run.
    
    Args:
        run_id: The scrape run ID
        
    Returns:
        List of job dictionaries with company info
    """
    client = get_supabase_client()
    if client is None:
        return []
    
    try:
        resp = (
            client.table("jobs")
            .select("*, companies(*)")
            .eq("run_id", run_id)
            .execute()
        )
        
        jobs = resp.data or []
        logger.info(f"Retrieved {len(jobs)} jobs for run_id={run_id}")
        return jobs
    except Exception as e:
        logger.error(f"Failed to retrieve jobs for run {run_id}: {e}")
        return []


def get_all_jobs(limit: int = 1000) -> List[Dict]:
    """
    Retrieve recent jobs from Supabase.
    
    Args:
        limit: Maximum number of jobs to retrieve
        
    Returns:
        List of job dictionaries with company info
    """
    client = get_supabase_client()
    if client is None:
        return []
    
    try:
        resp = (
            client.table("jobs")
            .select("*, companies(*)")
            .order("scraped_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        jobs = resp.data or []
        return jobs
    except Exception as e:
        logger.error(f"Failed to retrieve jobs from Supabase: {e}")
        return []
