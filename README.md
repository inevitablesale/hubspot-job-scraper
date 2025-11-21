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

Found roles are sent to `https://ntfy.sh/hubspot_job_alerts` with the configured email header.

## Usage (browser trigger + live log)

Launch the lightweight FastAPI server to start crawls from the browser and stream stdout in real time:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000` and click **Start Crawl** to trigger the spider. The page uses Server-Sent Events to show the live log and expose a `/status` endpoint so you can check whether a crawl is running.
