# Render-compatible Dockerfile for Playwright
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Ensure playwright browsers are already installed (they are in this image)
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Default command: run the web UI (control room)
# Note: render.yaml overrides this with port binding
CMD ["sh", "-c", "uvicorn control_room:app --host 0.0.0.0 --port ${PORT}"]
