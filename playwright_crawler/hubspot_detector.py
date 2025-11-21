import re
from typing import Dict, List, Optional

from playwright.async_api import BrowserContext, Page


HS_SCRIPT_PATTERN = re.compile(r"js\.hs-scripts\.com/(\d+)\.js")
HS_SCRIPT_CLUES = [
    "js.usemessages.com",
    "hs-banner",
    "hs-analytics",
    "hsforms",
    "hs-scripts.com",
    "hscollectedforms",  # collected forms embed
]

# Textual clues that usually appear on HubSpot-powered pages or partner sites.
HS_TEXT_CLUES = [
    "hubspot partner",
    "solutions partner",
    "hubspot solutions partner",
    "powered by hubspot",
]


async def _collect_script_sources(page: Page) -> List[str]:
    return await page.eval_on_selector_all(
        "script[src]", "(els) => els.map(e => e.getAttribute('src') || '')"
    )


async def _detect_forms(page: Page) -> bool:
    # HubSpot embeds forms either inline (hs-form), via iframes, or via hbspt.forms()
    form_selectors = [
        "form[class*='hs-form']",
        "form[id*='hs-form']",
        "iframe[src*='hsforms']",
        "iframe[src*='hubspot']",
    ]
    for selector in form_selectors:
        if await page.query_selector(selector):
            return True

    script_mentions = await page.eval_on_selector_all(
        "script",
        "(els) => els.map(e => e.innerText || '').filter(t => t && t.toLowerCase().includes('hbspt.forms'))",
    )
    return bool(script_mentions)


async def detect_hubspot(page: Page, domain: str) -> Dict:
    signals: List[str] = []
    portal_id: Optional[str] = None

    html = (await page.content()).lower()
    script_srcs = [s.lower() for s in await _collect_script_sources(page)]

    for src in script_srcs:
        match = HS_SCRIPT_PATTERN.search(src)
        if match:
            portal_id = match.group(1)
            signals.append("hs-scripts.com script tag")
        for clue in HS_SCRIPT_CLUES:
            if clue in src:
                signals.append(f"Script: {clue}")

    if await _detect_forms(page):
        signals.append("HubSpot forms detected")

    for clue in HS_TEXT_CLUES:
        if clue in html:
            signals.append(f"Text clue: {clue}")

    try:
        cookies = await page.context.cookies()
        for cookie in cookies:
            name = cookie.get("name", "")
            if name.startswith("__hs") or name in {"hubspotutk", "__hstc"}:
                signals.append("HubSpot cookies present")
                break
    except Exception:
        # Cookie access can fail in some contexts; ignore quietly.
        pass

    has = bool(signals)
    confidence = 0
    if portal_id:
        confidence += 40
    if any("forms" in s.lower() for s in signals):
        confidence += 25
    if any("script" in s.lower() for s in signals):
        confidence += 20
    if any("cookies" in s.lower() for s in signals):
        confidence += 10
    if any("text clue" in s.lower() for s in signals):
        confidence += 5
    confidence = min(confidence or (20 if has else 0), 100)

    return {
        "has_hubspot": has,
        "portal_id": portal_id,
        "signals": list(dict.fromkeys(signals)),
        "confidence": confidence,
        "domain": domain,
    }


async def detect_hubspot_by_url(context: BrowserContext, url: str, domain: str) -> Dict:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(1200)
        return await detect_hubspot(page, domain)
    finally:
        await page.close()
