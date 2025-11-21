from typing import Optional
from urllib.parse import urljoin
from playwright.async_api import Page

CAREER_KEYWORDS = [
    "career",
    "careers",
    "jobs",
    "join us",
    "join-our-team",
    "open roles",
    "open positions",
    "openings",
    "we're hiring",
    "we are hiring",
    "apply",
]


async def find_careers_link(page: Page, root_url: str) -> Optional[str]:
    anchors = await page.query_selector_all("a")
    seen = set()
    for anchor in anchors:
        href = await anchor.get_attribute("href")
        text = (await anchor.inner_text() or "").lower().strip()
        if not href:
            continue
        target = f"{href.lower()} {text}" if text else href.lower()
        if any(k in target for k in CAREER_KEYWORDS):
            absolute = urljoin(root_url, href)
            if absolute not in seen:
                seen.add(absolute)
                return absolute
    # try open-positions hash
    for candidate in ["#open-positions", "#careers", "#jobs"]:
        abs_candidate = urljoin(root_url, candidate)
        if abs_candidate not in seen:
            return abs_candidate
    return None
