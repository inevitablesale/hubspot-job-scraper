# UI Layer Instructions (FastAPI + HTMX)

This applies to:
- `server.py`
- `/templates/*`
- `/static/*`

## Rules

1. UI is a **monitor**, not control logic.
2. Must NOT call scraper functions directly.
3. Everything async.
4. HTMX is preferred for partial updates.
5. Template updates must preserve:
   - log stream panel
   - start/stop buttons
   - domain counter
   - progress indicator
6. Do not modify API response structure without updating JS/HTMX.
