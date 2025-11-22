# Scraper Engine Instructions

## Purpose
These rules apply to:
- `scraper_engine.py`
- `/utils/scraping/*`
- `/scraping_strategies/*`

## Core Principles

1. **Always use Playwright (async)** — never use `requests` or synchronous libs.
2. **Career page detection** follows hierarchical heuristics:
   - Tier 1: `/careers`, `/jobs`, `/join-us`, `/work-with-us`
   - Tier 2: `/about`, `/team`, `/company`
   - Tier 3: Global link text search ("Careers", "Jobs", "We're hiring")
3. **Role extraction** must support:
   - ATS embeds (Greenhouse, Lever, Workable, JazzHR, BambooHR, Ashby, etc.)
   - HTML lists of roles
   - Single-page job descriptions

## Required Output Fields

Each job must emit:

```python
{
  "company": str,
  "title": str,
  "location": str or None,
  "url": str,
  "source_page": str
}
```

## Logging Expectations

For every domain:

1. **[CANDIDATES]** list of possible career URLs
2. **[SELECTED]** chosen URL + reason
3. **[FOUND JOB TITLES]** extracted roles
4. Errors must include domain + URL

## Performance

- Use the existing concurrency manager
- Limit page loads
- Timeout max: 30–45s
