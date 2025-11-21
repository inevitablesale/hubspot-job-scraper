# hubspot-job-scraper

A small Scrapy project that crawls company websites, looks for career pages, and sends HubSpot-related roles to an ntfy topic.

## What it does

* Reads a JSON list of company websites from `DOMAINS_FILE` (or the Render secret mount at `/etc/secrets/DOMAINS_FILE`).
* Visits each homepage, follows internal career-looking links (including common ATS hosts), and flags pages that score as HubSpot **Developer** or **Consultant** roles.
* Follows off-domain ATS career links (Greenhouse, Ashby, Workable, BambooHR, Lever, etc.), then recursively walks job / listing URLs on those hosts and scores every page.
* Buffers only new jobs (deduped via `.job_cache.json`) and posts formatted alerts to `https://ntfy.sh/hubspot_job_alerts` with optional email/SMS/Slack headers.
* Exposes a FastAPI “control room” with live log streaming, status endpoints, and an ECharts-powered activity pulse.
* Handles DNS failures gracefully, marks dead domains to avoid repeated errors, skips social/link-shortener detours (Instagram, Facebook, Yelp, Wix, etc.), and throttles per-domain requests with exponential backoff retries for noisy sites.

## HubSpot-first detection

The spider requires **both** HubSpot technology signals and role intent. Pages are scored and only emitted when they cross the relevant threshold.

* Developer rules (threshold ≥ 60): HubSpot mentions (+25), CMS Hub (+25), custom modules/theme development (+15), HubSpot API/integrations (+20), developer/engineer title (+10).
* Consultant rules (threshold ≥ 50): HubSpot mentions (+25), RevOps/Marketing Ops/MOPS (+20), workflows/automation/implementation (+15), CRM migration/onboarding (+20), consultant/specialist/solutions architect (+10).

Career-link discovery is tightened with added keywords (apply, team, we-are-hiring, work-with-me) and recognition of hosted career systems (Greenhouse, Ashby, Workable, BambooHR, Lever) in addition to typical `/careers`/`/jobs` paths.

When a company’s “Careers” button points to a third-party ATS, the spider switches into **“follow-then-parse” ATS mode**:
it treats the ATS host as a mini crawl root, follows internal `/jobs` / `/job` / `/careers` / `/positions` style URLs, and applies the same HubSpot scoring to each job detail page.
Only pages that cross the score threshold emit notifications.

## Setup

```bash
pip install -r requirements.txt
```

Your domains file must be a JSON array using either of these shapes:

* Objects: `{ "website": "https://example.com", "title": "Example" }`
* Strings: `"https://example.com"` (used for both `website` and `title`)

Google `/url` redirect entries are unwrapped automatically so the crawl starts on the real site.

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

This runs the crawler with the same dataset rules and ntfy notification pipeline, then exits when complete.

## Configuration via environment variables

Most behavior can be tuned without touching the code:

**Core data / crawl**

* `DOMAINS_FILE` – path to the JSON file with domains (overrides `/etc/secrets/DOMAINS_FILE`).
* `LOG_LEVEL` – Scrapy log level (DEBUG, INFO, ERROR, etc.). Defaults to `ERROR`.
* `DOWNLOAD_TIMEOUT` – per-request timeout in seconds (default 20).

**Notifications**

* `NTFY_URL` – ntfy topic URL. Defaults to `https://ntfy.sh/hubspot_job_alerts`.
* `EMAIL_TO` – email address for ntfy email relay (optional).
* `SMS_TO` – phone number for ntfy SMS relay (optional).
* `SLACK_WEBHOOK` – Slack incoming webhook URL (optional).
* `JOB_CACHE_PATH` – path to the job cache file. Defaults to `.job_cache.json`.

**Role / fit filters**

* `ROLE_FILTER` – comma-separated list of allowed roles. Valid values: `developer`, `consultant`, `architect`, `senior_consultant`. Example: `ROLE_FILTER=developer,consultant`.
* `REMOTE_ONLY` – when set to true, only remote-friendly roles are kept (based on content signals).
* `ALLOW_AGENCIES` – when set to true, do not automatically drop staffing / recruiting agency job pages.

These flags let you tighten the feed to exactly what you care about (e.g., remote HubSpot developer roles only, architect-level consulting, etc.) without changing the spider logic.
