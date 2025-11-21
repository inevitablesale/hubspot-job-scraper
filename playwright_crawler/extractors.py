import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

from playwright.async_api import Frame, Page

HUBSPOT_TITLE_KEYWORDS = [
    "hubspot",
    "crm",
    "revops",
    "marketing ops",
    "revenue operations",
    "automation",
    "hubspot admin",
    "hubspot consultant",
    "hubspot specialist",
    "hubspot developer",
    "operations hub",
    "cms hub",
    "sales hub",
    "service hub",
    "workflow",
    "marketing automation",
]

ROLE_SELECTORS = [
    "a[href*='job']",
    "a[href*='jobs']",
    "a[href*='careers']",
    "a[href*='opening']",
    "a[href*='opportunity']",
    ".job-title",
    "div[class*='job'] a",
    "[data-qa='job-card']",
    "[role='listitem'] a",
]

PAGINATION_SELECTORS = [
    "button:has-text('Next')",
    "a[rel='next']",
    "button:has-text('Load More')",
    "button:has-text('More Jobs')",
]

SEARCH_KEYWORDS = ["HubSpot", "CRM", "RevOps"]

DESCRIPTION_SELECTORS = [
    ".job-description",
    "#content",
    "section:has-text('Responsibilities')",
    "section:has-text('Requirements')",
    ".gh-content",
    ".workable-content",
]

APPLY_SELECTORS = [
    "a[href*='apply']",
    "button:has-text('Apply')",
    "input[type='submit']",
    ".lever-apply-button",
    ".greenhouse-apply-button",
]

MULTI_ROLE_GUARD = [
    ".job-card",
    ".job-opening",
    ".opening-title",
    "a[href*='/jobs/']",
]

LOCATION_SELECTORS = [
    "[data-qa='job-location']",
    ".job-location",
    ".location",
]

DEPARTMENT_SELECTORS = [
    "[data-qa='job-department']",
    ".department",
]

ATS_ALLOWLIST = {
    "greenhouse.io",
    "lever.co",
    "workable.com",
    "jazzhr.com",
    "bamboohr.com",
    "ashbyhq.com",
    "pinpointhq.com",
    "teamtailor.com",
    "recruitee.com",
    "myworkdayjobs.com",
}


def _clean_text(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _host(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_allowed_host(target: str, root_host: str) -> bool:
    host = _host(target)
    return not host or host == root_host or host.endswith("." + root_host) or host in ATS_ALLOWLIST


def _normalize_url(base_url: str, href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    try:
        return urljoin(base_url, href)
    except Exception:
        return None


def _matches_hubspot_title(title: str) -> bool:
    lowered = title.lower()
    return any(k in lowered for k in HUBSPOT_TITLE_KEYWORDS)


async def _collect_listings_from_context(page: Page, base_url: str, root_host: str) -> List[Dict[str, str]]:
    listings: List[Dict[str, str]] = []
    for selector in ROLE_SELECTORS:
        try:
            elements = await page.query_selector_all(selector)
        except Exception:
            continue
        for el in elements:
            try:
                inside_ignored = await el.evaluate(
                    "(el) => !!el.closest('header, nav, footer, .footer, .site-footer')"
                )
            except Exception:
                inside_ignored = False
            if inside_ignored:
                continue

            try:
                text = _clean_text(await el.inner_text())
            except Exception:
                text = ""
            href = None
            try:
                href = await el.get_attribute("href")
            except Exception:
                href = None
            if not text:
                continue
            url = _normalize_url(base_url, href)
            if not url:
                continue
            if not _matches_hubspot_title(text):
                continue
            if not _is_allowed_host(url, root_host):
                continue
            listings.append({"title": text, "url": url})
    return listings


async def _run_search_if_available(page: Page):
    try:
        search_input = await page.query_selector("input[type='search'], input[name*='search']")
    except Exception:
        return
    if not search_input:
        return
    for term in SEARCH_KEYWORDS:
        try:
            await search_input.click()
            await search_input.fill(term)
            await search_input.press("Enter")
            await page.wait_for_timeout(1500)
            break
        except Exception:
            continue


async def _click_next(page: Page) -> bool:
    for selector in PAGINATION_SELECTORS:
        try:
            locator = page.locator(selector)
            if await locator.count() > 0:
                await locator.first.click(timeout=1500)
                await page.wait_for_timeout(1400)
                return True
        except Exception:
            continue
    return False


async def _infinite_scroll(page: Page) -> bool:
    try:
        before = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1200)
        after = await page.evaluate("document.body.scrollHeight")
        return after > before
    except Exception:
        return False


async def extract_hubspot_listings(page: Page, base_url: str, root_host: str) -> List[Dict[str, str]]:
    """Extract HubSpot-filtered role listings from a careers page (and allowed frames)."""

    await _run_search_if_available(page)
    listings: List[Dict[str, str]] = []
    seen = set()
    last_count = -1
    iterations = 0

    while iterations < 12:  # guard against infinite loops
        iterations += 1
        current: List[Dict[str, str]] = []
        current.extend(await _collect_listings_from_context(page, base_url, root_host))

        # Frames (ATS embeds)
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            frame_host = _host(frame.url)
            if frame_host and frame_host not in ATS_ALLOWLIST and frame_host != root_host and not frame_host.endswith("." + root_host):
                continue
            try:
                current.extend(await _collect_listings_from_context(frame, frame.url or base_url, root_host))
            except Exception:
                continue

        for entry in current:
            key = (entry.get("title"), entry.get("url"))
            if key in seen:
                continue
            seen.add(key)
            listings.append(entry)

        if len(listings) == last_count:
            # Try pagination or scroll; if neither adds items, break.
            if await _click_next(page):
                last_count = len(listings)
                continue
            if await _infinite_scroll(page):
                last_count = len(listings)
                continue
            paged = False
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                if await _click_next(frame):
                    last_count = len(listings)
                    paged = True
                    break
            if paged:
                continue
            break
        last_count = len(listings)

    return listings


async def validate_role_page(page: Page) -> Optional[Dict[str, str]]:
    """Ensure a role page contains a single job and required fields."""

    try:
        title_loc = page.locator("h1, .job-title, #job-title, .posting-headline")
        titles = []
        count = await title_loc.count()
        for idx in range(min(count, 5)):
            text = _clean_text(await title_loc.nth(idx).inner_text())
            if text:
                titles.append(text)
        uniq_titles = list(dict.fromkeys(titles))
        if len(uniq_titles) != 1:
            return None
        title = uniq_titles[0]
    except Exception:
        return None

    try:
        desc_node = None
        for selector in DESCRIPTION_SELECTORS:
            loc = page.locator(selector)
            if await loc.count() > 0:
                desc_node = loc.first
                break
        description_html = await desc_node.inner_html() if desc_node else ""
    except Exception:
        description_html = ""

    try:
        apply_ok = False
        for selector in APPLY_SELECTORS:
            loc = page.locator(selector)
            if await loc.count() > 0:
                apply_ok = True
                break
        if not apply_ok:
            return None
    except Exception:
        return None

    try:
        multi_links = []
        for selector in MULTI_ROLE_GUARD:
            loc = page.locator(selector)
            count = min(await loc.count(), 8)
            for idx in range(count):
                href = await loc.nth(idx).get_attribute("href")
                normalized = _normalize_url(page.url, href) if href else None
                if normalized and normalized != page.url and normalized not in multi_links:
                    multi_links.append(normalized)
        if len(multi_links) > 1:
            return None
    except Exception:
        pass

    location = ""
    for selector in LOCATION_SELECTORS:
        loc = page.locator(selector)
        if await loc.count() > 0:
            location = _clean_text(await loc.first.inner_text())
            break

    department = ""
    for selector in DEPARTMENT_SELECTORS:
        loc = page.locator(selector)
        if await loc.count() > 0:
            department = _clean_text(await loc.first.inner_text())
            break

    body_text = ""
    try:
        body_text = await page.inner_text("body")
    except Exception:
        pass

    return {
        "title": title,
        "location": location,
        "department": department,
        "description_html": description_html,
        "body_text": body_text,
    }
