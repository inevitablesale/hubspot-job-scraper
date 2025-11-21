import asyncio
import logging
from typing import Dict, Optional, List
from urllib.parse import urlparse, urljoin

from playwright.async_api import BrowserContext

from .browser import new_page, gentle_scroll
from .detect_pages import find_careers_link
from .extractors import extract_hubspot_listings, validate_role_page, ATS_ALLOWLIST
from .filters import is_blocked, allow_agency, passes_remote_filter
from .signals import score_roles
from .state import CrawlerState

logger = logging.getLogger(__name__)

LOG_PREFIX = {
    "start": "START domain",
    "careers": "FOUND careers page",
    "roles": "FOUND HubSpot roles",
    "nav": "NAVIGATING to role page",
    "valid": "VALID ROLE CONFIRMED",
    "saved": "SAVED role",
    "end": "END domain",
}


def _host(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_allowed_target(url: str, root_host: str) -> bool:
    host = _host(url)
    if not host:
        return True
    if host == root_host or host.endswith("." + root_host):
        return True
    return host in ATS_ALLOWLIST


def _remote_flag(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in ["remote", "distributed", "work from home", "us remote", "united states (remote)"])


async def _load_page(page, url: str, state: Optional[CrawlerState], label: str) -> bool:
    try:
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(1500)
        await gentle_scroll(page)
        return True
    except Exception as exc:
        if state:
            state.add_log("ERROR", f"Failed to load {label} {url}: {exc}")
        logger.error("Failed to load %s %s: %s", label, url, exc)
        return False


async def _log(state: Optional[CrawlerState], level: str, message: str):
    if state:
        state.add_log(level, message)


async def _process_role_page(context: BrowserContext, company: str, role_url: str, root_host: str, notifier, state: Optional[CrawlerState]):
    if not _is_allowed_target(role_url, root_host):
        await _log(state, "INFO", f"Skipping external role {role_url}")
        return 0

    await _log(state, "INFO", f"{LOG_PREFIX['nav']}: {role_url}")
    page = await new_page(context)
    try:
        if not await _load_page(page, role_url, state, "role"):
            return 0
        role_data = await validate_role_page(page)
        if not role_data:
            await _log(state, "WARNING", f"Invalid role page {role_url}")
            return 0

        page_text = " ".join([role_data.get("title", ""), role_data.get("body_text", "")])
        if not allow_agency(page_text):
            return 0
        if not passes_remote_filter(page_text):
            return 0

        scored = score_roles(page_text)
        if not scored:
            return 0

        await _log(state, "SUCCESS", f"{LOG_PREFIX['valid']}: {role_data['title']}")

        payload = {
            "company": company,
            "title": role_data.get("title") or "",
            "url": role_url,
            "location": role_data.get("location", ""),
            "summary": role_data.get("description_html", ""),
            "role": scored["role"],
            "score": scored["score"],
            "signals": scored.get("signals", []),
            "remote": _remote_flag(page_text),
            "domain": root_host,
            "ats": _host(role_url) if _host(role_url) in ATS_ALLOWLIST else "",
        }

        added = await notifier.notify_job(payload)
        if added:
            await _log(state, "SUCCESS", f"{LOG_PREFIX['saved']}: {payload['title']} ({payload['score']})")
            return 1
        return 0
    finally:
        await page.close()


async def crawl_domain(context: BrowserContext, company: str, url: str, notifier, state: Optional[CrawlerState] = None) -> Dict[str, Optional[int]]:
    root_host = _host(url)
    if is_blocked(url):
        await _log(state, "WARNING", f"Skipping blocked domain {url}")
        return {"delivered": 0}

    await _log(state, "INFO", f"{LOG_PREFIX['start']}: {company}")
    page = await new_page(context)

    if not await _load_page(page, url, state, "homepage"):
        await page.close()
        return {"delivered": 0}

    careers_url = await find_careers_link(page, url, root_host)
    if not careers_url:
        await _log(state, "WARNING", f"No careers link found for {url}")
        await page.close()
        await _log(state, "INFO", f"{LOG_PREFIX['end']}: {company}")
        return {"delivered": 0}

    await _log(state, "INFO", f"{LOG_PREFIX['careers']}: {careers_url}")

    if not await _load_page(page, careers_url, state, "careers"):
        await page.close()
        await _log(state, "INFO", f"{LOG_PREFIX['end']}: {company}")
        return {"delivered": 0}

    listings = await extract_hubspot_listings(page, careers_url, root_host)
    if listings:
        titles = ", ".join(sorted({l["title"] for l in listings}))
        await _log(state, "INFO", f"{LOG_PREFIX['roles']}: {titles}")
    else:
        await _log(state, "WARNING", f"No HubSpot roles found on careers page {careers_url}")
        await page.close()
        await _log(state, "INFO", f"{LOG_PREFIX['end']}: {company}")
        return {"delivered": 0}

    delivered = 0
    for listing in listings:
        role_url = urljoin(careers_url, listing.get("url") or careers_url)
        delivered += await _process_role_page(context, company, role_url, root_host, notifier, state)

    await page.close()
    await _log(state, "INFO", f"{LOG_PREFIX['end']}: {company}")
    return {"delivered": delivered}
