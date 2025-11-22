"""
Enhanced extraction patterns for enterprise-grade job intelligence.

Adds support for:
- Microdata extraction
- OpenGraph metadata
- Meta tags
- HTML comments with JSON
- JavaScript-rendered content (__NEXT_DATA__, __APOLLO_STATE__)
- CMS-specific patterns (Webflow, HubSpot COS, WordPress, CraftCMS)
"""

import json
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class MicrodataExtractor:
    """Extract jobs from microdata markup."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def extract(self, html: str) -> List[Dict]:
        """Extract jobs from microdata."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        # Find elements with itemtype="http://schema.org/JobPosting"
        for item in soup.find_all(attrs={"itemtype": re.compile(r"schema\.org/JobPosting")}):
            try:
                job = self._extract_microdata_job(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.debug("Failed to extract microdata job: %s", e)

        logger.debug("Microdata extractor found %d jobs", len(jobs))
        return jobs

    def _extract_microdata_job(self, element) -> Optional[Dict]:
        """Extract job from microdata element."""
        title = self._get_itemprop(element, 'title') or self._get_itemprop(element, 'name')
        if not title:
            return None

        url = self._get_itemprop(element, 'url')
        description = self._get_itemprop(element, 'description')
        location = self._get_itemprop(element, 'jobLocation')
        
        return {
            'title': title,
            'url': urljoin(self.base_url, url) if url else None,
            'summary': description[:500] if description else '',
            'location': location or '',
            'source': 'microdata',
        }

    def _get_itemprop(self, element, prop: str) -> Optional[str]:
        """Get itemprop value from element."""
        item = element.find(attrs={"itemprop": prop})
        if item:
            # Check for content attribute first
            if item.has_attr('content'):
                return item['content']
            # Then check text content
            return item.get_text(strip=True)
        return None


class OpenGraphExtractor:
    """Extract jobs from OpenGraph meta tags."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def extract(self, html: str) -> List[Dict]:
        """Extract job from OpenGraph tags."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        # Look for og:type="job"
        og_type = soup.find('meta', attrs={"property": "og:type", "content": "job"})
        if not og_type:
            return jobs

        # Extract job details from meta tags
        title = self._get_meta_content(soup, "og:title") or self._get_meta_content(soup, "job:title")
        url = self._get_meta_content(soup, "og:url")
        description = self._get_meta_content(soup, "og:description")
        location = self._get_meta_content(soup, "job:location")

        if title:
            jobs.append({
                'title': title,
                'url': urljoin(self.base_url, url) if url else None,
                'summary': description[:500] if description else '',
                'location': location or '',
                'source': 'opengraph',
            })

        logger.debug("OpenGraph extractor found %d jobs", len(jobs))
        return jobs

    def _get_meta_content(self, soup, property_name: str) -> Optional[str]:
        """Get content from meta tag."""
        tag = soup.find('meta', attrs={"property": property_name})
        if tag and tag.has_attr('content'):
            return tag['content']
        return None


class MetaTagExtractor:
    """Extract jobs from generic meta tags."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def extract(self, html: str) -> List[Dict]:
        """Extract job from meta tags."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        # Look for job-specific meta tags
        job_title = self._get_meta(soup, "job_title") or self._get_meta(soup, "jobtitle")
        if not job_title:
            return jobs

        job_url = self._get_meta(soup, "job_url")
        job_description = self._get_meta(soup, "job_description")
        job_location = self._get_meta(soup, "job_location")

        jobs.append({
            'title': job_title,
            'url': urljoin(self.base_url, job_url) if job_url else None,
            'summary': job_description[:500] if job_description else '',
            'location': job_location or '',
            'source': 'meta_tags',
        })

        logger.debug("Meta tag extractor found %d jobs", len(jobs))
        return jobs

    def _get_meta(self, soup, name: str) -> Optional[str]:
        """Get meta tag content."""
        tag = soup.find('meta', attrs={"name": name})
        if tag and tag.has_attr('content'):
            return tag['content']
        return None


class JavaScriptDataExtractor:
    """Extract jobs from JavaScript data embedded in HTML."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def extract(self, html: str) -> List[Dict]:
        """Extract jobs from JS data."""
        jobs = []

        # Extract from __NEXT_DATA__
        jobs.extend(self._extract_next_data(html))

        # Extract from __APOLLO_STATE__
        jobs.extend(self._extract_apollo_state(html))

        # Extract from window.jobData or similar
        jobs.extend(self._extract_window_data(html))

        # Extract from HTML comments
        jobs.extend(self._extract_from_comments(html))

        logger.debug("JavaScript data extractor found %d jobs", len(jobs))
        return jobs

    def _extract_next_data(self, html: str) -> List[Dict]:
        """Extract from Next.js __NEXT_DATA__."""
        jobs = []
        match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                # Navigate through typical Next.js structure
                props = data.get('props', {}).get('pageProps', {})
                
                # Look for jobs array
                if 'jobs' in props:
                    for job in props['jobs']:
                        jobs.append(self._normalize_js_job(job))
                
                # Look for other common structures
                elif 'initialData' in props and 'jobs' in props['initialData']:
                    for job in props['initialData']['jobs']:
                        jobs.append(self._normalize_js_job(job))

            except json.JSONDecodeError:
                logger.debug("Failed to parse __NEXT_DATA__")

        return jobs

    def _extract_apollo_state(self, html: str) -> List[Dict]:
        """Extract from Apollo GraphQL state."""
        jobs = []
        match = re.search(r'window\.__APOLLO_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                
                # Look for job objects in Apollo cache
                for key, value in data.items():
                    if isinstance(value, dict) and value.get('__typename') == 'JobPosting':
                        jobs.append(self._normalize_js_job(value))

            except json.JSONDecodeError:
                logger.debug("Failed to parse __APOLLO_STATE__")

        return jobs

    def _extract_window_data(self, html: str) -> List[Dict]:
        """Extract from window.jobData or similar."""
        jobs = []
        
        # Common patterns
        patterns = [
            r'window\.jobData\s*=\s*(\[.*?\]);',
            r'window\.jobs\s*=\s*(\[.*?\]);',
            r'var jobListings\s*=\s*(\[.*?\]);',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    for job in data:
                        jobs.append(self._normalize_js_job(job))
                except json.JSONDecodeError:
                    continue

        return jobs

    def _extract_from_comments(self, html: str) -> List[Dict]:
        """Extract JSON from HTML comments."""
        jobs = []
        
        # Look for JSON in comments
        pattern = r'<!--\s*({.*?"jobs".*?})\s*-->'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if 'jobs' in data:
                    for job in data['jobs']:
                        jobs.append(self._normalize_js_job(job))
            except json.JSONDecodeError:
                continue

        return jobs

    def _normalize_js_job(self, job: Dict) -> Dict:
        """Normalize job extracted from JavaScript."""
        title = job.get('title') or job.get('name') or job.get('position')
        url = job.get('url') or job.get('link') or job.get('applyUrl')
        description = job.get('description') or job.get('summary') or job.get('content')
        location = job.get('location') or job.get('office') or job.get('city')

        return {
            'title': title or '',
            'url': urljoin(self.base_url, url) if url else None,
            'summary': description[:500] if description else '',
            'location': location or '',
            'source': 'javascript',
        }


class CMSPatternExtractor:
    """Extract jobs from CMS-specific patterns."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def extract(self, html: str) -> List[Dict]:
        """Extract jobs based on CMS detection."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')

        # Detect CMS
        cms = self._detect_cms(soup, html)
        
        if cms == "webflow":
            jobs.extend(self._extract_webflow(soup))
        elif cms == "hubspot":
            jobs.extend(self._extract_hubspot_cos(soup))
        elif cms == "wordpress":
            jobs.extend(self._extract_wordpress(soup))
        elif cms == "craftcms":
            jobs.extend(self._extract_craftcms(soup))

        logger.debug("CMS pattern extractor (%s) found %d jobs", cms or "unknown", len(jobs))
        return jobs

    def _detect_cms(self, soup, html: str) -> Optional[str]:
        """Detect CMS platform."""
        # Webflow
        if soup.find('meta', attrs={"name": "generator", "content": re.compile(r"Webflow", re.I)}):
            return "webflow"
        if "webflow" in html.lower():
            return "webflow"

        # HubSpot COS
        if soup.find('meta', attrs={"name": "generator", "content": re.compile(r"HubSpot", re.I)}):
            return "hubspot"
        if "hs-scripts.com" in html:
            return "hubspot"

        # WordPress
        if soup.find('meta', attrs={"name": "generator", "content": re.compile(r"WordPress", re.I)}):
            return "wordpress"
        if "wp-content" in html or "wp-includes" in html:
            return "wordpress"

        # Craft CMS
        if "craftcms" in html.lower() or soup.find(attrs={"data-craft": True}):
            return "craftcms"

        return None

    def _extract_webflow(self, soup) -> List[Dict]:
        """Extract from Webflow-specific patterns."""
        jobs = []
        # Webflow often uses collection-item class
        for item in soup.find_all(class_=re.compile(r"collection-item|w-dyn-item")):
            title_elem = item.find(class_=re.compile(r"job-title|position-title"))
            if title_elem:
                link = item.find('a', href=True)
                jobs.append({
                    'title': title_elem.get_text(strip=True),
                    'url': urljoin(self.base_url, link['href']) if link else None,
                    'summary': '',
                    'source': 'webflow',
                })
        return jobs

    def _extract_hubspot_cos(self, soup) -> List[Dict]:
        """Extract from HubSpot COS patterns."""
        jobs = []
        # HubSpot COS often uses hs-module classes
        for item in soup.find_all(class_=re.compile(r"hs-job|hs-career")):
            title_elem = item.find(['h2', 'h3', 'h4'])
            if title_elem:
                link = item.find('a', href=True)
                jobs.append({
                    'title': title_elem.get_text(strip=True),
                    'url': urljoin(self.base_url, link['href']) if link else None,
                    'summary': '',
                    'source': 'hubspot_cos',
                })
        return jobs

    def _extract_wordpress(self, soup) -> List[Dict]:
        """Extract from WordPress patterns."""
        jobs = []
        # WordPress job listings often use specific post types
        for item in soup.find_all(class_=re.compile(r"job-listing|career-post|wp-job")):
            title_elem = item.find(class_="entry-title") or item.find(['h2', 'h3'])
            if title_elem:
                link = item.find('a', href=True)
                jobs.append({
                    'title': title_elem.get_text(strip=True),
                    'url': urljoin(self.base_url, link['href']) if link else None,
                    'summary': '',
                    'source': 'wordpress',
                })
        return jobs

    def _extract_craftcms(self, soup) -> List[Dict]:
        """Extract from Craft CMS patterns."""
        jobs = []
        # Craft CMS uses entry elements
        for item in soup.find_all(attrs={"data-entry-type": "job"}):
            title_elem = item.find(['h2', 'h3', 'h4'])
            if title_elem:
                link = item.find('a', href=True)
                jobs.append({
                    'title': title_elem.get_text(strip=True),
                    'url': urljoin(self.base_url, link['href']) if link else None,
                    'summary': '',
                    'source': 'craftcms',
                })
        return jobs
