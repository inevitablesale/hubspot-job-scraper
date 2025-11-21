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
    "apply",
    "team",
    "we-are-hiring",
    "work-with-me",
]

HUBSPOT_TECH_KEYWORDS = [
    "hubspot",
    "hub spot",
    "crm",
    "workflows",
    "integrations",
    "cms hub",
    "marketing hub",
    "service hub",
    "operations hub",
    "inbound",
    "reports",
    "dashboards",
    "portal",
    "map properties",
    "api",
    "app",
    "private app token",
]

# Additional strong indicators of real HubSpot roles
HUBSPOT_STRONG_SIGNALS = [
    "hubspot certified",
    "hubspot certification",
    "hubspot partner",
    "hubspot elite partner",
    "hubspot gold partner",
    "operations hub",
    "hubdb",
    "serverless functions",
    "custom object",
]

CONSULTANT_INTENT = [
    "hubspot consultant",
    "crm consultant",
    "revops consultant",
    "marketing ops",
    "solutions architect",
    "hubspot onboarding",
    "hubspot implementation",
    "hubspot specialist",
    "revops specialist",
    "workflow automation",
]

DEVELOPER_INTENT = [
    "hubspot developer",
    "hubspot cms developer",
    "hubspot theme",
    "hubspot custom modules",
    "hubspot serverless",
    "hubspot api",
    "hubspot integrations",
    "nodejs hubspot",
    "python hubspot api",
]

# Subtypes for better classification
SENIOR_CONSULTANT_INTENT = [
    "senior consultant",
    "lead consultant",
    "principal consultant",
]

ARCHITECT_INTENT = [
    "solutions architect",
    "revops architect",
    "technical architect",
    "systems architect",
]

SKIP_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "fb.com",
    "messenger.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "yelp.com",
    "youtube.com",
    "wix.com",
    "wixstatic.com",
    "godaddy.com",
    "about:blank",
}

CAREER_HOSTS = {
    "greenhouse.io",
    "ashbyhq.com",
    "workable.com",
    "bamboohr.com",
    "lever.co",
}

# Treat these as off-domain ATS “mini roots” we’re allowed to crawl.
ATS_HOSTS = CAREER_HOSTS

# Heuristics for URLs on ATS hosts that likely correspond to jobs or job listings.
ATS_JOB_URL_HINTS = [
    "job",
    "jobs",
    "careers",
    "positions",
    "opportunities",
    "opening",
    "open-positions",
    "vacancy",
]

DATASET_ENV_VAR = "DOMAINS_FILE"
RENDER_SECRET_DATASET = Path("/etc/secrets/DOMAINS_FILE")


class HubspotSpider(scrapy.Spider):
    name = "hubspot"
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
        "CONCURRENT_REQUESTS": 10,
        "ITEM_PIPELINES": {"scrapy_project.pipelines.NtfyNotifyPipeline": 1},
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track ATS URLs we’ve already crawled to avoid loops.
        self.ats_seen = set()

    def start_requests(self):
        companies = self._load_companies()
        if not companies:
            return

        for company in companies:
            website = company.get("website")
            title = company.get("title") or website
            normalized = self._normalize_start_url(website)
            if normalized and not self._should_skip_domain(normalized):
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

            if self._should_skip_domain(full_url):
                continue

            # 1) Off-domain ATS “follow-then-parse” mode
            if self._is_ats_host(full_url):
                norm = self._normalize_ats_url(full_url)
                if norm not in self.ats_seen:
                    self.ats_seen.add(norm)
                    yield scrapy.Request(
                        url=full_url,
                        callback=self.parse_ats_page,
                        meta={
                            "company": company,
                            # Treat the ATS host as a secondary root
                            "ats_root": self._get_host(full_url),
                        },
                    )
                continue

            # 2) Regular on-domain career links
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
        role_match = self._evaluate_roles(text)
        if not role_match:
            return

        yield {
            "company": response.meta["company"],
            "job_page": response.meta["job_page"],
            "role": role_match["role"],
            "score": role_match["score"],
            "signals": role_match["signals"],
        }

    def parse_ats_page(self, response):
        """
        Follow-then-parse mode for off-domain ATS hosts.
        Treats the ATS host as a small internal site: we score the current page
        and then follow other job-looking URLs on the same host.
        """
        company = response.meta["company"]
        ats_root = response.meta.get("ats_root") or self._get_host(response.url)

        text = response.text.lower()
        role_match = self._evaluate_roles(text)
        if role_match:
            yield {
                "company": company,
                "job_page": response.url,
                "role": role_match["role"],
                "score": role_match["score"],
                "signals": role_match["signals"],
            }

        # Discover more job pages within the ATS host
        for sel in response.css("a"):
            href = sel.attrib.get("href")
            if not href:
                continue

            full_url = self._safe_urljoin(response.url, href)
            if not full_url:
                continue

            if not self._is_internal(full_url, ats_root):
                continue

            if not self._looks_like_ats_job_url(full_url):
                continue

            norm = self._normalize_ats_url(full_url)
            if norm in self.ats_seen:
                continue

            self.ats_seen.add(norm)
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_ats_page,
                meta={"company": company, "ats_root": ats_root},
            )

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
        if any(h in target for h in CAREER_HINTS):
            return True

        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]

        if any(host == ch or host.endswith("." + ch) for ch in CAREER_HOSTS):
            return True

        path = urlparse(url).path.lower()
        hosted_signals = ["/careers", "/jobs", "/opportunities", "/open-positions", "apply"]
        return any(sig in path for sig in hosted_signals)

    def _evaluate_roles(self, text):
        developer_score, developer_signals = self._score_developer(text)
        consultant_score, consultant_signals = self._score_consultant(text)

        # Subtype classification
        senior = any(k in text for k in SENIOR_CONSULTANT_INTENT)
        architect = any(k in text for k in ARCHITECT_INTENT)
        remote = "remote" in text
        contract = "1099" in text or "contract" in text

        choices = []
        if developer_score >= 60:
            choices.append({"role": "developer", "score": developer_score, "signals": developer_signals})
        if consultant_score >= 50:
            choices.append({"role": "consultant", "score": consultant_score, "signals": consultant_signals})

        # Apply boosters
        for choice in choices:
            if remote:
                choice["score"] += 15
                choice["signals"].append("Remote-friendly")
            if contract:
                choice["score"] += 10
                choice["signals"].append("1099/Contract")
            if architect:
                choice["score"] += 20
                choice["role"] = "architect"
                choice["signals"].append("Architect-level")
            if senior and choice["role"] == "consultant":
                choice["score"] += 10
                choice["role"] = "senior_consultant"
                choice["signals"].append("Senior Consultant Fit")

        # Add strong HubSpot signals
        for choice in choices:
            if any(sig in text for sig in HUBSPOT_STRONG_SIGNALS):
                choice["score"] += 10
                choice["signals"].append("Strong HubSpot Expertise Signal")

        if not choices:
            return None

        return max(choices, key=lambda c: c["score"])

    def _score_developer(self, text):
        score = 0
        signals = []

        if not self._has_tech_and_intent(text, DEVELOPER_INTENT):
            return 0, []

        score, signals = self._apply_scoring_rules(
            text,
            [
                (HUBSPOT_TECH_KEYWORDS, 25, "HubSpot mentioned"),
                (HUBSPOT_STRONG_SIGNALS, 15, "HubSpot strong signals"),
                (["rss", "atom", "feed", "xml"], 5, "Job feed (RSS/XML)"),
                (["remote", "distributed"], 10, "Remote-role"),
                (["cms hub"], 25, "CMS Hub"),
                (
                    [
                        "custom module",
                        "custom modules",
                        "theme development",
                        "hubspot theme",
                    ],
                    15,
                    "Theme/modules",
                ),
                (
                    ["hubspot api", "api", "integrations", "private app"],
                    20,
                    "HubSpot API/Integrations",
                ),
                (["developer", "engineer"], 10, "Developer title"),
            ],
        )

        return score, signals

    def _score_consultant(self, text):
        score = 0
        signals = []

        if not self._has_tech_and_intent(text, CONSULTANT_INTENT):
            return 0, []

        score, signals = self._apply_scoring_rules(
            text,
            [
                (HUBSPOT_TECH_KEYWORDS, 25, "HubSpot mentioned"),
                (HUBSPOT_STRONG_SIGNALS, 15, "HubSpot strong signals"),
                (["rss", "atom", "feed", "xml"], 5, "Job feed (RSS/XML)"),
                (["remote", "distributed"], 10, "Remote-role"),
                (
                    ["revops", "marketing ops", "mops", "revenue operations"],
                    20,
                    "RevOps/Marketing Ops",
                ),
                (
                    ["workflows", "automation", "implementation"],
                    15,
                    "Automation/Implementation",
                ),
                (
                    ["crm migration", "onboarding", "data migration"],
                    20,
                    "CRM migration/onboarding",
                ),
                (
                    ["consultant", "specialist", "solutions architect"],
                    10,
                    "Consultant title",
                ),
            ],
        )

        # Skip recruiter agencies unless explicitly allowed
        if "agency" in text or "staffing" in text or "recruiting" in text:
            if not os.getenv("ALLOW_AGENCIES"):
                return 0, []
            signals.append("Agency Allowed")

        return score, signals

    def _apply_scoring_rules(self, text, rules):
        score = 0
        signals = []
        for keywords, points, label in rules:
            if any(kw in text for kw in keywords):
                score += points
                signals.append(label)
        return score, signals

    def _has_tech_and_intent(self, text, intent_keywords):
        has_tech = any(k in text for k in HUBSPOT_TECH_KEYWORDS)
        has_intent = any(k in text for k in intent_keywords)
        return has_tech and has_intent

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

        self.logger.warning("Skipping invalid website URL: %s", url)
        return None

    def _extract_redirect_target(self, url):
        """Handle Google /url redirects by pulling the ?q= target when present."""

        parsed = urlparse(url)

        if parsed.path == "/url":
            target = parse_qs(parsed.query).get("q", [None])[0]
            if target:
                return target

        return url

    def _should_skip_domain(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        if not host:
            return True
        if host.startswith("www."):
            host = host[4:]
        if any(host == sd or host.endswith("." + sd) for sd in SKIP_DOMAINS):
            return True
        return False

    def _is_ats_host(self, url: str) -> bool:
        """Return True if the URL belongs to a known ATS host."""
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return any(host == ats or host.endswith("." + ats) for ats in ATS_HOSTS)

    def _normalize_ats_url(self, url: str) -> str:
        """
        Normalization for ATS URLs to dedupe:
        use host + path (without querystring noise).
        """
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = parsed.path or "/"
        # Collapse trailing slashes so /jobs and /jobs/ are the same
        if path != "/":
            path = path.rstrip("/")
        return f"{host}{path}"

    def _looks_like_ats_job_url(self, url: str) -> bool:
        """
        Lightweight heuristic for ATS job/listing URLs:
        check for job-ish tokens in the path or obvious job IDs in the querystring.
        """
        parsed = urlparse(url)
        path = parsed.path.lower()
        if any(hint in path for hint in ATS_JOB_URL_HINTS):
            return True

        query = parsed.query.lower()
        # Pick up common patterns like gh_jid, ?lever-origin, etc.
        job_id_hints = ["gh_jid", "lever-", "ashby", "jobid", "job_id"]
        if any(hint in query for hint in job_id_hints):
            return True

        return False

    def _resolve_dataset_path(self):
        env_path = os.getenv(DATASET_ENV_VAR)
        candidate = Path(env_path) if env_path else RENDER_SECRET_DATASET

        if candidate.exists():
            return candidate

        self.logger.error("Dataset file not found: %s", candidate)
        return None
