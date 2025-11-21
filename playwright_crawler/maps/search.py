import asyncio
import random
import re
from typing import Dict, List

from playwright.async_api import BrowserContext, Page, ElementHandle

DEFAULT_QUERIES = [
    "hubspot partner",
    "hubspot agency",
    "marketing agency hubspot",
    "crm implementation partner",
    "revops agency",
]


async def _maybe_human_pause(page: Page, base: int = 600, jitter: int = 400):
    await page.wait_for_timeout(base + random.randint(0, jitter))


async def _scroll_results(page: Page, target: int):
    """Scroll the Maps results pane to load more cards."""
    scrollable = await page.query_selector("div[role='feed']")
    if not scrollable:
        return
    loaded = 0
    for _ in range(8):
        await _maybe_human_pause(page, 350, 250)
        try:
            await scrollable.evaluate("el => el.scrollTop = el.scrollHeight")
        except Exception:
            break
        cards = await page.query_selector_all("div[role='article']")
        loaded = len(cards)
        if loaded >= target:
            break


async def _parse_card(card: ElementHandle) -> Dict:
    title = await card.get_attribute("aria-label")
    rating_text = await card.get_attribute("aria-label") or ""
    url = await card.evaluate("el => el.querySelector('a') ? el.querySelector('a').href : ''")

    website = None
    try:
        website_el = await card.query_selector("a[data-value][role='link']")
        if website_el:
            website = await website_el.get_attribute("href")
    except Exception:
        website = None

    total_score = None
    reviews_count = None
    score_match = re.search(r"(\d+\.\d) star", rating_text)
    if score_match:
        try:
            total_score = float(score_match.group(1))
        except Exception:
            total_score = None
    reviews_match = re.search(r"(\d+) review", rating_text)
    if reviews_match:
        try:
            reviews_count = int(reviews_match.group(1))
        except Exception:
            reviews_count = None

    category = None
    try:
        # category chips often show up as the first span inside the card
        category = await card.evaluate(
            "el => { const node = el.querySelector('span[jsinstance]'); return node ? node.textContent : '' }"
        )
    except Exception:
        category = None

    return {
        "title": title or "",
        "categoryName": category or None,
        "website": website,
        "url": url,
        "totalScore": total_score,
        "reviewsCount": reviews_count,
        "location": {"street": None, "city": None, "state": None, "countryCode": None},
    }


async def run_search(context: BrowserContext, query: str, max_results: int = 25) -> List[Dict]:
    page = await context.new_page()
    from server import set_current_page

    set_current_page(page)
    results: List[Dict] = []
    try:
        await page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
        await _maybe_human_pause(page, 700, 300)
        await page.fill("input#searchboxinput", query)
        await page.press("input#searchboxinput", "Enter")
        await page.wait_for_selector("div[role='article']", timeout=10000)
        await _scroll_results(page, max_results)

        cards = await page.query_selector_all("div[role='article']")
        for card in cards[:max_results]:
            results.append(await _parse_card(card))
            await asyncio.sleep(random.uniform(0.05, 0.15))
    finally:
        await page.close()
    return results


async def search_many(context: BrowserContext, queries: List[str]) -> List[Dict]:
    aggregated: List[Dict] = []
    for query in queries:
        aggregated.extend(await run_search(context, query))
        await asyncio.sleep(0.3)
    return aggregated
