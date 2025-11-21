# hubspot-job-scraper

An async Playwright crawler that opens each domain in a real browser, picks the most likely careers page, follows "see all jobs" CTAs, detects embedded ATS widgets, and logs every step for Render Live Logs.

## Quickstart

```bash
pip install -r requirements.txt
python main.py --domains-file domains.txt --output results.jsonl
```

* `domains.txt` should contain one domain per line (protocol optional).
* Results are appended as JSONL; omit `--output` to disable file writes.

## Render deployment

Render expects a build command; keep it as `./postinstall.sh` (the default) so the crawler installs dependencies and sets `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` for you. If you customize the command, make sure it includes a separator, e.g.:

```bash
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 && pip install -r requirements.txt
```

Without the `&&`, `export` treats the rest of the command as variable names and Render fails with `not a valid identifier`.

At runtime the crawler launches Playwright using Render's built-in Chrome channel:

```python
browser = await playwright.chromium.launch(channel="chrome", headless=True)
```

No browser download is required on Render.

## Running the control server

The optional FastAPI control server keeps single-process execution while letting you trigger crawls remotely:

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

POST to `/run` to start a crawl; logs stream back through the app log output.

## What gets logged

The crawler prints the same structured events as the former Scrapy spider:

* `[Visiting] URL` — every navigation, including within ATS iframes/feeds.
* `[CANDIDATES] [...]` — ranked career-link candidates from the homepage.
* `[SELECTED] URL` — the chosen careers page.
* `[PAGE] URL → title="..."`
* `[FOUND JOB TITLES] [...]`
* `[ATS] Detected: <name>` (Greenhouse, Lever, Ashby, Workable, BambooHR, JazzHR, Pinpoint, Breezy, etc.)
* `[HIRING EMAIL] → ...` when email-only hiring is detected.
* `[RESULT] Company → N job roles found`

Throttle controls keep concurrency at 1, randomize user agents, and insert 0.5–2.0s pauses between domains.
