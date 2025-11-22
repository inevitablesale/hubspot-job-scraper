# Testing Guidelines

## Overview
This document provides guidelines for testing the HubSpot job scraper.

## Testing Strategy

### Test Types
1. **Unit Tests**: Test individual components (extractors, classifiers, detectors)
2. **Integration Tests**: Test component interactions
3. **Snapshot Tests**: Regression testing for extraction outputs
4. **End-to-End Tests**: Test complete scraping workflows

## Required Test Coverage

### 1. Blacklist Tests
Test that blacklisted domains are properly filtered:

```python
def test_blacklist_social_media():
    """Test that social media links are blocked"""
    blacklist = DomainBlacklist()
    
    # Social networks
    assert blacklist.is_blacklisted_domain("https://facebook.com/company")
    assert blacklist.is_blacklisted_domain("https://www.linkedin.com/company/xyz")
    assert blacklist.is_blacklisted_domain("https://twitter.com/company")
    assert blacklist.is_blacklisted_domain("https://instagram.com/company")
    
def test_blacklist_hubspot_ecosystem():
    """Test that HubSpot ecosystem is blocked"""
    blacklist = DomainBlacklist()
    
    assert blacklist.is_blacklisted_domain("https://blog.hubspot.com/marketing")
    assert blacklist.is_blacklisted_domain("https://academy.hubspot.com/courses")
    assert blacklist.is_blacklisted_domain("https://www.hubspot.com")
    
def test_blacklist_generic_platforms():
    """Test that generic platforms are blocked"""
    blacklist = DomainBlacklist()
    
    assert blacklist.is_blacklisted_domain("https://canva.com/design/123")
    assert blacklist.is_blacklisted_domain("https://figma.com/file/xyz")
    assert blacklist.is_blacklisted_domain("https://notion.site/page")
    assert blacklist.is_blacklisted_domain("https://eventbrite.com/event/123")
```

### 2. Career Page Detection Tests
Test that career pages are correctly identified:

```python
def test_valid_career_url_patterns():
    """Test valid career URL patterns"""
    detector = CareerPageDetector()
    
    valid_urls = [
        "https://example.com/careers",
        "https://example.com/careers/",
        "https://example.com/career",
        "https://example.com/join-us",
        "https://example.com/about/careers",
        "https://example.com/company/careers",
        "https://example.com/jobs",
        "https://example.com/open-roles",
        "https://example.com/work-with-us",
        "https://example.com/we-are-hiring",
    ]
    
    for url in valid_urls:
        assert detector.is_career_page(url), f"Failed for {url}"
        
def test_invalid_career_url_patterns():
    """Test that invalid patterns are rejected"""
    detector = CareerPageDetector()
    
    invalid_urls = [
        "https://example.com/blog",
        "https://example.com/resources",
        "https://example.com/insights",
        "https://example.com/news",
        "https://example.com/events",
        "https://example.com/contact",
    ]
    
    for url in invalid_urls:
        assert not detector.is_career_page(url), f"Should reject {url}"
```

### 3. Header/Footer Filtering Tests
Test that header/footer links are properly filtered:

```python
def test_header_footer_link_filtering():
    """Test that header/footer links are ignored unless they have career keywords"""
    detector = CareerPageDetector()
    
    html = """
    <html>
        <header>
            <nav>
                <a href="/blog">Blog</a>
                <a href="/careers">Careers</a>
                <a href="/contact">Contact</a>
            </nav>
        </header>
        <body>
            <a href="/about/careers">Join Our Team</a>
        </body>
        <footer>
            <a href="https://facebook.com/company">Facebook</a>
            <a href="/privacy">Privacy</a>
        </footer>
    </html>
    """
    
    career_links = detector.get_career_links(html, "https://example.com")
    
    # Should find body career link and header career link
    assert len(career_links) == 2
    assert any("careers" in link for link in career_links)
    
    # Should NOT include blog, contact, facebook, privacy
    assert not any("blog" in link for link in career_links)
    assert not any("facebook" in link for link in career_links)
```

### 4. Crawl Depth Tests
Test that depth limits are enforced:

```python
async def test_max_depth_enforcement():
    """Test that MAX_DEPTH is enforced"""
    scraper = JobScraper()
    await scraper.initialize()
    
    # Mock page that links to another page
    # Should not crawl beyond MAX_DEPTH=2
    
    # Track visited URLs
    visited = []
    
    # After crawl, verify depth was not exceeded
    assert max(depth for url, depth in visited) <= 2
    
async def test_stop_crawling_after_career_page():
    """Test that crawling stops once career page is found"""
    scraper = JobScraper()
    await scraper.initialize()
    
    # Should stop after finding first career page
    # Should not visit additional pages unnecessarily
```

### 5. Extraction Tests
Test multi-layer extraction with snapshots:

```python
def test_json_ld_extraction():
    """Test JSON-LD extraction with snapshot"""
    with open('tests/fixtures/jsonld_jobs.html') as f:
        html = f.read()
    
    extractor = JSONLDExtractor("https://example.com/careers")
    jobs = extractor.extract(html)
    
    # Compare with snapshot
    expected = load_snapshot('tests/snapshots/jsonld_jobs.json')
    assert jobs == expected

def test_microdata_extraction():
    """Test microdata extraction"""
    with open('tests/fixtures/microdata_jobs.html') as f:
        html = f.read()
    
    extractor = MicrodataExtractor("https://example.com/careers")
    jobs = extractor.extract(html)
    
    assert len(jobs) > 0
    assert all('title' in job for job in jobs)
```

### 6. Mock HTTP Responses
Use mocking for reliable tests:

```python
@pytest.fixture
def mock_page(mocker):
    """Mock Playwright page"""
    page = mocker.MagicMock()
    page.goto = mocker.AsyncMock()
    page.content = mocker.AsyncMock(return_value="<html>...</html>")
    page.close = mocker.AsyncMock()
    return page

async def test_scraper_with_mock(mock_page):
    """Test scraper with mocked responses"""
    scraper = JobScraper()
    scraper.browser = mocker.MagicMock()
    scraper.browser.new_page = mocker.AsyncMock(return_value=mock_page)
    
    jobs = await scraper.scrape_domain("https://example.com", "Example Co")
    
    # Verify page was visited
    mock_page.goto.assert_called()
```

## Test Data

### Fixtures
Store HTML fixtures in `tests/fixtures/`:
- `jsonld_jobs.html` - Page with JSON-LD structured data
- `microdata_jobs.html` - Page with microdata
- `ats_greenhouse.html` - Page with Greenhouse ATS
- `no_jobs.html` - Page with "no jobs available" message
- `header_footer_links.html` - Page with header/footer navigation

### Snapshots
Store expected outputs in `tests/snapshots/`:
- `jsonld_jobs.json` - Expected JSON-LD extraction
- `microdata_jobs.json` - Expected microdata extraction
- `ats_jobs.json` - Expected ATS extraction

## Running Tests

```bash
# Run all tests
python -m unittest discover -s . -p "test_*.py" -v

# Run specific test file
python -m unittest test_blacklist.py -v

# Run snapshot tests
python -m unittest tests.test_snapshots -v

# Update snapshots (after intentional changes)
UPDATE_SNAPSHOTS=1 python -m unittest tests.test_snapshots -v
```

## Continuous Integration
- Run tests on every commit
- Require passing tests before merge
- Track test coverage (aim for >80%)
- Run linting (flake8, black, mypy)

## Test Best Practices
1. Use descriptive test names
2. One assertion per test (when possible)
3. Mock external dependencies
4. Clean up resources (close browsers, delete temp files)
5. Use fixtures for common setup
6. Test edge cases and error conditions
7. Keep tests fast (< 1s per test)
8. Make tests deterministic (no random data)
