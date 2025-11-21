import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .utils import normalize_domain


class LogBroker:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []

    async def register(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    async def unregister(self, queue: asyncio.Queue):
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def publish(self, message: Dict):
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except Exception:
                continue


class CrawlerState:
    def __init__(self):
        self.running: bool = False
        self.status: str = "idle"
        self.last_run: Optional[str] = None
        self.jobs: List[Dict] = []
        self.logs: List[Dict] = []
        self.history: List[Dict] = []
        self.company_progress: Dict[str, Dict] = {}
        self.total_companies: int = 0
        self.processed_companies: int = 0
        self.high_priority: int = 0
        self.remote_us_matches: int = 0
        self.log_broker = LogBroker()
        self._max_logs = 500

    def start_run(self, companies: List[Dict[str, str]]):
        self.running = True
        self.status = "running"
        self.last_run = datetime.utcnow().isoformat() + "Z"
        self.jobs = []
        self.logs = []
        self.company_progress = {
            c.get("company", c.get("url", "")): {
                "status": "pending",
                "url": c.get("url"),
                "jobs": 0,
                "last_scan": None,
            }
            for c in companies
        }
        self.total_companies = len(companies)
        self.processed_companies = 0
        self.high_priority = 0
        self.remote_us_matches = 0

    def finish_run(self, delivered: int):
        self.running = False
        self.status = "idle"
        self.history.append(
            {
                "time": self.last_run,
                "delivered": delivered,
                "companies": self.total_companies,
            }
        )
        self.history = self.history[-10:]

    def add_log(self, level: str, message: str):
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "message": message,
        }
        self.logs.append(entry)
        self.logs = self.logs[-self._max_logs :]
        self.log_broker.publish(entry)

    def add_job(self, job: Dict):
        job["ts"] = datetime.utcnow().isoformat() + "Z"
        self.jobs.append(job)
        if job.get("score", 0) >= 80:
            self.high_priority += 1
        if job.get("remote"):
            self.remote_us_matches += 1

    def mark_company_status(self, company: str, status: str, jobs: int = 0):
        if company in self.company_progress:
            self.company_progress[company]["status"] = status
            self.company_progress[company]["last_scan"] = datetime.utcnow().isoformat() + "Z"
            self.company_progress[company]["jobs"] += jobs
        if status == "done":
            self.processed_companies += 1

    def snapshot(self) -> Dict:
        return {
            "running": self.running,
            "status": self.status,
            "last_run": self.last_run,
            "total_companies": self.total_companies,
            "processed_companies": self.processed_companies,
            "jobs_found": len(self.jobs),
            "high_priority": self.high_priority,
            "remote_us": self.remote_us_matches,
            "history": list(reversed(self.history[-10:])),
        }

    def coverage(self) -> List[Dict]:
        return [
            {
                "company": company,
                **data,
            }
            for company, data in self.company_progress.items()
        ]

    def recent_logs(self) -> List[Dict]:
        return list(self.logs)

    def results(self) -> List[Dict]:
        return list(self.jobs)


def get_state() -> CrawlerState:
    global _STATE
    try:
        return _STATE
    except NameError:
        _STATE = CrawlerState()
        return _STATE


class DomainRegistry:
    """Lightweight domain registry backed by the DOMAINS_FILE JSON.

    The registry normalizes existing datasets once, then provides helpers to add,
    update, and remove domains while keeping backward compatibility with the
    crawler's expected list-of-dicts format.
    """

    def __init__(self, dataset_env: str = "DOMAINS_FILE", stamp: Path = Path("/data/.domains_initialized")):
        self.dataset_env = dataset_env
        self.dataset_path = Path(os.getenv(dataset_env) or "/etc/secrets/DOMAINS_FILE")

        # Choose a writable storage target. If the primary dataset path is read-only
        # (e.g., Render secrets mount), fall back to a runtime copy under /data or
        # a caller-provided DOMAINS_WRITE_PATH.
        self.storage_path = Path(
            os.getenv("DOMAINS_WRITE_PATH")
            or ("/data/domains_runtime.json" if not self._is_writable(self.dataset_path) else str(self.dataset_path))
        )

        self.events_path = Path(
            os.getenv("DOMAIN_EVENTS_FILE")
            or f"{self.storage_path}.events.json"
        )
        self.stamp = stamp
        self._lock = asyncio.Lock()
        self._cache: List[Dict] = []
        self._events: List[Dict] = []
        self._load_and_normalize()

    def _is_writable(self, path: Path) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a"):
                pass
            return True
        except Exception:
            return False

    def _load_raw(self) -> List[Dict]:
        # Prefer the source dataset (secrets or configured path). If it is missing,
        # fall back to the writable storage copy if present.
        candidates = [self.dataset_path]
        if self.storage_path not in candidates:
            candidates.append(self.storage_path)

        for path in candidates:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text())
                if isinstance(data, list):
                    return data
            except Exception:
                continue
        return []

    def _load_and_normalize(self):
        raw = self._load_raw()
        normalized: List[Dict] = []
        for entry in raw:
            if isinstance(entry, str):
                domain = normalize_domain(entry)
                if domain:
                    normalized.append(
                        {
                            "domain": domain,
                            "company": entry,
                            "categoryName": None,
                            "source": "seed",
                            "score": 100,
                            "hubspot": None,
                            "last_seen": None,
                            "failures": 0,
                        }
                    )
            elif isinstance(entry, dict):
                website = entry.get("website") or entry.get("url") or entry.get("domain")
                domain = normalize_domain(website) if website else None
                if not domain:
                    continue
                normalized.append(
                    {
                        "domain": domain,
                        "company": entry.get("title") or entry.get("company") or domain,
                        "categoryName": entry.get("categoryName"),
                        "source": entry.get("source") or "seed",
                        "score": entry.get("score") or 100,
                        "hubspot": entry.get("hubspot"),
                        "last_seen": entry.get("last_seen"),
                        "failures": entry.get("failures", 0),
                        "signals": entry.get("signals", []),
                    }
                )
        self._cache = normalized
        self._events = self._load_events()
        self._write()
        if not self.stamp.exists():
            try:
                self.stamp.parent.mkdir(parents=True, exist_ok=True)
                self.stamp.write_text(datetime.utcnow().isoformat())
            except Exception:
                pass

    def _write(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(self._cache, indent=2))
        except Exception:
            # Storage may be read-only; fail silently to avoid crashing the app.
            pass
        self._write_events()

    def _write_events(self):
        try:
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            self.events_path.write_text(json.dumps(self._events[-500:], indent=2))
        except Exception:
            pass

    def _load_events(self) -> List[Dict]:
        if not self.events_path.exists():
            return []
        try:
            data = json.loads(self.events_path.read_text())
            if isinstance(data, list):
                return data
        except Exception:
            return []
        return []

    def _record_event(self, event_type: str, domain: str):
        event = {"type": event_type, "domain": domain, "ts": datetime.utcnow().isoformat() + "Z"}
        self._events.append(event)
        self._write_events()

    async def add_candidate(self, candidate: Dict, source: str = "maps"):
        domain = normalize_domain(candidate.get("domain") or candidate.get("raw_website"))
        if not domain:
            return False
        if candidate.get("score", 0) < 80:
            return False
        async with self._lock:
            existing = next((c for c in self._cache if c.get("domain") == domain), None)
            if existing:
                existing["score"] = max(existing.get("score", 0), candidate.get("score", 0))
                existing["last_seen"] = datetime.utcnow().isoformat() + "Z"
                existing["signals"] = sorted(set((existing.get("signals") or []) + candidate.get("signals", [])))
                if candidate.get("hubspot"):
                    existing["hubspot"] = candidate["hubspot"]
            else:
                self._cache.append(
                    {
                        "domain": domain,
                        "company": candidate.get("company") or candidate.get("title") or domain,
                        "categoryName": candidate.get("categoryName"),
                        "source": source,
                        "score": candidate.get("score", 0),
                        "hubspot": candidate.get("hubspot"),
                        "signals": candidate.get("signals", []),
                        "maps_url": candidate.get("maps_url"),
                        "last_seen": datetime.utcnow().isoformat() + "Z",
                        "failures": 0,
                    }
                )
                self._record_event("added", domain)
            self._write()
        return True

    async def mark_failure(self, domain: str):
        async with self._lock:
            for entry in self._cache:
                if entry.get("domain") == domain:
                    entry["failures"] = entry.get("failures", 0) + 1
                    break
            self._write()

    async def mark_success(self, domain: str):
        async with self._lock:
            for entry in self._cache:
                if entry.get("domain") == domain:
                    entry["failures"] = 0
                    entry["last_seen"] = datetime.utcnow().isoformat() + "Z"
                    break
            self._write()

    async def remove(self, domain: str):
        async with self._lock:
            self._cache = [c for c in self._cache if c.get("domain") != domain]
            self._record_event("removed", domain)
            self._write()

    def get_all(self) -> List[Dict]:
        return list(self._cache)

    def stats(self) -> Dict:
        total = len(self._cache)
        with_hubspot = len([c for c in self._cache if c.get("hubspot", {}).get("has_hubspot")])
        return {"total": total, "with_hubspot": with_hubspot}

    def get_changes(self, hours: int = 24) -> Dict:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        def _recent(events, etype):
            recent = []
            for e in events:
                if e.get("type") != etype:
                    continue
                ts = e.get("ts")
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", ""))
                except Exception:
                    continue
                if dt >= cutoff:
                    recent.append(e)
            return recent

        added = _recent(self._events, "added")
        removed = _recent(self._events, "removed")
        return {
            "added": added,
            "removed": removed,
            "added_count": len(added),
            "removed_count": len(removed),
            "total": len(self._cache),
            "with_hubspot": len([c for c in self._cache if c.get("hubspot", {}).get("has_hubspot")]),
        }


def get_registry() -> DomainRegistry:
    global _REGISTRY
    try:
        return _REGISTRY
    except NameError:
        _REGISTRY = DomainRegistry()
        return _REGISTRY
