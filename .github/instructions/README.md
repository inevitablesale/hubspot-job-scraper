# 🧠 Global Copilot Coding Agent Instructions

These are repository-wide instructions for GitHub Copilot's coding agent.  
They define architecture, conventions, coding patterns, and expectations for all changes in this project.

---

## 📦 Project Overview

This repository contains a **full-stack job-scraping platform** built with:

- **Python 3.11+**
- **Playwright (async)**
- **FastAPI** for the Control Room UI
- **Tailwind + HTMX** on the frontend
- **Docker (Playwright base image)** for deployment on Render
- **Scraper Engine** (`scraper_engine.py`) that:
  - Identifies career pages
  - Extracts job roles across ATS, custom pages, or static HTML
  - Uses heuristics + DOM pattern detection
  - Streams logs in real time

---

## 🧱 Architecture Summary

```
/server.py → FastAPI web UI
/main.py → CLI entry (headless scraping)
/scraper_engine.py → Main scraping engine (Playwright)
/utils/ → shared helper modules
/templates/ → HTML UI (Jinja2)
/static/ → JS/CSS assets
/.github/ → Copilot instructions + workflows
/Dockerfile → Playwright-enabled container
/render.yaml → Render infrastructure config
```

---

## 🚦 Coding Standards

### 1. Use async/await everywhere
- **Never use blocking calls** inside scraper logic.
- All browser operations: `await page.goto()`, `await browser.new_page()`, etc.

### 2. Logging rules
- Use Python `logging` module, not `print()`.
- Scraper logs **must** include:
  - Domain being visited
  - Candidate career links found
  - Final chosen link
  - Extracted job titles
  - Errors or fallbacks taken

### 3. Error handling
Follow this structure:

```python
try:
    ...
except PlaywrightTimeoutError:
    logger.warning("Timeout on %s", url)
except Exception as e:
    logger.error("Unexpected error on %s: %s", url, e)
```

### 4. Naming conventions
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Files: `lower_snake_case.py`

### 5. File Organization
- UI logic never touches scraper engine functions.
- Scraper engine must remain headless-compatible.

---

## 📝 Issue Requirements

Every issue given to Copilot must include:

✔ **Description**  
What the change should accomplish.

✔ **Acceptance Criteria**  
Bullet list verifying when done.

✔ **Affected Paths**  
Tell the agent where changes belong.

✔ **Avoid**  
Stating _how_ to fix — focus on the goal.

**Example:**

```
Description:
Add LinkedIn ATS detection.

Acceptance Criteria:
- Detect embedded LinkedIn job widgets.
- Extract job titles & detail URLs.
- Include them in final job list.

Affected Paths:
- scraper_engine.py
- utils/ats_detectors.py
```

---

## 🔁 Build, Test & Run

### Local (non-Docker)
```bash
pip install -r requirements.txt
playwright install chromium
DOMAINS_FILE=domains.json python main.py
```

### Local (Docker)
```bash
docker build -t scraper .
docker run scraper
```

### Render
Render uses:
- `Dockerfile`
- `render.yaml`

**Never modify Render build commands in the UI.**

---

## 🌐 Scope Rules for the Copilot Agent

### Allowed
- Modify Python code
- Add new detectors / heuristics
- Improve UI
- Improve Dockerfile
- Add new endpoints
- Refactor scraper engine

### Avoid
- Adding unrelated libraries
- Changing core architecture
- Introducing blocking (non-async) scraping logic
- Modifying Playwright base image without reason

---

## 📁 Path-Specific Rules

Additional rules exist in:
- `/.github/instructions/scraper.instructions.md`
- `/.github/instructions/ui.instructions.md`
- `/.github/instructions/docker.instructions.md`
- `/.github/instructions/tests.instructions.md`

Copilot should follow those for specialized changes.
