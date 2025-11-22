# UI Design Guidelines

## Overview
The web interface should provide a clean, modern control room for monitoring and triggering the job scraper.

## Design System

### Visual Style
- **Framework**: Use Tailwind CSS or ShadCN UI components
- **Theme**: White & slate color scheme with dark mode support
- **Typography**: Clean, modern fonts (Inter, SF Pro Text, or system-ui)
- **Components**: Rounded cards, progress bars, colored status tags

### Color Palette
```css
Background: Gradient with subtle accent colors
Primary: #f59e0b (Orange/Amber)
Secondary: #6366f1 (Indigo)
Text: #e2e8f0 (Slate-200)
Cards: rgba(15, 23, 42, 0.8) with backdrop blur
Borders: #1f2937
```

## Required UI Elements

### 1. Start Crawl Button
**CRITICAL**: Must be large and prominent
```html
<button class="start-crawl-btn">
  Start Crawl
</button>
```

Styling:
- Large size (e.g., 16px font, 12px+ padding)
- Gradient background (orange to red)
- Box shadow for depth
- Disabled state when crawler is running

### 2. Live Log Viewer
Display real-time logs from the crawler with:
- Auto-scroll to bottom
- Monospace font for readability
- Color coding for log levels (info, warning, error)
- Syntax highlighting for structured log prefixes ([DOMAIN], [JOB], etc.)

Example structure:
```html
<div class="log-console">
  <pre id="log-output"></pre>
</div>
```

Features:
- WebSocket or SSE connection to `/events` endpoint
- Buffer recent logs (e.g., last 500 lines)
- Clear button
- Copy to clipboard functionality

### 3. Domain Lists
Display three separate lists:

**Queued Domains**:
- Domains waiting to be crawled
- Show count and domain names

**Completed Domains**:
- Successfully crawled domains
- Show job count for each
- Green status indicator

**Errored Domains**:
- Domains that failed
- Show error message
- Red status indicator

### 4. Job Results Table
Display extracted jobs with these columns:
- **Title**: Job title
- **Location**: City/state or "Remote"
- **URL**: Link to job posting
- **Source**: Extraction source (JSON-LD, ATS, etc.)
- **Company**: Company name
- **Score**: Role relevance score

Table features:
- Sortable columns
- Filter by company
- Export to CSV/JSON
- Pagination (if many results)

### 5. Status Indicators
Show crawler status:
- **Status Pill**: "Running" (green) / "Idle" (gray) / "Error" (red)
- **Progress Bar**: Show crawling progress
- **Metrics Cards**: 
  - Total domains processed
  - Total jobs found
  - Current crawl time
  - Success rate

## Layout Structure

```
┌─────────────────────────────────────────┐
│  Header (Title + Status Pill)          │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌─────────────────┐ │
│  │ Start Crawl  │  │  Metric Cards   │ │
│  │   Button     │  │  (Jobs, Time)   │ │
│  └──────────────┘  └─────────────────┘ │
├─────────────────────────────────────────┤
│  Live Log Viewer                        │
│  (Streaming logs with auto-scroll)     │
├─────────────────────────────────────────┤
│  Domain Lists (Queued/Complete/Error)  │
├─────────────────────────────────────────┤
│  Job Results Table                      │
│  (Title, Location, URL, Source)        │
└─────────────────────────────────────────┘
```

## Interactivity

### Start Crawl Flow
1. User clicks "Start Crawl" button
2. Button becomes disabled with "Running..." text
3. POST request to `/run` endpoint
4. Log viewer starts streaming from `/events`
5. Progress indicators update in real-time
6. Job table updates as jobs are found
7. Button re-enables when complete

### Real-time Updates
Use Server-Sent Events (SSE) for:
- Log streaming
- Job results as they're found
- Status updates
- Progress tracking

Example JavaScript:
```javascript
const eventSource = new EventSource('/events');
eventSource.onmessage = (event) => {
  const logLine = event.data;
  appendToLogConsole(logLine);
};
```

## Accessibility
- ARIA labels for all interactive elements
- Keyboard navigation support
- Screen reader friendly
- High contrast mode support
- Semantic HTML elements

## Responsive Design
- Mobile-friendly layout
- Collapsible sections on small screens
- Touch-friendly buttons (min 44x44px)
- Horizontal scroll for table on mobile

## Error Handling
- Display user-friendly error messages
- Show retry button on failures
- Log connection issues
- Graceful degradation if SSE not supported

## Best Practices
- Use semantic HTML5 elements
- Minimize JavaScript bundle size
- Progressive enhancement
- Fast initial load time
- Smooth animations (CSS transitions)
