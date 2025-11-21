import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Dict

from .browser import browser_context
from .crawler import crawl_domain
from .hubspot_detector import detect_hubspot_by_url
from .maps import details as maps_details
from .maps import domain_extractor, search as maps_search, signals as map_signals
from .notifications import Notifier
from .state import get_registry, get_state
from .utils import normalize_domain

DATASET_ENV_VAR = "DOMAINS_FILE"
RENDER_SECRET_DATASET = Path("/etc/secrets/DOMAINS_FILE")

logger = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def load_companies() -> List[Dict[str, str]]:
    registry = get_registry()
    records = registry.get_all()
    if not records:
        # fall back to legacy loader
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
        records = data if isinstance(data, list) else []

    companies: List[Dict[str, str]] = []
    for entry in records:
        if isinstance(entry, str):
            companies.append({"company": entry, "url": _normalize_url(entry)})
        elif isinstance(entry, dict):
            domain = entry.get("domain") or entry.get("website") or entry.get("url")
            dom = normalize_domain(domain) if domain else None
            if not dom:
                continue
            companies.append({"company": entry.get("company") or entry.get("title") or dom, "url": _normalize_url(dom)})
    return companies


async def run_all(headless: bool = True, companies: List[Dict[str, str]] = None, prestarted: bool = False) -> Dict[str, int]:
    state = get_state()
    companies = companies or load_companies()
    if not companies:
        state.add_log("ERROR", "No companies to crawl")
        state.mark_idle()
        return {"delivered": 0}

    if not prestarted:
        state.start_run(companies)
    else:
        # Ensure the dashboard sees an active run even if start_run was called earlier.
        state.set_running_mode("jobs")
    delivered_total = 0
    notifier = Notifier(on_new_job=state.add_job)

    try:
        async with browser_context(headless=headless) as context:
            for company in companies:
                state.add_log("INFO", f"Starting crawl for {company['company']}")
                state.mark_company_status(company["company"], "processing")
                result = await crawl_domain(context, company["company"], company["url"], notifier, state)
                delivered_total += result.get("delivered", 0)
                state.mark_company_status(company["company"], "done", jobs=result.get("delivered", 0))
    except asyncio.CancelledError:
        state.add_log("WARNING", "Run cancelled")
        state.finish_run(delivered_total)
        raise
    except Exception as exc:
        state.add_log("ERROR", f"Run failed: {exc}")
        state.finish_run(delivered_total)
        raise

    state.finish_run(delivered_total)
    return {"delivered": delivered_total}


async def run_maps_radar(
    queries: List[str] = None,
    limit: int = 50,
    headless: bool = True,
    manage_state: bool = True,
) -> Dict:
    queries = queries or maps_search.DEFAULT_QUERIES
    registry = get_registry()
    state = get_state()
    added = 0
    seen = 0

    if manage_state:
        state.set_running_mode("maps")

    try:
        async with browser_context(headless=headless) as context:
            for query in queries:
                state.add_log("INFO", f"Maps radar search: {query}")
                listings = await maps_search.run_search(context, query)
                for listing in listings:
                    seen += 1
                    detail = await maps_details.fetch_details(context, listing)
                    signals = map_signals.score_detail(detail)
                    candidate = domain_extractor.to_candidate(detail, signals)
                    if not candidate:
                        continue
                    candidate["categoryName"] = listing.get("categoryName") or candidate.get("categoryName")
                    candidate["score"] = candidate.get("score", 0) + signals.get("score", 0)
                    candidate["signals"] = list(
                        dict.fromkeys(candidate.get("signals", []) + signals.get("signals", []))
                    )
                    if candidate.get("raw_website"):
                        hubspot_info = await detect_hubspot_by_url(context, candidate["raw_website"], candidate["domain"])
                        candidate["hubspot"] = hubspot_info
                    if await registry.add_candidate(candidate, source="maps"):
                        added += 1
                    if limit and added >= limit:
                        break
                if limit and added >= limit:
                    break
    finally:
        if manage_state:
            state.mark_idle()
    return {"queries": len(queries), "seen": seen, "added": added}


async def run_domain_cleanup(failure_threshold: int = 3):
    registry = get_registry()
    removed = []
    records = registry.get_all()
    for rec in records:
        if rec.get("failures", 0) >= failure_threshold:
            await registry.remove(rec.get("domain"))
            removed.append(rec.get("domain"))
    return {"removed": removed, "count": len(removed)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_all())
