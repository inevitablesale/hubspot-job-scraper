import json
import re
from typing import List, Dict, Any
from urllib.parse import urljoin
from selectolax.parser import HTMLParser

TITLE_HINTS = ["manager", "architect", "specialist", "director", "developer", "consultant", "engineer", "lead"]
SECTION_HINTS = ["open positions", "jobs", "careers", "opportunities", "join our", "join us"]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _extract_json_ld(tree: HTMLParser, base_url: str) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for node in tree.css("script[type='application/ld+json']"):
        try:
            data = json.loads(node.text())
        except Exception:
            continue
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict):
                continue
            if entry.get("@type") in {"JobPosting", ["JobPosting"]}:
                title = entry.get("title") or ""
                url = entry.get("url") or base_url
                location = ""
                loc = entry.get("jobLocation")
                if isinstance(loc, dict):
                    address = loc.get("address") or {}
                    location = address.get("addressLocality") or address.get("addressRegion") or ""
                summary = entry.get("description") or ""
                jobs.append(
                    {
                        "title": _clean_text(title),
                        "url": urljoin(base_url, url),
                        "location": _clean_text(location),
                        "summary": _clean_text(summary),
                    }
                )
    return jobs


def _extract_anchors(tree: HTMLParser, base_url: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for a in tree.css("a"):
        href = a.attrs.get("href")
        text = _clean_text(a.text())
        if not href or not text:
            continue
        lower = (href + " " + text).lower()
        if "job" in lower or "career" in lower or any(h in lower for h in TITLE_HINTS):
            results.append({"title": text, "url": urljoin(base_url, href), "summary": ""})
    return results


def _extract_headings(tree: HTMLParser) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for tag in ["h2", "h3", "h4"]:
        for h in tree.css(tag):
            text = _clean_text(h.text())
            if any(k in text.lower() for k in TITLE_HINTS) and len(text.split()) <= 12:
                results.append({"title": text, "url": None, "summary": ""})
    return results


def _extract_buttons(tree: HTMLParser, base_url: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for btn in tree.css("button, [role='button']"):
        text = _clean_text(btn.text())
        if any(k in text.lower() for k in TITLE_HINTS):
            href = btn.attrs.get("onclick") or ""
            match = re.search(r"['\"](http[^'\"]+)['\"]", href)
            url = match.group(1) if match else None
            results.append({"title": text, "url": url, "summary": ""})
    return results


def _extract_sections(tree: HTMLParser, base_url: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for section in tree.css("section, div"):
        text = _clean_text(section.text())
        if not text:
            continue
        lower = text.lower()
        if any(h in lower for h in SECTION_HINTS):
            # look for headings inside
            for node in section.css("h2, h3, h4"):
                title = _clean_text(node.text())
                if title and any(k in title.lower() for k in TITLE_HINTS):
                    results.append({"title": title, "url": None, "summary": text[:400]})
    return results


def extract_jobs_from_html(html: str, base_url: str) -> List[Dict[str, Any]]:
    tree = HTMLParser(html)
    jobs: List[Dict[str, Any]] = []
    jobs.extend(_extract_json_ld(tree, base_url))
    jobs.extend(_extract_anchors(tree, base_url))
    jobs.extend(_extract_buttons(tree, base_url))
    jobs.extend(_extract_sections(tree, base_url))
    jobs.extend(_extract_headings(tree))

    deduped = []
    seen = set()
    for job in jobs:
        key = (job.get("title"), job.get("url"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)
    return deduped
