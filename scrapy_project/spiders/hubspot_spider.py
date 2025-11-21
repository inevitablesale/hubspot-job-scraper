import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import scrapy

CAREER_HINTS = [
    "career",
    "careers",
    "jobs",
    "job-openings",
    "join-our-team",
    "join-us",
    "work-with",
    "work-with-us",
    "work-for-us",
    "opportunities",
    "open-positions",
    "openings",
]

HUBSPOT_KEYWORDS = ["hubspot", "hub spot"]
ROLE_KEYWORDS = [
    "consultant",
    "developer",
    "engineer",
    "specialist",
    "architect",
    "admin",
    "administrator",
]

DATASET_ENV_VAR = "DOMAINS_FILE"
RENDER_SECRET_DATASET = Path("/etc/secrets/DOMAINS_FILE")


class HubspotSpider(scrapy.Spider):
    name = "hubspot"
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
        "CONCURRENT_REQUESTS": 10,
        "ITEM_PIPELINES": {"scrapy_project.pipelines.NtfyNotifyPipeline": 1},
        "LOG_LEVEL": "ERROR",
    }

    def start_requests(self):
        companies = self._load_companies()
        if not companies:
            return

        for company in companies:
            website = company.get("website")
            title = company.get("title") or website
            normalized = self._normalize_start_url(website)
            if normalized:
                yield scrapy.Request(
                    url=normalized,
                    callback=self.parse_home,
                    meta={"company": title, "root": normalized},
                )

    def parse_home(self, response):
        company = response.meta["company"]
        root = response.meta["root"]
        host_root = self._get_host(root)

        seen = set()
        for sel in response.css("a"):
            href = sel.attrib.get("href")
            text = sel.css("::text").get() or ""
            if not href:
                continue
            full_url = self._safe_urljoin(root, href)
            if not full_url:
                continue
            if self._is_internal(full_url, host_root) and self._looks_like_career(full_url, text):
                if full_url not in seen:
                    seen.add(full_url)
                    yield scrapy.Request(
                        url=full_url,
                        callback=self.parse_career_page,
                        meta={"company": company, "job_page": full_url},
                    )

    def parse_career_page(self, response):
        text = response.text.lower()
        if any(k in text for k in HUBSPOT_KEYWORDS) and any(r in text for r in ROLE_KEYWORDS):
            yield {
                "company": response.meta["company"],
                "job_page": response.meta["job_page"],
            }

    def _get_host(self, url):
        netloc = urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc

    def _safe_urljoin(self, base, href):
        try:
            joined = urljoin(base, href)
        except ValueError:
            return None

        scheme = urlparse(joined).scheme.lower()
        if scheme not in {"http", "https"}:
            return None

        return joined

    def _is_internal(self, url, root_host):
        link_host = urlparse(url).netloc.lower()
        if link_host.startswith("www."):
            link_host = link_host[4:]
        return link_host == root_host or link_host.endswith("." + root_host)

    def _looks_like_career(self, url, text):
        target = url.lower() + " " + text.lower()
        return any(h in target for h in CAREER_HINTS)

    def _load_companies(self):
        dataset_path = self._resolve_dataset_path()

        if not dataset_path:
            return []

        try:
            with dataset_path.open() as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            self.logger.error("Invalid JSON in %s: %s", dataset_path, exc)
            return []

        companies = []
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, str):
                    companies.append({"title": entry, "website": entry})
                elif isinstance(entry, dict):
                    website = entry.get("website") or entry.get("url")
                    title = entry.get("title") or website
                    if website:
                        companies.append({"title": title, "website": website})
        else:
            self.logger.error("Dataset %s must be a JSON array", dataset_path)

        if not companies:
            self.logger.error("No valid companies found in %s", dataset_path)

        return companies

    def _normalize_start_url(self, url):
        if not url:
            return None

        redirected = self._extract_redirect_target(url)
        parsed = urlparse(redirected)
        if parsed.scheme and parsed.netloc:
            return redirected

        candidate = f"https://{redirected}" if not parsed.scheme else redirected
        parsed_candidate = urlparse(candidate)

        if parsed_candidate.scheme in {"http", "https"} and parsed_candidate.netloc:
            return candidate

        self.logger.error("Skipping invalid website URL: %s", url)
        return None

    def _extract_redirect_target(self, url):
        """Handle Google /url redirects by pulling the ?q= target when present."""

        parsed = urlparse(url)

        if parsed.path == "/url":
            target = parse_qs(parsed.query).get("q", [None])[0]
            if target:
                return target

        return url

    def _resolve_dataset_path(self):
        env_path = os.getenv(DATASET_ENV_VAR)
        candidate = Path(env_path) if env_path else RENDER_SECRET_DATASET

        if candidate.exists():
            return candidate

        self.logger.error("Dataset file not found: %s", candidate)
        return None
