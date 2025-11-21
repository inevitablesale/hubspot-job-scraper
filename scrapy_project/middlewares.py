import logging
import time
from urllib.parse import urlparse

from scrapy.exceptions import IgnoreRequest
from scrapy.http import TextResponse
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from twisted.internet import reactor
from twisted.internet.error import DNSLookupError
from twisted.internet.task import deferLater


class DomainThrottleMiddleware:
    """Apply a minimal delay between requests per domain to avoid burstiness."""

    def __init__(self, delay: float):
        self.delay = max(delay, 0)
        self._last_seen = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_crawler(cls, crawler):
        delay = crawler.settings.getfloat("DOMAIN_THROTTLE_DELAY", 0.0)
        return cls(delay)

    def process_request(self, request, spider):
        if self.delay <= 0:
            return None

        domain = urlparse(request.url).netloc
        now = time.monotonic()
        last = self._last_seen.get(domain)
        wait = self.delay - (now - last) if last else 0

        if wait > 0:
            return deferLater(reactor, wait, self._mark_and_continue, domain)

        self._last_seen[domain] = now
        return None

    def _mark_and_continue(self, domain):
        self._last_seen[domain] = time.monotonic()
        return None


class DeadDomainMiddleware:
    """Suppress noisy DNS failures by classifying domains as dead and skipping them."""

    def __init__(self):
        self.dead_domains = set()
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request, spider):
        domain = self._normalize_domain(request.url)
        if domain in self.dead_domains:
            raise IgnoreRequest(f"Skipping dead domain: {domain}")
        return None

    def process_exception(self, request, exception, spider):
        if isinstance(exception, DNSLookupError):
            domain = self._normalize_domain(request.url)
            if domain not in self.dead_domains:
                self.dead_domains.add(domain)
                spider.logger.warning("Marking domain as dead after DNS failure: %s", domain)
            return TextResponse(url=request.url, status=599, request=request, body=b"")
        return None

    def _normalize_domain(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host


class ExponentialBackoffRetryMiddleware(RetryMiddleware):
    """Retry with exponential backoff and quieter logging for non-actionable errors."""

    def __init__(self, settings):
        super().__init__(settings)
        self.backoff_base = settings.getfloat("RETRY_BACKOFF_BASE", 1.5)
        self.max_backoff = settings.getfloat("RETRY_BACKOFF_MAX", 30.0)
        self.logger = logging.getLogger(self.__class__.__name__)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def _retry(self, request, reason, spider):
        retries = request.meta.get("retry_times", 0) + 1
        if retries <= self.max_retry_times:
            backoff = min(self.max_backoff, self.backoff_base * (2 ** (retries - 1)))
            retryreq = request.copy()
            retryreq.meta["retry_times"] = retries
            retryreq.dont_filter = True
            self.logger.info(
                "Retrying %s (attempt %s) after %.1fs backoff due to %s",
                request.url,
                retries,
                backoff,
                reason,
            )
            return deferLater(reactor, backoff, lambda: retryreq)

        self.logger.error("Gave up retrying %s after %s attempts", request.url, retries)
        return None
