# Production-Grade Frontend for HubSpot Job Scraper

This directory contains production-ready TypeScript/React code for integrating with the backend API.

## 📁 Structure

```
frontend/
├── api/
│   └── client.ts           # HTTP client with retry, timeout, SSE support
├── types/
│   └── api.ts              # TypeScript type definitions
├── hooks/
│   ├── index.ts            # Export all hooks
│   ├── useCrawlSummary.ts  # Crawl status polling
│   ├── useCrawlerEvents.ts # Real-time SSE events
│   ├── useJobs.ts          # Jobs data with filtering & debouncing
│   ├── useDomains.ts       # Domains list
│   ├── useDomainDetail.ts  # Single domain with flow & screenshots
│   ├── useConfig.ts        # Configuration with optimistic updates
│   ├── useCrawlControl.ts  # Start/stop crawl actions
│   └── useLogs.ts          # Log history with export
└── components/             # UI components (existing)
```

## 🚀 Features

### API Client (`api/client.ts`)

**Production Features:**
- ✅ **Retry logic** with exponential backoff
- ✅ **Timeout handling** (configurable per request)
- ✅ **Request cancellation** via AbortController
- ✅ **Error handling** with custom APIError class
- ✅ **SSE auto-reconnect** with exponential backoff
- ✅ **Type safety** throughout

```typescript
import { apiGet, apiPost, createSSEClient } from './api/client';

// Simple GET request
const data = await apiGet<JobItem[]>('/jobs');

// With custom timeout and retries
const data = await apiGet<JobItem[]>('/jobs', {
  timeout: 10000,
  retries: 3,
  retryDelay: 1000
});

// SSE with auto-reconnect
const client = createSSEClient('/events/stream', {
  onConnected: () => console.log('Connected'),
  onDisconnected: () => console.log('Disconnected'),
});
client.on('event', (data) => console.log(data));
client.connect();
```

### Hooks

#### 1. `useCrawlSummary` - Dashboard Status

**Features:**
- Automatic polling (configurable interval)
- Request deduplication
- Manual refetch
- Cleanup on unmount

```typescript
function Dashboard() {
  const { data, loading, error, refetch } = useCrawlSummary({
    pollInterval: 5000,  // Poll every 5 seconds
    enabled: true,
    onError: (err) => console.error(err)
  });

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>State: {data?.state}</h1>
      <p>Jobs: {data?.jobs_found}</p>
      <button onClick={refetch}>Refresh</button>
    </div>
  );
}
```

#### 2. `useCrawlerEvents` - Real-Time Updates

**Features:**
- SSE connection management
- Auto-reconnect on disconnect
- Separate event and log streams
- Buffer size limiting
- Connection state tracking

```typescript
function ControlRoom() {
  const { events, logs, connected, clearEvents } = useCrawlerEvents({
    maxEvents: 500,
    maxLogs: 1000,
    onConnected: () => console.log('Live'),
    onDisconnected: () => console.log('Offline'),
  });

  return (
    <div>
      <div>Status: {connected ? 'Connected' : 'Disconnected'}</div>
      <Timeline events={events} />
      <LogConsole logs={logs} />
    </div>
  );
}
```

#### 3. `useJobs` - Jobs with Search

**Features:**
- Debounced search queries
- Multiple filters (query, domain, remote-only)
- Request cancellation
- Manual refetch

```typescript
function JobsPage() {
  const [search, setSearch] = useState('');
  const [remoteOnly, setRemoteOnly] = useState(false);

  const { jobs, loading, error } = useJobs({
    q: search,
    remoteOnly,
    debounceMs: 300,  // Debounce search for 300ms
  });

  return (
    <div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search jobs..."
      />
      <label>
        <input
          type="checkbox"
          checked={remoteOnly}
          onChange={(e) => setRemoteOnly(e.target.checked)}
        />
        Remote only
      </label>
      {loading ? <Spinner /> : <JobsTable jobs={jobs} />}
    </div>
  );
}
```

#### 4. `useDomains` - Domains List

**Features:**
- Automatic fetching
- Request cancellation
- Manual refetch

```typescript
function DomainsPage() {
  const { domains, loading, refetch } = useDomains();

  return (
    <div>
      <button onClick={refetch}>Refresh</button>
      {domains.map(d => (
        <DomainCard key={d.domain} domain={d} />
      ))}
    </div>
  );
}
```

#### 5. `useDomainDetail` - Single Domain Details

**Features:**
- Fetch domain info, navigation flow, and screenshots in parallel
- Configurable data inclusion
- Request cancellation
- Manual refetch

```typescript
function DomainDetailPanel({ domain }: { domain: string | null }) {
  const {
    domainInfo,
    navigationFlow,
    screenshots,
    loading
  } = useDomainDetail({
    domain,
    includeFlow: true,
    includeScreenshots: true,
  });

  if (!domain) return <div>Select a domain</div>;
  if (loading) return <Spinner />;

  return (
    <div>
      <h2>{domainInfo?.domain}</h2>
      <p>Jobs: {domainInfo?.jobs_count}</p>
      <NavigationFlow steps={navigationFlow} />
      <Screenshots items={screenshots} />
    </div>
  );
}
```

#### 6. `useConfig` - Configuration

**Features:**
- Automatic config loading
- Optimistic updates
- Rollback on error
- Manual refetch

```typescript
function ConfigPage() {
  const { config, loading, updating, updateConfig } = useConfig({
    onUpdate: () => alert('Config saved!'),
  });

  async function handleSave(newConfig: ConfigSettings) {
    try {
      await updateConfig(newConfig);
    } catch (err) {
      // Error is already handled by hook
      // UI shows error state
    }
  }

  if (loading) return <Spinner />;

  return (
    <ConfigForm
      config={config!}
      onSave={handleSave}
      saving={updating}
    />
  );
}
```

#### 7. `useCrawlControl` - Start/Stop Actions

**Features:**
- Loading states for actions
- Error handling
- Callbacks for success/error

```typescript
function CrawlControls() {
  const summary = useCrawlSummary();
  const { starting, stopping, startCrawl, stopCrawl } = useCrawlControl({
    onStart: () => console.log('Started!'),
    onStop: () => console.log('Stopped!'),
  });

  const canStart = summary.data?.state === 'idle';
  const canStop = summary.data?.state === 'running';

  return (
    <div>
      <button
        onClick={() => startCrawl()}
        disabled={!canStart || starting}
      >
        {starting ? 'Starting...' : 'Start Crawl'}
      </button>
      <button
        onClick={stopCrawl}
        disabled={!canStop || stopping}
      >
        {stopping ? 'Stopping...' : 'Stop Crawl'}
      </button>
    </div>
  );
}
```

#### 8. `useLogs` - Log History

**Features:**
- Initial log fetch
- Log level filtering
- Domain filtering
- Export to file

```typescript
function LogsPage() {
  const { filteredLogs, loading, exportLogs } = useLogs({
    initialLimit: 500,
    filterLevel: 'error',  // Only show errors
  });

  return (
    <div>
      <button onClick={exportLogs}>Export Logs</button>
      <LogConsole logs={filteredLogs} />
    </div>
  );
}
```

## 🎯 Best Practices

### Error Handling

All hooks provide error states and optional error callbacks:

```typescript
const { data, error } = useJobs({
  onError: (error) => {
    // Global error handler
    toast.error(error.message);
    logToService(error);
  }
});

// Or handle in component
if (error) {
  return <ErrorBoundary error={error} />;
}
```

### Loading States

All hooks provide loading states:

```typescript
const { data, loading } = useCrawlSummary();

if (loading) {
  return <Skeleton />;  // Or spinner, placeholder, etc.
}
```

### Request Cancellation

All hooks automatically cancel requests on unmount or when dependencies change:

```typescript
// No manual cleanup needed!
const { jobs } = useJobs({ q: search });

// When search changes, previous request is automatically cancelled
```

### Conditional Fetching

All hooks support conditional fetching:

```typescript
const { data } = useJobs({
  enabled: isAuthenticated,  // Only fetch when authenticated
});
```

## 📦 TypeScript Support

All types are fully exported:

```typescript
import type {
  CrawlSummary,
  JobItem,
  DomainItem,
  ConfigSettings,
  // ...
} from './types/api';

import type {
  UseJobsOptions,
  UseJobsResult,
  // ...
} from './hooks';
```

## 🔒 Security

- All requests go through the centralized `apiClient`
- CORS handled by backend
- No credentials stored in frontend
- XSS protection via React
- Input sanitization in components

## ⚡ Performance

- **Request deduplication** - Prevents duplicate simultaneous requests
- **Debouncing** - Search queries debounced automatically
- **Buffer limiting** - Events and logs auto-trim to prevent memory leaks
- **Request cancellation** - Old requests cancelled on new deps
- **Optimistic updates** - Config updates show immediately

## 🧪 Testing

Example test for a hook:

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useJobs } from './hooks/useJobs';

test('fetches jobs', async () => {
  const { result } = renderHook(() => useJobs());

  expect(result.current.loading).toBe(true);

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.jobs).toHaveLength(10);
});
```

## 📝 Integration Example

Complete page example:

```typescript
import {
  useCrawlSummary,
  useCrawlerEvents,
  useCrawlControl,
} from './hooks';

export function ControlRoomPage() {
  const summary = useCrawlSummary({ pollInterval: 3000 });
  const { events, logs, connected } = useCrawlerEvents();
  const { startCrawl, stopCrawl, starting } = useCrawlControl();

  return (
    <div className="control-room">
      <header>
        <h1>Control Room</h1>
        <div className="status">
          State: {summary.data?.state}
          {connected && <Badge>Live</Badge>}
        </div>
        <div className="actions">
          {summary.data?.state === 'idle' && (
            <button onClick={() => startCrawl()} disabled={starting}>
              Start Crawl
            </button>
          )}
          {summary.data?.state === 'running' && (
            <button onClick={stopCrawl}>Stop</button>
          )}
        </div>
      </header>

      <main>
        <Timeline events={events} />
        <LogConsole logs={logs} />
      </main>
    </div>
  );
}
```

## 🚢 Deployment

These hooks are framework-agnostic and work with:
- ✅ React
- ✅ Next.js
- ✅ Remix
- ✅ Vite
- ✅ Create React App

No special configuration needed - just import and use!

## 📄 License

Same as main project.
