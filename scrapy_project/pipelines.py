import asyncio
import hashlib
import json
from pathlib import Path

import aiohttp
from scrapy.exceptions import DropItem

NTFY_URL = "https://ntfy.sh/hubspot_job_alerts"
EMAIL_TO = "christabb@gmail.com"
SMS_TO = None
SLACK_WEBHOOK = None
JOB_CACHE_PATH = Path(".job_cache.json")


class JobCache:
    def __init__(self, path: Path):
        self.path = path
        self.seen = self._load()

    def _load(self):
        if self.path.exists():
            try:
                with self.path.open() as f:
                    data = json.load(f)
                return set(data)
            except (json.JSONDecodeError, OSError):
                return set()
        return set()

    def contains(self, job_hash: str) -> bool:
        return job_hash in self.seen

    def add(self, job_hash: str):
        self.seen.add(job_hash)

    def persist(self):
        try:
            with self.path.open("w") as f:
                json.dump(sorted(self.seen), f)
        except OSError:
            pass


class NtfyNotifyPipeline:
    def __init__(self):
        self.jobs = []
        self.cache = JobCache(JOB_CACHE_PATH)

    def process_item(self, item, spider):
        job_hash = hashlib.sha256(f"{item['company']}{item['job_page']}".encode("utf-8")).hexdigest()
        if self.cache.contains(job_hash):
            spider.logger.debug("Skipping duplicate job: %s", item["job_page"])
            raise DropItem("Duplicate job")

        self.cache.add(job_hash)
        self.jobs.append(item)
        return item

    def close_spider(self, spider):
        if not self.jobs:
            spider.logger.info("No HubSpot jobs found. Nothing to notify.")
            return

        asyncio.run(self.send_notification(self.jobs, spider))
        self.cache.persist()

    async def send_notification(self, jobs, spider):
        grouped = {
            "developer": [],
            "consultant": [],
            "architect": [],
            "senior_consultant": [],
            "unknown": [],
        }
        # Clean notification formatting
        for job in jobs:
            role = job.get("role", "unknown")
            if role not in grouped:
                grouped["unknown"].append(job)
            else:
                grouped[role].append(job)

        message_lines = []
        for role, entries in grouped.items():
            if not entries:
                continue
            title = role.replace("_", " ").title() if role != "unknown" else "Role"
            for entry in entries:
                block = [
                    f"New HubSpot {title} Role",
                    f"Company: {entry['company']}",
                    f"Apply: {entry['job_page']}",
                    f"Score: {entry.get('score', 0)}/100",
                    "Why it matched:",
                    *[f"- {signal}" for signal in entry.get("signals", [])],
                    "",
                ]
                message_lines.extend(block)

        payload = "\n".join(message_lines).strip()

        # Add Markdown header for ntfy
        if len(jobs) > 1:
            payload = f"## {len(jobs)} New HubSpot Roles Found\n\n" + payload
        else:
            payload = f"## New HubSpot Role\n\n" + payload

        headers = {
            "Title": f"{len(self.jobs)} New HubSpot Roles",
        }
        email_to = EMAIL_TO or spider.settings.get("EMAIL_TO")
        if email_to:
            headers["X-Email"] = email_to

        sms_to = SMS_TO or spider.settings.get("SMS_TO")
        if sms_to:
            headers["X-Phone"] = sms_to

        async with aiohttp.ClientSession() as session:
            await session.post(NTFY_URL, data=payload.encode("utf-8"), headers=headers)

            slack_hook = SLACK_WEBHOOK or spider.settings.get("SLACK_WEBHOOK")
            if slack_hook:
                await session.post(slack_hook, json={"text": payload})
