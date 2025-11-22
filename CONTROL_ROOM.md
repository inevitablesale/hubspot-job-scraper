# Control Room Documentation

## Overview

The HubSpot Job Scraper Control Room is a web-based interface for managing and monitoring the crawler. It provides real-time status updates, log streaming, and job result viewing.

## Features

### 1. **No Auto-Run on Deploy**
- The scraper does NOT start automatically when the container starts
- Only the FastAPI web server starts on deploy
- Crawls are triggered manually via the UI or API

### 2. **Control Room UI**

Access the control room at the root URL of your deployment (e.g., `https://your-app.onrender.com/`)

**Key Components:**
- **Status Badge**: Shows current crawler state (Idle, Running, Completed, Error)
- **Crawler Controls**: 
  - Role Filter: Comma-separated keywords (e.g., "revops, sales ops, hubspot")
  - Remote Only: Checkbox to filter for remote positions only
  - Start Crawl Button: Triggers a new crawl run
- **Metrics Cards**:
  - State: Current crawler state
  - Domains: Progress (processed / total)
  - Jobs Found: Total jobs found in current/last run
  - Last Run: Timestamp of last crawl
- **Live Logs**: Real-time log viewer with auto-scroll
- **Recent Jobs**: Summary of recently found job postings

### 3. **API Endpoints**

#### `GET /`
Serves the control room UI (HTML page)

#### `GET /health`
Health check endpoint for Render monitoring
```json
{ "status": "ok" }
```

#### `GET /status`
Get current crawler status and metrics
```json
{
  "state": "idle|running|completed|error",
  "last_run_started_at": "2024-01-01T12:00:00Z",
  "last_run_finished_at": "2024-01-01T12:30:00Z",
  "domains_total": 622,
  "domains_processed": 120,
  "jobs_found": 34,
  "last_error": null
}
```

#### `POST /start`
Start a new crawl run with optional filters
```json
{
  "role_filter": "revops,sales ops",
  "remote_only": true
}
```

Response:
```json
{
  "status": "started",
  "message": "Crawl initiated in background"
}
```

#### `GET /logs?lines=100`
Get recent log entries (default 100, max 500)
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00",
      "level": "INFO",
      "message": "Starting crawl run..."
    }
  ]
}
```

#### `GET /jobs`
Get recent job results
```json
{
  "jobs": [...],
  "count": 34
}
```

## Logging

### Structured Logging

All logs use structured logging with contextual information:

```
2024-01-01 12:00:00 - hubspot_scraper - INFO - 🚀 Starting crawl run | domains_count=622 source=/etc/secrets/DOMAINS_FILE
2024-01-01 12:00:05 - hubspot_scraper - INFO - 🌐 Starting domain [1/622] | domain=https://example.com company=Example Co
2024-01-01 12:00:10 - hubspot_scraper - INFO - 🎯 Found career page | url=https://example.com/careers depth=0
2024-01-01 12:00:15 - hubspot_scraper - INFO - 📝 Jobs extracted from page | url=... raw_extractions=15 filtered_jobs=3
```

### Log Levels

Set via `LOG_LEVEL` environment variable:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages

### Emoji Markers

Logs use emojis for easy visual scanning:
- 🚀 Crawl start
- 🌐 Domain processing
- 🎯 Career page found
- 🔍 Scanning for jobs
- 📝 Jobs extracted
- ✅ Success
- ❌ Error
- ⚠️ Warning
- 🏁 Crawl complete

## Configuration

### Environment Variables

- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `DOMAINS_FILE`: Path to domains JSON file
- `ROLE_FILTER`: Default role filter (comma-separated)
- `REMOTE_ONLY`: Default remote-only setting (true/false)
- `MAX_PAGES_PER_DOMAIN`: Maximum pages to crawl per domain (default: 20)
- `PAGE_TIMEOUT`: Page load timeout in milliseconds (default: 30000)

## Deployment

### Docker

```bash
docker build -t hubspot-scraper .
docker run -p 8000:8000 hubspot-scraper
```

The server will start on port 8000 and serve the control room UI at `http://localhost:8000/`

### Render

The app is configured for Render via `render.yaml`:
- Uses Docker runtime
- Starts `uvicorn control_room:app` on deploy
- Exposes web service on `$PORT`

## Security

### XSS Protection
- All user-provided content is HTML-escaped
- URLs are validated before rendering as links
- External links use `rel="noopener noreferrer"`

### CORS
The control room is designed for same-origin access. Cross-origin requests are not enabled by default.

## Monitoring

### Render Logs
All structured logs are sent to stdout and are visible in Render's log viewer.

### Health Checks
Render can use the `/health` endpoint for uptime monitoring.

## Troubleshooting

### Crawler Not Starting
- Check `/status` endpoint to see current state
- Review `/logs` for error messages
- Verify `DOMAINS_FILE` environment variable is set
- Check that domains file exists and is valid JSON

### No Jobs Found
- Enable `DEBUG` logging to see detailed extraction logs
- Check if domains have accessible career pages
- Review role filters and remote-only settings

### UI Not Loading
- Verify the server is running: `curl http://localhost:8000/health`
- Check browser console for JavaScript errors
- Ensure Tailwind CSS CDN is accessible (or use local CSS)

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the control room server
uvicorn control_room:app --host 0.0.0.0 --port 8000 --reload

# Or run the scraper directly (CLI mode)
python main.py
```

### Testing

```bash
# Run all tests
python -m unittest discover -s . -p "test_*.py"

# Test specific module
python -m unittest test_extractors
```
