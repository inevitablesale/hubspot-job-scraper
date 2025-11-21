import asyncio
from typing import Dict, List

from playwright.async_api import BrowserContext


DEFAULT_QUERIES = [
    "hubspot partner",
    "hubspot agency",
    "marketing agency hubspot",
    "crm implementation partner",
    "revops agency",
]


async def run_search(context: BrowserContext, query: str, max_results: int = 25) -> List[Dict]:
    page = await context.new_page()
    results: List[Dict] = []
    await page.goto("https://www.google.com/maps", wait_until="networkidle")
    await page.fill("input#searchboxinput", query)
    await page.press("input#searchboxinput", "Enter")
    await page.wait_for_timeout(1500)
    await page.wait_for_selector("div[role='article']", timeout=8000)

    cards = await page.query_selector_all("div[role='article']")
    for card in cards[:max_results]:
        title = await card.get_attribute("aria-label")
        website = None
        try:
            # Small info chips sometimes include website as data-value
            website_el = await card.query_selector("a[data-value][role='link']")
            if website_el:
                website = await website_el.get_attribute("href")
        except Exception:
            website = None

        url = await card.evaluate("el => el.querySelector('a') ? el.querySelector('a').href : ''")
        category = await card.evaluate('el => el.querySelector("[aria-label*=\\"stars\\"]") ? "" : ""')
        rating_text = await card.get_attribute("aria-label") or ""
        total_score = None
        reviews_count = None
        # crude parse from aria-label e.g. "Business name 4.7 stars from 23 reviews"
        import re

        match = re.search(r"(\d+\.\d) star", rating_text)
        if match:
            try:
                total_score = float(match.group(1))
            except Exception:
                total_score = None
        match_reviews = re.search(r"(\d+) review", rating_text)
        if match_reviews:
            try:
                reviews_count = int(match_reviews.group(1))
            except Exception:
                reviews_count = None

        results.append(
            {
                "title": title or "",
                "categoryName": category or None,
                "website": website,
                "url": url,
                "totalScore": total_score,
                "reviewsCount": reviews_count,
                "location": {
                    "street": None,
                    "city": None,
                    "state": None,
                    "countryCode": None,
                },
            }
        )
    await page.close()
    return results


async def search_many(context: BrowserContext, queries: List[str]) -> List[Dict]:
    aggregated: List[Dict] = []
    for query in queries:
        aggregated.extend(await run_search(context, query))
        await asyncio.sleep(0.2)
    return aggregated
