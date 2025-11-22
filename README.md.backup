# hubspot-job-scraper

A domain-level job scraper that crawls company websites directly, detects career pages, and extracts HubSpot-related roles using multi-layer extraction and scoring.

## What it does

* **NOT a job board scraper** - this targets individual company domains
* Reads a JSON list of company websites from `DOMAINS_FILE` (or the Render secret mount at `/etc/secrets/DOMAINS_FILE`)
* Uses **Playwright** for browser automation (headless Chrome)
* Crawls each domain directly with custom recursion logic
* Detects pages that resemble "careers", "jobs", "opportunities", "join us", etc.
* Runs a **multi-layer extraction engine** to find jobs:
  1. **JSON-LD JobPosting extractor** - structured data
  2. **Anchor-based extractor** - `<a>` tags with job keywords
  3. **Button-based extractor** - `<button>` elements (handles modals)
  4. **Section-based extractor** - blocks under "Open Positions" / "Join Us" / "We're Hiring"
  5. **Heading-based extractor** - fallback using `<h1>`-`<h6>` tags
* **Deduplicates** job entries based on (title, url)
* **Classifies and scores** each job using the role-scoring engine:
  - Developer rules (threshold ≥ 60): HubSpot mentions (+25), CMS Hub (+25), custom modules/theme development (+15), HubSpot API/integrations (+20), developer/engineer title (+10)
  - Consultant rules (threshold ≥ 50): HubSpot mentions (+25), RevOps/Marketing Ops/MOPS (+20), workflows/automation/implementation (+15), CRM migration/onboarding (+20), consultant/specialist/solutions architect (+10)
* Detects **remote / hybrid / onsite** signals
* Builds complete job payload including:
  - Job title
  - URL
  - Summary
  - Company metadata
  - Role classification
  - Score
  - Extracted hiring signals
  - Timestamp
* Sends jobs into **notifier pipelines** (ntfy, Slack, future: HubSpot sync)

## Architecture

**100% Playwright + BeautifulSoup + custom recursion. NO Scrapy. NO spiders. NO crawler frameworks.**

```
Domain List → Playwright Browser → Career Page Detection → Multi-Layer Extraction →
Role Scoring → Deduplication → Job Payloads → Notifications (ntfy/Slack/HubSpot)
```

## Setup

```bash
pip install -r requirements.txt
playwright install chromium  # Install browser
```

Your domains file must be a JSON array using either of these shapes:

* Objects: `{ "website": "https://example.com", "title": "Example" }`
* Strings: `"https://example.com"` (used for both `website` and `title`)

## Running as a Web Service (FastAPI UI)

1. Mount your domains file at `/etc/secrets/DOMAINS_FILE` (or set the `DOMAINS_FILE` env var).
2. Start the web service:

   ```bash
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

3. Open the service URL (e.g., `https://<your-service>.onrender.com/`). The homepage shows status pills, metric cards, a live log console, and an ECharts "Live Pulse" chart.
4. Click **Start Crawl** to POST to `/run`; watch the log stream and chart update via `/events`. Health checks can hit `/health` (or `HEAD /`).

## Running as a Background Worker (no UI)

If you prefer a portless worker, use the simpler entrypoint:

```bash
python run_spider.py
```

This runs the crawler with the same dataset rules and notification pipeline, then exits when complete.

## Configuration via environment variables

Most behavior can be tuned without touching the code:

**Core data / crawl**

* `DOMAINS_FILE` – path to the JSON file with domains (overrides `/etc/secrets/DOMAINS_FILE`).
* `LOG_LEVEL` – Log level (DEBUG, INFO, ERROR, etc.). Defaults to `INFO`.
* `PAGE_TIMEOUT` – Page load timeout in milliseconds (default 30000).
* `MAX_PAGES_PER_DOMAIN` – Maximum pages to crawl per domain (default 20).
* `MAX_DEPTH` – Maximum recursion depth (default 3).

**Notifications**

* `NTFY_URL` – ntfy topic URL. Defaults to `https://ntfy.sh/hubspot_job_alerts`.
* `EMAIL_TO` – email address for ntfy email relay (optional).
* `SMS_TO` – phone number for ntfy SMS relay (optional).
* `SLACK_WEBHOOK` – Slack incoming webhook URL (optional).

**Role / fit filters**

* `ROLE_FILTER` – comma-separated list of allowed roles. Valid values: `developer`, `consultant`, `architect`, `senior_consultant`. Example: `ROLE_FILTER=developer,consultant`.
* `REMOTE_ONLY` – when set to true, only remote-friendly roles are kept (based on content signals).
* `ALLOW_AGENCIES` – when set to true, do not automatically drop staffing / recruiting agency job pages.

These flags let you tighten the feed to exactly what you care about (e.g., remote HubSpot developer roles only, architect-level consulting, etc.) without changing the scraper logic.

## Testing

Run the test suite:

```bash
python -m unittest discover -s . -p "test_*.py" -v
```

Tests cover:
- Multi-layer extraction (JSON-LD, anchors, buttons, sections, headings)
- Role classification and scoring
- Deduplication
- Filter logic

## Project Structure

```
├── career_detector.py      # Career page detection logic
├── extractors.py            # Multi-layer job extraction engine
├── role_classifier.py       # Role scoring and classification
├── scraper_engine.py        # Main Playwright-based scraper
├── notifier.py              # Notification system (ntfy, Slack)
├── main.py                  # Main entry point
├── run_spider.py            # Background worker entry point
├── server.py                # FastAPI control room
├── test_extractors.py       # Extractor tests
├── test_role_classifier.py  # Role classifier tests
└── scrapy_project/          # Legacy Scrapy code (deprecated)
```

## Key Features

✅ **NO Scrapy** - Pure Playwright + BeautifulSoup + custom recursion  
✅ **Multi-layer extraction** - 5 different extraction strategies  
✅ **HubSpot-focused** - Role classification tailored for HubSpot jobs  
✅ **Smart deduplication** - Based on (title, url) tuples  
✅ **Location detection** - Remote/hybrid/onsite signals  
✅ **Configurable** - Environment-based configuration  
✅ **FastAPI UI** - Live log streaming and control room  
✅ **Tested** - Comprehensive test coverage  

## Future Enhancements

- [ ] HubSpot API integration for syncing jobs as deals/custom objects
- [ ] Concurrency improvements for faster crawling
- [ ] Caching layer for career page detection
- [ ] Enhanced ATS platform support
- [ ] Webhook notifications
- [ ] Job history tracking and analytics
