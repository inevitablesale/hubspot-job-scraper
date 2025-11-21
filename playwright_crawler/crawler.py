import asyncio
import logging
from typing import Dict, Optional

from playwright.async_api import Page, BrowserContext

from .browser import new_page, gentle_scroll
from .detect_pages import find_careers_link
from .extractors import extract_jobs_from_html
from .filters import is_blocked, allow_agency, passes_remote_filter
from .signals import score_roles
from .state import CrawlerState

logger = logging.getLogger(__name__)

BUTTON_PROMPTS = [
    "open positions",
    "view roles",
    "see all jobs",
    "view openings",
    "openings",
    "view positions",
]


async def _click_prompts(page: Page):
    for label in BUTTON_PROMPTS:
        locator = page.get_by_text(label, exact=False)
        try:
            if await locator.count() > 0:
                await locator.first.click(timeout=2000)
                await asyncio.sleep(0.5)
        except Exception:
            continue


def _is_remote(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in ["remote", "distributed", "work from home", "us remote", "united states (remote)"])


async def _process_page(page: Page, company: str, source_url: str, notifier, state: Optional[CrawlerState]) -> int:
    html = await page.content()
    body_text = await page.inner_text("body") if await page.locator("body").count() else html
    jobs = extract_jobs_from_html(html, source_url)
    delivered = 0
    for job in jobs:
        job_text = " ".join([
            job.get("title", ""),
            job.get("summary", ""),
            body_text,
        ])
        if not allow_agency(job_text):
            if state:
                state.add_log("INFO", f"Skipping agency job on {source_url}")
            continue
        if not passes_remote_filter(job_text):
            if state:
                state.add_log("INFO", f"Skipping non-remote job on {source_url}")
            continue
        score = score_roles(job_text)
        if not score:
            continue
        payload = {
            "company": company,
            "title": job.get("title") or "",
            "url": job.get("url") or source_url,
            "location": job.get("location", ""),
            "summary": job.get("summary", ""),
            "role": score["role"],
            "score": score["score"],
            "signals": score.get("signals", []),
            "remote": _is_remote(job_text),
        }
        added = await notifier.notify_job(payload)
        if added and state:
            state.add_log("SUCCESS", f"Matched {payload['title']} ({payload['score']}) at {company}")
        if added:
            delivered += 1
    return delivered


async def crawl_domain(context: BrowserContext, company: str, url: str, notifier, state: Optional[CrawlerState] = None) -> Dict[str, Optional[int]]:
    if is_blocked(url):
        if state:
            state.add_log("WARNING", f"Skipping blocked domain {url}")
        return {"delivered": 0}

    page = await new_page(context)
    try:
        await page.goto(url, wait_until="load")
        await page.wait_for_timeout(1500)
        await gentle_scroll(page)
    except Exception as exc:
        logger.error("Failed to load %s: %s", url, exc)
        if state:
            state.add_log("ERROR", f"Failed to load {url}: {exc}")
        await page.close()
        return {"delivered": 0}

    careers_url = await find_careers_link(page, url)
    if not careers_url:
        if state:
            state.add_log("WARNING", f"No careers link found for {url}")
        await page.close()
        return {"delivered": 0}

    try:
        await page.goto(careers_url, wait_until="load")
        await page.wait_for_timeout(1500)
        await gentle_scroll(page)
        await _click_prompts(page)
        await gentle_scroll(page)
    except Exception as exc:
        logger.error("Failed to load careers page %s: %s", careers_url, exc)
        if state:
            state.add_log("ERROR", f"Failed to load careers page {careers_url}: {exc}")
        await page.close()
        return {"delivered": 0}

    delivered = await _process_page(page, company, careers_url, notifier, state)

    for frame in page.frames:
        try:
            html = await frame.content()
        except Exception:
            continue
        jobs = extract_jobs_from_html(html, frame.url)
        if not jobs:
            continue
        body_text = html
        for job in jobs:
            job_text = " ".join([job.get("title", ""), job.get("summary", ""), body_text])
            if not allow_agency(job_text):
                continue
            if not passes_remote_filter(job_text):
                continue
            score = score_roles(job_text)
            if not score:
                continue
            payload = {
                "company": company,
                "title": job.get("title") or "",
                "url": job.get("url") or careers_url,
                "location": job.get("location", ""),
                "summary": job.get("summary", ""),
                "role": score["role"],
                "score": score["score"],
                "signals": score.get("signals", []),
                "remote": _is_remote(job_text),
            }
            added = await notifier.notify_job(payload)
            if added and state:
                state.add_log("SUCCESS", f"Matched {payload['title']} ({payload['score']}) at {company}")
            if added:
                delivered += 1

    await page.close()
    return {"delivered": delivered}
