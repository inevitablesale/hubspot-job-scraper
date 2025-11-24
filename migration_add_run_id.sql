-- Migration: Add run_id column to jobs table
-- This column links jobs to specific scrape runs for better tracking
-- and allows the UI to filter jobs by run

-- Add run_id column to jobs table (nullable for backward compatibility)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES scrape_runs(id) ON DELETE SET NULL;

-- Create an index for faster queries by run_id
CREATE INDEX IF NOT EXISTS idx_jobs_run_id ON jobs(run_id);

-- Optional: Add a comment to document the column
COMMENT ON COLUMN jobs.run_id IS 'Links job to the scrape run that discovered it';
