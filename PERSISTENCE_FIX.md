# Supabase Persistence Fix

## Problem
Jobs disappeared from UI because:
- Scraper saved to Supabase ✅
- UI read from in-memory state ❌ 
- In-memory cleared on new runs ❌

## Solution
Changed UI to read from Supabase (persistent storage) instead of memory.

## Changes

### supabase_persistence.py
- Added `create_scrape_run()` - creates run, returns run_id
- Added `update_scrape_run()` - updates progress/completion
- Modified `save_jobs_for_domain()` - accepts and saves run_id
- Added `get_jobs_for_run()` - fetches jobs by run_id
- Logging: "Saving X jobs for run_id=..., domain=..."

### scraper_engine.py  
- Creates scrape run at start
- Passes run_id through pipeline
- Updates run progress per domain
- Marks run complete at end

### control_room.py
- `_get_recent_jobs()` now queries Supabase
- Falls back to memory if Supabase unavailable
- No more empty array broadcasts

## Result
✅ Jobs persist across page refreshes
✅ Multiple runs don't interfere  
✅ No data loss
✅ No destructive operations
