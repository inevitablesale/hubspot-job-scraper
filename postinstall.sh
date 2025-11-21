#!/usr/bin/env bash
set -euo pipefail

# Render's default build command is './postinstall.sh'.
# Install Python dependencies for both the API server and crawler.
pip install --no-cache-dir -r requirements.txt
