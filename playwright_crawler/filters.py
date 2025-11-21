import os
from urllib.parse import urlparse

REMOTE_ONLY = os.getenv("REMOTE_ONLY", "false").lower() == "true"
ALLOW_AGENCIES = os.getenv("ALLOW_AGENCIES", "false").lower() == "true"

BLOCKED_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "yelp.com",
    "youtube.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
    "zoominfo.com",
    "mailchimp.com",
    "doubleclick.net",
    "godaddy.com",
    "wix.com",
    "wixstatic.com",
    "about:blank",
    "hubspot.com",
    "medium.com",
    "shopify.com",
    "wordpress.com",
}

REMOTE_BAD_REGIONS = ["emea", "latam", "apac", "canada", "australia", "nz", "new zealand"]


def is_blocked(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == d or host.endswith("." + d) for d in BLOCKED_DOMAINS)


def is_agency(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in ["agency", "recruiting", "staffing", "talent agency"])


def passes_remote_filter(text: str) -> bool:
    if not REMOTE_ONLY:
        return True
    lowered = text.lower()
    if not any(k in lowered for k in ["remote", "work from home", "distributed"]):
        return False
    return not any(k in lowered for k in REMOTE_BAD_REGIONS)


def allow_agency(text: str) -> bool:
    if ALLOW_AGENCIES:
        return True
    return not is_agency(text)
