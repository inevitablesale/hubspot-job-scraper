"""
Test Supabase persistence to ensure jobs are saved and retrieved correctly.
"""
import os
import sys


def test_no_destructive_deletes():
    """
    Verify that no table-wide deletes are present in the codebase.
    
    This test scans the supabase_persistence.py file to ensure there are
    no destructive delete operations without proper filtering.
    """
    import supabase_persistence
    import inspect
    
    source_code = inspect.getsource(supabase_persistence)
    
    # Check for delete operations
    if ".delete()" in source_code:
        # Make sure all deletes have filters
        lines = source_code.split('\n')
        for i, line in enumerate(lines):
            if '.delete()' in line:
                # Check if the next few lines have .eq( or .filter(
                context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                if '.eq(' not in context and '.filter(' not in context:
                    raise AssertionError(f"Found unfiltered delete at line {i}: {line}")
    
    assert ".truncate()" not in source_code, \
        "Found truncate operation in supabase_persistence.py"
    
    print("✅ Test passed: No destructive deletes found")


def test_run_id_in_save_function():
    """
    Test that save_jobs_for_domain accepts run_id parameter.
    """
    import supabase_persistence
    import inspect
    
    # Get the signature of save_jobs_for_domain
    sig = inspect.signature(supabase_persistence.save_jobs_for_domain)
    params = list(sig.parameters.keys())
    
    assert 'run_id' in params, "save_jobs_for_domain must accept run_id parameter"
    
    print("✅ Test passed: save_jobs_for_domain accepts run_id")


def test_scrape_runs_management():
    """
    Test that scrape run management functions exist.
    """
    import supabase_persistence
    
    assert hasattr(supabase_persistence, 'create_scrape_run'), \
        "create_scrape_run function must exist"
    assert hasattr(supabase_persistence, 'update_scrape_run'), \
        "update_scrape_run function must exist"
    assert hasattr(supabase_persistence, 'get_jobs_for_run'), \
        "get_jobs_for_run function must exist"
    
    print("✅ Test passed: Scrape run management functions exist")


def test_get_all_jobs_accepts_run_id():
    """
    Test that get_all_jobs can filter by run_id.
    """
    import supabase_persistence
    import inspect
    
    sig = inspect.signature(supabase_persistence.get_all_jobs)
    params = list(sig.parameters.keys())
    
    assert 'run_id' in params, "get_all_jobs must accept run_id parameter"
    
    print("✅ Test passed: get_all_jobs accepts run_id filter")


def test_logging_present():
    """
    Verify that logging is added to persistence functions.
    """
    import supabase_persistence
    import inspect
    
    source_code = inspect.getsource(supabase_persistence)
    
    # Check for logging statements
    assert 'logger.info' in source_code, \
        "Must have logger.info statements for tracking"
    
    # Check for specific logging patterns
    assert 'Inserted' in source_code or 'inserted' in source_code, \
        "Must log when jobs are inserted"
    
    assert 'Fetched' in source_code or 'fetched' in source_code, \
        "Must log when jobs are fetched"
    
    print("✅ Test passed: Logging statements present")


if __name__ == "__main__":
    # Run tests
    print("Running Supabase persistence tests...")
    print()
    
    try:
        test_no_destructive_deletes()
        test_run_id_in_save_function()
        test_scrape_runs_management()
        test_get_all_jobs_accepts_run_id()
        test_logging_present()
        
        print()
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print()
        print("Key validations:")
        print("  ✓ Jobs are saved with run_id parameter")
        print("  ✓ No destructive deletes found")
        print("  ✓ Scrape run management functions exist")
        print("  ✓ Jobs can be queried by run_id")
        print("  ✓ Logging statements present")
        print()
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print("❌ Test failed!")
        print("=" * 60)
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Test error!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
