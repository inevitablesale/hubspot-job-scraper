from typing import Optional
from urllib.parse import urljoin, urlparse
from playwright.async_api import Page

# Patterns considered as careers links
CAREER_KEYWORDS = [
    "career",
    "careers",
    "jobs",
    "join-our-team",
    "join us",
    "open roles",
    "openings",
    "employment",
    "opportunities",
    "roles",
    "positions",
    "work-with-us",
]

# Selectors that should be ignored when searching for careers links
IGNORE_CONTAINERS = [
    "header a",
    "nav a",
    "footer a",
    ".footer a",
    ".site-footer a",
]

# Common non-career destinations to skip
SKIP_KEYWORDS = [
    "privacy",
    "legal",
    "terms",
    "contact",
    "blog",
    "pricing",
    "partners",
    "login",
    "support",
]


def _is_internal(target: str, root_host: str) -> bool:
    parsed = urlparse(target)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return not host or host == root_host or host.endswith("." + root_host)


def _matches_career(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in CAREER_KEYWORDS)


def _should_skip(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in SKIP_KEYWORDS)


def _candidate_selectors() -> str:
    ignored = ",".join([f":not({sel})" for sel in IGNORE_CONTAINERS])
    return f"a{ignored}"


async def find_careers_link(page: Page, root_url: str, root_host: str) -> Optional[str]:
    """Locate a single careers link on the homepage following strict rules."""

    selector = _candidate_selectors()
    anchors = await page.query_selector_all(selector)
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

    # Fallback to common hash anchors on the same page
    for candidate in ["#open-positions", "#careers", "#jobs"]:
        abs_candidate = urljoin(root_url, candidate)
        if _is_internal(abs_candidate, root_host):
            return abs_candidate

    return None
