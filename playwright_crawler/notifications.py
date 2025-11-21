import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List

import aiohttp

NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh/hubspot_job_alerts")
EMAIL_TO = os.getenv("EMAIL_TO", "christabb@gmail.com")
SMS_TO = os.getenv("SMS_TO")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")
JOB_CACHE_PATH = Path(os.getenv("JOB_CACHE_PATH", ".job_cache.json"))


class JobCache:
    def __init__(self, path: Path):
        self.path = path
        self._seen = set()
        if path.exists():
            try:
                self._seen = set(json.loads(path.read_text()))
            except Exception:
                self._seen = set()

    def contains(self, job_hash: str) -> bool:
        return job_hash in self._seen

    def add(self, job_hash: str):
        self._seen.add(job_hash)

    def persist(self):
        try:
            self.path.write_text(json.dumps(list(self._seen)))
        except Exception:
            pass


class Notifier:
    def __init__(self):
        self.cache = JobCache(JOB_CACHE_PATH)
        self.jobs: List[Dict[str, str]] = []

    def _hash_job(self, company: str, url: str) -> str:
        return hashlib.sha256(f"{company}{url}".encode("utf-8")).hexdigest()

    def add(self, job: Dict[str, str]):
        job_hash = self._hash_job(job.get("company", ""), job.get("url", ""))
        if self.cache.contains(job_hash):
            return False
        self.cache.add(job_hash)
        self.jobs.append(job)
        return True

    async def flush(self):
        if not self.jobs:
            return
        payload_lines = []
        for job in self.jobs:
            block = [
                f"New HubSpot {job.get('role', '').title() or 'Role'}",
                f"Company: {job.get('company')}",
                f"Title: {job.get('title')}",
                f"Apply: {job.get('url')}",
                f"Score: {job.get('score')} / signals: {', '.join(job.get('signals', []))}",
                f"Location: {job.get('location', '')}",
                f"Summary: {job.get('summary', '')[:240]}",
                "",
            ]
            payload_lines.extend(block)
        payload = "\n".join(payload_lines).strip()
        headers = {"Title": f"{len(self.jobs)} HubSpot roles"}
        if EMAIL_TO:
            headers["X-Email"] = EMAIL_TO
        if SMS_TO:
            headers["X-SMS"] = SMS_TO
        if SLACK_WEBHOOK:
            headers["X-Webhook"] = SLACK_WEBHOOK

        async with aiohttp.ClientSession() as session:
            await session.post(NTFY_URL, data=payload.encode("utf-8"), headers=headers)
        self.cache.persist()

    async def notify_job(self, job: Dict[str, str]):
        if not self.add(job):
            return
        await self.flush()
