import asyncio
from datetime import datetime
from typing import Dict, List, Optional


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
