"""
Blacklist rules for the HubSpot job scraper.

This module defines domains and business categories that should NOT be crawled
or followed by the scraper. These represent irrelevant verticals and external
platforms that do not contain primary job postings.
"""

import logging
from typing import Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Blacklisted business categories (from Google Places API categories)
# These represent local SMBs or irrelevant verticals
BLACKLISTED_BUSINESS_CATEGORIES = {
    # Retail & Food Service
    "Bicycle Shop",
    "Bar",
    "Bar & Grill",
    "Restaurant",
    "Cafe",
    "Coffee Shop",
    "Retail Store",
    
    # Health & Wellness
    "Gym",
    "Fitness Center",
    "Wellness Center",
    "Salon",
    "Barber Shop",
    
    # Real Estate
    "Real Estate Agency",
    "Real Estate Developer",
    "Property Management Company",
    "Student Housing Center",
    "Apartment Rental Agency",
    
    # Coworking
    "Coworking Space",
    "Shared Workspace",
    "Business Center",
    
    # IT Services (local)
    "Computer Support and Services",
    "IT Services",
    "Managed Service Provider",
    "Computer Repair Service",
    "Electronics Store",
    
    # Freelancers & Local Services
    "Graphic Designer",
    "Website Designer",
    "Web Design Service",
    "Photographer",
    "Videographer",
    "Marketing Freelancer",
    "Branding Consultant",
    "Market Researcher",
    
    # Logistics & Construction
    "Shipping Company",
    "Logistics Service",
    "Construction Company",
    
    # Home Services
    "Home Services",
    "Plumber",
    "Electrician",
    "Cleaning Service",
    
    # Automotive
    "Auto Repair Shop",
    "Car Dealer",
    
    # Other
    "Corporate Office",
}

# Blacklisted external domains that should NEVER be crawled
# These don't contain primary job postings and lead to irrelevant or infinite link trees
BLACKLISTED_DOMAINS = {
    # Social Media Platforms (from problem statement)
    "facebook.com",
    "fb.com",
    "messenger.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "pinterest.com",
    "threads.net",
    "snapchat.com",
    
    # Publishing Platforms (from problem statement)
    "medium.com",
    "substack.com",
    "blogger.com",
    "wordpress.com",
    "wix.com",
    "wixstatic.com",
    "squarespace.com",
    "vimeo.com",
    
    # HubSpot Ecosystem (from problem statement - all subdomains blocked)
    "hubspot.com",
    
    # Generic Platforms (from problem statement - always external)
    "canva.com",
    "figma.com",
    "notion.site",
    "eventbrite.com",
    "mailchimp.com",
    "intercom.help",
    "zendesk.com",
    
    # Analytics / Tracking (subdomains automatically blocked)
    "google.com",
    "gstatic.com",
    "doubleclick.net",
    
    # Unrelated Major Domains (subdomains automatically blocked)
    "amazon.com",
    "apple.com",
    "microsoft.com",
    "reddit.com",
    "quora.com",
    
    # Additional domains from original SKIP_DOMAINS
    "yelp.com",
    "godaddy.com",
    "about:blank",
}


class DomainBlacklist:
    """
    Utility for checking if domains should be blacklisted from crawling.
    
    The scraper should ONLY visit real business domains belonging to:
    - Marketing agencies
    - RevOps consultancies
    - HubSpot solutions partners
    - CRM consultancies
    - B2B service providers
    - SaaS companies
    - Digital advertising agencies
    - Lead gen, demand gen, content, SEO, CRO agencies
    """
    
    def __init__(self):
        self.blacklisted_domains: Set[str] = BLACKLISTED_DOMAINS
        self.blacklisted_categories: Set[str] = BLACKLISTED_BUSINESS_CATEGORIES
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def is_blacklisted_domain(self, url: str) -> bool:
        """
        Check if a URL's domain is blacklisted.
        
        Args:
            url: The URL to check
            
        Returns:
            True if the domain is blacklisted, False otherwise
        """
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            
            # Remove www. prefix
            if host.startswith('www.'):
                host = host[4:]
            
            # Check if host matches any blacklisted domain
            for blacklisted in self.blacklisted_domains:
                if host == blacklisted or host.endswith('.' + blacklisted):
                    self.logger.debug("Blocked blacklisted domain: %s", url)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.debug("Error parsing URL %s: %s", url, e)
            return False
    
    def is_blacklisted_category(self, category: str) -> bool:
        """
        Check if a business category is blacklisted.
        
        Args:
            category: The business category to check
            
        Returns:
            True if the category is blacklisted, False otherwise
        """
        return category in self.blacklisted_categories
    
    def get_blacklisted_domains(self) -> Set[str]:
        """
        Get the set of blacklisted domains.
        
        Returns:
            Set of blacklisted domain strings
        """
        return self.blacklisted_domains.copy()
    
    def get_blacklisted_categories(self) -> Set[str]:
        """
        Get the set of blacklisted business categories.
        
        Returns:
            Set of blacklisted category strings
        """
        return self.blacklisted_categories.copy()
