# Supabase Integration

This project uses Supabase for persistent job storage across server restarts.

## Setup

### 1. Create Supabase Table

Run the SQL script in `supabase_schema.sql` in your Supabase SQL Editor:

1. Go to https://dlcjgctfijlnolktfmfg.supabase.co
2. Navigate to SQL Editor
3. Copy and paste the contents of `supabase_schema.sql`
4. Run the script

This will create:
- `jobs` table with all required columns
- Indexes for optimized queries
- Row Level Security (RLS) policies

### 2. Configure Environment Variables

Set these environment variables in your deployment (e.g., Render.com):

```bash
SUPABASE_URL=https://dlcjgctfijlnolktfmfg.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
# OR
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Note:** Use `SUPABASE_SERVICE_ROLE_KEY` for full access, or `SUPABASE_ANON_KEY` if using RLS policies.

### 3. Get Your Keys

1. Go to Supabase Project Settings → API
2. Copy the `anon public` key or `service_role` key
3. Add to your environment variables in Render

## Features

- **Automatic Persistence**: Jobs are automatically saved to Supabase when scraped
- **Load on Startup**: Jobs are loaded from database when the server starts
- **Query Support**: Filter jobs by domain, remote type, etc.
- **Graceful Fallback**: If Supabase is not configured, the app works in memory-only mode

## Database Schema

```sql
jobs (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    remote_type TEXT,
    url TEXT NOT NULL,
    source_page TEXT NOT NULL,
    ats TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

## Testing Locally

To test locally with Supabase:

1. Create a `.env` file:
```bash
SUPABASE_URL=https://dlcjgctfijlnolktfmfg.supabase.co
SUPABASE_ANON_KEY=your-key-here
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python -m uvicorn api_server:app --reload
```

Jobs will now persist across server restarts!
