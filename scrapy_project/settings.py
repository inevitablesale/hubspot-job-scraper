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

LOG_LEVEL = "ERROR"

# Disable the default Scrapy telnet console to avoid noisy Twisted
# negotiation errors in environments that probe random ports (e.g.,
# Render health checks).
TELNETCONSOLE_ENABLED = False
