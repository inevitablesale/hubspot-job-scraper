#!/usr/bin/env bash
set -euo pipefail

# Render's default build command is './postinstall.sh'.
# Install Python dependencies and Playwright browser runtime.
pip install --no-cache-dir -r requirements.txt
playwright install --with-deps chromium
