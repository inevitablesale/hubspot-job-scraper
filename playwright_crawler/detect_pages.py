from typing import Optional
from urllib.parse import urljoin, urlparse
from playwright.async_api import Page

# Patterns considered as careers links
CAREER_KEYWORDS = [
    "career",
    "careers",
    "jobs",
    "job",
    "hiring",
    "join",
    "join-our-team",
    "join us",
    "join-us",
    "team",
    "open roles",
    "openings",
    "employment",
    "opportunities",
    "roles",
    "positions",
    "work-with-us",
    "company/careers",
]

# Common non-career destinations to skip
SKIP_KEYWORDS = [
    "privacy",
    "legal",
    "terms",
    "contact",
    "about",
    "resources",
    "pricing",
    "blog",
    "news",
    "press",
    "events",
    "partners",
    "support",
    "facebook",
    "instagram",
    "linkedin",
    "twitter",
    "x.com",
    "youtube",
    "medium",
    "tiktok",
    "mailchimp",
    "wix",
    "shopify",
]


def _is_internal(target: str, root_host: str) -> bool:
    parsed = urlparse(target)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return not host or host == root_host


def _matches_career(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in CAREER_KEYWORDS)


def _should_skip(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in SKIP_KEYWORDS)


async def find_careers_link(page: Page, root_url: str, root_host: str) -> Optional[str]:
    """Locate a single careers link on the homepage following strict rules."""

    anchors = await page.query_selector_all("a")
    seen = set()

    for anchor in anchors:
        href = await anchor.get_attribute("href")
        text = (await anchor.inner_text() or "").strip()
        if not href:
            continue
        if _should_skip(f"{href} {text}"):
            continue
        absolute = urljoin(root_url, href)
        if not _is_internal(absolute, root_host):
            continue
        target_blob = f"{href} {text}".lower()
        if _matches_career(target_blob):
            if absolute not in seen:
                seen.add(absolute)
                return absolute

    for candidate_path in ["/careers", "/jobs", "/about/careers", "/careers/"]:
        candidate = urljoin(root_url, candidate_path)
        if not _is_internal(candidate, root_host):
            continue
        try:
            response = await page.context.request.get(
                candidate, max_redirects=2, timeout=8000
            )
        except Exception:
            continue
        status = response.status
        if 200 <= status < 400:
            final_url = str(response.url)
            if _is_internal(final_url, root_host):
                return final_url

    return None
