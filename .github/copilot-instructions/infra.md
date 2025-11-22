# Infrastructure Guidelines

## Overview
This document provides guidelines for deploying and running the HubSpot job scraper.

## Core Principle
**DO NOT run the scraper automatically on deployment.**

The scraper must only run when explicitly triggered through the UI or API.

## Deployment Requirements

### 1. No Auto-Start on Boot
The application should start a web server but NOT begin crawling automatically.

**Correct behavior**:
```python
# main.py or server.py
if __name__ == "__main__":
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    # DO NOT call scraper.scrape_domain() here
```

**Incorrect behavior** (DO NOT DO THIS):
```python
# WRONG - do not do this
if __name__ == "__main__":
    asyncio.run(scraper.scrape_all_domains())  # ❌ NO AUTO-RUN
    uvicorn.run(app, ...)
```

### 2. UI-Triggered Execution Only
The scraper must only run via:
- POST request to `/run` endpoint from UI
- POST request to `/scrape/stream` endpoint with domains

### 3. Docker Configuration
Use the official Playwright Docker image for compatibility:

**Dockerfile**:
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install Playwright browsers (already in base image)
RUN playwright install chromium

# Expose port
EXPOSE 8000

# Start web server (NOT the scraper)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. Render Configuration
**render.yaml**:
```yaml
services:
  - type: web
    name: hubspot-job-scraper
    env: docker
    plan: starter
    dockerfilePath: ./Dockerfile
    envVars:
      - key: PORT
        value: 8000
      - key: DOMAINS_FILE
        sync: false
      - key: MAX_PAGES_PER_DOMAIN
        value: 12
      - key: MAX_DEPTH
        value: 2
```

### 5. Environment Variables
Required for proper configuration:

```bash
# Core settings
PORT=8000
DOMAINS_FILE=/etc/secrets/DOMAINS_FILE

# Crawl limits (per problem statement)
MAX_PAGES_PER_DOMAIN=12
MAX_DEPTH=2
RATE_LIMIT_DELAY=1.0
PAGE_TIMEOUT=30000

# API
CORS_ORIGINS=*  # Restrict in production

# Optional features
ENABLE_HTML_ARCHIVE=false
HTML_ARCHIVE_DIR=/tmp/html_archive
JOB_TRACKING_CACHE=.job_tracking.json

# Notifications (optional)
NTFY_URL=https://ntfy.sh/hubspot_job_alerts
SLACK_WEBHOOK=

# Filters (optional)
ROLE_FILTER=developer,consultant
REMOTE_ONLY=false
```

## Logging Configuration

### Log Streaming via WebSocket/SSE
Surface logs via Server-Sent Events for real-time UI updates:

```python
@app.get("/events")
async def stream_events():
    async def event_generator():
        queue = app.state.log_queue
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=20)
                yield f"data: {line}\n\n"
                queue.task_done()
            except asyncio.TimeoutError:
                yield "data: [heartbeat]\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Log Format
Use structured logging with the required prefixes:
- `[DOMAIN]` for domain-level events
- `[DISCOVERY]` for link discovery
- `[SKIP]` for filtered links
- `[CAREERS]` for career page navigation
- `[JOB]` for job extraction
- `[ATS]` for ATS detection
- `[COMPLETE]` for completion

## Playwright Compatibility

### Browser Installation
Ensure browsers are installed with system dependencies:

```bash
# In Dockerfile or deployment script
playwright install --with-deps chromium
```

### Headless Mode
Always run in headless mode in production:

```python
browser = await playwright.chromium.launch(headless=True)
```

### Resource Cleanup
Properly close browsers and pages:

```python
try:
    page = await browser.new_page()
    # ... use page ...
finally:
    await page.close()

# On shutdown
await browser.close()
```

## Health Checks

### Endpoints
Provide health check endpoints:

```python
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.head("/")
async def head_check():
    return Response(status_code=200)
```

### Monitoring
- Log all errors with stack traces
- Track scraper run duration
- Monitor memory usage
- Alert on failures

## Security

### Secrets Management
Never commit secrets to code:
- Use environment variables
- Use secret management service (Render secrets, AWS Secrets Manager, etc.)
- Mount secrets as files (e.g., `/etc/secrets/DOMAINS_FILE`)

### CORS Configuration
Restrict CORS in production:
```python
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
```

### Rate Limiting
Respect crawl politeness:
- Default 1s delay per domain
- Exponential backoff on failures
- Respect robots.txt

## Scaling Considerations

### Concurrency
For parallel domain scraping:
```python
# Use asyncio.as_completed for streaming results
tasks = [scrape_domain(url, company) for url, company in domains]
for completed_task in asyncio.as_completed(tasks):
    result = await completed_task
    yield result
```

### Resource Limits
- Limit concurrent browser instances
- Close pages after use
- Clear visited URL sets between domains
- Limit memory usage with pagination

## Troubleshooting

### Common Issues

**Executable doesn't exist**:
- Solution: Use Docker deployment with Playwright base image
- Or: Run `playwright install --with-deps chromium`

**Scraper runs on deploy**:
- Check: Ensure no `asyncio.run()` or scraper calls in `if __name__ == "__main__"`
- Only start web server, not scraper

**Out of memory**:
- Reduce MAX_PAGES_PER_DOMAIN
- Close browser pages after use
- Clear caches between domains

**Timeout errors**:
- Increase PAGE_TIMEOUT
- Add retry logic with exponential backoff
- Check network connectivity

## Production Checklist
- [ ] No auto-run on deployment
- [ ] Docker image uses Playwright base
- [ ] Browsers installed with `--with-deps`
- [ ] Health check endpoint configured
- [ ] Logs streamed via SSE
- [ ] Environment variables configured
- [ ] CORS restricted to known origins
- [ ] Secrets stored securely
- [ ] Rate limiting enabled
- [ ] Error monitoring in place
