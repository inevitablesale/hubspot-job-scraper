"""
Notification system for HubSpot job scraper.

Handles sending notifications via:
- ntfy (with email/SMS relay)
- Slack webhooks
- Future: HubSpot API sync
"""

import logging
import os
from typing import List, Dict

import aiohttp

logger = logging.getLogger(__name__)

# Configuration from environment
NTFY_URL = os.getenv("NTFY_URL", "https://ntfy.sh/hubspot_job_alerts")
EMAIL_TO = os.getenv("EMAIL_TO")
SMS_TO = os.getenv("SMS_TO")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")


class JobNotifier:
    """Handles notifications for found jobs."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def send_notifications(self, jobs: List[Dict]):
        """
        Send notifications for a list of jobs.

        Args:
            jobs: List of job dicts to notify about
        """
        if not jobs:
            self.logger.info("No jobs to notify about")
            return

        self.logger.info("Sending notifications for %d jobs", len(jobs))

        # Group jobs by role
        grouped = self._group_jobs_by_role(jobs)

        # Format the message
        message = self._format_notification_message(grouped)

        # Send via ntfy
        await self._send_ntfy(message, len(jobs))

        # Send via Slack if configured
        if SLACK_WEBHOOK:
            await self._send_slack(message)

    def _group_jobs_by_role(self, jobs: List[Dict]) -> Dict[str, List[Dict]]:
        """Group jobs by role type."""
        grouped = {
            "developer": [],
            "consultant": [],
            "architect": [],
            "senior_consultant": [],
            "unknown": [],
        }

        for job in jobs:
            role = job.get("role", "unknown")
            if role not in grouped:
                grouped["unknown"].append(job)
            else:
                grouped[role].append(job)

        return grouped

    def _format_notification_message(self, grouped: Dict[str, List[Dict]]) -> str:
        """Format notification message with job details."""
        lines = []

        for role, jobs in grouped.items():
            if not jobs:
                continue

            role_title = role.replace("_", " ").title() if role != "unknown" else "Role"

            for job in jobs:
                block = [
                    f"New HubSpot {role_title} Role",
                    f"Company: {job['company']}",
                    f"Title: {job['title']}",
                    f"Apply: {job['url']}",
                    f"Score: {job.get('score', 0)}/100",
                    f"Location: {job.get('location_type', 'unknown')}",
                ]

                signals = job.get('signals', [])
                if signals:
                    block.append("Why it matched:")
                    for signal in signals:
                        block.append(f"  - {signal}")

                if job.get('summary'):
                    summary = job['summary'][:200]
                    block.append(f"Summary: {summary}...")

                block.append("")
                lines.extend(block)

        return "\n".join(lines).strip()

    async def _send_ntfy(self, message: str, job_count: int):
        """Send notification via ntfy."""
        try:
            headers = {
                "Title": f"{job_count} New HubSpot Job{'s' if job_count > 1 else ''}",
                "Priority": "default",
                "Tags": "briefcase,rocket",
            }

            # Add email relay if configured
            if EMAIL_TO:
                headers["X-Email"] = EMAIL_TO

            # Add SMS relay if configured
            if SMS_TO:
                headers["X-Phone"] = SMS_TO

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    NTFY_URL,
                    data=message.encode("utf-8"),
                    headers=headers
                ) as response:
                    if response.status == 200:
                        self.logger.info("ntfy notification sent successfully")
                    else:
                        self.logger.warning("ntfy notification failed: %d", response.status)

        except Exception as e:
            self.logger.error("Error sending ntfy notification: %s", e)

    async def _send_slack(self, message: str):
        """Send notification via Slack webhook."""
        try:
            # Format for Slack
            slack_message = {
                "text": message,
                "username": "HubSpot Job Alert",
                "icon_emoji": ":briefcase:",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    SLACK_WEBHOOK,
                    json=slack_message
                ) as response:
                    if response.status == 200:
                        self.logger.info("Slack notification sent successfully")
                    else:
                        self.logger.warning("Slack notification failed: %d", response.status)

        except Exception as e:
            self.logger.error("Error sending Slack notification: %s", e)

    async def send_hubspot_sync(self, jobs: List[Dict]):
        """
        Placeholder for HubSpot API sync.

        TODO: Implement HubSpot API integration to sync jobs as:
        - Deals
        - Custom objects
        - Or other HubSpot entities
        """
        self.logger.info("HubSpot API sync not yet implemented (%d jobs)", len(jobs))
        # Future implementation:
        # - Use HubSpot API client
        # - Create/update deals or custom objects
        # - Associate with companies
        # - Set properties for role, score, signals, etc.
