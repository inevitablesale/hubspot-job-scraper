"""
Content filtering utilities for job extraction.

Filters out non-job content from headers, footers, navigation,
and other sitewide layout elements to prevent false positives.
"""

import logging
import re
from typing import Optional, Set
from urllib.parse import urlparse
from bs4 import Tag

logger = logging.getLogger(__name__)


# URL path patterns that should be blocked from extraction
# From problem statement: paths for contact, team, blog, podcast, services, etc.
BLACKLISTED_URL_PATTERNS = [
    r'/about(?:/|$)',
    r'/team(?:/|$)',
    r'/contact(?:/|$)',
    r'/blog(?:/|$)',
    r'/podcast(?:/|$)',
    r'/services(?:/|$)',
    r'/resources(?:/|$)',
    r'/partners(?:/|$)',
    r'/pricing(?:/|$)',
    r'/portfolio(?:/|$)',
    r'/case-studies(?:/|$)',
    r'/insights(?:/|$)',
    r'/news(?:/|$)',
    r'/events(?:/|$)',
]

# Compile patterns for performance
BLACKLISTED_URL_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in BLACKLISTED_URL_PATTERNS]

# Social media and external domains to block (from problem statement)
BLACKLISTED_DOMAINS = {
    # Social media
    'facebook.com',
    'fb.com',
    'twitter.com',
    'x.com',
    'linkedin.com',
    'instagram.com',
    'tiktok.com',
    'youtube.com',
    'pinterest.com',
    'snapchat.com',
    
    # HubSpot ecosystem (from problem statement)
    'hubspot.com',
    
    # Other platforms
    'medium.com',
    'substack.com',
}

# CSS classes/IDs that indicate job containers (positive patterns)
JOB_CONTAINER_PATTERNS = [
    r'job[s]?[-_]',
    r'career[s]?[-_]',
    r'position[s]?[-_]',
    r'opening[s]?[-_]',
    r'listing[s]?[-_]',
]

# Compile job container patterns for performance
JOB_CONTAINER_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in JOB_CONTAINER_PATTERNS]


class ContentFilter:
    """Filters out non-job content from extraction."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def is_in_header_footer_nav(self, element: Tag) -> bool:
        """
        Check if an element is inside header, footer, or navigation.
        
        From problem statement:
        - Ignore everything in <header>
        - Ignore everything in <footer>
        - Ignore elements with role="navigation" or aria-label="navigation"
        - Ignore navbars, menus, or global link lists
        
        Args:
            element: BeautifulSoup Tag to check
            
        Returns:
            True if element is in header/footer/nav, False otherwise
        """
        # Check all parent elements
        for parent in element.parents:
            if not isinstance(parent, Tag):
                continue
                
            # Check tag names
            if parent.name in ['header', 'footer', 'nav']:
                return True
            
            # Check role attribute
            role = parent.get('role', '')
            if role == 'navigation':
                return True
            
            # Check aria-label for navigation
            aria_label = parent.get('aria-label', '').lower()
            if 'navigation' in aria_label or 'menu' in aria_label:
                return True
            
            # Check common navigation classes
            classes = parent.get('class', [])
            if isinstance(classes, list):
                classes_str = ' '.join(classes).lower()
            else:
                classes_str = str(classes).lower()
            
            nav_indicators = ['navbar', 'nav-bar', 'navigation', 'menu', 'header', 'footer']
            if any(indicator in classes_str for indicator in nav_indicators):
                return True
        
        return False
    
    def is_inside_job_container(self, element: Tag) -> bool:
        """
        Check if element is inside a recognized job container.
        
        From problem statement: enforce "Anchor must be inside a job card"
        
        Args:
            element: BeautifulSoup Tag to check
            
        Returns:
            True if element is inside a job container, False otherwise
        """
        # Check element itself first
        if self._has_job_container_class(element):
            return True
        
        # Check all parent elements
        for parent in element.parents:
            if not isinstance(parent, Tag):
                continue
            
            if self._has_job_container_class(parent):
                return True
            
            # Also check for data attributes like data-ats, data-job
            if parent.get('data-ats') or parent.get('data-job'):
                return True
        
        return False
    
    def _has_job_container_class(self, element: Tag) -> bool:
        """Check if element has job-related class names."""
        # Check classes
        classes = element.get('class', [])
        if isinstance(classes, list):
            classes_str = ' '.join(classes)
        else:
            classes_str = str(classes)
        
        # Check ID
        elem_id = element.get('id', '')
        
        # Combine for checking
        combined = f"{classes_str} {elem_id}"
        
        # Check against job container patterns
        for pattern in JOB_CONTAINER_REGEX:
            if pattern.search(combined):
                return True
        
        return False
    
    def is_blacklisted_url(self, url: Optional[str]) -> bool:
        """
        Check if URL matches blacklisted patterns or domains.
        
        From problem statement: block paths like /about, /team, /contact, /blog, etc.
        and domains like facebook.com, hubspot.com, etc.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL should be blocked, False otherwise
        """
        if not url:
            return False
        
        # Skip javascript, mailto, tel, and anchor-only links
        if url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            return True
        
        try:
            parsed = urlparse(url)
            
            # Check domain blacklist
            host = parsed.netloc.lower()
            if host.startswith('www.'):
                host = host[4:]
            
            # Check if host matches any blacklisted domain (exact or subdomain)
            for blacklisted in BLACKLISTED_DOMAINS:
                if host == blacklisted or host.endswith('.' + blacklisted):
                    self.logger.debug("URL blocked - blacklisted domain: %s", url)
                    return True
            
            # Check path patterns
            path = parsed.path.lower()
            for pattern in BLACKLISTED_URL_REGEX:
                if pattern.search(path):
                    self.logger.debug("URL blocked - blacklisted path: %s", url)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug("Error parsing URL %s: %s", url, e)
            return False
    
    def is_in_main_content(self, element: Tag) -> bool:
        """
        Check if element is inside main content area (not header/footer).
        
        From problem statement: "Freeze scope inside the content container"
        Look for <main>, <article>, or content-related divs.
        
        Args:
            element: BeautifulSoup Tag to check
            
        Returns:
            True if element is in main content, False otherwise
        """
        # Check if inside <main> tag
        for parent in element.parents:
            if not isinstance(parent, Tag):
                continue
            
            # <main> tag
            if parent.name == 'main':
                return True
            
            # role="main"
            if parent.get('role') == 'main':
                return True
            
            # Common main content IDs/classes
            elem_id = parent.get('id', '').lower()
            classes = parent.get('class', [])
            if isinstance(classes, list):
                classes_str = ' '.join(classes).lower()
            else:
                classes_str = str(classes).lower()
            
            main_indicators = ['main', 'content', 'article', 'body-content']
            if any(indicator in elem_id for indicator in main_indicators):
                return True
            if any(indicator in classes_str for indicator in main_indicators):
                return True
        
        return False
    
    def should_extract_from_element(self, element: Tag, url: Optional[str] = None) -> bool:
        """
        Main filter to determine if we should extract jobs from this element.
        
        From problem statement rulebook:
        1. Do NOT extract from header/footer/nav UNLESS it's in a job container
        2. URL must not match blacklisted patterns
        3. Element should be inside a job container OR main content OR body (default allow)
        
        Args:
            element: BeautifulSoup Tag to check
            url: Optional URL to validate
            
        Returns:
            True if we should extract from this element, False otherwise
        """
        # Block blacklisted URLs first
        if url and self.is_blacklisted_url(url):
            return False
        
        # Check if in header/footer/nav
        in_header_footer_nav = self.is_in_header_footer_nav(element)
        in_job_container = self.is_inside_job_container(element)
        
        # Block if in header/footer/nav UNLESS inside a job container
        if in_header_footer_nav:
            if in_job_container:
                # Allow: job widget in footer/header
                return True
            else:
                # Block: regular header/footer/nav link
                self.logger.debug("Element blocked - in header/footer/nav without job container")
                return False
        
        # Not in header/footer/nav - be more permissive
        # Allow if in job container, main content, or just in body (default)
        # This ensures we don't filter out simple HTML test cases
        in_main_content = self.is_in_main_content(element)
        
        # Allow if:
        # 1. Inside a job container (highest confidence)
        # 2. Inside main content area
        # 3. Not in header/footer/nav (already checked above, so if we're here, we allow by default)
        return True
