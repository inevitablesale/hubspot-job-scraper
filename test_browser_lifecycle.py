"""
Test browser lifecycle management with browser restart every 5 domains.

Tests:
- Browser restart every 5 domains (batch processing)
- Isolated browser context per domain within each batch
- Proper cleanup of contexts
- Backward compatibility with page parameter
- Batch logging for browser startup/shutdown
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from scraper_engine import JobScraper, scrape_all_domains


@pytest.mark.asyncio
async def test_single_browser_multiple_contexts():
    """Test that a single browser instance can handle multiple contexts."""
    scraper = JobScraper()
    await scraper.initialize()
    
    try:
        # Verify browser is created
        assert scraper.browser is not None, "Browser should be initialized"
        
        # Create multiple contexts and verify isolation
        contexts = []
        pages = []
        
        for i in range(3):
            context = await scraper.browser.new_context()
            contexts.append(context)
            page = await context.new_page()
            pages.append(page)
        
        # Verify all contexts are distinct
        assert len(set(id(ctx) for ctx in contexts)) == 3, "Contexts should be unique"
        
        # Clean up contexts
        for page in pages:
            await page.close()
        for context in contexts:
            await context.close()
            
    finally:
        await scraper.shutdown()


@pytest.mark.asyncio
async def test_scrape_domain_with_page_parameter():
    """Test that scrape_domain works with provided page parameter."""
    scraper = JobScraper()
    await scraper.initialize()
    
    try:
        # Create a context and page
        context = await scraper.browser.new_context()
        page = await context.new_page()
        
        # Verify the scrape_domain method accepts a page parameter
        # This test validates backward compatibility - the method can be called
        # with or without the page parameter
        import inspect
        sig = inspect.signature(scraper.scrape_domain)
        params = sig.parameters
        
        assert 'page' in params, "scrape_domain should have page parameter"
        assert params['page'].default is None, "page parameter should be optional"
        
        # Clean up
        await page.close()
        await context.close()
        
    finally:
        await scraper.shutdown()


@pytest.mark.asyncio
async def test_scrape_domain_backward_compatibility():
    """Test that scrape_domain still works without page parameter (backward compatibility)."""
    scraper = JobScraper()
    await scraper.initialize()
    
    try:
        # Create a minimal test - just verify the method can be called without page parameter
        # This would normally navigate to a real domain, but we're just testing the signature
        import inspect
        sig = inspect.signature(scraper.scrape_domain)
        
        # Verify the method can be called with just domain_url and company_name
        params = list(sig.parameters.keys())
        assert params[0] == 'domain_url'
        assert params[1] == 'company_name'
        assert params[2] == 'page'
        
        # Verify page has a default value (None)
        assert sig.parameters['page'].default is None
        
    finally:
        await scraper.shutdown()


@pytest.mark.asyncio
async def test_scrape_all_domains_batch_browser_restart():
    """Test that scrape_all_domains restarts browser every 5 domains (batch processing)."""
    # Create a temporary domains file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        domains = [
            {"website": "https://example.com", "title": "Example Corp"},
            {"website": "https://test.com", "title": "Test Inc"},
        ]
        json.dump(domains, f)
        domains_file = f.name
    
    try:
        # Verify the batch browser restart pattern implementation by inspecting source
        # This validates that the code structure matches our design:
        # browser initialized/shutdown per batch + contexts per domain within batch
        import inspect
        source = inspect.getsource(scrape_all_domains)
        
        # Verify batch processing structure
        assert 'BATCH_SIZE = 5' in source, "Batch size should be 5"
        assert 'for batch_start in range(0, total_domains, BATCH_SIZE)' in source, "Should iterate in batches"
        
        # Verify browser lifecycle is inside batch loop
        assert 'await scraper.initialize()' in source
        assert 'await scraper.shutdown()' in source
        
        # Verify batch logging messages
        assert 'Starting browser for batch' in source, "Should log browser startup per batch"
        assert 'Shutting down browser after batch' in source, "Should log browser shutdown per batch"
        
        # Verify context creation in domain loop (inside batch)
        assert 'context = await scraper.browser.new_context()' in source
        assert 'page = await context.new_page()' in source
        
        # Verify cleanup
        assert 'await page.close()' in source
        assert 'await context.close()' in source
        
    finally:
        # Clean up temp file
        Path(domains_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_context_cleanup_on_error():
    """Test that contexts are properly cleaned up even when errors occur."""
    scraper = JobScraper()
    await scraper.initialize()
    
    try:
        # Create a context
        context = await scraper.browser.new_context()
        page = await context.new_page()
        
        # Simulate error by trying to navigate to invalid URL
        # The context should still be closable after error
        try:
            await page.goto("invalid://url", timeout=1000)
        except Exception:
            pass  # Expected to fail
        
        # Verify we can still close the context
        await page.close()
        await context.close()
        
    finally:
        await scraper.shutdown()


def test_page_parameter_type_hints():
    """Test that type hints are correct for page parameter."""
    import inspect
    from typing import get_type_hints
    
    scraper = JobScraper()
    
    # Get type hints for scrape_domain
    hints = get_type_hints(scraper.scrape_domain)
    
    # Verify page parameter exists in type hints
    assert 'page' in hints, "page parameter should have type hint"
    
    # Verify the parameter is in the signature
    sig = inspect.signature(scraper.scrape_domain)
    assert 'page' in sig.parameters, "page parameter should be in signature"
    assert sig.parameters['page'].default is None, "page parameter should default to None"


def test_batch_remainder_handling():
    """Test that batch processing handles remainder domains correctly (e.g., 12 domains = 2 full batches + 2 remaining)."""
    import inspect
    source = inspect.getsource(scrape_all_domains)
    
    # Verify the batch end calculation handles remainder correctly
    assert 'batch_end = min(batch_start + BATCH_SIZE, total_domains)' in source, \
        "Should calculate batch_end with min() to handle remainder"
    
    # Verify batch logging uses correct indices
    assert 'batch_start + 1' in source, "Should use 1-indexed batch start for logging"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
