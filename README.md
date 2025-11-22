# hubspot-job-scraper

An enterprise-grade domain-level job intelligence system that crawls company websites directly, detects career pages, and extracts HubSpot-related roles using progressive multi-layer extraction, advanced deduplication, and company health signal generation.

## What it does

* **NOT a job board scraper** - this targets individual company domains
* Reads a JSON list of company websites from `DOMAINS_FILE` (or the Render secret mount at `/etc/secrets/DOMAINS_FILE`)
* Uses **Playwright** for browser automation (headless Chrome)
* Crawls each domain directly with custom recursion logic
* **Automatic ATS detection** - detects and integrates with Greenhouse, Lever, Workable, JazzHR
* Detects pages that resemble "careers", "jobs", "opportunities", "join us", etc.
* Runs a **progressive 8-layer extraction engine** with fallback:
  1. **JSON-LD JobPosting** - structured data (highest priority)
  2. **Microdata** - schema.org microdata
  3. **OpenGraph** - meta tags
  4. **Meta tags** - job-specific meta tags
  5. **JavaScript data** - __NEXT_DATA__, __APOLLO_STATE__, window.jobData
  6. **CMS patterns** - Webflow, HubSpot COS, WordPress, CraftCMS
  7. **Anchor-based** - `<a>` tags with job keywords
  8. **Section/Button/Heading** - DOM structure analysis
* **Advanced deduplication** with fuzzy matching (85% similarity threshold)
* **Comprehensive normalization** - titles, locations, employment types, compensation
* **Incremental tracking** - detects new, removed, and updated jobs
* **Company health signals** - analyzes hiring trends (expanding/contracting/stable)
* **Rate limiting** with exponential backoff - respects crawl politeness
* **"No jobs available" detection** - prevents false positives
* **Strict domain confinement** - blocks calendars, contact pages, query explosions
* **Classifies and scores** each job using the role-scoring engine:
  - Developer rules (threshold ≥ 60): HubSpot mentions (+25), CMS Hub (+25), custom modules/theme development (+15), HubSpot API/integrations (+20), developer/engineer title (+10)
  - Consultant rules (threshold ≥ 50): HubSpot mentions (+25), RevOps/Marketing Ops/MOPS (+20), workflows/automation/implementation (+15), CRM migration/onboarding (+20), consultant/specialist/solutions architect (+10)
* Detects **remote / hybrid / onsite** signals
* **HTML archiving** for debugging (optional)
* **Extractor-level failure logging** - continues on errors
* Builds complete job payload including:
  - Job title (normalized)
  - URL
  - Summary
  - Location (parsed city/state/country)
  - Department
  - Seniority level
  - Employment type
  - Company metadata
  - Role classification
  - Score
  - Extracted hiring signals
  - Extraction source
  - Company health trend
  - Timestamp
* Sends jobs into **notifier pipelines** (ntfy, Slack, future: HubSpot sync)

## Architecture

**100% Playwright + BeautifulSoup + custom recursion. NO Scrapy. NO spiders. NO crawler frameworks.**

```
Domain List → Playwright Browser → ATS Detection → Career Page Detection → 
Progressive 8-Layer Extraction → Normalization → Cross-Layer Deduplication →
Role Scoring → Company Health Analysis → Job Payloads → Notifications (ntfy/Slack/HubSpot)
```

### Enterprise Features

**Extraction Intelligence**
- Progressive fallback (8 layers)
- ATS API integration (Greenhouse, Lever, Workable)
- CMS-specific patterns
- JavaScript data extraction
- Structured data prioritization

**Data Quality**
- Fuzzy matching deduplication
- Title normalization with synonyms
- Location parsing
- Employment type detection
- Seniority classification
- Department categorization

**Crawl Intelligence**
- Strict domain confinement
- Rate limiting (1s per domain default)
- Exponential backoff on failures
- Robots.txt respect
- "No jobs" detection
- ATS redirect allow list
- Job board redirect blocking

**Tracking & Analytics**
- Incremental job tracking
- Change detection (new/removed/updated)
- Company health signals
- Hiring trend analysis
- Role breakdown
- Extraction reporting

**Reliability**
- Extractor-level failure logging
- Partial results on errors
- HTML archiving for debugging
- Snapshot testing

## Setup

### Docker Deployment (Recommended for Production)

The easiest way to deploy is using Docker with the official Playwright base image:

```bash
docker build -t hubspot-scraper .
docker run -e DOMAINS_FILE=/app/my_domains.json \
           -v $(pwd)/my_domains.json:/app/my_domains.json \
           hubspot-scraper
```

This eliminates browser installation issues and includes all required dependencies.

**Deploying to Render:** The repository includes a `render.yaml` file that automatically configures Render to use Docker deployment. This ensures Playwright browsers are pre-installed and eliminates "Executable doesn't exist" errors. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### Local Development

```bash
pip install -r requirements.txt
playwright install --with-deps chromium  # Install browser with system dependencies
```

**Note:** Use `--with-deps` flag when deploying to cloud platforms like Render to ensure all required system dependencies are installed. For production deployment on Render, use the Docker approach (see DEPLOYMENT.md).

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

### Real-Time Streaming API (SSE)

The service includes a real-time Server-Sent Events (SSE) endpoint for parallel job scraping:

**POST /scrape/stream**

Stream scraping results in real-time with parallel domain processing:

```bash
curl -N -X POST \
  -H "Content-Type: application/json" \
  --data '{"domains":["https://company1.com","https://company2.com"]}' \
  http://localhost:8000/scrape/stream
```

Features:
- **Parallel execution**: All domains scraped concurrently using `asyncio.as_completed()`
- **Real-time streaming**: Results streamed immediately as each domain completes
- **SSE format**: Standard Server-Sent Events (`data: {json}\n\n`)
- **CORS enabled**: Works from browser frontends
- **No batching**: First domain finished → first result sent

See [SSE_ENDPOINT_DOCS.md](SSE_ENDPOINT_DOCS.md) for detailed API documentation, examples, and usage patterns.

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
* `RATE_LIMIT_DELAY` – Delay between requests per domain in seconds (default 1.0).

**API / Server**

* `CORS_ORIGINS` – Comma-separated list of allowed CORS origins for SSE streaming. Defaults to `*` (all origins). Example: `CORS_ORIGINS=https://example.com,https://app.example.com`.

**Extraction & Tracking**

* `ENABLE_HTML_ARCHIVE` – Enable HTML archiving for debugging (default false).
* `HTML_ARCHIVE_DIR` – Directory for HTML archives (default /tmp/html_archive).
* `JOB_TRACKING_CACHE` – Path to job tracking cache file (default .job_tracking.json).

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
# Run all tests
python -m unittest discover -s . -p "test_*.py" -v

# Run snapshot tests specifically
python -m unittest tests.test_snapshots -v

# Update snapshots (after intentional changes)
UPDATE_SNAPSHOTS=1 python -m unittest tests.test_snapshots -v
```

Tests cover:
- Multi-layer extraction (JSON-LD, microdata, OpenGraph, meta tags, JavaScript, CMS patterns)
- Role classification and scoring
- Deduplication (exact and fuzzy matching)
- Normalization (titles, locations, employment types)
- Filter logic
- Snapshot regression testing
- HTML cleanup
- URL normalization

## Project Structure

```
├── ats_detectors.py         # ATS detection and API integration
├── career_detector.py        # Career page detection logic
├── deduplication.py          # Cross-layer deduplication and tracking
├── enhanced_extractors.py    # Advanced extraction patterns
├── extraction_utils.py       # Utilities (no jobs detection, failure logging)
├── extractors.py             # Core 5-layer extraction engine
├── normalization.py          # Data normalization and classification
├── role_classifier.py        # Role scoring and classification
├── scraper_engine.py         # Main Playwright-based scraper with enterprise features
├── notifier.py               # Notification system (ntfy, Slack)
├── main.py                   # Main entry point
├── run_spider.py             # Background worker entry point
├── server.py                 # FastAPI control room
├── test_extractors.py        # Extractor tests
├── test_role_classifier.py   # Role classifier tests
├── tests/
│   ├── test_snapshots.py     # Snapshot testing framework
│   ├── fixtures/             # HTML test fixtures
│   └── snapshots/            # Expected extraction outputs
└── scrapy_project/           # Legacy Scrapy code (deprecated)
```

## Key Features

✅ **NO Scrapy** - Pure Playwright + BeautifulSoup + custom recursion  
✅ **Progressive 8-layer extraction** - Structured data to DOM analysis  
✅ **ATS integration** - Greenhouse, Lever, Workable APIs  
✅ **HubSpot-focused** - Role classification tailored for HubSpot jobs  
✅ **Advanced deduplication** - Fuzzy matching + exact hashing  
✅ **Comprehensive normalization** - Titles, locations, types, seniority  
✅ **Incremental tracking** - Detects new/removed/updated jobs  
✅ **Company health signals** - Hiring trend analysis  
✅ **Location detection** - Remote/hybrid/onsite signals  
✅ **Rate limiting** - Exponential backoff, crawl politeness  
✅ **Domain confinement** - Strict same-domain rules  
✅ **Failure handling** - Continues on errors, logs failures  
✅ **HTML archiving** - Debug failed extractions  
✅ **Snapshot testing** - Regression detection  
✅ **FastAPI UI** - Live log streaming and control room  
✅ **Configurable** - Environment-based configuration  

## Enterprise Capabilities

### Extraction Intelligence

**ATS Detection**
- Automatic detection via script tags, iframes, DOM signatures
- API integration for Greenhouse, Lever, Workable, JazzHR
- Allowed redirect list (ATS platforms only)
- Banned redirect list (blocks LinkedIn, Indeed, Glassdoor)

**Progressive Fallback**
1. Structured data (JSON-LD, microdata, OpenGraph)
2. JavaScript state (__NEXT_DATA__, __APOLLO_STATE__)
3. CMS patterns (Webflow, HubSpot COS, WordPress, CraftCMS)
4. DOM analysis (anchors, buttons, sections, headings)

**"No Jobs" Detection**
- Detects empty job listings
- Recognizes placeholder messages
- Prevents false positives

### Data Quality

**Normalization**
- Title synonyms (e.g., "SWE" → "Software Engineer")
- Location parsing (city, state, country, type)
- Employment type detection (full-time, part-time, contract)
- Seniority classification (entry, mid, senior, staff, director)
- Department categorization (engineering, sales, marketing, etc.)
- Compensation parsing

**Deduplication**
- Cross-layer deduplication
- Hash-based exact matching
- Fuzzy matching (85% similarity threshold)
- Considers: title, URL, location, summary

### Tracking & Analytics

**Incremental Tracking**
- Persistent cache (.job_tracking.json)
- Detects new jobs
- Detects removed jobs
- Detects updated jobs

**Company Health Signals**
- Trend analysis (expanding, contracting, stable, actively_hiring)
- Net change calculation
- Role breakdown by department
- Insight generation:
  - "Surge in engineering roles"
  - "Hiring for leadership positions"
  - "Focus on entry-level hires"

### Reliability

**Error Handling**
- Extractor-level failure logging
- Partial results on errors
- Continues processing after failures
- Extraction success/failure reporting

**Crawl Politeness**
- Per-domain rate limiting (default 1s)
- Exponential backoff (1s → 2s → 4s → 8s → max 60s)
- Success resets backoff
- Robots.txt checking

**Domain Confinement**
- Strict same-domain enforcement
- Blocks calendar pages
- Blocks contact pages (unless career-related)
- Limits query parameters (max 5)
- Prevents query parameter explosions  

## Future Enhancements

- [ ] HubSpot API integration for syncing jobs as deals/custom objects
- [ ] Concurrency improvements for faster crawling
- [ ] Caching layer for career page detection
- [ ] Enhanced ATS platform support
- [ ] Webhook notifications
- [ ] Job history tracking and analytics
