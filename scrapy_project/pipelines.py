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
        grouped = {"developer": [], "consultant": [], "unknown": []}
        for job in jobs:
            grouped.get(job.get("role"), grouped["unknown"]).append(job)

        message_lines = []
        for role, entries in grouped.items():
            if not entries:
                continue
            title = role.capitalize() if role != "unknown" else "Role"
            for entry in entries:
                message_lines.extend(
                    [
                        f"New HubSpot {title} Role Found",
                        f"Company: {entry['company']}",
                        f"URL: {entry['job_page']}",
                        f"Score: {entry.get('score', 0)}/100",
                        "Why it matched:",
                        *[f"- {signal}" for signal in entry.get("signals", [])],
                        "",
                    ]
                )

        payload = "\n".join(message_lines).strip()

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
