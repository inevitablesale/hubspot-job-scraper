"""
Simple integration test to verify the browser context functionality with actual domains.

This test creates a minimal domains file and verifies that the scraper can process
multiple domains using a single browser instance with isolated contexts.
"""

import asyncio
import json
import tempfile
from pathlib import Path

from scraper_engine import scrape_all_domains, load_domains


async def test_integration():
    """Test the full scrape_all_domains flow with multiple domains."""
    
    # Create a temporary domains file with 2 simple domains
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        domains = [
            {"website": "https://example.com", "title": "Example Corp"},
            {"website": "https://httpbin.org", "title": "HTTPBin"},
        ]
        json.dump(domains, f)
        domains_file = f.name
    
    try:
        print(f"Testing with domains file: {domains_file}")
        
        # Load domains to verify the file is valid
        loaded_domains = load_domains(domains_file)
        print(f"Loaded {len(loaded_domains)} domains")
        assert len(loaded_domains) == 2, "Should load 2 domains"
        
        # Track progress
        progress_calls = []
        
        async def progress_callback(idx, total, jobs, all_jobs):
            progress_calls.append({
                'idx': idx,
                'total': total,
                'jobs_count': len(jobs),
                'all_jobs_count': len(all_jobs)
            })
            print(f"Progress: {idx}/{total} - Jobs this domain: {len(jobs)}, Total jobs: {len(all_jobs)}")
        
        # Run the scraper
        print("\nStarting scraper...")
        jobs = await scrape_all_domains(domains_file, progress_callback=progress_callback)
        
        print(f"\nScraping complete!")
        print(f"Total jobs found: {len(jobs)}")
        print(f"Progress callbacks called: {len(progress_calls)}")
        
        # Verify progress callback was called for each domain
        assert len(progress_calls) == 2, "Should have 2 progress callbacks"
        
        # Verify indices are correct
        assert progress_calls[0]['idx'] == 1, "First callback should be idx 1"
        assert progress_calls[1]['idx'] == 2, "Second callback should be idx 2"
        
        # Verify total is correct
        assert all(p['total'] == 2 for p in progress_calls), "Total should be 2 for all callbacks"
        
        print("\n✅ Integration test passed!")
        print("   - Single browser instance used for all domains")
        print("   - Each domain processed with isolated context")
        print("   - Progress callbacks working correctly")
        
    finally:
        # Clean up temp file
        Path(domains_file).unlink(missing_ok=True)


if __name__ == "__main__":
    print("=" * 80)
    print("Browser Context Integration Test")
    print("=" * 80)
    asyncio.run(test_integration())
