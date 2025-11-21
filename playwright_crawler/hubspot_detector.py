import re
from typing import Dict, List, Optional

from playwright.async_api import BrowserContext, Page


HS_SCRIPT_PATTERN = re.compile(r"js\.hs-scripts\.com/(\d+)\.js")
HS_CLUES = [
    "js.usemessages.com",
    "hs-banner",
    "hs-analytics",
    "hsforms",
    "hs-scripts.com",
]


async def detect_hubspot(page: Page, domain: str) -> Dict:
    signals: List[str] = []
    portal_id: Optional[str] = None

    html = await page.content()
    for match in HS_SCRIPT_PATTERN.finditer(html):
        portal_id = match.group(1)
        signals.append("hs-scripts.com script tag")

    for clue in HS_CLUES:
        if clue in html:
            signals.append(f"Found {clue}")

    try:
        cookies = await page.context.cookies()
        for cookie in cookies:
            if cookie.get("name", "").startswith("__hs") or cookie.get("name") == "hubspotutk":
                signals.append("HubSpot cookies present")
                break
    except Exception:
        pass

    has = bool(signals)
    confidence = 30 + (20 if portal_id else 0) + (10 if len(signals) > 2 else 0)
    return {
        "has_hubspot": has,
        "portal_id": portal_id,
        "signals": list(dict.fromkeys(signals)),
        "confidence": min(confidence, 100),
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
