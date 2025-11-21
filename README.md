# hubspot-job-scraper

A small Scrapy project that crawls company websites, looks for career pages, and sends HubSpot-related roles to an ntfy topic.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage (CLI)

Provide a dataset as a JSON array using one of two formats:

* List of objects with `website` (and optional `title`)
* List of strings (each string is treated as both `title` and `website`)

The spider loads domains from `DOMAINS_FILE` if set; otherwise it reads the Render secret mount at `/etc/secrets/DOMAINS_FILE`.
If you mount a different path, set `DOMAINS_FILE` accordingly:

```bash
export DOMAINS_FILE=/etc/secrets/domains
python main.py
```

Then run:

```bash
python main.py
```

### Render start command
- **Background Worker (no web UI):** set the Start Command to `python run_spider.py` so the crawl runs and exits without binding a port.
- **Web Service (with FastAPI UI):** use `uvicorn server:app --host 0.0.0.0 --port $PORT`.

Found roles are sent to `https://ntfy.sh/hubspot_job_alerts` with the configured email header.

### Render Web Service quickstart
1. Set the Start Command to `uvicorn server:app --host 0.0.0.0 --port $PORT` and deploy as a **Web Service**.
2. Mount your domains JSON at `/etc/secrets/DOMAINS_FILE` (or set the `DOMAINS_FILE` env var to your path).
3. Open the service URL (e.g., `https://<your-service>.onrender.com/`) and click **Start Crawl**.
4. Watch the live log and check `/status` or `/health` for platform health checks.

### Cleaning Google redirect URLs

If your dataset contains Google redirect links such as `/url?q=https://example.com&...` or `https://www.google.com/url?q=...`, the spider now extracts the `q` parameter so the crawl starts on the real site instead of skipping the entry.

## Usage (browser trigger + live log)

Launch the lightweight FastAPI server to start crawls from the browser and stream stdout in real time:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000` and click **Start Crawl** to trigger the spider. The page uses Server-Sent Events to show the live log and expose a `/status` endpoint so you can check whether a crawl is running.

> Render note: the crawler does not bind a port; deploy it as a Background Worker (or use the FastAPI server/uvicorn command above if you need a Web Service).
