import os

BOT_NAME = "scrapy_project"

SPIDER_MODULES = ["scrapy_project.spiders"]
NEWSPIDER_MODULE = "scrapy_project.spiders"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 10

ITEM_PIPELINES = {
    "scrapy_project.pipelines.NtfyNotifyPipeline": 1,
}

# Allow dynamic override for debugging
LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR")

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    "scrapy_project.middlewares.ExponentialBackoffRetryMiddleware": 550,
    "scrapy_project.middlewares.DomainThrottleMiddleware": 560,
    "scrapy_project.middlewares.DeadDomainMiddleware": 570,
}

DOMAIN_THROTTLE_DELAY = 1.0
RETRY_BACKOFF_BASE = 1.5
RETRY_BACKOFF_MAX = 30.0
RETRY_ENABLED = True
RETRY_TIMES = 3

# Treat 429s and 5xx as retriable
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Keep requests from hanging forever
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "20"))

# Disable the default Scrapy telnet console to avoid noisy Twisted
# negotiation errors in environments that probe random ports (e.g.,
# Render health checks).
TELNETCONSOLE_ENABLED = False
