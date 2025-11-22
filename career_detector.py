"""
Career page detection for HubSpot domain-level job scraper.

Detects pages that resemble "careers", "jobs", "opportunities", "join us", etc.
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from blacklist import DomainBlacklist

logger = logging.getLogger(__name__)

# URL path hints that suggest a career page
CAREER_PATH_HINTS = [
    "career",
    "careers",
    "jobs",
    "job",
    "job-openings",
    "join-our-team",
    "join-us",
    "join",
    "work-with-us",
    "work-with",
    "work-for-us",
    "opportunities",
    "open-positions",
    "openings",
    "apply",
    "team",
    "we-are-hiring",
    "hiring",
    "positions",
    "employment",
    "work-here",
]

# Content hints that suggest a career page
CAREER_CONTENT_HINTS = [
    "open positions",
    "job openings",
    "career opportunities",
    "join our team",
    "we're hiring",
    "we are hiring",
    "work with us",
    "apply now",
    "current openings",
    "available positions",
    "job listings",
    "employment opportunities",
    "become part of",
    "join us",
]

# Known ATS (Applicant Tracking System) domains
ATS_DOMAINS = [
    "greenhouse.io",
    "ashbyhq.com",
    "workable.com",
    "bamboohr.com",
    "lever.co",
    "jobvite.com",
    "recruitee.com",
    "smartrecruiters.com",
    "breezy.hr",
    "applytojob.com",
    "icims.com",
]


class CareerPageDetector:
    """Detects whether a page is a career/jobs page."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.domain_blacklist = DomainBlacklist()

    def is_career_page(self, url: str, html_content: Optional[str] = None) -> bool:
        """
        Determine if a URL or page content represents a career page.

        Args:
            url: The URL to check
            html_content: Optional HTML content to analyze

        Returns:
            True if this appears to be a career page
        """
        # Check URL first
        if self._url_suggests_careers(url):
            return True

        # Check if it's an ATS domain
        if self._is_ats_domain(url):
            return True

        # If we have content, check that too
        if html_content:
            return self._content_suggests_careers(html_content)

        return False

    def _url_suggests_careers(self, url: str) -> bool:
        """Check if URL path/query suggests a career page."""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            query = parsed.query.lower()

            # Check path and query for career hints
            combined = f"{path} {query}"
            return any(hint in combined for hint in CAREER_PATH_HINTS)

        except Exception as e:
            self.logger.debug("Failed to parse URL %s: %s", url, e)
            return False

    def _is_ats_domain(self, url: str) -> bool:
        """Check if URL is from a known ATS platform."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()

            # Remove www. prefix
            if host.startswith('www.'):
                host = host[4:]

            # Check if it matches any ATS domain
            return any(host == ats or host.endswith('.' + ats) for ats in ATS_DOMAINS)

        except Exception as e:
            self.logger.debug("Failed to parse URL %s: %s", url, e)
            return False

    def _content_suggests_careers(self, html_content: str) -> bool:
        """Check if page content suggests a career page."""
        # Convert to lowercase for case-insensitive matching
        content_lower = html_content.lower()

        # Count how many career hints are present
        hint_count = sum(1 for hint in CAREER_CONTENT_HINTS if hint in content_lower)

        # If we find at least 2 career hints, consider it a career page
        return hint_count >= 2

    def get_career_links(self, html_content: str, base_url: str) -> list:
        """
        Extract links from a page that might lead to career pages.
        
        Filters out blacklisted domains to avoid following links to:
        - Social media platforms
        - Publishing platforms
        - HubSpot ecosystem domains
        - Analytics/tracking domains
        - Other irrelevant external sites

        Args:
            html_content: HTML content to analyze
            base_url: Base URL for resolving relative links

        Returns:
            List of URLs that might be career pages
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        career_links = []
        soup = BeautifulSoup(html_content, 'lxml')

        for anchor in soup.find_all('a', href=True):
            href = anchor.get('href')
            text = anchor.get_text().strip().lower()
            title = anchor.get('title', '').lower()

            # Combine text sources
            combined = f"{text} {title}"

            # Check if link text or href suggests careers
            if any(hint in combined for hint in CAREER_PATH_HINTS) or \
               any(hint in href.lower() for hint in CAREER_PATH_HINTS):
                
                # Resolve relative URLs
                full_url = urljoin(base_url, href)
                
                # Skip javascript and mailto links
                if not full_url.startswith(('javascript:', 'mailto:', '#')):
                    # Filter out blacklisted domains
                    if not self.domain_blacklist.is_blacklisted_domain(full_url):
                        career_links.append(full_url)
                    else:
                        self.logger.debug("Filtered blacklisted career link: %s", full_url)

        self.logger.debug("Found %d potential career links", len(career_links))
        return career_links
