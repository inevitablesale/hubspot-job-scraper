# hubspot-job-scraper

A small Scrapy project that crawls company websites, looks for career pages, and sends HubSpot-related roles to an ntfy topic.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Ensure `dataset_crawler-google-places_2025-11-20_21-44-01-758.json` exists in the project root and contains objects with `title` and `website` fields. Then run:

```bash
python main.py
```

Found roles are sent to `https://ntfy.sh/hubspot_job_alerts` with the configured email header.
