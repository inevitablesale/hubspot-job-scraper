"""
Integration module to connect the new API server with the existing scraper.

This module bridges the gap between the existing scraper_engine and the new
state-managed API architecture.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from models import (
    CrawlEvent, JobItem, DomainItem,
    NavigationFlowStep, ScreenshotInfo
)
from state import crawler_state, events_bus, logs_buffer
from main import run_scraper, get_domains_file


logger = logging.getLogger(__name__)


class LogCapture(logging.Handler):
    """
    Custom logging handler that captures logs and publishes them to the event bus.
    """
    
    def emit(self, record: logging.LogRecord):
        try:
            # Create a LogLine from the record
            from models import LogLine
            
            log_line = LogLine(
                ts=datetime.fromtimestamp(record.created),
                level=record.levelname.lower(),
                message=self.format(record),
                domain=getattr(record, 'domain', None),
                source="crawler"
            )
            
            # Add to buffer
            logs_buffer.append(log_line)
            
            # Publish to event bus for SSE
            asyncio.create_task(events_bus.publish(log_line))
            
        except Exception as e:
            logger.error(f"Error in log capture: {e}")


async def run_crawl_with_events():
    """
    Run the scraper with event publishing for real-time updates.
    
    This is the main integration function that should be called by
    crawler_state.run_crawl_job.
    """
    try:
        # Get domains
        domains_file = get_domains_file()
        from scraper_engine import load_domains
        domains = load_domains(domains_file)
        
        # Initialize crawler state
        crawler_state.start_run(len(domains))
        
        # Publish start event
        await events_bus.publish(CrawlEvent(
            id=str(uuid4()),
            ts=datetime.utcnow(),
            level="info",
            type="log",
            message=f"Starting crawl of {len(domains)} domains",
            metadata={"domains_count": len(domains)}
        ))
        
        # Process domains
        for idx, domain_data in enumerate(domains):
            # Check for stop request
            if crawler_state._stop_requested:
                logger.info("Stop requested, halting crawl")
                await events_bus.publish(CrawlEvent(
                    id=str(uuid4()),
                    ts=datetime.utcnow(),
                    level="warning",
                    type="log",
                    message="Crawl stopped by user",
                    metadata={}
                ))
                break
            
            # Extract domain name
            if isinstance(domain_data, dict):
                domain_name = domain_data.get("website", "")
                category = domain_data.get("category", "Unknown")
            else:
                domain_name = domain_data
                category = "Unknown"
            
            # Publish domain started event
            await events_bus.publish(CrawlEvent(
                id=str(uuid4()),
                ts=datetime.utcnow(),
                level="info",
                type="domain_started",
                domain=domain_name,
                message=f"Processing {domain_name}",
                metadata={"progress": f"{idx + 1}/{len(domains)}"}
            ))
            
            try:
                # Here you would call the actual scraper
                # For now, we'll use the existing run_scraper but you might want
                # to refactor to scrape individual domains
                
                # This is a placeholder - you should integrate with scraper_engine
                logger.info(f"Scraping {domain_name}")
                
                # Add domain to state
                domain_item = DomainItem(
                    domain=domain_name,
                    category=category,
                    blacklisted=False,
                    last_scraped_at=datetime.utcnow(),
                    jobs_count=0,
                    status="processing"
                )
                crawler_state.add_domain(domain_item)
                
                # Simulate scraping (replace with actual scraper call)
                await asyncio.sleep(0.1)  # Placeholder
                
                # Mark domain as completed
                crawler_state.increment_completed()
                
                # Publish domain finished event
                await events_bus.publish(CrawlEvent(
                    id=str(uuid4()),
                    ts=datetime.utcnow(),
                    level="info",
                    type="domain_finished",
                    domain=domain_name,
                    message=f"Completed {domain_name}",
                    metadata={"jobs_found": 0}
                ))
                
            except Exception as e:
                logger.error(f"Error scraping {domain_name}: {e}")
                crawler_state.increment_errors()
                
                # Publish error event
                await events_bus.publish(CrawlEvent(
                    id=str(uuid4()),
                    ts=datetime.utcnow(),
                    level="error",
                    type="error",
                    domain=domain_name,
                    message=f"Error: {str(e)}",
                    metadata={"error_type": type(e).__name__}
                ))
        
        # Finish the run
        crawler_state.finish_run(success=True)
        
        # Publish completion event
        summary = crawler_state.summary()
        await events_bus.publish(CrawlEvent(
            id=str(uuid4()),
            ts=datetime.utcnow(),
            level="info",
            type="log",
            message=f"Crawl completed: {summary.jobs_found} jobs found from {summary.domains_completed} domains",
            metadata={
                "jobs_found": summary.jobs_found,
                "domains_completed": summary.domains_completed,
                "errors": summary.errors_count
            }
        ))
        
    except Exception as e:
        logger.error(f"Crawl failed: {e}", exc_info=True)
        crawler_state.finish_run(success=False)
        
        # Publish failure event
        await events_bus.publish(CrawlEvent(
            id=str(uuid4()),
            ts=datetime.utcnow(),
            level="error",
            type="error",
            message=f"Crawl failed: {str(e)}",
            metadata={"error_type": type(e).__name__}
        ))


def integrate_with_existing_scraper():
    """
    Hook the new API server into the existing scraper.
    
    Call this function during app startup to replace the placeholder
    run_crawl_job with the actual scraper integration.
    """
    # Replace the placeholder run_crawl_job with the actual implementation
    crawler_state.run_crawl_job = run_crawl_with_events
    
    # Install log capture handler
    log_capture = LogCapture()
    log_capture.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logging.getLogger().addHandler(log_capture)
    
    logger.info("Scraper integration initialized")


# Helper functions for adding data to the state

def add_job_to_state(
    domain: str,
    title: str,
    url: str,
    source_page: str,
    location: Optional[str] = None,
    remote_type: Optional[str] = None,
    ats: Optional[str] = None
) -> JobItem:
    """
    Add a job to the crawler state and publish an event.
    
    Call this from the scraper when a job is found.
    """
    job = JobItem(
        id=str(uuid4()),
        domain=domain,
        title=title,
        location=location,
        remote_type=remote_type,
        url=url,
        source_page=source_page,
        ats=ats,
        created_at=datetime.utcnow()
    )
    
    crawler_state.add_job(job)
    
    # Publish event (async)
    asyncio.create_task(events_bus.publish(CrawlEvent(
        id=str(uuid4()),
        ts=datetime.utcnow(),
        level="info",
        type="job_extracted",
        domain=domain,
        message=f"Found job: {title}",
        metadata={
            "job_id": job.id,
            "title": title,
            "remote_type": remote_type,
            "ats": ats
        }
    )))
    
    return job


def add_navigation_step(
    domain: str,
    step: int,
    url: str,
    step_type: str,
    jobs_found: int = 0,
    screenshot_path: Optional[str] = None
):
    """
    Add a navigation flow step for a domain.
    
    Call this from the scraper to track navigation.
    """
    flow_step = NavigationFlowStep(
        step=step,
        url=url,
        type=step_type,
        timestamp=datetime.utcnow(),
        screenshot=screenshot_path,
        jobs_found=jobs_found
    )
    
    # Get existing flow or create new
    flow = crawler_state.get_navigation_flow(domain)
    flow.append(flow_step)
    crawler_state.set_navigation_flow(domain, flow)
    
    # If there's a screenshot, add it
    if screenshot_path:
        screenshot = ScreenshotInfo(
            filename=screenshot_path.split('/')[-1],
            url=screenshot_path,
            step=step,
            timestamp=datetime.utcnow(),
            description=f"{step_type} page"
        )
        crawler_state.add_screenshot(domain, screenshot)


def update_domain_status(
    domain: str,
    status: str,
    career_page: Optional[str] = None,
    ats: Optional[str] = None,
    jobs_count: int = 0
):
    """
    Update domain information in the state.
    
    Call this from the scraper as domain info is discovered.
    """
    # Get or create domain item
    domain_item = crawler_state.get_domain(domain)
    
    if domain_item:
        # Update existing
        domain_item.status = status
        domain_item.last_scraped_at = datetime.utcnow()
        if career_page:
            domain_item.career_page = career_page
        if ats:
            domain_item.ats = ats
        if jobs_count > 0:
            domain_item.jobs_count = jobs_count
    else:
        # Create new
        domain_item = DomainItem(
            domain=domain,
            blacklisted=False,
            last_scraped_at=datetime.utcnow(),
            career_page=career_page,
            ats=ats,
            jobs_count=jobs_count,
            status=status
        )
    
    crawler_state.add_domain(domain_item)
    
    # Publish event if career page found
    if career_page and status == "career_page_found":
        asyncio.create_task(events_bus.publish(CrawlEvent(
            id=str(uuid4()),
            ts=datetime.utcnow(),
            level="info",
            type="career_page_found",
            domain=domain,
            message=f"Found career page: {career_page}",
            metadata={"career_page": career_page, "ats": ats}
        )))


# Example usage in scraper
"""
# In your scraper code:

from integration import add_job_to_state, add_navigation_step, update_domain_status

# When starting to scrape a domain
update_domain_status("example.com", "starting")
add_navigation_step("example.com", 1, "https://example.com", "homepage")

# When career page is found
update_domain_status("example.com", "career_page_found", 
                     career_page="https://example.com/careers", 
                     ats="Greenhouse")
add_navigation_step("example.com", 2, "https://example.com/careers", "careers")

# When a job is found
job = add_job_to_state(
    domain="example.com",
    title="Senior Software Engineer",
    url="https://example.com/jobs/123",
    source_page="https://example.com/careers",
    location="San Francisco, CA",
    remote_type="hybrid",
    ats="Greenhouse"
)

# When domain is complete
update_domain_status("example.com", "completed", jobs_count=5)
"""
