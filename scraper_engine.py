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
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from bs4 import BeautifulSoup
from career_detector import CareerPageDetector
from extractors import MultiLayerExtractor
from role_classifier import RoleClassifier
from ats_detectors import ATSDetector, ATSFetcher
from enhanced_extractors import (
    MicrodataExtractor,
    OpenGraphExtractor,
    MetaTagExtractor,
    JavaScriptDataExtractor,
    CMSPatternExtractor,
)
from normalization import JobNormalizer, TitleClassifier
from deduplication import JobDeduplicator, IncrementalTracker, CompanyHealthAnalyzer
from extraction_utils import (
    NoJobsDetector,
    ExtractionReporter,
    RateLimiter,
    RobotsTxtChecker,
)
from blacklist import DomainBlacklist
from logging_config import get_logger
from supabase_persistence import save_jobs_for_domain, create_scrape_run, update_scrape_run, get_or_create_company
from supabase_client import get_supabase_client

logger = get_logger(__name__)

# Legacy SKIP_DOMAINS - kept for backwards compatibility
# The comprehensive blacklist is now in blacklist.py
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

# Configuration (from problem statement requirements)
MAX_PAGES_PER_DOMAIN = int(os.getenv("MAX_PAGES_PER_DOMAIN", "12"))  # Set to 12 per requirements
PAGE_TIMEOUT = int(os.getenv("PAGE_TIMEOUT", "30000"))  # milliseconds
MAX_DEPTH = int(os.getenv("MAX_DEPTH", "2"))  # Set to 2 per requirements
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))  # seconds per domain
ENABLE_HTML_ARCHIVE = os.getenv("ENABLE_HTML_ARCHIVE", "false").lower() == "true"
HTML_ARCHIVE_DIR = Path(os.getenv("HTML_ARCHIVE_DIR", "/tmp/html_archive"))
JOB_TRACKING_CACHE = Path(os.getenv("JOB_TRACKING_CACHE", ".job_tracking.json"))


class JobScraper:
    """Main scraper engine using Playwright with enterprise features."""

    def __init__(self):
        self.career_detector = CareerPageDetector()
        self.role_classifier = RoleClassifier()
        self.ats_detector = ATSDetector()
        self.ats_fetcher = ATSFetcher()
        self.job_normalizer = JobNormalizer()
        self.title_classifier = TitleClassifier()
        self.job_deduplicator = JobDeduplicator()
        self.no_jobs_detector = NoJobsDetector()
        self.rate_limiter = RateLimiter(default_delay=RATE_LIMIT_DELAY)
        self.robots_checker = RobotsTxtChecker()
        self.extraction_reporter = ExtractionReporter(
            archive_dir=HTML_ARCHIVE_DIR if ENABLE_HTML_ARCHIVE else None
        )
        self.incremental_tracker = IncrementalTracker(JOB_TRACKING_CACHE)
        self.health_analyzer = CompanyHealthAnalyzer()
        self.domain_blacklist = DomainBlacklist()
        
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
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        self.logger.info("Browser initialized")

    async def shutdown(self):
        """Shutdown browser cleanly and save tracking data."""
        # Save incremental tracking cache
        self.incremental_tracker.save_cache()
        
        # Log extraction summary
        summary = self.extraction_reporter.get_extraction_summary()
        self.logger.info(
            "Extraction summary: %d total, %d successes, %d failures",
            summary['total_extractions'],
            summary['total_successes'],
            summary['total_failures']
        )
        
        if self.browser:
            self.logger.info("Shutting down browser...")
            await self.browser.close()
            self.logger.info("Browser closed")

    async def scrape_domain(self, domain_url: str, company_name: str, page: Optional[Page] = None, run_id: Optional[str] = None) -> List[Dict]:
        """
        Scrape a single company domain for job postings.
        
        Enhanced logging as per problem statement:
        - [DOMAIN] Starting discovery...
        - [DISCOVERY] Found potential careers link
        - [SKIP] Footer/social link skipped / Header navigation ignored
        - [CAREERS] Navigating to
        - [JOB] Title: ... Source: ...
        - [ATS] Detection messages
        - [COMPLETE] Domain: ... | Jobs found: ...

        Args:
            domain_url: The company's website URL
            company_name: The company name
            page: Optional Page instance to use. If provided, uses this page directly.
                  If None, creates a new context and page internally (backward compatibility).
            run_id: Optional scrape run ID to associate jobs with

        Returns:
            List of job dicts found on this domain
        """
        # Enhanced logging per requirements
        self.logger.info("[DOMAIN] Starting discovery...")
        self.logger.info(f"Root URL: {domain_url}")
        
        # Reset per-domain state
        self.visited_urls.clear()
        domain_jobs = []

        try:
            # Start with the homepage
            await self._crawl_page(domain_url, company_name, domain_url, depth=0, jobs_list=domain_jobs, page=page)

        except Exception as e:
            self.logger.error("Error scraping domain %s: %s", domain_url, e)

        # Enhanced completion logging per requirements
        self.logger.info(f"[COMPLETE] Domain: {domain_url} | Jobs found: {len(domain_jobs)}")
        
        # Analyze hiring trends and generate health signals
        changes = self.incremental_tracker.get_changes(company_name)
        if changes['new'] or changes['removed'] or changes['updated']:
            health_analysis = self.health_analyzer.analyze_hiring_trend(changes)
            self.logger.info(
                "Company health for %s: %s (%s)",
                company_name,
                health_analysis['trend'],
                health_analysis['reason']
            )
            
            # Attach health analysis to company metadata
            for job in domain_jobs:
                job['company_health'] = health_analysis
        
        # Save jobs to Supabase (if configured)
        if run_id and domain_jobs:
            try:
                # Extract clean domain from URL
                parsed = urlparse(domain_url)
                domain = parsed.netloc
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Get or create company
                company_id = get_or_create_company(
                    client=get_supabase_client(),
                    name=company_name,
                    domain=domain,
                    source_url=domain_url,
                )
                
                if company_id:
                    # Prepare jobs with all required fields
                    # Use single timestamp for all jobs in this batch for consistency
                    batch_timestamp = datetime.utcnow().isoformat()
                    prepared_jobs = []
                    for job in domain_jobs:
                        prepared_job = {
                            "job_title": job.get("title") or job.get("job_title") or "Unknown",
                            "job_url": job.get("url") or job.get("job_url") or "",
                            "department": job.get("department") or "other",
                            "location": job.get("location") or "",
                            "remote_type": job.get("remote_type") or job.get("location_type") or "",
                            "description": job.get("summary") or job.get("description") or "",
                            "posted_at": job.get("posted_at"),
                            "scraped_at": job.get("timestamp") or batch_timestamp,
                            "hash": hashlib.sha256(f"{company_id}:{job.get('title', '')}:{job.get('url', '')}".encode()).hexdigest(),
                            "active": True,
                            "ats_provider": job.get("ats_provider") or job.get("extraction_source") or "hubspot",
                        }
                        prepared_jobs.append(prepared_job)
                    
                    save_jobs_for_domain(
                        run_id=run_id,
                        company_id=company_id,
                        jobs=prepared_jobs,
                    )
                    
                    self.logger.info(f"Saved {len(prepared_jobs)} jobs to Supabase for domain={domain}, run_id={run_id}")
            except Exception as e:
                self.logger.error(
                    "Error saving jobs to Supabase",
                    extra={"domain": domain_url, "run_id": run_id, "error": str(e)},
                )
        
        return domain_jobs

    async def _crawl_page(
        self,
        url: str,
        company_name: str,
        root_domain: str,
        depth: int,
        jobs_list: List[Dict],
        page: Optional[Page] = None
    ):
        """
        Recursively crawl a page.

        Args:
            url: Page URL to crawl
            company_name: Company name
            root_domain: Root domain for this crawl
            depth: Current recursion depth
            jobs_list: List to append found jobs to
            page: Optional Page instance. If provided for depth=0, will be used for first page.
                  Subsequent recursive calls will create new pages from browser.
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
        if not self._is_internal_strict(normalized_url, root_domain):
            # Check if it's an allowed ATS redirect
            if self.ats_detector.is_allowed_ats_redirect(normalized_url):
                self.logger.info("Following allowed ATS redirect: %s", normalized_url)
            elif self.ats_detector.is_banned_redirect(normalized_url):
                self.logger.info("Blocking banned redirect: %s", normalized_url)
                return
            else:
                self.logger.debug("Skipping external URL: %s", normalized_url)
                return

        # Check robots.txt
        can_crawl = await self.robots_checker.can_crawl(normalized_url)
        if not can_crawl:
            self.logger.debug("Blocked by robots.txt: %s", normalized_url)
            return

        # Apply rate limiting
        domain = urlparse(normalized_url).netloc
        delay = self.rate_limiter.get_delay(domain)
        if delay > 0:
            self.logger.debug("Rate limiting: waiting %.1fs for %s", delay, domain)
            await asyncio.sleep(delay)

        # Mark as visited
        self.visited_urls.add(normalized_url)
        self.logger.debug("Crawling: %s (depth=%d)", normalized_url, depth)

        # Ensure browser is initialized (needed for recursive calls)
        if not self.browser:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        try:
            # Use provided page for first page, or create a new one
            page_created_here = False
            if page is None:
                page = await self.browser.new_page()
                page_created_here = True
            
            try:
                # Navigate to the page with timeout
                await page.goto(normalized_url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(1000)
                
                # Get page content
                html = await page.content()
                
                # Record success
                self.rate_limiter.record_success(domain)
                
                # Check if this is a career page
                is_career = self.career_detector.is_career_page(normalized_url, html)
                
                if is_career:
                    # Enhanced logging per requirements
                    self.logger.info(f"[CAREERS] Navigating to: {normalized_url}")
                    
                    # Extract jobs from this page
                    await self._extract_jobs_from_page(html, normalized_url, company_name, jobs_list)
                    
                    # IMPORTANT: Stop crawling once career page is found (per requirements)
                    # This prevents unnecessary deep crawling
                    return
                else:
                    # Look for career links on non-career pages
                    career_links = self.career_detector.get_career_links(html, normalized_url)
                    
                    if career_links:
                        self.logger.debug(
                            "Found career link candidates",
                            extra={
                                "url": normalized_url,
                                "candidates": career_links[:5],
                                "count": len(career_links)
                            }
                        )
                    
                    # Recursively crawl career links
                    for career_link in career_links[:5]:  # Limit career links per page
                        await self._crawl_page(
                            career_link,
                            company_name,
                            root_domain,
                            depth + 1,
                            jobs_list,
                            page=None  # Force new page for each recursive URL to maintain isolation
                        )
                        # If we found jobs, stop crawling (per requirements)
                        if jobs_list:
                            return
                
            finally:
                # Only close the page if we created it here
                if page_created_here:
                    await page.close()

        except PlaywrightTimeout:
            self.logger.warning("Timeout loading page: %s", normalized_url)
            self.rate_limiter.record_failure(domain)
        except Exception as e:
            self.logger.warning("Error crawling page %s: %s", normalized_url, e)
            self.rate_limiter.record_failure(domain)

    async def _extract_jobs_from_page(
        self,
        html: str,
        page_url: str,
        company_name: str,
        jobs_list: List[Dict]
    ):
        """
        Extract jobs from a career page using progressive fallback extraction.

        Args:
            html: HTML content
            page_url: Page URL
            company_name: Company name
            jobs_list: List to append jobs to
        """
        self.logger.debug(
            "🔍 Scanning page for jobs",
            extra={"url": page_url, "company": company_name}
        )
        
        # Check for "no jobs available" first
        if self.no_jobs_detector.has_no_jobs(html):
            self.logger.info(
                "ℹ️  No jobs available on page",
                extra={"company": company_name, "url": page_url}
            )
            self.extraction_reporter.archive_html(page_url, html, success=True, jobs_found=0)
            return

        # Detect ATS
        ats_type = self.ats_detector.detect_ats(html, page_url)
        if ats_type:
            # Enhanced logging per requirements
            self.logger.info(f"[ATS] {ats_type} detected. Scraping via embedded jobs list.")
            await self._extract_from_ats(ats_type, page_url, company_name, jobs_list)
            return

        # Progressive fallback extraction
        all_extracted_jobs = []

        # Layer 1: Structured data (highest priority)
        try:
            json_ld_extractor = MultiLayerExtractor(page_url).extractors[0]  # JSON-LD
            jobs = json_ld_extractor.extract(html)
            all_extracted_jobs.extend(jobs)
            self.extraction_reporter.log_extraction_success('json_ld', page_url, len(jobs))
        except Exception as e:
            self.extraction_reporter.log_extractor_failure('json_ld', page_url, e)

        # Layer 2: Enhanced structured extractors
        for extractor_class, name in [
            (MicrodataExtractor, 'microdata'),
            (OpenGraphExtractor, 'opengraph'),
            (MetaTagExtractor, 'meta_tags'),
        ]:
            try:
                extractor = extractor_class(page_url)
                jobs = extractor.extract(html)
                all_extracted_jobs.extend(jobs)
                self.extraction_reporter.log_extraction_success(name, page_url, len(jobs))
            except Exception as e:
                self.extraction_reporter.log_extractor_failure(name, page_url, e)

        # Layer 3: JavaScript data
        try:
            js_extractor = JavaScriptDataExtractor(page_url)
            jobs = js_extractor.extract(html)
            all_extracted_jobs.extend(jobs)
            self.extraction_reporter.log_extraction_success('javascript', page_url, len(jobs))
        except Exception as e:
            self.extraction_reporter.log_extractor_failure('javascript', page_url, e)

        # Layer 4: CMS-specific patterns
        try:
            cms_extractor = CMSPatternExtractor(page_url)
            jobs = cms_extractor.extract(html)
            all_extracted_jobs.extend(jobs)
            self.extraction_reporter.log_extraction_success('cms', page_url, len(jobs))
        except Exception as e:
            self.extraction_reporter.log_extractor_failure('cms', page_url, e)

        # Layer 5: Standard multi-layer extractor (anchors, buttons, sections, headings)
        try:
            extractor = MultiLayerExtractor(page_url)
            jobs = extractor.extract_all(html)
            all_extracted_jobs.extend(jobs)
            self.extraction_reporter.log_extraction_success('multi_layer', page_url, len(jobs))
        except Exception as e:
            self.extraction_reporter.log_extractor_failure('multi_layer', page_url, e)

        # Convert HTML to text for classification
        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)

        # Process and deduplicate jobs
        jobs_added = 0
        for job_data in all_extracted_jobs:
            # Cross-layer deduplication
            if self.job_deduplicator.is_duplicate(job_data, use_fuzzy=True):
                continue

            # Normalize job data
            normalized_job = self._normalize_job(job_data, page_text)
            if not normalized_job:
                continue

            # Classify and score the job
            classification = self.role_classifier.classify_and_score(page_text, normalized_job)
            
            if not classification:
                self.logger.debug("Job did not meet scoring threshold: %s", normalized_job.get('title'))
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
                "title": normalized_job.get('title', 'Unknown Title'),
                "url": normalized_job.get('url') or page_url,
                "summary": normalized_job.get('summary', ''),
                "location": normalized_job.get('location', ''),
                "role": classification['role'],
                "score": classification['score'],
                "signals": classification['signals'],
                "location_type": classification['location_type'],
                "is_contract": classification.get('is_contract', False),
                "department": normalized_job.get('department', 'other'),
                "seniority": normalized_job.get('seniority', 'mid'),
                "employment_type": normalized_job.get('employment_type', 'full_time'),
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "source_page": page_url,
                "extraction_source": job_data.get('source', 'unknown'),
            }

            jobs_list.append(job_payload)
            self.incremental_tracker.add_job(company_name, job_payload)
            jobs_added += 1
            
            # Enhanced logging per requirements - full job details
            title = job_payload.get("title")
            url = job_payload.get("url") or job_payload.get("apply_url")
            desc = job_payload.get("summary") or job_payload.get("description") or job_payload.get("body") or ""
            
            # Truncate descriptions for log readability
            desc_snippet = (desc[:200] + "...") if len(desc) > 200 else desc
            
            self.logger.info("──────── JOB EXTRACTED ────────")
            self.logger.info(f"📌 Title: {title}")
            self.logger.info(f"🔗 URL: {url}")
            self.logger.info(f"📝 Description: {desc_snippet}")
            self.logger.info("────────────────────────────────")
            
            self.logger.debug(
                "✓ Job matched filters: %s - %s (score: %d, role: %s, source: %s)",
                company_name,
                job_payload['title'],
                job_payload['score'],
                job_payload['role'],
                job_payload['extraction_source']
            )

        # Archive HTML if enabled
        self.extraction_reporter.archive_html(page_url, html, success=jobs_added > 0, jobs_found=jobs_added)
        
        # Summary logging
        if jobs_added > 0:
            self.logger.info(
                "📝 Jobs extracted from page",
                extra={
                    "url": page_url,
                    "company": company_name,
                    "raw_extractions": len(all_extracted_jobs),
                    "filtered_jobs": jobs_added
                }
            )
        else:
            self.logger.debug(
                "No qualifying jobs on page",
                extra={
                    "url": page_url,
                    "raw_extractions": len(all_extracted_jobs)
                }
            )

    async def _extract_from_ats(
        self,
        ats_type: str,
        page_url: str,
        company_name: str,
        jobs_list: List[Dict]
    ):
        """Extract jobs from ATS API."""
        identifier = self.ats_fetcher.extract_ats_identifier(page_url, ats_type)
        if not identifier:
            self.logger.warning("Could not extract ATS identifier from %s", page_url)
            return

        try:
            if ats_type == "greenhouse":
                jobs = await self.ats_fetcher.fetch_greenhouse_jobs(identifier)
            elif ats_type == "lever":
                jobs = await self.ats_fetcher.fetch_lever_jobs(identifier)
            elif ats_type == "workable":
                jobs = await self.ats_fetcher.fetch_workable_jobs(identifier)
            else:
                self.logger.warning("ATS type %s not supported yet", ats_type)
                return

            # Process ATS jobs
            for job in jobs:
                # Normalize
                normalized_job = self._normalize_job(job, "")
                
                # Deduplicate
                if self.job_deduplicator.is_duplicate(normalized_job):
                    continue

                jobs_list.append({
                    **normalized_job,
                    "company": company_name,
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "extraction_source": f"ats_{ats_type}",
                })
                self.incremental_tracker.add_job(company_name, normalized_job)

            self.logger.info("Extracted %d jobs from %s ATS", len(jobs), ats_type)

        except Exception as e:
            self.logger.error("Failed to extract from ATS: %s", e)

    def _normalize_job(self, job: Dict, context_text: str = "") -> Optional[Dict]:
        """
        Normalize job data.

        Args:
            job: Raw job dict
            context_text: Context text for classification

        Returns:
            Normalized job dict or None
        """
        title = job.get('title', '')
        if not title:
            return None

        # Normalize fields
        normalized_title = self.job_normalizer.normalize_title(title)
        location_data = self.job_normalizer.normalize_location(job.get('location', ''))
        summary = self.job_normalizer.normalize_summary(job.get('summary', ''))
        
        # Classify title
        title_classification = self.title_classifier.classify_title(normalized_title)
        
        # Detect employment type
        text_for_analysis = f"{title} {summary} {context_text}"
        employment_type = self.job_normalizer.normalize_employment_type(text_for_analysis)
        
        return {
            'title': normalized_title,
            'url': job.get('url'),
            'summary': summary,
            'location': location_data['raw'],
            'location_type': location_data['type'],
            'location_city': location_data['city'],
            'location_state': location_data['state'],
            'location_country': location_data['country'],
            'department': title_classification['department'],
            'seniority': title_classification['seniority'],
            'employment_type': employment_type,
            'is_technical': title_classification['is_technical'],
            'is_leadership': title_classification['is_leadership'],
            'is_hubspot_focused': title_classification['is_hubspot_focused'],
            'source': job.get('source', 'unknown'),
        }

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
        """
        Check if a domain should be skipped.
        
        Uses comprehensive blacklist from blacklist.py which includes:
        - Social media platforms
        - Publishing platforms
        - HubSpot ecosystem domains
        - Analytics/tracking domains
        - Unrelated major domains
        - Legacy SKIP_DOMAINS for backwards compatibility
        """
        # Check comprehensive blacklist
        if self.domain_blacklist.is_blacklisted_domain(url):
            return True
        
        # Also check legacy SKIP_DOMAINS for backwards compatibility
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

    def _is_internal_strict(self, url: str, root_domain: str) -> bool:
        """
        Strict domain confinement check.
        
        Enforces:
        - Same domain only
        - No query param explosions
        - Blocks calendars/contact pages
        """
        # Basic domain check
        if not self._is_internal(url, root_domain):
            return False

        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Block calendar pages
            if any(blocked in path for blocked in ['/calendar', '/schedule', '/book']):
                self.logger.debug("Blocking calendar page: %s", url)
                return False
            
            # Block contact/support pages (unless they're career-related)
            if any(blocked in path for blocked in ['/contact', '/support']):
                if 'career' not in path and 'job' not in path:
                    self.logger.debug("Blocking contact page: %s", url)
                    return False
            
            # Limit query parameters to prevent explosion
            if parsed.query:
                params = parsed.query.split('&')
                if len(params) > 5:
                    self.logger.debug("Too many query params: %s", url)
                    return False
            
            return True

        except Exception:
            return False


async def scrape_all_domains(domains_file: str, progress_callback=None) -> Tuple[List[Dict], Optional[str]]:
    """
    Scrape all domains from a JSON file.

    Args:
        domains_file: Path to JSON file with domain list
        progress_callback: Optional callback function called after each domain with
                          (domain_idx, total_domains, jobs_from_domain, all_jobs_so_far)

    Returns:
        Tuple of (list of all jobs found, run_id if created)
    """
    from datetime import datetime
    
    start_time = datetime.utcnow()
    
    # Load domains
    domains = load_domains(domains_file)
    if not domains:
        logger.error("No domains loaded from %s", domains_file)
        return [], None

    logger.info(
        "📋 Starting crawl run",
        extra={
            "domains_count": len(domains),
            "source": domains_file
        }
    )
    
    # Create scrape run in Supabase
    run_id = create_scrape_run()
    if run_id:
        logger.info(f"Created scrape run with ID: {run_id}")

    all_jobs = []
    success_count = 0
    failed_count = 0

    # Create a single scraper instance for all domains
    scraper = JobScraper()
    await scraper.initialize()

    try:
        # Scrape each domain with a new browser context
        for idx, domain_data in enumerate(domains, 1):
            website = domain_data.get('website')
            company_name = domain_data.get('title', website)

            if not website:
                logger.warning(
                    "Skipping entry with no website",
                    extra={"index": idx, "data": domain_data}
                )
                continue

            logger.info(
                "🌐 Starting domain [%d/%d]",
                idx,
                len(domains),
                extra={"domain": website, "company": company_name}
            )

            # Create a new isolated browser context for this domain
            context = None
            page = None
            try:
                context = await scraper.browser.new_context()
                page = await context.new_page()
                
                # Scrape the domain using the isolated context's page, passing run_id
                jobs = await scraper.scrape_domain(website, company_name, page=page, run_id=run_id)
                all_jobs.extend(jobs)
                
                if jobs:
                    success_count += 1
                    logger.info(
                        "✅ Domain complete",
                        extra={
                            "domain": website,
                            "jobs_found": len(jobs),
                            "progress": f"{idx}/{len(domains)}"
                        }
                    )
                else:
                    logger.info(
                        "ℹ️  Domain complete - no jobs found",
                        extra={
                            "domain": website,
                            "progress": f"{idx}/{len(domains)}"
                        }
                    )
                
                # Call progress callback if provided
                if progress_callback:
                    await progress_callback(idx, len(domains), jobs, all_jobs)
                
                # Update scrape run progress after each domain
                if run_id:
                    update_scrape_run(run_id, {
                        "last_domain": website,
                        "domains_completed": idx
                    })
                    
            except Exception as e:
                failed_count += 1
                logger.error(
                    "❌ Domain failed",
                    extra={
                        "domain": website,
                        "error": str(e),
                        "progress": f"{idx}/{len(domains)}"
                    },
                    exc_info=False
                )
                
                # Call progress callback even on failure
                if progress_callback:
                    await progress_callback(idx, len(domains), [], all_jobs)
            finally:
                # Always close the browser context after each domain
                if page:
                    await page.close()
                if context:
                    await context.close()
    finally:
        # Always shutdown the browser after all domains are processed
        await scraper.shutdown()
        
        # Mark scrape run as finished
        if run_id:
            update_scrape_run(run_id, {"active": False})
    
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    logger.info(
        "🏁 Crawl run completed",
        extra={
            "run_id": run_id,
            "domains_total": len(domains),
            "domains_success": success_count,
            "domains_failed": failed_count,
            "jobs_found": len(all_jobs),
            "duration_seconds": round(duration, 2)
        }
    )
    
    return all_jobs, run_id


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
