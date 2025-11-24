# Supabase Persistence Fix - Implementation Summary

## Problem
Jobs were being saved to Supabase correctly, but the UI read from in-memory state (`crawl_status.recent_jobs`) which was cleared between runs and on page refresh, causing jobs to disappear.

## Root Cause
- Scraper saved jobs to Supabase ✅
- UI fetched jobs from in-memory state ❌
- In-memory state was reset on new runs ❌
- No `run_id` tracking to link jobs to specific runs ❌

## Solution Implemented

### 1. Added `run_id` Tracking
**File: `supabase_persistence.py`**
- Added `create_scrape_run()` to create new run records
- Added `update_scrape_run()` to update run progress
- Modified `save_jobs_for_domain()` to accept and save `run_id`
- Added `get_jobs_for_run()` to fetch jobs for a specific run
- Modified `get_all_jobs()` to optionally filter by `run_id`

**Key Changes:**
```python
# Now accepts run_id and saves it to jobs table (or metadata as fallback)
save_jobs_for_domain(..., run_id=run_id)

# Try to save run_id in jobs table directly
insert_data["run_id"] = run_id

# Fallback: if column doesn't exist, store in job_metadata.raw_json
raw_json["run_id"] = run_id
```

### 2. Updated Scraper Engine
**File: `scraper_engine.py`**
- Modified `scrape_all_domains()` to create scrape run and track run_id
- Pass run_id to `scrape_domain()` method
- Pass run_id to `save_jobs_for_domain()` call
- Update run progress after each domain
- Mark run as finished when complete

**Key Changes:**
```python
# Create run at start
run_id = create_scrape_run(total_companies=len(domains))

# Pass run_id through scraping pipeline
jobs = await scraper.scrape_domain(website, company_name, page=page, run_id=run_id)

# Update progress
update_scrape_run(run_id, total_jobs=len(all_jobs))

# Mark complete
update_scrape_run(run_id, total_jobs=len(all_jobs), finished=True)
```

### 3. Updated Control Room API
**File: `control_room.py`**
- Added `current_run_id` to `CrawlStatus` class
- Modified `_get_recent_jobs()` to read from Supabase instead of memory
- Track current run_id in crawl status
- Return Supabase data to UI, fall back to memory only if Supabase unavailable

**Key Changes:**
```python
# Track current run
crawl_status.current_run_id = run_id

# Fetch from Supabase (persistent)
jobs_from_db = get_all_jobs(limit=500, run_id=run_id)

# Transform and return
return {"jobs": formatted_jobs, "count": len(formatted_jobs)}
```

### 4. Added Logging
Added comprehensive logging as per requirements:
- `logger.info(f"Inserted {n} jobs into Supabase (run_id={run_id}, domain={domain})")`
- `logger.info(f"Fetched {n} jobs for UI (run_id={run_id})")`
- `logger.info(f"Created scrape run with id={run_id}, total_companies={n}")`

### 5. Database Schema Update
**File: `migration_add_run_id.sql`**
```sql
-- Add run_id column to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES scrape_runs(id) ON DELETE SET NULL;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_jobs_run_id ON jobs(run_id);
```

**Note:** The code handles both cases:
1. If `run_id` column exists → saves directly to jobs table
2. If `run_id` column doesn't exist → saves to job_metadata.raw_json (backward compatible)

### 6. Validated No Destructive Operations
✅ Searched entire codebase - no table-wide deletes found
✅ No `.delete()` without `.eq()` filter
✅ No `.truncate()` operations
✅ All deletes are scoped to specific records

## Testing

Created `test_supabase_persistence.py` with tests for:
- ✅ `run_id` parameter accepted in save functions
- ✅ Scrape run management functions exist
- ✅ Jobs can be queried by run_id
- ✅ No destructive deletes present
- ✅ Logging statements present

All tests pass successfully.

## How It Works Now

### Scraping Flow
```
1. Control Room triggers crawl
   ↓
2. scrape_all_domains() creates scrape run → run_id
   ↓
3. For each domain:
   - scrape_domain() passes run_id
   - save_jobs_for_domain() saves jobs with run_id
   - update_scrape_run() updates progress
   ↓
4. Mark run as finished
   ↓
5. Store current_run_id in crawl_status
```

### UI Data Flow
```
1. UI requests /api/jobs
   ↓
2. _get_recent_jobs() called
   ↓
3. Query Supabase: get_all_jobs(run_id=current_run_id)
   ↓
4. Return jobs from Supabase (persistent!)
   ↓
5. UI displays jobs
```

### Benefits
- ✅ **Jobs persist across page refreshes** (read from Supabase)
- ✅ **Multiple runs don't interfere** (each has unique run_id)
- ✅ **No data loss** (jobs saved immediately after each domain)
- ✅ **Backward compatible** (works with or without run_id column)
- ✅ **Proper logging** (track insert/fetch operations)
- ✅ **No destructive deletes** (data is safe)

## Manual Verification Steps

1. **Start a crawl:**
   - UI should show jobs as they're discovered
   
2. **Refresh the page mid-crawl:**
   - Jobs should still be visible (loaded from Supabase)
   
3. **Start a second crawl:**
   - First run's jobs remain in database
   - Can query by run_id to see either run
   
4. **Check Supabase:**
   - `scrape_runs` table has entries
   - `jobs` table has `run_id` field (or run_id in job_metadata.raw_json)
   - No rows deleted between runs

## Files Modified

1. ✅ `supabase_persistence.py` - Added run management and run_id support
2. ✅ `scraper_engine.py` - Create/track run_id, pass through pipeline
3. ✅ `control_room.py` - Read from Supabase, track current run_id

## Files Created

1. ✅ `migration_add_run_id.sql` - SQL to add run_id column
2. ✅ `test_supabase_persistence.py` - Validation tests
3. ✅ `SUPABASE_FIX_SUMMARY.md` - This documentation

## Next Steps

To fully enable this functionality:

1. **Run the migration** (if you want run_id in jobs table directly):
   ```bash
   # In Supabase SQL Editor, run:
   cat migration_add_run_id.sql | pbcopy
   # Paste and execute
   ```
   
   **OR** skip this - the code works without the column (uses metadata fallback)

2. **Deploy the updated code:**
   ```bash
   git commit -am "Fix Supabase persistence for job results"
   git push
   ```

3. **Test:**
   - Start a crawl
   - Refresh page
   - Verify jobs remain visible
   - Start another crawl
   - Verify both runs' data exists in Supabase

## Backward Compatibility

✅ Works with existing Supabase schema (no migration required)
✅ If `run_id` column doesn't exist, stores in job_metadata.raw_json
✅ Falls back to in-memory jobs if Supabase is not configured
✅ Existing deployments continue to work without changes
