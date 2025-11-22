# UI Design Documentation

## Overview

The HubSpot Job Scraper Control Room features an operator-grade UI inspired by Linear, Vercel, Railway, Supabase, and Raycast. The design prioritizes clarity, precision, and efficiency for managing job scraping operations.

## Design Philosophy

### Core Principles

1. **Clarity**: Every element is instantly understandable with no visual noise
2. **Precision**: Crisp typography and clean separation between sections
3. **Operator-Grade**: Built for power users, not marketing
4. **Non-Blocking**: Thin shell over API endpoints, scraper only runs when triggered
5. **State Persistence**: Maintains state across page refreshes

### Visual Language

The UI feels like a developer console with:
- Generous spacing and clear hierarchy
- Consistent grid system (12-column for wide screens)
- Dark mode by default (light mode ready)
- Subtle animations (fade-ins, slide-ins)
- No playful or distracting animations

## Color System

### Dark Mode (Default)

```css
Background: #0F1115
Panels: #1A1C20
Primary Text: #F3F4F6
Secondary Text: #9CA3AF
Border: #2D3035
Accent: #3B82F6
```

### Light Mode

```css
Background: #F9FAFB
Panels: #FFFFFF
Primary Text: #111827
Secondary Text: #6B7280
Border: #E5E7EB
Accent: #2563EB
```

### Semantic Colors

```css
Success: #16A34A
Warning: #F59E0B
Error: #DC2626
```

## Typography

### Font Stack

- **Body**: Inter (Google Fonts)
- **Mono**: JetBrains Mono (for logs and code)

### Scale

```css
H1: 26px / 700
H2: 22px / 600
H3: 18px / 600
Body: 15–16px / 400
Mono (logs): JetBrains Mono, 13px
```

## Layout Structure

### Overall Layout

```
┌─────────────────────────────────────────────┐
│ Sidebar (240px)    │ Main Content          │
│                    │ (max-width: 1400px)   │
│ - System           │                        │
│   • Dashboard      │ Page Content           │
│   • Control Room   │                        │
│                    │                        │
│ - Data             │                        │
│   • Domains        │                        │
│   • Jobs           │                        │
│   • Logs           │                        │
│                    │                        │
│ - Settings         │                        │
│   • Config         │                        │
└─────────────────────────────────────────────┘
```

### Sidebar

- Fixed width: 240px
- Sticky positioning
- Three sections: SYSTEM, DATA, SETTINGS
- Active state: 4px left border + background tint
- Icons: Lucide (18px)
- Section headers: 11px uppercase

## Components

### Cards

```css
Border radius: 8px
Padding: 20–24px
Border: 1px solid var(--border-dark)
Shadow: 0 1px 3px rgba(0, 0, 0, 0.1)
```

**Variants:**
- Default: Standard card
- Stat: Metrics display (label + large value)
- Hero: Enhanced card with gradient background

### Badges

```css
Padding: 4px 10px
Font size: 12px
Border radius: 6px
Font weight: 600
```

**Colors:**
- Gray: Neutral states
- Green: Success, running
- Yellow: Warning
- Red: Error
- Blue: Info, completed

### Buttons

```css
Padding: 10px 18px
Font size: 15px
Border radius: 6px
Font weight: 600
```

**Variants:**
- Primary: Blue background, white text
- Secondary: Transparent with border
- Danger: Red background, white text

### Tables

```css
Sticky headers: position: sticky; top: 0
Row hover: background: rgba(255, 255, 255, 0.03)
Cell padding: 14px 16px
Header font: 13px uppercase
```

### Timeline

Vertical timeline with:
- 2px connecting line
- 12px dot indicators
- Event cards with domain, status badge, timestamp, notes
- Smooth fade-in animations for new events

### Log Console

```css
Background: #0b0e14
Font: JetBrains Mono, 13px
Line height: 1.6
Height: 500px
Overflow: auto
```

**Color coding:**
- Info: #9CA3AF (gray)
- Warning: #FCD34D (yellow)
- Error: #F87171 (red)
- Domain events: #60A5FA (blue)

### Modal

```css
Centered overlay
Max width: 500px
Background: rgba(0, 0, 0, 0.7) backdrop
Border radius: 12px
Padding: 32px
```

### Drawer

```css
Fixed right: -500px (hidden)
Width: 500px
Height: 100vh
Transition: right 0.3s ease
Overflow-y: auto
```

## Pages

### A. Dashboard

**Purpose**: System overview and quick actions

**Layout:**
- Hero status bar (system status, last run timestamp)
- Primary CTAs (Start Crawl, View Control Room)
- 4-column stats grid:
  - Domains Loaded
  - Career Pages Found
  - Jobs Extracted
  - Errors

### B. Crawl Control Room

**Purpose**: Live monitoring and debugging

**Layout:**
```
┌──────────────┬─────────────────────────────┐
│ Timeline     │ Detail Panel                │
│ (scrollable) │ - Tabs: Overview, Extraction│
│              │ - Domain info               │
│              │ - Status, notes             │
└──────────────┴─────────────────────────────┘
```

**Timeline:**
- Vertical events list
- Each domain = one card
- Contains: domain, status badge, timestamp, note
- Auto-updates during crawl

**Detail Panel Tabs:**
- Overview: Domain, career page URL, ATS provider, pages visited
- Extraction Notes: Patterns matched, nodes skipped, heuristics

### C. Logs

**Purpose**: Real-time system logs

**Features:**
- Terminal-like dark console
- Auto-scroll toggle
- Jump to latest button
- Download logs button
- Filter checkboxes (future)
- Color-coded by level

### D. Jobs

**Purpose**: Browse and search extracted jobs

**Layout:**
- Search bar (full-width)
- Data table with columns:
  - Job Title
  - Domain
  - Location
  - Type (Remote/Hybrid/Office)
  - Actions (View button)
- Right-side drawer for job details

**Drawer tabs:**
- Full Text
- Raw HTML
- Classifications
- Metadata

### E. Domains

**Purpose**: Manage and monitor domains

**Table columns:**
- Domain
- Category
- Status
- Last Scraped
- Actions

**Future:** Click domain for detail page showing:
- Screenshot
- Detected menus
- Career page candidates
- Chosen path + reason
- Fallback attempts

### F. Config

**Purpose**: System settings and filters

**Sections:**
- Role Filters:
  - Allowed roles (comma-separated input)
  - Remote-only toggle
- Crawl Settings:
  - Max depth (slider/number)
  - Max pages per domain (slider/number)
  - Request timeout (future)
  - Concurrency (future)
- ATS Patterns: Read-only list (future)

## Motion & Animation

### Guidelines

- Extremely subtle, no playful animations
- Fade-ins for new content
- Slide-ins for drawers and modals
- Timeline expansion
- No distractions from work

### Transitions

```css
Standard: 0.15s ease
Drawer: 0.3s ease
Pulse animation: 2s infinite
```

## Navigation

### Top-level

- Sidebar navigation (6 pages)
- Mobile: Collapsible sidebar
- Active state: Left border + background tint
- Smooth page transitions

### URL Structure (Future)

```
/
/control-room
/domains
/jobs
/logs
/config
```

## Branding

- No large logos
- No hero illustrations
- Strictly functional
- Small wordmark in sidebar: "HUBSPOT SCRAPER CONTROL ROOM" (12px uppercase)

## Responsive Design

### Desktop (> 768px)

- Full sidebar (240px)
- Multi-column grids (2, 3, 4 columns)
- Max content width: 1400px

### Mobile (≤ 768px)

- Collapsible sidebar
- Single column grids
- Full-width components
- Touch-friendly buttons (min 44px)

## API Integration

### Endpoints

```
GET  /                 → Serve UI
GET  /status           → Crawler status
POST /start            → Start crawl
GET  /logs?lines=100   → Recent logs
GET  /jobs             → Job results
GET  /domains          → Domain list
GET  /health           → Health check
```

### Polling Strategy

```javascript
Status: Every 3 seconds
Logs: Every 2 seconds (when on logs page)
Jobs: Every 5 seconds
```

### State Persistence

- Use localStorage for UI preferences (auto-scroll, filters)
- Backend `/status` endpoint for true crawl state
- Refresh-safe: State survives page reloads

## Security

### XSS Protection

```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

### URL Validation

```javascript
function isValidUrl(url) {
    try {
        const parsed = new URL(url);
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
        return false;
    }
}
```

### Best Practices

- Always escape user-provided content
- Validate URLs before rendering links
- Use `rel="noopener noreferrer"` for external links
- No inline event handlers in user content
- Sanitize all API responses

## Accessibility

### ARIA

- Use semantic HTML
- Add ARIA labels to icon-only buttons
- Ensure keyboard navigation works
- Focus visible on interactive elements

### Contrast

- WCAG AA compliant color contrast
- Dark mode: White text (#F3F4F6) on dark bg (#0F1115) = 14.7:1
- Button text always readable

## Performance

### Optimization

- Minimal DOM updates
- Debounced search (300ms)
- Virtual scrolling for long lists (future)
- Lazy load images (future)
- Code splitting (future)

### Bundle Size

Current: Single HTML file with inline CSS/JS (~60KB)
Future: Modular components, CSS modules, tree-shaking

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile: iOS Safari, Chrome Android

## Future Enhancements

### Phase 2

- [ ] Light mode toggle
- [ ] SSE streaming integration
- [ ] Real-time notifications (toast)
- [ ] Keyboard shortcuts (? for help)
- [ ] Export to CSV/JSON

### Phase 3

- [ ] Screenshot viewer modal
- [ ] Extraction tree visualizer
- [ ] ATS detector panel with API endpoint details
- [ ] Domain detail pages
- [ ] Advanced filtering (multi-select, date range)

### Phase 4

- [ ] User preferences persistence
- [ ] Saved filters/presets
- [ ] Crawl scheduling
- [ ] Email notifications
- [ ] Webhook configuration

## File Structure

```
static/
├── control-room.html      # Main UI (current)
└── index.html             # Legacy UI (fallback)

frontend/
├── components/
│   ├── Badge.js
│   ├── Button.js
│   ├── Card.js
│   ├── LogConsole.js
│   ├── Table.js
│   └── Timeline.js
├── pages/              # Future page-specific logic
├── styles/             # Future modular CSS
└── README.md
```

## Implementation Notes

### Current State

- Single-page application (SPA)
- Vanilla JavaScript (no framework)
- Inline CSS (design tokens as CSS variables)
- Lucide icons via CDN
- Inter & JetBrains Mono via Google Fonts

### Technology Stack

**Current:**
- HTML5 + CSS3
- Vanilla JavaScript (ES6+)
- Lucide Icons
- Google Fonts

**Future Options:**
- React/Next.js
- HTMX
- SvelteKit
- Tailwind CSS (already in old index.html)

### Decision Rationale

Vanilla JavaScript chosen for:
- Zero build step
- Minimal dependencies
- Fast initial load
- Easy to understand and modify
- Framework-agnostic (can migrate later)

## Testing Checklist

- [ ] All pages render correctly
- [ ] Navigation works between pages
- [ ] API integration functional
- [ ] Logs stream in real-time
- [ ] Jobs table displays data
- [ ] Modals and drawers open/close
- [ ] Buttons disabled during running state
- [ ] XSS protection verified
- [ ] URL validation working
- [ ] Responsive on mobile
- [ ] Icons render (Lucide)
- [ ] Fonts load (Inter, JetBrains Mono)

## Deployment

### Render

The UI is served by the FastAPI control room server:

```yaml
# render.yaml
services:
  - type: web
    runtime: docker
    dockerCommand: uvicorn control_room:app --host 0.0.0.0 --port $PORT
```

### Docker

```dockerfile
# Dockerfile includes static files
COPY static /app/static
```

### Local Development

```bash
uvicorn control_room:app --host 0.0.0.0 --port 8000 --reload
```

Open: http://localhost:8000/

## Changelog

### v1.0.0 (Current)

- ✅ Created operator-grade UI
- ✅ Implemented 6 pages (Dashboard, Control Room, Logs, Jobs, Domains, Config)
- ✅ Built component library (Cards, Badges, Buttons, Tables, Timeline, Log Console)
- ✅ Integrated Lucide icons
- ✅ Set up Inter + JetBrains Mono fonts
- ✅ Implemented dark mode color scheme
- ✅ Added responsive grid layouts
- ✅ Created sidebar navigation
- ✅ Integrated with backend API
- ✅ Added modals and drawers
- ✅ Implemented XSS protection

### Planned v1.1.0

- [ ] Light mode toggle
- [ ] SSE streaming
- [ ] Toast notifications
- [ ] Advanced filtering
- [ ] Keyboard shortcuts
