from typing import Dict

from playwright.async_api import BrowserContext


async def fetch_details(context: BrowserContext, listing: Dict) -> Dict:
    url = listing.get("url")
    page = await context.new_page()
    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(1500)

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
        name_el = await page.query_selector("h1");
        if name_el:
            result["title"] = (await name_el.inner_text()) or result["title"]
    except Exception:
        pass

    # Categories chips
    try:
        cat_nodes = await page.query_selector_all("button[jslog*='pane.rating.category']")
        for node in cat_nodes:
            txt = (await node.inner_text() or "").strip()
            if txt:
                result["categories"].append(txt)
    except Exception:
        pass

    # Description / highlights
    try:
        desc_node = await page.query_selector("div[aria-label*='About']")
        if desc_node:
            result["description"] = (await desc_node.inner_text())
    except Exception:
        pass

    # Website button in detail panel
    try:
        website_btn = await page.query_selector("a[data-item-id='authority']")
        if website_btn:
            href = await website_btn.get_attribute("href")
            if href:
                result["website"] = href
    except Exception:
        pass

    # Rating / reviews
    try:
        score_node = await page.query_selector("div[aria-label*='stars']")
        if score_node:
            aria = await score_node.get_attribute("aria-label")
            if aria and "star" in aria:
                import re

                m = re.search(r"(\d+\.\d)", aria)
                if m:
                    result["totalScore"] = float(m.group(1))
                m2 = re.search(r"(\d+) review", aria)
                if m2:
                    result["reviewsCount"] = int(m2.group(1))
    except Exception:
        pass

    # Tags (chips)
    try:
        chips = await page.query_selector_all("button[jslog*='pane.rating.tags']")
        for chip in chips:
            txt = (await chip.inner_text() or "").strip()
            if txt:
                result["tags"].append(txt)
    except Exception:
        pass

    await page.close()
    result["categories"] = sorted(set(result["categories"]))
    result["tags"] = sorted(set(result["tags"]))
    return result
