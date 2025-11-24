# supabase_persistence.py
import hashlib
from datetime import datetime
from typing import Dict, List, Optional

from supabase import Client

from supabase_client import get_supabase_client


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


def save_jobs_for_domain(
    company_name: str,
    domain: str,
    jobs: List[Dict],
    source_url: Optional[str] = None,
) -> None:
    """
    Persist all jobs for a given domain into Supabase.

    - No-op if Supabase is not configured.
    - Uses domain to dedupe companies.
    - Uses hash to dedupe jobs.
    - Writes metadata when available.
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
            # Optional: Update description/active flags if changed
            # client.table("jobs").update({...}).eq("id", job_id).execute()
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
            resp = client.table("jobs").insert(insert_data).execute()
            job_id = resp.data[0]["id"] if resp.data else None

            # Insert job_metadata if present
            if job_id:
                _save_job_metadata(client, job_id, job)


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
