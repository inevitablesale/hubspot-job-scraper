# hubspot-job-scraper

A small Scrapy project that crawls company websites, looks for career pages, and sends HubSpot-related roles to an ntfy topic.

## What it does

* Reads a JSON list of company websites from `DOMAINS_FILE` (or the Render secret mount at `/etc/secrets/DOMAINS_FILE`).
* Visits each homepage, follows internal career-looking links (including common ATS hosts), and flags pages that score as HubSpot **Developer** or **Consultant** roles.
* Buffers only new jobs (deduped via `.job_cache.json`) and posts formatted alerts to `https://ntfy.sh/hubspot_job_alerts` with optional email/SMS/Slack headers.
* Exposes a FastAPI “control room” with live log streaming, status endpoints, and an ECharts-powered activity pulse.
* Handles DNS failures gracefully, marks dead domains to avoid repeated errors, skips social/link-shortener detours (Instagram, Facebook, Yelp, Wix, etc.), and throttles per-domain requests with exponential backoff retries for noisy sites.

## HubSpot-first detection

The spider requires **both** HubSpot technology signals and role intent. Pages are scored and only emitted when they cross the relevant threshold.

* Developer rules (threshold ≥ 60): HubSpot mentions (+25), CMS Hub (+25), custom modules/theme development (+15), HubSpot API/integrations (+20), developer/engineer title (+10).
* Consultant rules (threshold ≥ 50): HubSpot mentions (+25), RevOps/Marketing Ops/MOPS (+20), workflows/automation/implementation (+15), CRM migration/onboarding (+20), consultant/specialist/solutions architect (+10).

Career-link discovery is tightened with added keywords (apply, team, we-are-hiring, work-with-me) and recognition of hosted career systems (Greenhouse, Ashby, Workable, BambooHR, Lever) in addition to typical `/careers`/`/jobs` paths.

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
