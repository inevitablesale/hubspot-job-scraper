#!/usr/bin/env bash
set -euxo pipefail

echo "=== Install backend dependencies ==="
pip install --upgrade pip

# Install backend deps
pip install -r requirements.txt

echo "=== Install Playwright browsers ==="
# Install Chromium only (fastest + compatible with Render) without requiring sudo/apt
python -m playwright install chromium

echo "=== Building frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Copying frontend build to ./static ==="
mkdir -p static
cp -r frontend/dist/* static/

echo "=== Build done ==="
