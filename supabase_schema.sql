-- Supabase schema for jobs table
-- Run this SQL in your Supabase SQL editor to create the jobs table

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    remote_type TEXT,
    url TEXT NOT NULL,
    source_page TEXT NOT NULL,
    ats TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_jobs_domain ON jobs(domain);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_remote_type ON jobs(remote_type);

-- Enable Row Level Security (RLS)
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations for now
-- In production, you may want to restrict this
CREATE POLICY "Allow all operations on jobs" ON jobs
    FOR ALL
    USING (true)
    WITH CHECK (true);
