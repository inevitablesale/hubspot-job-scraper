"""
Main entry point for HubSpot domain-level job scraper.

Uses Playwright-based scraper engine with multi-layer extraction.
"""

import asyncio
import logging
import os
from pathlib import Path

from scraper_engine import scrape_all_domains
from notifier import JobNotifier

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

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

    logger.error("No domains file found. Set DOMAINS_FILE env var or mount at /etc/secrets/DOMAINS_FILE")
    raise FileNotFoundError("Domains file not found")


async def run_scraper():
    """Main scraper execution."""
    logger.info("Starting HubSpot domain-level job scraper")

    try:
        # Get domains file
        domains_file = get_domains_file()
        logger.info("Using domains file: %s", domains_file)

        # Run the scraper
        jobs = await scrape_all_domains(domains_file)

        logger.info("Scraping complete. Found %d jobs total", len(jobs))

        # Send notifications
        if jobs:
            notifier = JobNotifier()
            await notifier.send_notifications(jobs)
            logger.info("Notifications sent")
        else:
            logger.info("No jobs found to notify about")

    except Exception as e:
        logger.error("Scraper failed: %s", e, exc_info=True)
        raise


def main():
    """Synchronous entry point."""
    asyncio.run(run_scraper())


if __name__ == "__main__":
    main()
