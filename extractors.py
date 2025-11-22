"""
Multi-layer job extraction engine for HubSpot domain-level job scraper.

Implements:
1. JSON-LD JobPosting extractor
2. Anchor-based extractor (<a> tags)
3. Button-based extractor (<button> elements)
4. Section-based extractor (blocks under Open Positions / Join Us / We're Hiring)
5. Heading-based extractor (fallback titles in <h1>-<h6>)
"""

import json
import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# Keywords that suggest a link/button contains job titles or job pages
# These are ROLE-SPECIFIC keywords that indicate actual job titles
TITLE_HINTS = [
    "developer",
    "engineer",
    "consultant",
    "architect",
    "specialist",
    "manager",
    "analyst",
    "designer",
    "coordinator",
    "director",
    "representative",
    "associate",
    "lead",
    "position",
    "role",
    "opening",
    "opportunity",
]

# Generic industry/department words that need additional validation
GENERIC_KEYWORDS = [
    "marketing",
    "sales",
    "support",
    "product",
    "engineering",
    "design",
    "creative",
    "revenue",
]

# Patterns that indicate this is NOT a job title
FALSE_POSITIVE_PATTERNS = [
    # Questions
    r'^what\s+(is|are)',
    r'^how\s+to',
    r'^why\s+',
    # Social media / podcasts
    r'youtube',
    r'spotify',
    r'podcast',
    r'listen\s+on',
    r'watch\s+on',
    # Generic CTAs
    r'^apply\s+(now|today)$',
    r'^join\s+(us|our\s+team)$',
    r'^view\s+',
    r'^see\s+(all|our)',
    r'^explore\s+',
    r'^learn\s+more$',
    # Blog/resources
    r'^episode\s+\d+',
    r'^chapter\s+\d+',
    # Generic navigation
    r'^about\s+(us)?$',
    r'^contact\s+(us)?$',
    r'^our\s+(team|services)',
    r'^meet\s+',
]

# Headings that indicate job sections
SECTION_HEADINGS = [
    "open positions",
    "current openings",
    "job openings",
    "career opportunities",
    "join us",
    "join our team",
    "we're hiring",
    "we are hiring",
    "work with us",
    "available positions",
    "careers",
]


class JobExtractor:
    """Base class for job extractors."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.seen_jobs: Set[tuple] = set()

    def _normalize_url(self, url: Optional[str]) -> Optional[str]:
        """Normalize and validate a URL."""
        if not url:
            return None

        # Handle relative URLs
        if not url.startswith(('http://', 'https://', '//', 'javascript:', 'mailto:')):
            url = urljoin(self.base_url, url)

        # Skip javascript and mailto links
        if url.startswith(('javascript:', 'mailto:', '#')):
            return None

        # Ensure it's a valid http/https URL
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return None

        return url

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def _is_job_like(self, text: str) -> bool:
        """Check if text looks like a job title or job-related content."""
        if not text or len(text.strip()) < 3:
            return False
            
        text_lower = text.lower().strip()
        
        # Filter out false positives
        for pattern in FALSE_POSITIVE_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False
        
        # Check for role-specific keywords using word boundaries
        # This prevents "engineering" from matching "engineer"
        has_role_keyword = False
        for hint in TITLE_HINTS:
            # Use word boundary to ensure exact word match
            if re.search(r'\b' + re.escape(hint) + r'\b', text_lower):
                has_role_keyword = True
                break
        
        # If it has a role keyword, it's likely a job
        if has_role_keyword:
            return True
        
        # For generic keywords alone (without role keywords), reject
        # These are typically department names or categories, not job titles
        return False

    def _dedupe_job(self, title: str, url: Optional[str]) -> bool:
        """
        Check if this job has already been seen.
        Returns True if it's new, False if it's a duplicate.
        """
        key = (self._clean_text(title).lower(), url)
        if key in self.seen_jobs:
            return False
        self.seen_jobs.add(key)
        return True


class JsonLdExtractor(JobExtractor):
    """Extract jobs from JSON-LD JobPosting structured data."""

    def extract(self, html: str) -> List[Dict[str, str]]:
        """Extract jobs from JSON-LD JobPosting markup."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        # Find all script tags with type="application/ld+json"
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)

                # Handle both single objects and arrays
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # Handle @graph structure
                    if '@graph' in item:
                        items.extend(item['@graph'])
                        continue

                    # Check if it's a JobPosting
                    type_value = item.get('@type', '')
                    if type_value == 'JobPosting' or (isinstance(type_value, list) and 'JobPosting' in type_value):
                        job = self._extract_job_posting(item)
                        if job and self._dedupe_job(job['title'], job.get('url')):
                            jobs.append(job)

            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug("Failed to parse JSON-LD: %s", e)
                continue

        logger.debug("JSON-LD extractor found %d jobs", len(jobs))
        return jobs

    def _extract_job_posting(self, data: Dict) -> Optional[Dict[str, str]]:
        """Extract job information from a JobPosting object."""
        title = data.get('title') or data.get('name')
        if not title:
            return None

        url = None
        # Try different URL fields
        if isinstance(data.get('url'), str):
            url = data['url']
        elif isinstance(data.get('directApplyUrl'), str):
            url = data['directApplyUrl']
        elif isinstance(data.get('jobLocation'), dict):
            loc_url = data['jobLocation'].get('url')
            if isinstance(loc_url, str):
                url = loc_url

        description = data.get('description', '')
        if isinstance(description, dict):
            description = description.get('text', '')

        return {
            'title': self._clean_text(title),
            'url': self._normalize_url(url),
            'summary': self._clean_text(description)[:500] if description else '',
        }


class AnchorExtractor(JobExtractor):
    """Extract jobs from <a> tags based on TITLE_HINTS heuristics."""

    def extract(self, html: str) -> List[Dict[str, str]]:
        """Extract jobs from anchor tags."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        for anchor in soup.find_all('a', href=True):
            text = self._clean_text(anchor.get_text())
            href = anchor.get('href')
            title_attr = anchor.get('title', '')

            # Skip if text is too short to be a meaningful job title
            if len(text) < 5:
                continue

            # Combine text sources
            combined_text = f"{text} {title_attr}".lower()

            # Check if this looks like a job
            if self._is_job_like(combined_text) and text:
                url = self._normalize_url(href)
                if url and self._dedupe_job(text, url):
                    jobs.append({
                        'title': text,
                        'url': url,
                        'summary': '',
                    })

        logger.debug("Anchor extractor found %d jobs", len(jobs))
        return jobs


class ButtonExtractor(JobExtractor):
    """Extract jobs from <button> elements."""

    def extract(self, html: str) -> List[Dict[str, str]]:
        """Extract jobs from button elements."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        for button in soup.find_all('button'):
            text = self._clean_text(button.get_text())
            
            # Skip if text is too short to be a meaningful job title
            if len(text) < 5:
                continue
            
            data_url = button.get('data-url') or button.get('data-href') or button.get('onclick', '')

            # Extract URL from onclick handlers
            url = None
            if 'http' in data_url:
                match = re.search(r'https?://[^\s\'"]+', data_url)
                if match:
                    url = match.group(0)

            # Check if this looks like a job
            if self._is_job_like(text) and text:
                # Note: URL might be None for modal-based jobs
                if self._dedupe_job(text, url):
                    jobs.append({
                        'title': text,
                        'url': self._normalize_url(url) if url else None,
                        'summary': '',
                    })

        logger.debug("Button extractor found %d jobs", len(jobs))
        return jobs


class SectionExtractor(JobExtractor):
    """Extract jobs from sections under headings like 'Open Positions' or 'Join Us'."""

    def extract(self, html: str) -> List[Dict[str, str]]:
        """Extract jobs from job listing sections."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        # Find headings that indicate job sections
        for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(heading_tag):
                heading_text = self._clean_text(heading.get_text()).lower()

                if any(section_hint in heading_text for section_hint in SECTION_HEADINGS):
                    # Found a jobs section, extract cards/items below it
                    jobs.extend(self._extract_from_section(heading))

        logger.debug("Section extractor found %d jobs", len(jobs))
        return jobs

    def _extract_from_section(self, heading: Tag) -> List[Dict[str, str]]:
        """Extract job cards from a section."""
        jobs = []

        # Get the parent container
        parent = heading.parent
        if not parent:
            return jobs

        # Look for common card/list patterns
        for card_class in ['job-card', 'job-item', 'position', 'opening', 'listing', 'card', 'item']:
            cards = parent.find_all(class_=re.compile(card_class, re.I))
            for card in cards:
                job = self._extract_from_card(card)
                if job and self._dedupe_job(job['title'], job.get('url')):
                    jobs.append(job)

        # Also check for list items
        for ul_ol in parent.find_all(['ul', 'ol']):
            for li in ul_ol.find_all('li'):
                job = self._extract_from_card(li)
                if job and self._dedupe_job(job['title'], job.get('url')):
                    jobs.append(job)

        return jobs

    def _extract_from_card(self, card: Tag) -> Optional[Dict[str, str]]:
        """Extract job details from a card element."""
        # Try to find a link
        link = card.find('a', href=True)
        url = self._normalize_url(link.get('href')) if link else None

        # Extract title - prefer heading tags first
        title = None
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            heading = card.find(tag)
            if heading:
                title = self._clean_text(heading.get_text())
                break

        # Fallback to link text or card text
        if not title and link:
            title = self._clean_text(link.get_text())
        if not title:
            title = self._clean_text(card.get_text())[:100]

        if not title:
            return None

        # Extract summary
        summary = ''
        desc = card.find(class_=re.compile(r'description|summary|excerpt', re.I))
        if desc:
            summary = self._clean_text(desc.get_text())[:500]

        return {
            'title': title,
            'url': url,
            'summary': summary,
        }


class HeadingExtractor(JobExtractor):
    """Fallback extractor using heading tags as job titles."""

    def extract(self, html: str) -> List[Dict[str, str]]:
        """Extract jobs from heading tags."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            for heading in soup.find_all(heading_tag):
                text = self._clean_text(heading.get_text())

                # Skip if text is too short to be a meaningful job title
                if len(text) < 5:
                    continue

                # Check if this looks like a job title
                if self._is_job_like(text) and text:
                    # Try to find a nearby link
                    url = None
                    link = heading.find('a', href=True)
                    if not link:
                        link = heading.find_next('a', href=True)

                    if link:
                        url = self._normalize_url(link.get('href'))

                    if self._dedupe_job(text, url):
                        jobs.append({
                            'title': text,
                            'url': url,
                            'summary': '',
                        })

        logger.debug("Heading extractor found %d jobs", len(jobs))
        return jobs


class MultiLayerExtractor:
    """
    Orchestrates all extraction layers and returns deduplicated results.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.extractors = [
            JsonLdExtractor(base_url),
            AnchorExtractor(base_url),
            ButtonExtractor(base_url),
            SectionExtractor(base_url),
            HeadingExtractor(base_url),
        ]

    def extract_all(self, html: str) -> List[Dict[str, str]]:
        """
        Run all extractors and return deduplicated results.
        Each extractor maintains its own seen set, so we get the union of all unique jobs.
        """
        all_jobs = []

        for extractor in self.extractors:
            try:
                jobs = extractor.extract(html)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.warning("Extractor %s failed: %s", extractor.__class__.__name__, e)
                continue

        logger.info("Multi-layer extraction found %d total jobs from %s", len(all_jobs), self.base_url)
        return all_jobs
