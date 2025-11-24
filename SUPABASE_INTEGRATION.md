# Supabase Integration Guide

This document describes the Supabase database integration for storing job scraping data.

## Overview

The job scraper now saves all scraped data to Supabase, a PostgreSQL-based cloud database. The integration is optional - if Supabase credentials are not configured, the scraper will continue to work but won't persist data to the database.

## Database Schema

The following tables are used (exact schema as defined in requirements):

### 1. companies
Stores company information with domain-based deduplication.

- `id` (uuid, primary key)
- `name` (text)
- `domain` (text, unique) - used for deduplication
- `source_url` (text)
- `logo_url` (text, nullable)
- `created_at` (timestamptz)
- `updated_at` (timestamptz)

### 2. jobs
Stores job postings with hash-based deduplication.

- `id` (uuid, primary key)
- `company_id` (uuid, foreign key → companies.id)
- `job_title` (text)
- `job_url` (text)
- `department` (text, nullable)
- `location` (text, nullable)
- `remote_type` (text, nullable)
- `description` (text, nullable)
- `posted_at` (timestamptz, nullable)
- `scraped_at` (timestamptz)
- `hash` (text, unique) - SHA256 hash for deduplication
- `active` (boolean)
- `ats_provider` (text, nullable)

### 3. job_metadata
Stores additional job metadata (only when data is present).

- `id` (uuid, primary key)
- `job_id` (uuid, foreign key → jobs.id)
- `seniority` (text, nullable)
- `employment_type` (text, nullable)
- `salary_min` (numeric, nullable)
- `salary_max` (numeric, nullable)
- `technologies` (text[], nullable)
- `raw_json` (jsonb, nullable)
- `created_at` (timestamptz)

### 4. ats_sources
Stores ATS detection information.

- `id` (uuid, primary key)
- `job_id` (uuid, foreign key → jobs.id)
- `provider` (text)
- `raw_html` (text, nullable)
- `detected_at` (timestamptz)

### 5. scrape_runs
Logs each scraping run with metrics.

- `id` (uuid, primary key)
- `started_at` (timestamptz)
- `finished_at` (timestamptz, nullable)
- `total_companies` (int)
- `total_jobs` (int)
- `errors` (jsonb, nullable)

### 6. job_history
Captures job snapshots for change tracking.

- `id` (uuid, primary key)
- `job_id` (uuid, foreign key → jobs.id)
- `snapshot` (jsonb)
- `captured_at` (timestamptz)

## Setup Instructions

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Wait for the project to be provisioned

### 2. Create Database Tables

Run the following SQL in your Supabase SQL editor:

```sql
-- Companies table
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT NOT NULL UNIQUE,
    source_url TEXT NOT NULL,
    logo_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_companies_domain ON companies(domain);

-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    job_title TEXT NOT NULL,
    job_url TEXT NOT NULL,
    department TEXT,
    location TEXT,
    remote_type TEXT,
    description TEXT,
    posted_at TIMESTAMPTZ,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    hash TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT true,
    ats_provider TEXT
);

CREATE INDEX idx_jobs_company_id ON jobs(company_id);
CREATE INDEX idx_jobs_hash ON jobs(hash);
CREATE INDEX idx_jobs_active ON jobs(active);

-- Job metadata table
CREATE TABLE job_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    seniority TEXT,
    employment_type TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    technologies TEXT[],
    raw_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_metadata_job_id ON job_metadata(job_id);

-- ATS sources table
CREATE TABLE ats_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    raw_html TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ats_sources_job_id ON ats_sources(job_id);
CREATE INDEX idx_ats_sources_provider ON ats_sources(provider);

-- Scrape runs table
CREATE TABLE scrape_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    total_companies INT NOT NULL DEFAULT 0,
    total_jobs INT NOT NULL DEFAULT 0,
    errors JSONB
);

CREATE INDEX idx_scrape_runs_started_at ON scrape_runs(started_at DESC);

-- Job history table
CREATE TABLE job_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    snapshot JSONB NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_history_job_id ON job_history(job_id);
CREATE INDEX idx_job_history_captured_at ON job_history(captured_at DESC);
```

### 3. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Get your Supabase credentials:
   - Go to your Supabase project settings
   - Navigate to API section
   - Copy the `URL` and `service_role` key

3. Update `.env` file:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-service-role-key
   ```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

Once configured, the scraper will automatically save data to Supabase during the scraping process. No code changes are required.

### Running the Scraper

```bash
# Set environment variables (if not using .env file)
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"

# Run the scraper
python main.py
```

### Optional Mode (No Database)

If Supabase credentials are not configured, the scraper will:
1. Log a warning message
2. Continue scraping normally
3. Return job data as before
4. Not persist data to database

This allows development and testing without requiring a database.

## Data Flow

When a job is scraped:

1. **Company Creation/Retrieval**
   - Checks if company exists by domain
   - Creates new company if not found
   - Updates `updated_at` timestamp if found

2. **Job Creation/Retrieval**
   - Calculates hash from `company_id + job_title + job_url`
   - Checks if job exists by hash
   - Creates new job if not found
   - Reactivates inactive jobs if found

3. **Metadata Insertion**
   - Inserts job_metadata only if meaningful data exists
   - Stores seniority, employment_type, technologies, etc.

4. **ATS Detection**
   - Records ATS provider if detected
   - Stores in ats_sources table

5. **Job History**
   - Captures snapshot of job data
   - Stores in job_history for change tracking

6. **Scrape Run Tracking**
   - Creates scrape_run record at start
   - Updates with final metrics at end
   - Captures errors if any occur

## Deduplication Strategy

### Company Deduplication
- Uses `domain` field (unique constraint)
- Multiple companies with same domain → returns existing company

### Job Deduplication
- Uses SHA256 hash of `company_id:job_title:job_url`
- Stored in `hash` field (unique constraint)
- Same job posted again → returns existing job
- Inactive jobs are reactivated when found again

## Querying the Data

### Get all jobs for a company
```sql
SELECT j.*, c.name as company_name
FROM jobs j
JOIN companies c ON j.company_id = c.id
WHERE c.domain = 'example.com'
AND j.active = true
ORDER BY j.scraped_at DESC;
```

### Get jobs by ATS provider
```sql
SELECT j.*, c.name as company_name, a.provider
FROM jobs j
JOIN companies c ON j.company_id = c.id
JOIN ats_sources a ON a.job_id = j.id
WHERE a.provider = 'greenhouse'
ORDER BY j.scraped_at DESC;
```

### Get scrape run statistics
```sql
SELECT 
    id,
    started_at,
    finished_at,
    total_companies,
    total_jobs,
    EXTRACT(EPOCH FROM (finished_at - started_at)) as duration_seconds
FROM scrape_runs
ORDER BY started_at DESC
LIMIT 10;
```

### Track job changes
```sql
SELECT 
    jh.captured_at,
    jh.snapshot->>'title' as title,
    jh.snapshot->>'location' as location,
    jh.snapshot->>'department' as department
FROM job_history jh
WHERE jh.job_id = 'your-job-uuid'
ORDER BY jh.captured_at DESC;
```

## Security Considerations

1. **Use Service Role Key for Backend**
   - The scraper uses the service role key
   - This bypasses Row Level Security (RLS)
   - Only use in secure backend environments

2. **Enable RLS for Public Access**
   - If building a public-facing API, enable RLS
   - Create policies for read-only access
   - Never expose service role key to frontend

3. **Environment Variables**
   - Never commit `.env` to version control
   - Use secrets management in production
   - Rotate keys periodically

## Troubleshooting

### "Supabase credentials not configured" warning
- Check that `SUPABASE_URL` and `SUPABASE_KEY` are set
- Verify they are correctly formatted
- Ensure the service role key has proper permissions

### Database connection errors
- Verify Supabase project is active
- Check network connectivity
- Verify API key permissions

### Duplicate key errors
- This is expected behavior (deduplication working)
- The code handles these gracefully
- Check logs for actual errors vs. expected deduplication

## Architecture

```
┌──────────────────┐
│  scraper_engine  │
│   (main logic)   │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│   db_service     │
│  (database ops)  │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│ supabase_client  │
│  (connection)    │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│    Supabase      │
│   (PostgreSQL)   │
└──────────────────┘
```

## Future Enhancements

- [ ] Add batch insert optimization for large scrapes
- [ ] Implement soft delete for companies
- [ ] Add full-text search on job descriptions
- [ ] Create views for common queries
- [ ] Add materialized views for analytics
- [ ] Implement job expiry/archival logic
- [ ] Add webhook notifications for new jobs
