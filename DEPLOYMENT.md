# Deployment Guide

## Deploying to Render (Docker-based)

This scraper is designed to run on Render as a Docker-based web service with background job execution.

### Setup Steps

1. **Create a new Web Service** on Render
   - Connect your GitHub repository
   - Set the branch to deploy
   - **Select "Docker" as the runtime environment**

2. **Configure Build Settings**
   Render will automatically detect the Dockerfile and build the image.
   
   No build command needed - the Dockerfile handles everything.

3. **Configure Start Command**
   For the web server (control room UI):
   ```bash
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```
   
   For the standalone scraper:
   ```bash
   python main.py
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
   - Render will build the Docker image and deploy your service
   - Access the control room at your service URL
   - Click "Start Crawl" to begin scraping

### Why Docker?

This deployment uses the official Microsoft Playwright Python Docker image which:
- **Pre-installs all browsers** (Chromium, Firefox, WebKit)
- **Eliminates browser installation errors** ("Executable doesn't exist", "Please run playwright install")
- **Includes all system dependencies** required for headless browser automation
- **Works reliably** in Render's container runtime environment
- **Reduces deployment complexity** - no need for custom build scripts

### Health Checks

Render will automatically ping `/health` or send `HEAD /` requests to check if your service is running.

### Resource Requirements

- **Instance Type**: Starter or higher (Docker-based, includes all browser dependencies)
- **RAM**: At least 512MB (1GB recommended for concurrent crawling)
- **Disk**: Default is sufficient (browsers included in Docker image)

### Monitoring

- View logs in real-time via the Render dashboard
- Use the FastAPI control room UI for live log streaming
- Check `/status` endpoint for crawler state

## Running Locally with Docker

1. **Build the Docker image:**
   ```bash
   docker build -t hubspot-scraper .
   ```

2. **Create a domains file:**
   ```bash
   cp example_domains.json my_domains.json
   # Edit my_domains.json with your companies
   ```

3. **Run the scraper:**
   ```bash
   docker run -e DOMAINS_FILE=/app/my_domains.json \
              -v $(pwd)/my_domains.json:/app/my_domains.json \
              hubspot-scraper
   ```
   
   Or with the web UI:
   ```bash
   docker run -p 8000:8000 \
              -e DOMAINS_FILE=/app/my_domains.json \
              -v $(pwd)/my_domains.json:/app/my_domains.json \
              hubspot-scraper \
              uvicorn server:app --host 0.0.0.0 --port 8000
   ```
   Then visit http://localhost:8000

## Running Locally without Docker

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
   DOMAINS_FILE=my_domains.json python main.py
   ```

   Or with the web UI:
   ```bash
   DOMAINS_FILE=my_domains.json uvicorn server:app --reload
   ```
   Then visit http://localhost:8000

## Troubleshooting

### Docker-Based Deployment

#### Browser Issues
The Docker image includes pre-installed browsers. If you encounter browser-related errors:
- Ensure you're using the official Playwright Docker image (specified in Dockerfile)
- Verify the Dockerfile hasn't been modified
- Check Render logs for any container startup errors

#### Build Failures
If Docker build fails on Render:
- Check that Dockerfile is in the repository root
- Verify requirements.txt is valid
- Review Render build logs for specific error messages

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
