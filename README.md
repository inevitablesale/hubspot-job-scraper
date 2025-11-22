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

Render expects a build and start command. Use the repo defaults to avoid the "not a valid identifier" error:

```
build: ./postinstall.sh
start: uvicorn server:app --host 0.0.0.0 --port $PORT
```

If you want Render to read the commands from code instead of the dashboard, drop this repo's `render.yaml` into your service; it points to the same build/start commands.

If you **must** inline the install in the Render dashboard, either set the variable as a prefix or add `&&` between commands:

```bash
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pip install -r requirements.txt
# or
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 && pip install -r requirements.txt
```

**Do not run** `export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 pip install -r requirements.txt` without the `&&`; Bash will treat `-r` and `requirements.txt` as identifiers and Render will fail the build with `not a valid identifier`.

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
