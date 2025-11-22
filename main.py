"""
Main entry point for HubSpot domain-level job scraper.

Uses Playwright-based scraper engine with multi-layer extraction.

This module provides the run_scraper() function for programmatic invocation
(e.g., from FastAPI server). It does NOT auto-run when imported.
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from scraper_engine import scrape_all_domains
from notifier import JobNotifier
from logging_config import setup_logging, get_logger

# Configure logging on module load
logger = setup_logging("hubspot_scraper")

# Domain file location
DATASET_ENV_VAR = "DOMAINS_FILE"
RENDER_SECRET_DATASET = Path("/etc/secrets/DOMAINS_FILE")


def get_domains_file() -> str:
    """Get the path to the domains file."""
    env_path = os.getenv(DATASET_ENV_VAR)
    if env_path:
        return env_path

    if RENDER_SECRET_DATASET.exists():
        return str(RENDER_SECRET_DATASET)

    # Fallback to example_domains.json for demo/testing
    example_file = Path(__file__).parent / "example_domains.json"
    if example_file.exists():
        logger.warning(
            "Using example_domains.json as fallback. "
            "Set DOMAINS_FILE env var or mount at /etc/secrets/DOMAINS_FILE for production."
        )
        return str(example_file)

    logger.error("No domains file found. Set DOMAINS_FILE env var or mount at /etc/secrets/DOMAINS_FILE")
    raise FileNotFoundError("Domains file not found")


async def run_scraper(domains_file: Optional[str] = None) -> List[Dict]:
    """
    Main scraper execution function.
    
    This is the primary entry point used by the FastAPI control room.
    
    Args:
        domains_file: Path to domains JSON file. If None, uses environment/default.
        
    Returns:
        List of all jobs found across all domains
    """
    start_time = datetime.utcnow()
    
    logger.info(
        "🚀 Starting HubSpot domain-level job scraper",
        extra={"requested_by": "control_room" if domains_file is None else "cli"}
    )

    try:
        # Get domains file
        if domains_file is None:
            domains_file = get_domains_file()
        
        logger.info("Using domains file: %s", domains_file)

        # Run the scraper
        jobs = await scrape_all_domains(domains_file)
        
        duration = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            "✅ Scraping complete",
            extra={
                "jobs_found": len(jobs),
                "duration_seconds": round(duration, 2)
            }
        )

        # Send notifications
        if jobs:
            notifier = JobNotifier()
            await notifier.send_notifications(jobs)
            logger.info("Notifications sent", extra={"job_count": len(jobs)})
        else:
            logger.info("No jobs found to notify about")
        
        return jobs

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.error(
            "❌ Scraper failed",
            extra={
                "error": str(e),
                "duration_seconds": round(duration, 2)
            },
            exc_info=True
        )
        raise


def main():
    """
    Synchronous entry point for CLI usage.
    
    This is only used for local development/testing.
    In production (Docker/Render), the FastAPI server is used instead.
    """
    asyncio.run(run_scraper())


# Only run if executed directly, NOT when imported
if __name__ == "__main__":
    main()
