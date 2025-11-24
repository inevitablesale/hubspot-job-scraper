# supabase_persistence.py
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

from supabase import Client

from supabase_client import get_supabase_client
from logging_config import get_logger

logger = get_logger(__name__)


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


def create_scrape_run(
    total_companies: int = 0,
) -> Optional[str]:
    """
    Create a new scrape run record in Supabase.
    
    Args:
        total_companies: Total number of companies to scrape
        
    Returns:
        run_id (UUID as string) if successful, None otherwise
    """
    client = get_supabase_client()
    if client is None:
        return None
    
    try:
        insert_data = {
            "total_companies": total_companies,
            "total_jobs": 0,
        }
        resp = client.table("scrape_runs").insert(insert_data).execute()
        
        if resp.data:
            run_id = resp.data[0]["id"]
            logger.info(f"Created scrape run with id={run_id}, total_companies={total_companies}")
            return run_id
        return None
    except Exception as e:
        logger.error(f"Failed to create scrape run: {e}")
        return None


def update_scrape_run(
    run_id: str,
    total_jobs: Optional[int] = None,
    finished: bool = False,
    errors: Optional[Dict] = None,
) -> None:
    """
    Update a scrape run with progress or completion.
    
    Args:
        run_id: The scrape run ID
        total_jobs: Total jobs found (optional)
        finished: Whether to mark run as finished
        errors: Any errors encountered (optional)
    """
    client = get_supabase_client()
    if client is None:
        return
    
    try:
        update_data = {}
        if total_jobs is not None:
            update_data["total_jobs"] = total_jobs
        if finished:
            update_data["finished_at"] = datetime.utcnow().isoformat()
        if errors is not None:
            update_data["errors"] = errors
        
        if update_data:
            client.table("scrape_runs").update(update_data).eq("id", run_id).execute()
            logger.debug(f"Updated scrape run {run_id}: {update_data}")
    except Exception as e:
        logger.error(f"Failed to update scrape run {run_id}: {e}")


def save_jobs_for_domain(
    company_name: str,
    domain: str,
    jobs: List[Dict],
    source_url: Optional[str] = None,
    run_id: Optional[str] = None,
) -> None:
    """
    Persist all jobs for a given domain into Supabase.

    - No-op if Supabase is not configured.
    - Uses domain to dedupe companies.
    - Uses hash to dedupe jobs.
    - Writes metadata when available.
    - Associates jobs with a scrape run if run_id provided.
    
    Args:
        company_name: Company name
        domain: Company domain
        jobs: List of job dictionaries
        source_url: Source URL for the company page
        run_id: Optional scrape run ID to associate jobs with
    """

    client = get_supabase_client()
    if client is None:
        # Supabase not configured, silently skip
        return

    company_id = get_or_create_company(
        client=client,
        name=company_name,
        domain=domain,
        source_url=source_url,
    )

    if not company_id:
        return

    jobs_inserted = 0
    for job in jobs:
        title = job.get("job_title") or job.get("title") or ""
        job_url = job.get("job_url") or job.get("url") or ""
        description = job.get("description") or ""
        department = job.get("department")
        location = job.get("location")
        remote_type = job.get("remote_type")
        ats_provider = job.get("ats_provider") or job.get("ats")
        posted_at = job.get("posted_at")

        # Normalize posted_at to ISO or None
        if isinstance(posted_at, datetime):
            posted_at_iso = posted_at.isoformat()
        else:
            posted_at_iso = posted_at or None

        job_hash = _compute_job_hash(company_id, title, job_url)

        # Check if job already exists
        existing = (
            client.table("jobs")
            .select("id, description")
            .eq("hash", job_hash)
            .execute()
        )

        if existing.data:
            job_id = existing.data[0]["id"]
            # Update the job with the new run_id if provided
            if run_id:
                try:
                    client.table("jobs").update({"run_id": run_id}).eq("id", job_id).execute()
                except Exception as e:
                    # Column might not exist yet - that's OK, continue
                    logger.debug(f"Could not update run_id (column may not exist): {e}")
        else:
            insert_data = {
                "company_id": company_id,
                "job_title": title,
                "job_url": job_url,
                "department": department,
                "location": location,
                "remote_type": remote_type,
                "description": description,
                "posted_at": posted_at_iso,
                "hash": job_hash,
                "ats_provider": ats_provider,
            }
            
            # Add run_id to the jobs table if provided
            if run_id:
                insert_data["run_id"] = run_id
            
            try:
                resp = client.table("jobs").insert(insert_data).execute()
                job_id = resp.data[0]["id"] if resp.data else None
                
                if job_id:
                    jobs_inserted += 1

                # Insert job_metadata if present
                if job_id:
                    _save_job_metadata(client, job_id, job)
            except Exception as e:
                # If run_id column doesn't exist, try without it and store in metadata
                if "run_id" in str(e) or "column" in str(e).lower():
                    logger.debug(f"run_id column not in jobs table, storing in metadata instead")
                    insert_data.pop("run_id", None)
                    resp = client.table("jobs").insert(insert_data).execute()
                    job_id = resp.data[0]["id"] if resp.data else None
                    
                    if job_id:
                        jobs_inserted += 1
                        # Save metadata with run_id
                        _save_job_metadata(client, job_id, job, run_id=run_id)
                else:
                    raise
    
    # Log insertion summary as per requirements
    if jobs_inserted > 0:
        logger.info(f"Inserted {jobs_inserted} jobs into Supabase (run_id={run_id}, domain={domain})")


def _save_job_metadata(client: Client, job_id: str, job: Dict, run_id: Optional[str] = None) -> None:
    """
    Save optional metadata into job_metadata if available on the job object.
    
    Args:
        client: Supabase client
        job_id: Job ID
        job: Job dictionary with metadata
        run_id: Optional scrape run ID to include in raw_json
    """
    seniority = job.get("seniority")
    employment_type = job.get("employment_type")
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    technologies = job.get("technologies")
    raw_json = job.get("raw_json") or {}
    
    # Add run_id to raw_json for tracking
    if run_id:
        if isinstance(raw_json, dict):
            raw_json["run_id"] = run_id
        else:
            raw_json = {"run_id": run_id}

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
        List of job dictionaries with company and metadata info
    """
    client = get_supabase_client()
    if client is None:
        return []
    
    try:
        # First try to query by run_id column directly (if it exists)
        try:
            resp = (
                client.table("jobs")
                .select("*, companies(*), job_metadata(*)")
                .eq("run_id", run_id)
                .execute()
            )
            
            if resp.data:
                logger.info(f"Fetched {len(resp.data)} jobs for UI (run_id={run_id})")
                return resp.data
        except Exception as e:
            logger.debug(f"run_id column query failed (may not exist): {e}")
        
        # Fallback: Query all jobs and filter by run_id in metadata
        resp = (
            client.table("jobs")
            .select("*, companies(*), job_metadata(*)")
            .execute()
        )
        
        if not resp.data:
            return []
        
        # Filter jobs by run_id in metadata
        jobs = []
        for job in resp.data:
            # Check if job has run_id in metadata
            if job.get("job_metadata"):
                for metadata in job["job_metadata"]:
                    raw_json = metadata.get("raw_json") or {}
                    if isinstance(raw_json, dict) and raw_json.get("run_id") == run_id:
                        jobs.append(job)
                        break
        
        logger.info(f"Fetched {len(jobs)} jobs for UI (run_id={run_id})")
        return jobs
    except Exception as e:
        logger.error(f"Failed to retrieve jobs for run {run_id}: {e}")
        return []


def get_all_jobs(limit: int = 1000, run_id: Optional[str] = None) -> List[Dict]:
    """
    Retrieve all jobs from Supabase.
    
    Args:
        limit: Maximum number of jobs to retrieve
        run_id: Optional filter by specific run_id
        
    Returns:
        List of job dictionaries with company info
    """
    client = get_supabase_client()
    if client is None:
        return []
    
    try:
        query = client.table("jobs").select("*, companies(*), job_metadata(*)")
        
        # Filter by run_id if provided and column exists
        if run_id:
            try:
                query = query.eq("run_id", run_id)
            except Exception as e:
                logger.debug(f"run_id filter not supported (column may not exist): {e}")
        
        resp = query.order("scraped_at", desc=True).limit(limit).execute()
        
        jobs = resp.data or []
        
        # If run_id was requested but column doesn't exist, filter by metadata
        if run_id and jobs:
            filtered_jobs = []
            for job in jobs:
                # Check if run_id matches in column
                if job.get("run_id") == run_id:
                    filtered_jobs.append(job)
                # Or check in metadata
                elif job.get("job_metadata"):
                    for metadata in job["job_metadata"]:
                        raw_json = metadata.get("raw_json") or {}
                        if isinstance(raw_json, dict) and raw_json.get("run_id") == run_id:
                            filtered_jobs.append(job)
                            break
            jobs = filtered_jobs
        
        logger.info(f"Fetched {len(jobs)} jobs for UI (run_id={run_id or 'all'})")
        return jobs
    except Exception as e:
        logger.error(f"Failed to retrieve jobs from Supabase: {e}")
        return []
