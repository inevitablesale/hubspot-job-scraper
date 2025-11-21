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
python -m playwright install --with-deps chromium
python main.py
```

## Render (web service)
- Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Add a build step (postinstall):
  ```
  python -m playwright install --with-deps chromium
  ```
- Trigger a run: `POST https://<your-service>/run`
- Check status: `GET https://<your-service>/status`
- Health: `GET https://<your-service>/health`

## Render (background worker)
Use the same code but start with:
```bash
python run_spider.py
```

## Configuration (env vars)
- **DOMAINS_FILE**: JSON array of strings or objects (`{"website": ..., "title": ...}`); defaults to `/etc/secrets/DOMAINS_FILE`.
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
