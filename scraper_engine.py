"""
Main Playwright-based scraper engine for HubSpot domain-level job scraper.

Uses Playwright for browser automation and BeautifulSoup for HTML parsing.
Implements custom recursion logic for crawling company domains.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from bs4 import BeautifulSoup
from career_detector import CareerPageDetector
from extractors import MultiLayerExtractor
from role_classifier import RoleClassifier

logger = logging.getLogger(__name__)

# Domains to skip (social media, link shorteners, etc.)
SKIP_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "fb.com",
    "messenger.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "yelp.com",
    "youtube.com",
    "wix.com",
    "wixstatic.com",
    "godaddy.com",
    "about:blank",
}

# Configuration
MAX_PAGES_PER_DOMAIN = int(os.getenv("MAX_PAGES_PER_DOMAIN", "20"))
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "30000"))  # milliseconds
MAX_DEPTH = int(os.getenv("MAX_DEPTH", "3"))


class JobScraper:
    """Main scraper engine using Playwright."""

    def __init__(self):
        self.career_detector = CareerPageDetector()
        self.role_classifier = RoleClassifier()
        self.browser: Optional[Browser] = None
        self.visited_urls: Set[str] = set()
        self.job_cache: Set[str] = set()
        self.jobs_found: List[Dict] = []
        self.logger = logging.getLogger(self.__class__.__name__)

    async def initialize(self):
        """Initialize Playwright browser."""
        self.logger.info("Initializing Playwright browser...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.logger.info("Browser initialized")

    async def shutdown(self):
        """Shutdown browser cleanly."""
        if self.browser:
            self.logger.info("Shutting down browser...")
            await self.browser.close()
            self.logger.info("Browser closed")

    async def scrape_domain(self, domain_url: str, company_name: str) -> List[Dict]:
        """
        Scrape a single company domain for job postings.

        Args:
            domain_url: The company's website URL
            company_name: The company name

        Returns:
            List of job dicts found on this domain
        """
        self.logger.info("Starting scrape for %s (%s)", company_name, domain_url)
        
        # Reset per-domain state
        self.visited_urls.clear()
        domain_jobs = []

        try:
            # Start with the homepage
            await self._crawl_page(domain_url, company_name, domain_url, depth=0, jobs_list=domain_jobs)

        except Exception as e:
            self.logger.error("Error scraping domain %s: %s", domain_url, e)

        self.logger.info("Found %d jobs for %s", len(domain_jobs), company_name)
        return domain_jobs

    async def _crawl_page(
        self,
        url: str,
        company_name: str,
        root_domain: str,
        depth: int,
        jobs_list: List[Dict]
    ):
        """
        Recursively crawl a page.

        Args:
            url: Page URL to crawl
            company_name: Company name
            root_domain: Root domain for this crawl
            depth: Current recursion depth
            jobs_list: List to append found jobs to
        """
        # Check limits
        if depth > MAX_DEPTH:
            self.logger.debug("Max depth reached for %s", url)
            return

        if len(self.visited_urls) >= MAX_PAGES_PER_DOMAIN:
            self.logger.debug("Max pages limit reached for domain")
            return

        # Normalize URL
        normalized_url = self._normalize_url(url)
        if not normalized_url:
            return

        # Check if already visited
        if normalized_url in self.visited_urls:
            return

        # Check if should skip domain
        if self._should_skip_domain(normalized_url):
            self.logger.debug("Skipping blocked domain: %s", normalized_url)
            return

        # Check if internal to root domain
        if not self._is_internal(normalized_url, root_domain):
            self.logger.debug("Skipping external URL: %s", normalized_url)
            return

        # Mark as visited
        self.visited_urls.add(normalized_url)
        self.logger.debug("Crawling: %s (depth=%d)", normalized_url, depth)

        try:
            # Create a new page
            page = await self.browser.new_page()
            
            try:
                # Navigate to the page with timeout
                await page.goto(normalized_url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(1000)
                
                # Get page content
                html = await page.content()
                
                # Check if this is a career page
                is_career = self.career_detector.is_career_page(normalized_url, html)
                
                if is_career:
                    self.logger.info("Found career page: %s", normalized_url)
                    # Extract jobs from this page
                    await self._extract_jobs_from_page(html, normalized_url, company_name, jobs_list)
                else:
                    # Look for career links on non-career pages
                    career_links = self.career_detector.get_career_links(html, normalized_url)
                    
                    # Recursively crawl career links
                    for career_link in career_links[:5]:  # Limit career links per page
                        await self._crawl_page(
                            career_link,
                            company_name,
                            root_domain,
                            depth + 1,
                            jobs_list
                        )
                
            finally:
                await page.close()

        except PlaywrightTimeout:
            self.logger.warning("Timeout loading page: %s", normalized_url)
        except Exception as e:
            self.logger.warning("Error crawling page %s: %s", normalized_url, e)

    async def _extract_jobs_from_page(
        self,
        html: str,
        page_url: str,
        company_name: str,
        jobs_list: List[Dict]
    ):
        """
        Extract jobs from a career page using multi-layer extraction.

        Args:
            html: HTML content
            page_url: Page URL
            company_name: Company name
            jobs_list: List to append jobs to
        """
        # Use multi-layer extractor
        extractor = MultiLayerExtractor(page_url)
        extracted_jobs = extractor.extract_all(html)

        # Convert HTML to text for classification
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)

        # Process each extracted job
        for job_data in extracted_jobs:
            # Classify and score the job
            classification = self.role_classifier.classify_and_score(page_text, job_data)
            
            if not classification:
                self.logger.debug("Job did not meet scoring threshold: %s", job_data.get('title'))
                continue

            # Check role filters
            if not self.role_classifier.should_include_role(
                classification['role'],
                classification['location_type']
            ):
                continue

            # Build complete job payload
            job_payload = {
                "company": company_name,
                "title": job_data.get('title', 'Unknown Title'),
                "url": job_data.get('url') or page_url,  # Fallback to page URL if no specific job URL
                "summary": job_data.get('summary', ''),
                "role": classification['role'],
                "score": classification['score'],
                "signals": classification['signals'],
                "location_type": classification['location_type'],
                "is_contract": classification.get('is_contract', False),
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "source_page": page_url,
            }

            # Deduplicate based on (title, url)
            job_hash = self._get_job_hash(job_payload)
            if job_hash in self.job_cache:
                self.logger.debug("Duplicate job filtered: %s", job_payload['title'])
                continue

            self.job_cache.add(job_hash)
            jobs_list.append(job_payload)
            self.logger.info(
                "Found job: %s - %s (score: %d, role: %s)",
                company_name,
                job_payload['title'],
                job_payload['score'],
                job_payload['role']
            )

    def _get_job_hash(self, job: Dict) -> str:
        """Generate a hash for job deduplication."""
        key = f"{job['title'].lower()}|{job['url']}"
        return hashlib.sha256(key.encode()).hexdigest()

    def _normalize_url(self, url: str) -> Optional[str]:
        """Normalize a URL."""
        if not url:
            return None

        try:
            # Handle relative URLs
            if not url.startswith(('http://', 'https://')):
                return None

            # Parse and reconstruct to normalize
            parsed = urlparse(url)
            
            # Skip non-http protocols
            if parsed.scheme not in ('http', 'https'):
                return None

            # Reconstruct without fragment
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"

            return normalized

        except Exception:
            return None

    def _should_skip_domain(self, url: str) -> bool:
        """Check if a domain should be skipped."""
        try:
            host = urlparse(url).netloc.lower()
            if host.startswith('www.'):
                host = host[4:]

            return any(host == sd or host.endswith('.' + sd) for sd in SKIP_DOMAINS)

        except Exception:
            return True

    def _is_internal(self, url: str, root_domain: str) -> bool:
        """Check if a URL is internal to the root domain."""
        try:
            url_host = urlparse(url).netloc.lower()
            root_host = urlparse(root_domain).netloc.lower()

            # Remove www. prefix
            if url_host.startswith('www.'):
                url_host = url_host[4:]
            if root_host.startswith('www.'):
                root_host = root_host[4:]

            return url_host == root_host or url_host.endswith('.' + root_host)

        except Exception:
            return False


async def scrape_all_domains(domains_file: str) -> List[Dict]:
    """
    Scrape all domains from a JSON file.

    Args:
        domains_file: Path to JSON file with domain list

    Returns:
        List of all jobs found across all domains
    """
    # Load domains
    domains = load_domains(domains_file)
    if not domains:
        logger.error("No domains loaded from %s", domains_file)
        return []

    logger.info("Loaded %d domains to scrape", len(domains))

    # Initialize scraper
    scraper = JobScraper()
    await scraper.initialize()

    all_jobs = []

    try:
        # Scrape each domain
        for domain_data in domains:
            website = domain_data.get('website')
            company_name = domain_data.get('title', website)

            if not website:
                continue

            jobs = await scraper.scrape_domain(website, company_name)
            all_jobs.extend(jobs)

    finally:
        await scraper.shutdown()

    logger.info("Scraping complete. Total jobs found: %d", len(all_jobs))
    return all_jobs


def load_domains(file_path: str) -> List[Dict]:
    """
    Load domains from JSON file.

    Supports two formats:
    - Array of objects: [{"website": "...", "title": "..."}]
    - Array of strings: ["https://example.com"]
    """
    path = Path(file_path)
    if not path.exists():
        logger.error("Domains file not found: %s", file_path)
        return []

    try:
        with path.open() as f:
            data = json.load(f)

        if not isinstance(data, list):
            logger.error("Domains file must contain a JSON array")
            return []

        domains = []
        for entry in data:
            if isinstance(entry, str):
                domains.append({"website": entry, "title": entry})
            elif isinstance(entry, dict):
                website = entry.get("website") or entry.get("url")
                title = entry.get("title") or website
                if website:
                    domains.append({"website": website, "title": title})

        return domains

    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in domains file: %s", e)
        return []
    except Exception as e:
        logger.error("Error loading domains file: %s", e)
        return []
