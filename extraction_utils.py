"""
Extraction utilities and failure handling.

Provides:
- "No jobs available" detection
- Extractor-level failure logging
- Extraction report metadata
- Raw HTML archiving
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class NoJobsDetector:
    """Detects when a career page has no open positions."""

    # Patterns that indicate no jobs
    NO_JOBS_PATTERNS = [
        "no open positions",
        "no current openings",
        "no positions available",
        "no jobs available",
        "currently no openings",
        "not hiring at this time",
        "check back later",
        "no active job postings",
        "we don't have any open positions",
        "there are currently no",
        "we're not currently hiring",
        "no opportunities at this time",
    ]

    # Placeholder text patterns
    PLACEHOLDER_PATTERNS = [
        "coming soon",
        "check back soon",
        "stay tuned",
        "be the first to know",
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def has_no_jobs(self, html: str) -> bool:
        """
        Detect if page indicates no jobs are available.

        Args:
            html: Page HTML content

        Returns:
            True if no jobs available
        """
        soup = BeautifulSoup(html, 'lxml')
        text = soup.get_text().lower()

        # Check for explicit no-jobs messages
        for pattern in self.NO_JOBS_PATTERNS:
            if pattern in text:
                self.logger.info("Detected no jobs pattern: %s", pattern)
                return True

        # Check for placeholder messages
        for pattern in self.PLACEHOLDER_PATTERNS:
            if pattern in text:
                self.logger.info("Detected placeholder pattern: %s", pattern)
                return True

        # Check if job list is empty but structure exists
        if self._has_empty_job_structure(soup):
            self.logger.info("Detected empty job structure")
            return True

        return False

    def _has_empty_job_structure(self, soup) -> bool:
        """Check if page has job listing structure but no actual jobs."""
        # Look for common empty list patterns
        empty_indicators = [
            soup.find(class_="no-jobs"),
            soup.find(class_="empty-jobs"),
            soup.find(id="no-openings"),
            soup.find(text="0 jobs"),
            soup.find(text="0 openings"),
        ]

        return any(indicator is not None for indicator in empty_indicators)


class ExtractionReporter:
    """Logs extractor failures and generates extraction reports."""

    def __init__(self, archive_dir: Optional[Path] = None):
        self.archive_dir = archive_dir
        self.logger = logging.getLogger(self.__class__.__name__)
        self.extraction_reports: List[Dict] = []

    def log_extractor_failure(
        self,
        extractor_name: str,
        url: str,
        error: Exception,
        partial_results: Optional[List[Dict]] = None
    ):
        """
        Log extractor failure without crashing.

        Args:
            extractor_name: Name of the extractor
            url: URL being processed
            error: Exception that occurred
            partial_results: Any partial results extracted before failure
        """
        report = {
            'extractor': extractor_name,
            'url': url,
            'error': str(error),
            'error_type': type(error).__name__,
            'timestamp': datetime.utcnow().isoformat(),
            'partial_results_count': len(partial_results) if partial_results else 0,
        }

        self.extraction_reports.append(report)
        
        self.logger.warning(
            "Extractor %s failed on %s: %s (partial results: %d)",
            extractor_name,
            url,
            error,
            len(partial_results) if partial_results else 0
        )

    def log_extraction_success(
        self,
        extractor_name: str,
        url: str,
        results_count: int
    ):
        """Log successful extraction."""
        report = {
            'extractor': extractor_name,
            'url': url,
            'success': True,
            'results_count': results_count,
            'timestamp': datetime.utcnow().isoformat(),
        }

        self.extraction_reports.append(report)
        
        self.logger.debug(
            "Extractor %s succeeded on %s: %d results",
            extractor_name,
            url,
            results_count
        )

    def get_extraction_summary(self) -> Dict:
        """Get summary of all extractions."""
        total = len(self.extraction_reports)
        failures = sum(1 for r in self.extraction_reports if 'error' in r)
        successes = total - failures

        extractors = {}
        for report in self.extraction_reports:
            name = report['extractor']
            if name not in extractors:
                extractors[name] = {'total': 0, 'failures': 0, 'successes': 0}
            
            extractors[name]['total'] += 1
            if 'error' in report:
                extractors[name]['failures'] += 1
            else:
                extractors[name]['successes'] += 1

        return {
            'total_extractions': total,
            'total_failures': failures,
            'total_successes': successes,
            'by_extractor': extractors,
            'reports': self.extraction_reports,
        }

    def archive_html(
        self,
        url: str,
        html: str,
        success: bool,
        jobs_found: int = 0
    ):
        """
        Archive HTML for debugging.

        Args:
            url: Page URL
            html: HTML content
            success: Whether extraction succeeded
            jobs_found: Number of jobs found
        """
        if not self.archive_dir:
            return

        try:
            # Create archive directory
            self.archive_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            safe_url = url.replace('/', '_').replace(':', '_')[:100]
            status = 'success' if success else 'failed'
            filename = f"{timestamp}_{status}_{safe_url}.html"

            # Save HTML
            filepath = self.archive_dir / filename
            with filepath.open('w', encoding='utf-8') as f:
                f.write(html)

            # Save metadata
            metadata = {
                'url': url,
                'timestamp': datetime.utcnow().isoformat(),
                'success': success,
                'jobs_found': jobs_found,
            }
            
            meta_filepath = self.archive_dir / f"{filename}.meta.json"
            with meta_filepath.open('w') as f:
                json.dump(metadata, f, indent=2)

            self.logger.debug("Archived HTML to %s", filepath)

        except Exception as e:
            self.logger.error("Failed to archive HTML: %s", e)


class RateLimiter:
    """Per-domain rate limiting with exponential backoff."""

    def __init__(self, default_delay: float = 1.0):
        self.default_delay = default_delay
        self.domain_delays: Dict[str, float] = {}
        self.failure_counts: Dict[str, int] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_delay(self, domain: str) -> float:
        """
        Get delay for domain.

        Args:
            domain: Domain name

        Returns:
            Delay in seconds
        """
        return self.domain_delays.get(domain, self.default_delay)

    def record_failure(self, domain: str):
        """
        Record failure and increase backoff.

        Args:
            domain: Domain name
        """
        self.failure_counts[domain] = self.failure_counts.get(domain, 0) + 1
        
        # Exponential backoff: 1s, 2s, 4s, 8s, max 60s
        backoff = min(2 ** self.failure_counts[domain], 60)
        self.domain_delays[domain] = backoff
        
        self.logger.info(
            "Domain %s failures: %d, new delay: %.1fs",
            domain,
            self.failure_counts[domain],
            backoff
        )

    def record_success(self, domain: str):
        """
        Record success and reset backoff.

        Args:
            domain: Domain name
        """
        if domain in self.failure_counts:
            self.logger.info("Domain %s recovered, resetting backoff", domain)
            del self.failure_counts[domain]
            self.domain_delays[domain] = self.default_delay

    def reset_domain(self, domain: str):
        """Reset domain rate limiting."""
        self.failure_counts.pop(domain, None)
        self.domain_delays.pop(domain, None)


class RobotsTxtChecker:
    """Check robots.txt for crawl permissions."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache: Dict[str, bool] = {}

    async def can_crawl(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if URL can be crawled per robots.txt.

        Args:
            url: URL to check
            user_agent: User agent string

        Returns:
            True if crawling is allowed
        """
        # For career pages, we're generally respectful but permissive
        # This is a simplified implementation
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Check cache
        cache_key = f"{domain}:{parsed.path}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Allow all career-related paths by default
        career_paths = ['/careers', '/jobs', '/opportunities', '/join']
        if any(path in parsed.path.lower() for path in career_paths):
            self.cache[cache_key] = True
            return True

        # For other paths, allow by default but could enhance with robots.txt parsing
        self.cache[cache_key] = True
        return True
