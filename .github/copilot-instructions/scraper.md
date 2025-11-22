# Scraper Implementation Guidelines

## Overview
This document provides guidelines for implementing and maintaining the HubSpot job scraper using Playwright.

## Core Requirements

### 1. Navigation Strategy
- Implement Playwright navigation with proper timeout handling
- Use headless Chrome for browser automation
- Wait for `domcontentloaded` event before processing pages
- Add reasonable delays for dynamic content (e.g., 1000ms)

### 2. Domain Blacklist Enforcement
The scraper MUST enforce strict domain blacklisting to avoid crawling irrelevant sites:

**Social Networks** (NEVER crawl):
- facebook.com, instagram.com, linkedin.com
- twitter.com, x.com, youtube.com
- tiktok.com, pinterest.com, threads.net

**HubSpot Ecosystem** (NEVER crawl):
- hubspot.com (and all subdomains)
- blog.hubspot.com
- academy.hubspot.com

**Generic Platforms** (NEVER crawl):
- canva.com, figma.com, notion.site
- medium.com, eventbrite.com
- intercom.help, zendesk.com

### 3. Header/Footer Link Filtering
**CRITICAL**: Do not follow links from header or footer elements unless they contain career keywords.

Implementation:
```python
# Detect header/footer elements
header_elements = soup.find_all(['header', 'nav'])
footer_elements = soup.find_all('footer')

# Check if link is in header/footer
is_in_header_footer = False
for parent in anchor.parents:
    if parent in header_elements or parent in footer_elements:
        is_in_header_footer = True
        break

# Only follow if has career keywords OR not in header/footer
```

**Heuristic**: If 80%+ of links on a page come from header/footer, consider it a "layout page" and skip deep crawling.

### 4. Career Page Detection
Stop all recursive crawling once a valid career page is found. This prevents unnecessary page visits.

Valid career page patterns:
- /careers, /careers/, /career
- /join-us, /team#hiring
- /about/careers, /company/careers
- /jobs, /open-roles, /work-with-us
- /we-are-hiring

Invalid patterns (ALWAYS wrong):
- /blog, /resources, /insights
- /news, /events, /contact
- /about-us (unless also contains job posts)

### 5. ATS Integration
When an ATS (Applicant Tracking System) is detected:
1. Stop scanning the parent site
2. Scrape jobs directly from the ATS frame or API
3. Maintain attribution to the original company

Supported ATS platforms:
- Greenhouse (boards.greenhouse.io)
- Lever
- Workable
- BambooHR
- JazzHR
- BreezyHR

### 6. Crawl Depth Limits
Enforce strict limits:
- MAX_DEPTH = 2
- MAX_PAGES_PER_DOMAIN = 12

Once a career page is found, **STOP all further crawling**.

### 7. Logging Standards
Use structured logging with these prefixes:

```
[DOMAIN] Starting discovery...
Root URL: https://example.com

[DISCOVERY] Found potential careers link: /careers

[SKIP] Footer/social link skipped: https://facebook.com/xyz
[SKIP] Header navigation ignored: /blog

[CAREERS] Navigating to: https://example.com/careers

[ATS] Greenhouse detected. Scraping via embedded jobs list.

[JOB] Title: Senior HubSpot Specialist
     Source: On-site careers page

[COMPLETE] Domain: example.com | Jobs found: 6
```

## Implementation Patterns

### Page Crawling
```python
async def _crawl_page(url, company_name, root_domain, depth, jobs_list):
    # Check depth limit
    if depth > MAX_DEPTH:
        return
    
    # Check page limit
    if len(visited_urls) >= MAX_PAGES_PER_DOMAIN:
        return
    
    # Navigate and extract
    if is_career_page(url, html):
        logger.info(f"[CAREERS] Navigating to: {url}")
        await extract_jobs(html, url, company_name, jobs_list)
        return  # STOP crawling once career page is found
    
    # Otherwise, find career links
    career_links = get_career_links(html, url)
    for link in career_links[:5]:  # Limit links per page
        await _crawl_page(link, company_name, root_domain, depth + 1, jobs_list)
        if jobs_list:  # Stop if we found jobs
            return
```

### Blacklist Checking
```python
def should_skip_link(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix('www.')
    
    # Check blacklist
    for blacklisted in BLACKLISTED_DOMAINS:
        if host == blacklisted or host.endswith('.' + blacklisted):
            logger.debug(f"[SKIP] Footer/social link skipped: {url}")
            return True
    
    return False
```

## Testing
- Mock HTTP responses for reproducibility
- Snapshot job extraction results
- Test blacklist behavior with known domains
- Verify career-page-first navigation logic
- Test that crawling stops after finding career page

## Performance Considerations
- Use rate limiting (default 1s per domain)
- Implement exponential backoff on failures
- Respect robots.txt
- Close browser pages after use
- Clear visited URLs between domains
