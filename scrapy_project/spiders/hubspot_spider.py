import json
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse

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
DEFAULT_DATASET_FILE = (
    Path(__file__).resolve().parent.parent / "dataset_crawler-google-places_2025-11-20_21-44-01-758.json"
)


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
            if website:
                yield scrapy.Request(
                    url=website,
                    callback=self.parse_home,
                    meta={"company": title, "root": website},
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
            full_url = urljoin(root, href)
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

    def _is_internal(self, url, root_host):
        link_host = urlparse(url).netloc.lower()
        if link_host.startswith("www."):
            link_host = link_host[4:]
        return link_host == root_host or link_host.endswith("." + root_host)

    def _looks_like_career(self, url, text):
        target = url.lower() + " " + text.lower()
        return any(h in target for h in CAREER_HINTS)

    def _load_companies(self):
        dataset_path = Path(os.getenv(DATASET_ENV_VAR, DEFAULT_DATASET_FILE))

        if not dataset_path.exists():
            self.logger.error("Dataset file not found: %s", dataset_path)
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
