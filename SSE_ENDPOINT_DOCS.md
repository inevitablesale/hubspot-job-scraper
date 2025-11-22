# SSE Streaming Endpoint Documentation

## Overview

The `/scrape/stream` endpoint provides real-time Server-Sent Events (SSE) streaming of job scraping results. It processes multiple domains in parallel and streams each result as soon as it completes, without waiting for the entire batch to finish.

## Endpoint Details

- **URL**: `POST /scrape/stream`
- **Content-Type**: `application/json`
- **Response Type**: `text/event-stream`

## Request Format

```json
{
  "domains": [
    "https://example.com",
    "https://another-company.com",
    "https://third-company.com"
  ]
}
```

### Request Schema

- `domains` (array of strings, required): List of company website URLs to scrape

## Response Format

The endpoint streams Server-Sent Events (SSE) in the following format:

```
data: {"domain": "https://example.com", "status": "success", "jobs": [...]}

data: {"domain": "https://another-company.com", "status": "success", "jobs": [...]}

```

Each event consists of:
- Line starting with `data: `
- JSON object containing the result
- Double newline (`\n\n`) to mark the end of the event

### Response Schema

Each streamed event contains:

```typescript
{
  "domain": string,           // The domain URL that was scraped
  "status": "success" | "error",  // Status of the scrape operation
  "jobs": Array<Job>,         // Array of job objects found
  "error"?: string           // Error message (only present if status is "error")
}
```

### Job Object Schema

Each job in the `jobs` array contains:

```typescript
{
  "company": string,
  "title": string,
  "url": string,
  "summary": string,
  "location": string,
  "role": string,
  "score": number,
  "signals": Array<string>,
  "location_type": "remote" | "hybrid" | "onsite",
  "is_contract": boolean,
  "department": string,
  "seniority": string,
  "employment_type": string,
  "timestamp": string,
  "source_page": string,
  "extraction_source": string,
  "company_health"?: object
}
```

## Features

### Parallel Processing

- All domains are scraped concurrently using `asyncio.create_task()`
- Results are streamed using `asyncio.as_completed()` 
- First domain to complete → first domain sent to client
- No waiting for slower domains to finish

### Real-Time Streaming

- Each domain result is sent immediately upon completion
- Client receives updates as they happen
- Ideal for progressive UI updates
- No batching or buffering delays

### CORS Support

- Full CORS support enabled with `allow_origins=["*"]`
- Works from browser frontends
- No CORS-related errors

### Logging

- Each completed domain logs: `[STREAM] Finished <domain>`
- Uses Python's `logging` module (not `print`)
- Log level: `INFO`

## Usage Examples

### cURL

```bash
# Stream results from 3 domains
curl -N -X POST \
  -H "Content-Type: application/json" \
  --data '{"domains":["https://company1.com","https://company2.com","https://company3.com"]}' \
  http://localhost:8000/scrape/stream
```

The `-N` flag disables buffering to see results in real-time.

### JavaScript (Browser)

```javascript
async function scrapeJobsRealtime(domains) {
  const response = await fetch('http://localhost:8000/scrape/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domains })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        console.log(`Received results for ${data.domain}:`, data.jobs);
        // Update UI with results immediately
        updateUI(data);
      }
    }
  }
}

// Usage
scrapeJobsRealtime([
  'https://company1.com',
  'https://company2.com',
  'https://company3.com'
]);
```

### JavaScript (EventSource)

```javascript
// Note: EventSource only supports GET requests
// For POST, use fetch with streaming as shown above

// Alternative: Use a library like eventsource or fetch-event-source
import { fetchEventSource } from '@microsoft/fetch-event-source';

await fetchEventSource('http://localhost:8000/scrape/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    domains: ['https://company1.com', 'https://company2.com']
  }),
  onmessage(event) {
    const data = JSON.parse(event.data);
    console.log(`Results for ${data.domain}:`, data.jobs);
    updateUI(data);
  },
  onerror(err) {
    console.error('Stream error:', err);
  }
});
```

### Python (httpx)

```python
import httpx
import json

async def scrape_jobs_realtime(domains):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            'POST',
            'http://localhost:8000/scrape/stream',
            json={'domains': domains},
            timeout=None
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"Received results for {data['domain']}")
                    print(f"Jobs found: {len(data['jobs'])}")
                    # Process results immediately
                    process_jobs(data['jobs'])

# Usage
import asyncio
asyncio.run(scrape_jobs_realtime([
    'https://company1.com',
    'https://company2.com'
]))
```

## Testing

### Run Test Script

```bash
# Make script executable
chmod +x test_sse_stream.sh

# Run test
./test_sse_stream.sh
```

### Run Automated Tests

```python
# Run Python test suite
python test_sse_endpoint.py
```

## Performance Characteristics

- **Concurrency**: All domains scraped in parallel
- **Streaming**: Results sent immediately upon completion
- **Order**: Results arrive in completion order (fastest first)
- **Resource Sharing**: Single browser instance shared across all domains
- **Browser Lifecycle**: Browser initialized once, cleaned up after all domains complete

## Error Handling

- Individual domain failures don't stop the stream
- Errors are returned in the SSE stream with `"status": "error"`
- All domains continue processing even if some fail
- Browser cleanup happens regardless of success/failure

## Implementation Details

### Technology Stack

- **FastAPI**: Web framework
- **Playwright**: Browser automation (async API)
- **asyncio**: Concurrent task execution
- **SSE**: Server-Sent Events protocol

### Concurrency Pattern

```python
# Create tasks for all domains
tasks = [
    asyncio.create_task(scrape_domain(domain))
    for domain in domains
]

# Stream results as they complete
for finished_task in asyncio.as_completed(tasks):
    result = await finished_task
    yield f"data: {json.dumps(result)}\n\n"
```

### Key Functions

- `stream_scrape(domains)`: Main streaming generator
- `scrape_domain_wrapper(scraper, url, name)`: Wraps scraping with error handling
- `scrape_stream_endpoint(request)`: FastAPI endpoint handler

## Limitations

- No WebSocket support (SSE only)
- No client-to-server messaging during stream
- Browser process is shared (not fully isolated)
- Rate limiting applies per domain

## Migration from Batch API

If you're migrating from a batch endpoint:

**Before (Batch)**:
```bash
# Wait for all results
curl -X POST /scrape/batch -d '{"domains": [...]}'
# ... long wait ...
# All results at once
```

**After (Streaming)**:
```bash
# Get results as they complete
curl -N -X POST /scrape/stream -d '{"domains": [...]}'
# Result 1 arrives immediately
# Result 2 arrives when ready
# Result 3 arrives when ready
```

## Security Considerations

- CORS is configurable via `CORS_ORIGINS` environment variable
  - Default: `allow_origins=["*"]` - accepts all origins
  - Production: Set to specific domains, e.g., `CORS_ORIGINS=https://myapp.com,https://admin.myapp.com`
- No authentication required by default (add if needed)
- Rate limiting applies per domain
- Playwright runs in headless mode with sandboxing

## Monitoring

Server logs include:
- `[STREAM] Finished <domain>` for each completed domain
- Initialization and shutdown events
- Error messages for failed domains
- Extraction statistics

## Related Endpoints

- `GET /health` - Health check
- `GET /status` - Server status
- `POST /run` - Run full batch scraper
- `GET /events` - Stream scraper logs

## Support

For issues or questions:
1. Check server logs for `[STREAM]` entries
2. Verify CORS configuration
3. Test with curl first before browser clients
4. Ensure domains are valid URLs
