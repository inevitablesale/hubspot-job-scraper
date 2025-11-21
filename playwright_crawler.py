import asyncio
import json
import random
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Page, Route, async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
]

TIER1_KEYWORDS = ["career", "job", "opening", "join", "team", "work-with-us", "workwithus"]
TIER2_SEGMENTS = ["about", "team", "company", "people"]
SEE_ALL_TEXT = [
    "see all jobs",
    "view all roles",
    "view openings",
    "see openings",
    "explore roles",
    "view roles",
]
JOB_KEYWORDS = [
    "engineer",
    "developer",
    "designer",
    "manager",
    "specialist",
    "coordinator",
    "marketing",
    "sales",
    "analyst",
    "director",
    "lead",
    "intern",
    "product",
    "operations",
    "data",
    "staff",
]
ATS_HOSTS = {
    "greenhouse.io": "Greenhouse",
    "ghgr.co": "Greenhouse",
    "lever.co": "Lever",
    "workable.com": "Workable",
    "ashbyhq.com": "Ashby",
    "ashbyhq.net": "Ashby",
    "bamboohr.com": "BambooHR",
    "jazzhr.com": "JazzHR",
    "pinpointhq.com": "Pinpoint",
    "breezy.hr": "Breezy",
    "recruitee.com": "Recruitee",
    "smartrecruiters.com": "SmartRecruiters",
}


def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    if not domain:
        return ""
    parsed = urlparse(domain)
    if parsed.scheme:
        return domain
    return f"https://{domain}"


def is_same_domain(url: str, base: str) -> bool:
    base_host = urlparse(base).netloc
    target_host = urlparse(url).netloc
    return base_host and target_host and base_host.split(":")[0] == target_host.split(":")[0]


def looks_like_job_title(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in JOB_KEYWORDS) and len(text.split()) <= 12


def absolute_link(href: str, base_url: str) -> str:
    return urljoin(base_url, href)


async def block_media(route: Route):
    if route.request.resource_type in {"image", "media", "font"}:
        await route.abort()
    else:
        await route.continue_()


async def gather_links(page: Page, base_url: str) -> List[Dict[str, str]]:
    anchors = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(el => ({ href: el.href, text: el.innerText || '' }))",
    )
    seen: Set[str] = set()
    results: List[Dict[str, str]] = []
    for anchor in anchors:
        href = anchor.get("href") or ""
        text = (anchor.get("text") or "").strip()
        if not href:
            continue
        resolved = absolute_link(href, base_url)
        if resolved in seen:
            continue
        seen.add(resolved)
        results.append({"url": resolved, "text": text})
    return results


def rank_candidates(links: List[Dict[str, str]], base_url: str) -> List[str]:
    tier1: List[str] = []
    tier2: List[str] = []
    for link in links:
        url = link["url"]
        if not is_same_domain(url, base_url):
            continue
        path_lower = urlparse(url).path.lower()
        text_lower = (link.get("text") or "").lower()
        if any(keyword in path_lower for keyword in TIER1_KEYWORDS) or any(
            keyword in text_lower for keyword in TIER1_KEYWORDS
        ):
            tier1.append(url)
        elif any(path_lower.startswith(f"/{seg}") for seg in TIER2_SEGMENTS):
            tier2.append(url)
    return tier1 or tier2


async def click_see_all_jobs(page: Page) -> None:
    for label in SEE_ALL_TEXT:
        locator = page.get_by_text(label, exact=False)
        if await locator.count() > 0:
            try:
                await locator.first.click()
                await page.wait_for_load_state("networkidle")
                return
            except Exception:
                continue


def parse_jobs_from_html(html: str, base_url: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: List[Dict[str, str]] = []

    # Headings and list items
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "li"]):
        text = tag.get_text(strip=True)
        if text and looks_like_job_title(text):
            link = None
            if tag.name == "a":
                href = tag.get("href")
                link = absolute_link(href, base_url) if href else None
            jobs.append({"title": text, "url": link})

    # Anchor-based job cards
    for anchor in soup.find_all("a", href=True):
        text = anchor.get_text(strip=True)
        if not text:
            continue
        href = anchor.get("href")
        if looks_like_job_title(text) or "apply" in text.lower():
            jobs.append({"title": text, "url": absolute_link(href, base_url) if href else None})

    # Deduplicate by title + url
    seen: Set[str] = set()
    unique: List[Dict[str, str]] = []
    for job in jobs:
        key = f"{job.get('title','').lower()}|{job.get('url') or ''}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique


async def extract_ats_jobs_from_frame(frame) -> List[Dict[str, str]]:
    anchors = await frame.eval_on_selector_all(
        "a[href]",
        "els => els.map(el => ({ href: el.href, text: el.innerText || '' }))",
    )
    jobs: List[Dict[str, str]] = []
    for anchor in anchors:
        title = (anchor.get("text") or "").strip()
        href = anchor.get("href")
        if not title:
            continue
        if looks_like_job_title(title) or "apply" in title.lower():
            jobs.append({"title": title, "url": href})
    return jobs


async def detect_ats(page: Page) -> (Optional[str], List[Dict[str, str]]):
    # Check iframes
    for frame in page.frames:
        host = urlparse(frame.url).netloc
        for domain, name in ATS_HOSTS.items():
            if domain in host:
                jobs = await extract_ats_jobs_from_frame(frame)
                return name, jobs

    # Check page content for ATS API hints (e.g., Greenhouse)
    content = await page.content()
    greenhouse_match = re.search(r"boards(?:-api)?\.greenhouse\.io\/v1\/boards\/([\w-]+)/jobs", content)
    if greenhouse_match:
        board = greenhouse_match.group(1)
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        try:
            resp = httpx.get(api_url, timeout=10)
            resp.raise_for_status()
            payload = resp.json()
            jobs = [
                {"title": job.get("title"), "url": job.get("absolute_url")}
                for job in payload.get("jobs", [])
                if job.get("title")
            ]
            if jobs:
                return "Greenhouse", jobs
        except Exception:
            pass

    return None, []


def find_hiring_emails(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)


async def process_domain(domain: str, context, output_path: Optional[Path]) -> None:
    base_url = normalize_domain(domain)
    if not base_url:
        return

    page = await context.new_page()
    print(f"[Visiting] {base_url}")
    try:
        await page.goto(base_url, wait_until="networkidle", timeout=30000)
    except Exception:
        print(f"[RESULT] {domain} → failed to load homepage")
        await page.close()
        return

    links = await gather_links(page, base_url)
    candidates = rank_candidates(links, base_url)
    print(f"[CANDIDATES] → {candidates}")
    selected = candidates[0] if candidates else base_url
    print(f"[SELECTED] → {selected}")

    if selected != base_url:
        try:
            await page.goto(selected, wait_until="networkidle", timeout=30000)
        except Exception:
            print(f"[RESULT] {domain} → failed to load selected career page")
            await page.close()
            return

    await click_see_all_jobs(page)
    print(f"[PAGE] {page.url} → title=\"{await page.title()}\"")

    ats_name, ats_jobs = await detect_ats(page)
    html = await page.content()
    native_jobs = parse_jobs_from_html(html, page.url)
    text_content = await page.inner_text("body") if await page.locator("body").count() else ""
    hiring_emails = find_hiring_emails(text_content)

    all_jobs = ats_jobs or native_jobs
    job_titles = [job.get("title") for job in all_jobs if job.get("title")]
    print(f"[FOUND JOB TITLES] → {job_titles}")
    print(f"[ATS] Detected: {ats_name or 'None'}")
    if hiring_emails:
        print(f"[HIRING EMAIL] → {hiring_emails}")

    result_summary = {
        "domain": domain,
        "page": page.url,
        "ats": ats_name,
        "jobs": all_jobs,
        "hiring_emails": hiring_emails,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result_summary) + "\n")

    job_count = len(job_titles)
    result_line = f"[RESULT] {domain} → {job_count} job roles found"
    if not job_titles and hiring_emails:
        result_line = f"[RESULT] {domain} → Hiring via email: {', '.join(hiring_emails)}"
    print(result_line)
    await page.close()


async def crawl(domains: List[str], output_file: Optional[str]) -> None:
    if not domains:
        print("No domains provided.")
        return

    ua = random.choice(USER_AGENTS)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=ua)
        await context.route("**/*", block_media)

        output_path = Path(output_file) if output_file else None
        for domain in domains:
            await process_domain(domain, context, output_path)
            await asyncio.sleep(random.uniform(0.5, 2.0))

        await browser.close()


def load_domains(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Domains file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main(domains_file: str, output_file: Optional[str]) -> None:
    domains = load_domains(Path(domains_file))
    asyncio.run(crawl(domains, output_file))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Playwright-based career page crawler")
    parser.add_argument("--domains-file", required=True, help="Path to newline-delimited domains list")
    parser.add_argument("--output", default="results.jsonl", help="Path to JSONL output file")
    args = parser.parse_args()
    main(args.domains_file, args.output)
