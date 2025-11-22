#!/bin/bash
# Test script for SSE streaming endpoint
# This demonstrates real-time streaming of scraping results

echo "Testing SSE streaming endpoint..."
echo "=================================="
echo ""
echo "Sending request to stream 3 domains in parallel..."
echo ""

curl -N -X POST \
  -H "Content-Type: application/json" \
  --data '{"domains":["https://example.com","https://www.google.com","https://github.com"]}' \
  http://localhost:8000/scrape/stream

echo ""
echo "=================================="
echo "Stream complete!"
