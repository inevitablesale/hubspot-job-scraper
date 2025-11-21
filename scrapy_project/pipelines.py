import asyncio

import aiohttp

NTFY_URL = "https://ntfy.sh/hubspot_job_alerts"
EMAIL_TO = "christabb@gmail.com"


class NtfyNotifyPipeline:
    def __init__(self):
        self.jobs = []

    def process_item(self, item, spider):
        self.jobs.append(item)
        return item

    def close_spider(self, spider):
        if not self.jobs:
            spider.logger.info("No HubSpot jobs found. Nothing to notify.")
            return

        lines = [f"{j['company']}\n{j['job_page']}\n" for j in self.jobs]
        message = "\n".join(lines).strip()

        asyncio.run(self.send_notification(message))

    async def send_notification(self, message):
        async with aiohttp.ClientSession() as session:
            await session.post(
                NTFY_URL,
                data=message.encode("utf-8"),
                headers={
                    "Title": f"{len(self.jobs)} HubSpot Roles Found",
                    "X-Email": EMAIL_TO,
                },
            )
