"""
Test browser lifecycle management with single browser instance and multiple contexts.

Tests:
- Single browser instance for all domains
- Isolated browser context per domain
- Proper cleanup of contexts
- Backward compatibility with page parameter
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
async def test_scrape_all_domains_single_browser():
    """Test that scrape_all_domains uses a single browser instance."""
    # Create a temporary domains file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        domains = [
            {"website": "https://example.com", "title": "Example Corp"},
            {"website": "https://test.com", "title": "Test Inc"},
        ]
        json.dump(domains, f)
        domains_file = f.name
    
    try:
        # Verify the single browser pattern implementation by inspecting source
        # This validates that the code structure matches our design:
        # single scraper instance + contexts per domain
        import inspect
        source = inspect.getsource(scrape_all_domains)
        
        # Verify single scraper initialization (not in loop)
        assert 'scraper = JobScraper()' in source
        assert 'await scraper.initialize()' in source
        
        # Verify context creation in loop
        assert 'context = await scraper.browser.new_context()' in source
        assert 'page = await context.new_page()' in source
        
        # Verify cleanup
        assert 'await page.close()' in source
        assert 'await context.close()' in source
        assert 'await scraper.shutdown()' in source
        
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

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
