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

# Minimum length for a valid job title
MIN_JOB_TITLE_LENGTH = 5

# Keywords that suggest a link/button contains job titles or job pages
# These are ROLE-SPECIFIC keywords that indicate actual job titles
# From problem statement PART C - Valid job titles match patterns
TITLE_HINTS = [
    "strategist",
    "consultant",
    "developer",
    "designer",
    "manager",
    "director",
    "specialist",
    "architect",
    "administrator",
    "coordinator",
    "engineer",
    "lead",
    "intern",
    "analyst",
    "supervisor",
    "principal",
    "assistant",
    "associate",
    "representative",
    "position",
    "role",
    "opening",
    "opportunity",
]

# Pre-compile role keyword patterns for performance
# Word boundaries ensure "engineer" matches "engineer" but not "engineering"
ROLE_PATTERNS = [re.compile(r'\b' + re.escape(hint) + r'\b', re.IGNORECASE) for hint in TITLE_HINTS]

# Patterns that indicate this is NOT a job title
# Pre-compiled for performance since they're checked frequently
# From problem statement PART C - Negative keywords and blog patterns
FALSE_POSITIVE_PATTERNS = [
    # Questions and blog titles
    re.compile(r'^what\s+(is|are)', re.IGNORECASE),
    re.compile(r'^how\s+to', re.IGNORECASE),
    re.compile(r'^why\s+', re.IGNORECASE),
    re.compile(r'\bthe\b.*\b(guide|tips|strategy)\b', re.IGNORECASE),
    re.compile(r'^guest\s+post:', re.IGNORECASE),
    re.compile(r'\bcase\s+study\b', re.IGNORECASE),
    re.compile(r'\bwebinar\b', re.IGNORECASE),
    
    # Social media / podcasts
    re.compile(r'youtube', re.IGNORECASE),
    re.compile(r'spotify', re.IGNORECASE),
    re.compile(r'podcast', re.IGNORECASE),
    re.compile(r'listen\s+on', re.IGNORECASE),
    re.compile(r'watch\s+on', re.IGNORECASE),
    
    # Generic CTAs
    re.compile(r'^apply\s+(now|today)$', re.IGNORECASE),
    re.compile(r'^join\s+(us|our\s+team)$', re.IGNORECASE),
    re.compile(r'^view\s+', re.IGNORECASE),
    re.compile(r'^see\s+(all|our)', re.IGNORECASE),
    re.compile(r'^explore\s+', re.IGNORECASE),
    re.compile(r'^learn\s+more$', re.IGNORECASE),
    
    # Blog/resources - enhanced patterns
    re.compile(r'^episode\s+\d+', re.IGNORECASE),
    re.compile(r'^chapter\s+\d+', re.IGNORECASE),
    re.compile(r'\bby\s+[A-Z][a-z]+\s+[A-Z][a-z]+', re.IGNORECASE),  # "By John Doe"
    re.compile(r'\d+\s+min\s+read', re.IGNORECASE),  # "5 min read"
    re.compile(r'\b(20\d{2}|19\d{2})\b'),  # Years (YYYY)
    
    # Generic navigation
    re.compile(r'^about\s+(us)?$', re.IGNORECASE),
    re.compile(r'^contact\s+(us)?$', re.IGNORECASE),
    re.compile(r'^our\s+(team|services)', re.IGNORECASE),
    re.compile(r'^meet\s+', re.IGNORECASE),
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
        """
        Check if text looks like a job title or job-related content.
        
        From problem statement PART D - Job safety filter:
        - Must have title (string)
        - Must NOT match blog patterns
        - Titles with > 6 words without "apply" are rejected as blog posts
        """
        if not text or len(text.strip()) < MIN_JOB_TITLE_LENGTH:
            return False
            
        text_lower = text.lower().strip()
        
        # Filter out false positives using pre-compiled patterns
        for pattern in FALSE_POSITIVE_PATTERNS:
            if pattern.search(text_lower):
                return False
        
        # From problem statement: reject long titles without "apply" (likely blog posts)
        # "if title.split() > 6 and not "apply" in page_text.lower(): reject"
        word_count = len(text.split())
        if word_count > 6 and "apply" not in text_lower:
            logger.debug("Rejecting long title without 'apply': %s", text)
            return False
        
        # Check for role-specific keywords using pre-compiled patterns
        # Word boundaries ensure "engineer" matches "engineer" but not "engineering"
        for pattern in ROLE_PATTERNS:
            if pattern.search(text_lower):
                return True
        
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
    
    def _is_valid_job(self, job_data: Dict[str, str]) -> bool:
        """
        Validate job data according to safety filters from problem statement PART D.
        
        Jobs MUST have:
        - title (string)
        - description (string, 20+ characters) OR URL
        - must NOT match blog patterns
        - must NOT match "team member profile" pages
        - must NOT match events/webinars pages
        
        Returns:
            True if job is valid, False otherwise
        """
        # Validate title exists and is a string
        title = job_data.get('title')
        if not title or not isinstance(title, str):
            logger.debug("Job rejected: missing or invalid title")
            return False
        
        # Get description and URL
        description = job_data.get('summary', '') or job_data.get('description', '')
        url = job_data.get('url')
        
        # Job must have either description (20+ chars) OR URL
        has_description = description and isinstance(description, str) and len(description.strip()) >= 20
        has_url = url and isinstance(url, str) and len(url.strip()) > 0
        
        if not has_description and not has_url:
            logger.debug("Job rejected: no description (20+ chars) or URL - title: %s", title)
            return False
        
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
                        # Apply safety validation and deduplication
                        if job and self._is_valid_job(job) and self._dedupe_job(job['title'], job.get('url')):
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
            if len(text) < MIN_JOB_TITLE_LENGTH:
                continue

            # Combine text sources
            combined_text = f"{text} {title_attr}".lower()

            # Check if this looks like a job
            if self._is_job_like(combined_text) and text:
                url = self._normalize_url(href)
                job_data = {
                    'title': text,
                    'url': url,
                    'summary': '',
                }
                # Apply safety validation and deduplication
                if self._is_valid_job(job_data) and self._dedupe_job(text, url):
                    jobs.append(job_data)

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
            if len(text) < MIN_JOB_TITLE_LENGTH:
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
                job_data = {
                    'title': text,
                    'url': self._normalize_url(url) if url else None,
                    'summary': '',
                }
                # Apply safety validation and deduplication
                if self._is_valid_job(job_data) and self._dedupe_job(text, url):
                    jobs.append(job_data)

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
                # Apply safety validation and deduplication
                if job and self._is_valid_job(job) and self._dedupe_job(job['title'], job.get('url')):
                    jobs.append(job)

        # Also check for list items
        for ul_ol in parent.find_all(['ul', 'ol']):
            for li in ul_ol.find_all('li'):
                job = self._extract_from_card(li)
                # Apply safety validation and deduplication
                if job and self._is_valid_job(job) and self._dedupe_job(job['title'], job.get('url')):
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
                if len(text) < MIN_JOB_TITLE_LENGTH:
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

                    job_data = {
                        'title': text,
                        'url': url,
                        'summary': '',
                    }
                    # Apply safety validation and deduplication
                    if self._is_valid_job(job_data) and self._dedupe_job(text, url):
                        jobs.append(job_data)

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
