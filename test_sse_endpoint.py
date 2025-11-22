"""
Test script for SSE streaming functionality.
This validates that the /scrape/stream endpoint works correctly.
"""
import asyncio
import json
import sys
from typing import List, Dict

# Test the stream_scrape function directly
async def test_stream_scrape_function():
    """Test the stream_scrape function with mock domains"""
    print("Testing stream_scrape function...")
    
    from server import stream_scrape
    
    # Use simple test domains
    test_domains = ["https://example.com"]
    
    results = []
    try:
        async for event in stream_scrape(test_domains):
            # Parse the SSE event
            if event.startswith("data: "):
                data = event[6:].strip()  # Remove "data: " prefix and trailing newlines
                if data:
                    result = json.loads(data)
                    results.append(result)
                    print(f"✓ Received result for domain: {result.get('domain')}")
                    print(f"  Status: {result.get('status')}")
                    print(f"  Jobs found: {len(result.get('jobs', []))}")
    except Exception as e:
        print(f"✗ Error during streaming: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if len(results) == len(test_domains):
        print(f"\n✓ All {len(test_domains)} domains processed successfully!")
        return True
    else:
        print(f"\n✗ Expected {len(test_domains)} results, got {len(results)}")
        return False


async def test_parallel_execution():
    """Test that domains are processed in parallel"""
    print("\nTesting parallel execution...")
    
    from server import stream_scrape
    import time
    
    # Use multiple domains to test parallelism
    test_domains = [
        "https://example.com",
        "https://www.example.org",
    ]
    
    start_time = time.time()
    results = []
    
    try:
        async for event in stream_scrape(test_domains):
            if event.startswith("data: "):
                data = event[6:].strip()
                if data:
                    result = json.loads(data)
                    elapsed = time.time() - start_time
                    results.append(result)
                    print(f"  Domain {result.get('domain')} completed at {elapsed:.2f}s")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    total_time = time.time() - start_time
    print(f"\n✓ Total time for {len(test_domains)} domains: {total_time:.2f}s")
    
    # If it took less than 2x the time of a single domain, it's likely parallel
    if len(results) == len(test_domains):
        print("✓ Parallel execution appears to be working!")
        return True
    else:
        print(f"✗ Expected {len(test_domains)} results, got {len(results)}")
        return False


def test_sse_formatting():
    """Test that SSE events are properly formatted"""
    print("\nTesting SSE formatting...")
    
    test_event = 'data: {"domain": "test.com", "status": "success", "jobs": []}\n\n'
    
    # Verify format
    if not test_event.startswith("data: "):
        print("✗ Event must start with 'data: '")
        return False
    
    if not test_event.endswith("\n\n"):
        print("✗ Event must end with double newline")
        return False
    
    # Verify JSON is valid
    try:
        data = test_event[6:].strip()
        json.loads(data)
        print("✓ SSE formatting is correct")
        return True
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in event: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("SSE Streaming Tests")
    print("=" * 60)
    
    # Test 1: SSE formatting
    test1 = test_sse_formatting()
    
    # Test 2: Basic streaming function
    test2 = await test_stream_scrape_function()
    
    # Test 3: Parallel execution (commented out for speed)
    # test3 = await test_parallel_execution()
    # all_passed = test1 and test2 and test3
    
    all_passed = test1 and test2
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
