# Frontend Component Library

This directory contains the reusable UI components for the HubSpot Job Scraper Control Room.

## Design System

### Color Palette

**Dark Mode (Default)**
- Background: `#0F1115`
- Panels: `#1A1C20`
- Primary Text: `#F3F4F6`
- Secondary Text: `#9CA3AF`
- Border: `#2D3035`
- Accent: `#3B82F6`

**Light Mode**
- Background: `#F9FAFB`
- Panels: `#FFFFFF`
- Primary Text: `#111827`
- Secondary Text: `#6B7280`
- Border: `#E5E7EB`
- Accent: `#2563EB`

**Semantic Colors**
- Success: `#16A34A`
- Warning: `#F59E0B`
- Error: `#DC2626`

### Typography

- **Font Family**: Inter (body), JetBrains Mono (code)
- **H1**: 26px / 700
- **H2**: 22px / 600
- **H3**: 18px / 600
- **Body**: 15-16px / 400
- **Mono (logs)**: JetBrains Mono, 13px

### Spacing

- **Grid Gap**: 20px
- **Card Padding**: 20-24px
- **Border Radius**: 8-10px
- **Button Padding**: 10px 18px

## Components

### Card
Versatile card component with variants.

```javascript
import { Card } from './components/Card.js';

// Default card
const card = new Card();
card.render('Content here');

// Stat card
Card.stat('Jobs Found', '42', 'default');
```

### Badge
Small pill-shaped badges for status indicators.

```javascript
import { Badge } from './components/Badge.js';

Badge.render('Active', 'green', 'check');
Badge.status('running'); // Auto-styled based on state
```

### Button
Buttons with primary, secondary, and danger variants.

```javascript
import { Button } from './components/Button.js';

Button.primary('Start Crawl', 'play', { onClick: 'startCrawl()' });
Button.secondary('Cancel', 'x');
Button.danger('Delete', 'trash-2');
```

### Timeline
Vertical timeline for displaying events.

```javascript
import { Timeline } from './components/Timeline.js';

const timeline = new Timeline('timeline-container');
timeline.addEvent({
    domain: 'example.com',
    status: 'Extracting',
    statusColor: 'blue',
    note: 'Found JSON-LD',
    timestamp: new Date()
});
```

### Table
Data table with sorting and sticky headers.

```javascript
import { Table } from './components/Table.js';

const table = new Table('table-container', {
    columns: [
        { key: 'title', label: 'Job Title' },
        { key: 'company', label: 'Company' },
        { 
            key: 'actions', 
            label: 'Actions',
            render: (val, row) => `<button onclick="viewJob('${row.id}')">View</button>`
        }
    ],
    data: jobs
});
```

### LogConsole
Terminal-like log viewer.

```javascript
import { LogConsole } from './components/LogConsole.js';

const console = new LogConsole('log-container', {
    autoScroll: true,
    maxLines: 1000
});

console.addLog({
    timestamp: new Date(),
    level: 'INFO',
    message: 'Crawl started'
});

console.download(); // Download logs as .txt
```

## Pages

### Dashboard
- System status overview
- Quick stats cards
- Primary actions (Start Crawl, View Control Room)

### Crawl Control Room
- Live timeline of domain processing
- Detail panel with tabs (Overview, Extraction Notes)
- Real-time event streaming

### Logs
- Terminal-like log console
- Auto-scroll toggle
- Download logs
- Color-coded by level (info, warning, error, domain)

### Jobs
- Search and filter
- Data table with job listings
- Drawer panel for job details

### Domains
- Domain list table
- Status indicators
- Last scraped timestamp

### Config
- Role filters
- Remote-only toggle
- Crawl settings (max depth, max pages)
- Save configuration

## Icons

Using [Lucide Icons](https://lucide.dev/):
- `layout-dashboard` - Dashboard
- `radio` - Crawler Control
- `globe` - Domains
- `briefcase` - Jobs
- `terminal` - Logs
- `settings` - Config
- `play` - Start
- `square` - Stop
- `download` - Download
- `eye` - View

## Navigation

Sidebar navigation with sections:
- **SYSTEM**: Dashboard, Crawler Control
- **DATA**: Domains, Jobs, Logs
- **SETTINGS**: Config

Page navigation handled via JavaScript:
```javascript
function navigateTo(page) {
    // Hide all pages
    // Show selected page
    // Update nav active state
}
```

## State Management

Global state object:
```javascript
let state = {
    currentPage: 'dashboard',
    crawlerStatus: 'idle',
    autoScroll: true,
    logs: [],
    jobs: []
};
```

## API Integration

All pages integrate with backend endpoints:
- `GET /status` - Crawler status
- `POST /start` - Start crawl
- `GET /logs?lines=100` - Recent logs
- `GET /jobs` - Job results

Polling intervals:
- Status: Every 3 seconds
- Logs: Every 2 seconds (when on logs page)
- Jobs: Every 5 seconds

## Responsive Design

Mobile-first responsive breakpoints:
- Desktop: Full sidebar navigation
- Mobile: Collapsible sidebar, single-column grids

## Best Practices

1. **XSS Protection**: Always escape user-provided content
2. **URL Validation**: Validate URLs before rendering links
3. **No Auto-Run**: Scraper only runs when explicitly triggered
4. **Refresh-Safe**: State persists across page refreshes via localStorage + backend
5. **Error Handling**: Graceful degradation with user-friendly error messages
6. **Accessibility**: Semantic HTML, ARIA labels where needed
7. **Performance**: Efficient DOM updates, debounced search

## File Structure

```
frontend/
├── components/
│   ├── Badge.js
│   ├── Button.js
│   ├── Card.js
│   ├── LogConsole.js
│   ├── Table.js
│   └── Timeline.js
├── pages/
│   └── (future page-specific logic)
├── styles/
│   └── (future modular CSS)
└── README.md
```

## Future Enhancements

- [ ] Light mode toggle
- [ ] SSE streaming integration
- [ ] Screenshot viewer modal
- [ ] Extraction tree visualizer
- [ ] ATS detector panel
- [ ] Domain detail pages
- [ ] Advanced filtering and search
- [ ] Export to CSV/JSON
- [ ] Keyboard shortcuts
- [ ] Toast notifications
