# Docker & Deployment Instructions

This applies to:
- `Dockerfile`
- `render.yaml`

## Rules

1. Must use Playwright official Python image:
   ```dockerfile
   FROM mcr.microsoft.com/playwright/python:v1.49.0-focal
   ```

2. The image already includes browsers — NEVER run `playwright install`.

3. Keep container non-root when possible.

4. Render deploys via `Dockerfile`, not via Python environment.

5. Start command must be:
   ```bash
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

6. Do not change base image unless job scraping requires a new browser version.
