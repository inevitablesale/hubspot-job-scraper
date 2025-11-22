# Test Instructions

## Scope

Applies to:
- `/tests/*`
- future scraper regression tests

## Principles

1. Use pytest.
2. Use Playwright's test async fixtures.
3. Never hit real external domains in CI.
4. Use fixtures:
   - HTML snapshots
   - mock ATS responses
   - pre-saved DOMs

## Test Categories

### 1. Career-page detection tests
Given an HTML file → detect candidate URLs correctly.

### 2. Role extraction tests
Given an HTML snapshot → extract job titles.

### 3. Strategy fallbacks
Ensure:
- Tier 1 → Tier 2 → Tier 3 fallback works
- Errors are logged but do not break loop

### 4. Expected data model
Validate output matches:

```python
JobResult(company, title, location, url)
```
