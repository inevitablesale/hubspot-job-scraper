import json
import re
from typing import Dict, Optional

from playwright.async_api import BrowserContext, Page


def _parse_location(schema_obj: Dict) -> Dict:
    address = schema_obj.get("address") or {}
    return {
        "street": address.get("streetAddress") or address.get("street"),
        "city": address.get("addressLocality") or address.get("city"),
        "state": address.get("addressRegion") or address.get("state"),
        "countryCode": address.get("addressCountry") or address.get("countryCode"),
    }


def _clean_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.strip()
    return text or None


async def _extract_json_ld(page: Page) -> Optional[Dict]:
    try:
        nodes = await page.query_selector_all("script[type='application/ld+json']")
        for node in nodes:
            raw = await node.inner_text()
            if not raw:
                continue
            data = json.loads(raw)
            if isinstance(data, list):
                data = data[0]
            if isinstance(data, dict) and data.get("@type") in {"LocalBusiness", "Organization", "Place"}:
                return data
    except Exception:
        return None
    return None


async def fetch_details(context: BrowserContext, listing: Dict) -> Dict:
    url = listing.get("url")
    page = await context.new_page()
    from server import set_current_page

    set_current_page(page)
    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(1200)

    result = {
        "title": listing.get("title", ""),
        "website": listing.get("website"),
        "categories": [],
        "description": None,
        "totalScore": listing.get("totalScore"),
        "reviewsCount": listing.get("reviewsCount"),
        "tags": [],
        "maps_url": url,
        "location": listing.get("location") or {},
    }

    try:
        name_el = await page.query_selector("h1")
        if name_el:
            result["title"] = _clean_text(await name_el.inner_text()) or result["title"]
    except Exception:
        pass

    try:
        cat_nodes = await page.query_selector_all("button[jslog*='pane.rating.category']")
        for node in cat_nodes:
            txt = _clean_text(await node.inner_text())
            if txt:
                result["categories"].append(txt)
    except Exception:
        pass

    try:
        desc_node = await page.query_selector("div[aria-label*='About']")
        if desc_node:
            result["description"] = _clean_text(await desc_node.inner_text())
    except Exception:
        pass

    try:
        website_btn = await page.query_selector("a[data-item-id='authority']")
        if website_btn:
            href = await website_btn.get_attribute("href")
            if href:
                result["website"] = href
    except Exception:
        pass

    try:
        score_node = await page.query_selector("div[aria-label*='stars']")
        if score_node:
            aria = await score_node.get_attribute("aria-label")
            if aria and "star" in aria:
                m = re.search(r"(\d+\.\d)", aria)
                if m:
                    result["totalScore"] = float(m.group(1))
                m2 = re.search(r"(\d+) review", aria)
                if m2:
                    result["reviewsCount"] = int(m2.group(1))
    except Exception:
        pass

    try:
        chips = await page.query_selector_all("button[jslog*='pane.rating.tags']")
        for chip in chips:
            txt = _clean_text(await chip.inner_text())
            if txt:
                result["tags"].append(txt)
    except Exception:
        pass

    schema = await _extract_json_ld(page)
    if schema:
        result["description"] = result.get("description") or schema.get("description")
        result["website"] = result.get("website") or schema.get("url")
        schema_cats = schema.get("@type")
        if isinstance(schema_cats, list):
            result["categories"].extend(schema_cats)
        elif isinstance(schema_cats, str):
            result["categories"].append(schema_cats)
        result["location"] = result.get("location") or _parse_location(schema)

    await page.close()
    result["categories"] = sorted({c for c in result["categories"] if c})
    result["tags"] = sorted({t for t in result["tags"] if t})
    return result
