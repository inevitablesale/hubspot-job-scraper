#!/usr/bin/env bash
set -euo pipefail

# Render's default build command is './postinstall.sh'.
# Install Python dependencies without downloading Playwright browsers.
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
pip install --no-cache-dir -r requirements.txt
