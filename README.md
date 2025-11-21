# HubSpot Job Hunter (Playwright)

A Playwright-powered crawler that discovers careers pages on arbitrary websites (static or JS-heavy), extracts job postings from inline cards, ATS embeds, headings, JSON-LD, and iframe content, then scores HubSpot-specific Developer/Consultant roles before sending ntfy alerts.

## What it does
- Loads domains from `DOMAINS_FILE` (or `/etc/secrets/DOMAINS_FILE` on Render).
- Visits each homepage, finds a careers page via nav links, anchor text (careers/jobs/join us/open positions), or `#open-positions` anchors.
- Waits for JS to render, scrolls, and clicks prompts like “Open Positions” / “View Roles” to reveal dynamic listings.
- Extracts jobs from:
  - Inline job cards, headings, buttons, and anchor lists
  - JSON-LD JobPosting scripts
  - Webflow/HubSpot CMS/Elementor sections and `data-*` job cards
  - iframe-based ATS embeds (Greenhouse, Breezy, Lever, Workable, Bamboo, etc.)
- Scores pages for HubSpot tech + role intent (Developer/Consultant/Architect/Senior Consultant) and applies remote-only/agency guards.
- Dedupes by hash (`.job_cache.json`) and sends formatted ntfy alerts (email/SMS/Slack headers supported).

## Running locally
```bash
pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

## Render (web service)
- Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Runtime: pin Python to **3.11.6** to avoid `greenlet` build failures on Python 3.13. Use any of the following (pick one that fits your Render setup):
  - Set `pythonVersion: 3.11.6` in **render.yaml** or the Render dashboard.
  - Keep `runtime.txt` at `python-3.11.6` (Render expects the `python-` prefix).
  - Optionally honor `.python-version` (contains `3.11.6`) for local tooling and some buildpack detectors.
- **postinstall.sh** should run at build time to install Python deps, Playwright Chromium, and build the React UI:
  ```bash
  #!/usr/bin/env bash
  set -euxo pipefail

  pip install --upgrade pip
  pip install -r requirements.txt

  python -m playwright install chromium

  cd frontend
  npm install
  npm run build
  cd ..

  mkdir -p static
  cp -r frontend/dist/* static/
  ```
- Runtime fallback: if Render ever evicts the cached browser, the crawler will
  auto-run `python -m playwright install chromium` on startup and retry the
  launch, so runs keep working even after cache resets (requires outbound
  network during startup).
- Trigger a run: `POST https://<your-service>/run`
- Check status: `GET https://<your-service>/status`
- Health: `GET https://<your-service>/health`
- Live logs (WebSocket over TLS): `wss://<your-service>/ws/logs`
- Results API: `GET https://<your-service>/results`

## Render (background worker)
Use the same code but start with:
```bash
python run_spider.py
```

## Configuration (env vars)
- **DOMAINS_FILE**: JSON array of strings or objects (`{"website": ..., "title": ...}`); defaults to `/etc/secrets/DOMAINS_FILE`.
- **DOMAINS_WRITE_PATH**: Optional writable copy of the domains JSON (e.g., `/data/domains_runtime.json`) when the source is a read-only Render secret.
- **DOMAIN_EVENTS_FILE**: Optional path for domain added/removed events; defaults to `${DOMAINS_WRITE_PATH}.events.json`.
- **USER_AGENT**: Override browser UA.
- **PAGE_TIMEOUT_MS**: Per-action timeout (default 20000).
- **LOG_LEVEL**: Python logging level (default INFO).
- **NTFY_URL / EMAIL_TO / SMS_TO / SLACK_WEBHOOK**: ntfy target + relay headers.
- **JOB_CACHE_PATH**: Where to persist hashes (default `.job_cache.json`).
- **ROLE_FILTER**: Comma-separated roles to keep (developer, consultant, architect, senior_consultant).
- **REMOTE_ONLY**: If `true`, keep only remote-friendly jobs (US-focused).
- **ALLOW_AGENCIES**: If `true`, include staffing/recruiting pages.

## Tech + role scoring (high level)
- Developer (threshold ≥ 60): HubSpot mentions, CMS Hub, custom modules/themes, HubSpot API/integrations, developer/engineer titles, strong HubSpot partner signals, boosters for remote/contract/architect cues.
- Consultant (threshold ≥ 50): HubSpot mentions, RevOps/Marketing Ops, workflows/automation, migration/onboarding, consultant/specialist/solutions architect titles, boosters for remote/contract/senior.

Only pages crossing the threshold emit alerts. Remote-only and agency filters are applied before notification.

## Frontend dashboard (React + Vite)
- Located in `/frontend` with a Linear-style dark UI (Tailwind + Recharts + Zustand store).
- Panels: Dashboard (status, run controls, coverage radial, run history chart), Live Logs (SSE console with filtering), Results Explorer (coverage table + sortable job table with signals and scores).
- APIs used: `/schema` (UI config), `/state` (live sync), `/version` (bundle/version parity), `/run`, `/run/maps`, `/run/full`, `/stop`, `/results`, `/logs/stream`, `/domains`, `/domains/changes`.

### Domains view + Maps Radar
- New **Domains** tab lists all known agencies/domains, their scores, HubSpot detection confidence, last seen, and signals. You can remove domains inline.
- Backend endpoints: `GET /domains`, `GET /domains/changes` (added/removed in the last 24h), `DELETE /domains/{domain}`.
- Maps Radar endpoint: `POST /run/maps` (body: `{ "queries": [...], "limit": 50 }`). It runs Google Maps searches for HubSpot-ish agencies, scores them, detects HubSpot on their sites, and inserts high-quality domains into `DOMAINS_FILE`.
- The job crawler continues to read from `DOMAINS_FILE`, so newly discovered domains are automatically swept for HubSpot roles.

### Suggested scheduling
- Run Maps Radar daily (Render cron): `python -m playwright_crawler.runner run_maps_radar` via a cron entry or API call.
- Run jobs crawler hourly (existing `/run`).
- Optional cleanup (failures >=3): call `run_domain_cleanup()` every 6 hours if you wire a cron/maintenance task.

Run locally:
```bash
cd frontend
npm install
npm run dev
```
Set `VITE_API_BASE` / `VITE_WS_BASE` if your FastAPI backend is on a different host/port.
