import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Dict

from .browser import browser_context
from .crawler import crawl_domain
from .notifications import Notifier

DATASET_ENV_VAR = "DOMAINS_FILE"
RENDER_SECRET_DATASET = Path("/etc/secrets/DOMAINS_FILE")

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def load_companies() -> List[Dict[str, str]]:
    dataset_path = os.getenv(DATASET_ENV_VAR)
    if not dataset_path:
        dataset_path = str(RENDER_SECRET_DATASET)
    path = Path(dataset_path)
    if not path.exists():
        logger.error("Dataset file not found: %s", path)
        return []
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        logger.error("Failed to load dataset %s: %s", path, exc)
        return []
    companies: List[Dict[str, str]] = []
    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, str):
                companies.append({"company": entry, "url": _normalize_url(entry)})
            elif isinstance(entry, dict):
                website = entry.get("website") or entry.get("url")
                title = entry.get("title") or website or ""
                if website:
                    companies.append({"company": title, "url": _normalize_url(website)})
    return companies


async def run_all(headless: bool = True) -> Dict[str, int]:
    companies = load_companies()
    if not companies:
        return {"delivered": 0}

    delivered_total = 0
    notifier = Notifier()
    async with browser_context(headless=headless) as context:
        for company in companies:
            result = await crawl_domain(context, company["company"], company["url"], notifier)
            delivered_total += result.get("delivered", 0)
    return {"delivered": delivered_total}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_all())
