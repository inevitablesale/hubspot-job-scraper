"""
Automatic ATS (Applicant Tracking System) Detection and Integration.

Detects ATS providers by analyzing:
- Script tags (lever.js, boards.greenhouse.io)
- Network/XHR endpoints
- iframe sources
- DOM signatures

Implements ATS-specific fetchers for:
- Greenhouse
- Lever
- Workable
- JazzHR
- Ashby
- BambooHR
"""

import json
import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ATS providers with their detection signatures
ATS_SIGNATURES = {
    "greenhouse": {
        "scripts": ["boards.greenhouse.io", "boards-api.greenhouse.io", "greenhouse.js"],
        "iframes": ["boards.greenhouse.io"],
        "api_patterns": [r"boards-api\.greenhouse\.io/v\d+/boards"],
        "dom_selectors": [".greenhouse-board", "#greenhouse_application"],
    },
    "lever": {
        "scripts": ["lever.co/careers-hosted", "andromeda.lever.co"],
        "iframes": ["jobs.lever.co"],
        "api_patterns": [r"api\.lever\.co/v\d+/postings"],
        "dom_selectors": [".lever-jobs", "[data-qa='lever-job']"],
    },
    "workable": {
        "scripts": ["workable.com/assets", "apply.workable.com"],
        "iframes": ["apply.workable.com"],
        "api_patterns": [r"apply\.workable\.com/api/v\d+"],
        "dom_selectors": [".workable-job", "[data-ui='job-list']"],
    },
    "jazzhr": {
        "scripts": ["jazz.co", "jazzhr.com"],
        "iframes": ["jazzhr.com", "jazz.co"],
        "api_patterns": [r"api\.jazz\.co"],
        "dom_selectors": [".jazz-job", "#jazz-careers"],
    },
    "ashby": {
        "scripts": ["ashbyhq.com"],
        "iframes": ["jobs.ashbyhq.com"],
        "api_patterns": [r"api\.ashbyhq\.com"],
        "dom_selectors": [".ashby-job", "[data-ashby]"],
    },
    "bamboohr": {
        "scripts": ["bamboohr.com/careers", "bamboohr.com/jobs"],
        "iframes": ["bamboohr.com/careers"],
        "api_patterns": [r"api\.bamboohr\.com"],
        "dom_selectors": [".bamboohr-job"],
    },
}

# Allowed ATS redirect domains
ALLOWED_ATS_REDIRECTS = {
    "greenhouse.io",
    "boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "workable.com",
    "apply.workable.com",
    "jazzhr.com",
    "jazz.co",
    "ashbyhq.com",
    "jobs.ashbyhq.com",
    "bamboohr.com",
    "recruitee.com",
    "smartrecruiters.com",
    "breezy.hr",
    "applytojob.com",
    "icims.com",
    "jobvite.com",
}

# Banned job board domains (should NOT follow redirects)
BANNED_REDIRECTS = {
    "linkedin.com",
    "indeed.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "monster.com",
    "careerbuilder.com",
    "simplyhired.com",
    "dice.com",
}


class ATSDetector:
    """Detects ATS providers from HTML content."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def detect_ats(self, html: str, page_url: str) -> Optional[str]:
        """
        Detect which ATS (if any) is being used on this page.

        Args:
            html: Page HTML content
            page_url: URL of the page

        Returns:
            ATS provider name (e.g., "greenhouse", "lever") or None
        """
        soup = BeautifulSoup(html, 'lxml')

        for ats_name, signatures in ATS_SIGNATURES.items():
            # Check script tags
            for script in soup.find_all('script', src=True):
                src = script.get('src', '').lower()
                if any(pattern in src for pattern in signatures['scripts']):
                    self.logger.info("Detected %s via script tag: %s", ats_name, src)
                    return ats_name

            # Check iframes
            for iframe in soup.find_all('iframe', src=True):
                src = iframe.get('src', '').lower()
                if any(pattern in src for pattern in signatures['iframes']):
                    self.logger.info("Detected %s via iframe: %s", ats_name, src)
                    return ats_name

            # Check DOM selectors
            for selector in signatures['dom_selectors']:
                if soup.select(selector):
                    self.logger.info("Detected %s via DOM selector: %s", ats_name, selector)
                    return ats_name

            # Check for API patterns in content
            for pattern in signatures['api_patterns']:
                if re.search(pattern, html, re.IGNORECASE):
                    self.logger.info("Detected %s via API pattern: %s", ats_name, pattern)
                    return ats_name

        return None

    def is_allowed_ats_redirect(self, url: str) -> bool:
        """Check if URL is an allowed ATS redirect."""
        try:
            host = urlparse(url).netloc.lower()
            if host.startswith('www.'):
                host = host[4:]
            
            return any(host == ats or host.endswith('.' + ats) for ats in ALLOWED_ATS_REDIRECTS)
        except Exception:
            return False

    def is_banned_redirect(self, url: str) -> bool:
        """Check if URL is a banned job board redirect."""
        try:
            host = urlparse(url).netloc.lower()
            if host.startswith('www.'):
                host = host[4:]
            
            return any(host == banned or host.endswith('.' + banned) for banned in BANNED_REDIRECTS)
        except Exception:
            return False


class ATSFetcher:
    """Fetches jobs from ATS APIs."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def fetch_greenhouse_jobs(self, board_token: str) -> List[Dict]:
        """
        Fetch jobs from Greenhouse API.

        Args:
            board_token: Greenhouse board token

        Returns:
            List of job dicts
        """
        jobs = []
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        jobs_data = data.get('jobs', [])
                        
                        for job in jobs_data:
                            jobs.append({
                                'title': job.get('title', ''),
                                'url': job.get('absolute_url', ''),
                                'summary': job.get('content', '')[:500],
                                'location': job.get('location', {}).get('name', ''),
                                'ats': 'greenhouse',
                                'ats_id': job.get('id'),
                            })
                        
                        self.logger.info("Fetched %d jobs from Greenhouse", len(jobs))
                    else:
                        self.logger.warning("Greenhouse API returned %d", response.status)

        except Exception as e:
            self.logger.error("Failed to fetch Greenhouse jobs: %s", e)

        return jobs

    async def fetch_lever_jobs(self, company_name: str) -> List[Dict]:
        """
        Fetch jobs from Lever API.

        Args:
            company_name: Lever company identifier

        Returns:
            List of job dicts
        """
        jobs = []
        try:
            url = f"https://api.lever.co/v0/postings/{company_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        jobs_data = await response.json()
                        
                        for job in jobs_data:
                            jobs.append({
                                'title': job.get('text', ''),
                                'url': job.get('hostedUrl', ''),
                                'summary': job.get('description', '')[:500],
                                'location': ', '.join([loc.get('name', '') for loc in job.get('categories', {}).get('location', [])]),
                                'ats': 'lever',
                                'ats_id': job.get('id'),
                            })
                        
                        self.logger.info("Fetched %d jobs from Lever", len(jobs))
                    else:
                        self.logger.warning("Lever API returned %d", response.status)

        except Exception as e:
            self.logger.error("Failed to fetch Lever jobs: %s", e)

        return jobs

    async def fetch_workable_jobs(self, company_slug: str) -> List[Dict]:
        """
        Fetch jobs from Workable API.

        Args:
            company_slug: Workable company slug

        Returns:
            List of job dicts
        """
        jobs = []
        try:
            url = f"https://apply.workable.com/api/v3/accounts/{company_slug}/jobs"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        jobs_data = data.get('jobs', [])
                        
                        for job in jobs_data:
                            jobs.append({
                                'title': job.get('title', ''),
                                'url': job.get('url', ''),
                                'summary': job.get('description', '')[:500],
                                'location': job.get('location', {}).get('city', ''),
                                'ats': 'workable',
                                'ats_id': job.get('shortcode'),
                            })
                        
                        self.logger.info("Fetched %d jobs from Workable", len(jobs))
                    else:
                        self.logger.warning("Workable API returned %d", response.status)

        except Exception as e:
            self.logger.error("Failed to fetch Workable jobs: %s", e)

        return jobs

    def extract_ats_identifier(self, url: str, ats_type: str) -> Optional[str]:
        """
        Extract ATS identifier from URL.

        Args:
            url: ATS URL
            ats_type: Type of ATS (greenhouse, lever, workable)

        Returns:
            Identifier string or None
        """
        try:
            parsed = urlparse(url)
            
            if ats_type == "greenhouse":
                # Extract board token from URL like boards.greenhouse.io/company/jobs
                match = re.search(r'boards\.greenhouse\.io/([^/]+)', url)
                if match:
                    return match.group(1)
            
            elif ats_type == "lever":
                # Extract company from URL like jobs.lever.co/company
                match = re.search(r'lever\.co/([^/]+)', url)
                if match:
                    return match.group(1)
            
            elif ats_type == "workable":
                # Extract company from URL like apply.workable.com/company
                match = re.search(r'workable\.com/([^/]+)', url)
                if match:
                    return match.group(1)

        except Exception as e:
            self.logger.debug("Failed to extract ATS identifier: %s", e)

        return None
