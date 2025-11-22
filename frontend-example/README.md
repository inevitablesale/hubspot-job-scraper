# Frontend Example - React/TypeScript Integration

This directory contains example TypeScript/React code that demonstrates how to integrate with the enhanced backend API.

## Structure

```
frontend-example/
├── src/
│   ├── api/
│   │   └── client.ts           # HTTP and SSE utilities
│   ├── types/
│   │   └── api.ts              # TypeScript type definitions
│   └── hooks/
│       ├── useCrawlSummary.ts  # Hook for dashboard status
│       ├── useCrawlerEvents.ts # Hook for real-time SSE events
│       ├── useJobs.ts          # Hook for jobs data
│       ├── useDomains.ts       # Hook for domains data
│       └── useConfig.ts        # Hook for configuration
└── README.md
```

## Usage Examples

### Dashboard Page

```typescript
import { useCrawlSummary } from "../hooks/useCrawlSummary";
import { apiPost } from "../api/client";

export function DashboardPage() {
  const { data: summary, loading } = useCrawlSummary();

  async function handleStart() {
    if (!window.confirm("Start crawl?")) return;
    await apiPost("/crawl/start");
  }

  if (loading || !summary) return <div>Loading…</div>;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Dashboard</h1>
          <p className="text-sm text-gray-500">
            System status: <span className="font-medium">{summary.state}</span>
          </p>
        </div>
        <button onClick={handleStart} className="btn-primary">
          Start Crawl
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Domains Loaded" value={summary.domains_total} />
        <StatCard title="Domains Completed" value={summary.domains_completed} />
        <StatCard title="Jobs Found" value={summary.jobs_found} />
        <StatCard title="Errors" value={summary.errors_count} />
      </div>
    </div>
  );
}
```

### Control Room Page

```typescript
import { useState } from "react";
import { useCrawlSummary } from "../hooks/useCrawlSummary";
import { useCrawlerEvents } from "../hooks/useCrawlerEvents";

export function ControlRoomPage() {
  const { data: summary } = useCrawlSummary(3000);
  const { events, logs, connected } = useCrawlerEvents();
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[2fr_3fr] gap-6 h-full">
      <section>
        <header className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Crawl Control Room</h1>
            <p className="text-sm text-gray-500">
              State: {summary?.state ?? "unknown"} · Events: {events.length}
            </p>
          </div>
          <span className={connected ? "badge-success" : "badge-error"}>
            {connected ? "Live" : "Disconnected"}
          </span>
        </header>

        <Timeline
          events={events}
          onDomainClick={(domain) => setSelectedDomain(domain)}
        />
      </section>

      <section>
        <DomainDetailPanel domain={selectedDomain} />
      </section>
    </div>
  );
}
```

### Jobs Page

```typescript
import { useState } from "react";
import { useJobs } from "../hooks/useJobs";

export function JobsPage() {
  const [search, setSearch] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const { jobs, loading } = useJobs({ q: search, remoteOnly });

  return (
    <div className="flex flex-col h-full">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Jobs Explorer</h1>
        <div className="flex gap-2">
          <input
            className="input"
            placeholder="Search title, domain..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <label>
            <input
              type="checkbox"
              checked={remoteOnly}
              onChange={(e) => setRemoteOnly(e.target.checked)}
            />
            Remote only
          </label>
        </div>
      </header>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <JobsTable jobs={jobs} />
      )}
    </div>
  );
}
```

### Config Page

```typescript
import { useConfig } from "../hooks/useConfig";

export function ConfigPage() {
  const { config, loading, updating, updateConfig } = useConfig();

  async function handleSave(newConfig: ConfigSettings) {
    try {
      await updateConfig(newConfig);
      alert("Configuration saved!");
    } catch (e) {
      alert("Failed to save configuration");
    }
  }

  if (loading || !config) return <div>Loading...</div>;

  return (
    <div>
      <h1>Configuration</h1>
      <ConfigForm
        config={config}
        onSave={handleSave}
        disabled={updating}
      />
    </div>
  );
}
```

## Integration with Existing UI

To integrate these hooks with your existing static HTML UI:

1. **Set up a React/TypeScript project** (if not already):
   ```bash
   npm create vite@latest frontend -- --template react-ts
   cd frontend
   npm install
   ```

2. **Copy the example files**:
   ```bash
   cp -r frontend-example/src/* frontend/src/
   ```

3. **Update your pages** to use the hooks instead of direct fetch calls

4. **Build and serve**:
   ```bash
   npm run build
   # The build output goes to dist/
   # Configure your backend to serve these static files
   ```

## Key Features

### Real-Time Updates
The `useCrawlerEvents` hook provides real-time updates via SSE:
- Events for timeline display
- Logs for console
- Automatic reconnection
- Connection status indicator

### Type Safety
All API responses are typed with TypeScript interfaces that match the backend Pydantic models.

### Error Handling
All hooks include error states and graceful degradation.

### Polling vs. SSE
- **Polling**: Used for `useCrawlSummary` (every 5 seconds)
- **SSE**: Used for `useCrawlerEvents` (real-time push)

Choose the right approach based on update frequency needs.

## Notes

- These are **example implementations** - adapt to your needs
- Add proper error boundaries in production
- Consider adding retry logic for failed requests
- Implement loading states and skeletons for better UX
- Add proper TypeScript configuration (tsconfig.json)

## Next Steps

1. Create UI components (Timeline, JobsTable, DomainDetailPanel)
2. Add routing (React Router or similar)
3. Implement dark/light mode toggle
4. Add screenshot viewer modal
5. Create extraction tree visualizer
6. Build ATS detector panel
