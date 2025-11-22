#!/bin/bash
# Build script for Render deployment
# This script installs Python dependencies and Playwright with system dependencies

set -e  # Exit on error

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Installing Playwright browsers..."
playwright install chromium

echo "Build complete!"
