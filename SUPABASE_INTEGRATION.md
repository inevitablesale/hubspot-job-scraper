# Supabase Integration Guide

This document describes the Supabase database integration for storing job scraping data.

## Overview

The job scraper saves all scraped data to Supabase, a PostgreSQL-based cloud database. The integration is optional - if Supabase credentials are not configured, the scraper will continue to work but won't persist data to the database.

## Database Schema

The following tables are used:

### 1. companies
Stores company information with domain-based deduplication.

### 2. jobs
Stores job postings with hash-based deduplication (SHA256 of company_id:job_title:job_url).

### 3. job_metadata
Stores additional job metadata (only when data is present).

### 4. ats_sources
Stores ATS detection information.

### 5. scrape_runs
Logs each scraping run with metrics.

### 6. job_history
Captures job snapshots for change tracking.

## Setup Instructions

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Wait for the project to be provisioned

### 2. Create Database Tables

Run the following SQL in your Supabase SQL editor:

```sql
create extension if not exists "uuid-ossp";

-- 1. Companies
create table if not exists companies (
  id          uuid primary key default uuid_generate_v4(),
  name        text,
  domain      text unique,
  source_url  text,
  logo_url    text,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- 2. Jobs
create table if not exists jobs (
  id           uuid primary key default uuid_generate_v4(),
  company_id   uuid references companies(id) on delete cascade,
  job_title    text not null,
  job_url      text not null,
  department   text,
  location     text,
  remote_type  text,
  description  text,
  posted_at    timestamptz,
  scraped_at   timestamptz default now(),
  hash         text unique,
  active       boolean default true,
  ats_provider text
);

-- 3. Job metadata
create table if not exists job_metadata (
  id              uuid primary key default uuid_generate_v4(),
  job_id          uuid references jobs(id) on delete cascade,
  seniority       text,
  employment_type text,
  salary_min      numeric,
  salary_max      numeric,
  technologies    text[],
  raw_json        jsonb,
  created_at      timestamptz default now()
);

-- 4. ATS sources
create table if not exists ats_sources (
  id          uuid primary key default uuid_generate_v4(),
  job_id      uuid references jobs(id) on delete cascade,
  provider    text,
  raw_html    text,
  detected_at timestamptz default now()
);

-- 5. Scrape runs
create table if not exists scrape_runs (
  id             uuid primary key default uuid_generate_v4(),
  started_at     timestamptz default now(),
  finished_at    timestamptz,
  total_companies int,
  total_jobs      int,
  errors         jsonb
);

-- 6. Job history
create table if not exists job_history (
  id          uuid primary key default uuid_generate_v4(),
  job_id      uuid references jobs(id) on delete cascade,
  snapshot    jsonb,
  captured_at timestamptz default now()
);
```

### 3. Configure Environment Variables

Set these in your environment:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

Once configured, the scraper will automatically save data to Supabase during scraping. No code changes required.

### Running the Scraper

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"
python main.py
```

### Optional Mode (No Database)

If Supabase credentials are not configured, the scraper will:
1. Continue scraping normally
2. Return job data as before
3. Not persist data to database

## How It Works

Minimal integration with just 3 files:

1. **supabase_client.py** - Returns None if env vars aren't set
2. **supabase_persistence.py** - All database logic isolated here
3. **scraper_engine.py** - Single call to `save_jobs_for_domain()` at end of each domain

### Data Flow

```
scrape_domain() crawls and extracts jobs
    ↓
save_jobs_for_domain() called once at the end
    ↓
get_or_create_company() - dedupe by domain
    ↓
For each job: hash check, insert if new, save metadata
```

## Deduplication

- **Companies**: by `domain` (unique constraint)
- **Jobs**: by SHA256 hash of `company_id:job_title:job_url` (unique constraint)

## Architecture

```
scraper_engine → supabase_persistence → supabase_client → Supabase
```

No services, no repositories, no factory patterns - just simple database calls.
