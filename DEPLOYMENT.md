# Deployment Guide

## Deploying to Render

This scraper is designed to run on Render as a web service with background job execution.

### Setup Steps

1. **Create a new Web Service** on Render
   - Connect your GitHub repository
   - Set the branch to deploy

2. **Configure Build Command**
   ```bash
   pip install -r requirements.txt && playwright install chromium
   ```

3. **Configure Start Command**
   ```bash
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

4. **Add Environment Variables**
   - `DOMAINS_FILE` - Path to your domains JSON file (or use secrets mount)
   - `LOG_LEVEL` - Set to `INFO` for production
   - `NTFY_URL` - Your ntfy.sh topic URL
   - `EMAIL_TO` - (Optional) Email for notifications
   - `SLACK_WEBHOOK` - (Optional) Slack webhook URL
   - `ROLE_FILTER` - (Optional) Comma-separated list of roles to include
   - `REMOTE_ONLY` - (Optional) Set to `true` to filter only remote jobs

5. **Mount Secrets** (Alternative to DOMAINS_FILE env var)
   - Upload your domains JSON file as a secret file
   - Mount it at `/etc/secrets/DOMAINS_FILE`

6. **Deploy**
   - Render will build and deploy your service
   - Access the control room at your service URL
   - Click "Start Crawl" to begin scraping

### Health Checks

Render will automatically ping `/health` or send `HEAD /` requests to check if your service is running.

### Resource Requirements

- **Instance Type**: Starter or higher (needs headless Chrome)
- **RAM**: At least 512MB (1GB recommended)
- **Disk**: Default is sufficient

### Monitoring

- View logs in real-time via the Render dashboard
- Use the FastAPI control room UI for live log streaming
- Check `/status` endpoint for crawler state

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Create a domains file:
   ```bash
   cp example_domains.json my_domains.json
   # Edit my_domains.json with your companies
   ```

3. Run the scraper:
   ```bash
   DOMAINS_FILE=my_domains.json python run_spider.py
   ```

   Or with the web UI:
   ```bash
   DOMAINS_FILE=my_domains.json uvicorn server:app --reload
   ```
   Then visit http://localhost:8000

## Troubleshooting

### Browser Installation Issues

If Playwright browser fails to install:
```bash
playwright install --with-deps chromium
```

### Memory Issues

If the service runs out of memory:
- Reduce `MAX_PAGES_PER_DOMAIN` (default 20)
- Reduce `MAX_DEPTH` (default 3)
- Upgrade to a larger Render instance

### Network Timeouts

If pages are timing out:
- Increase `PAGE_TIMEOUT` (default 30000ms)
- Check if domains are accessible
- Review logs for DNS errors

### No Jobs Found

If scraper runs but finds no jobs:
- Check domain file format
- Verify domains have career pages
- Review `LOG_LEVEL=DEBUG` output
- Check role classification thresholds
