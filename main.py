import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scrapy_project.spiders.hubspot_spider import HubspotSpider


def run_spider():
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "scrapy_project.settings")
    process = CrawlerProcess(get_project_settings())
    process.crawl(HubspotSpider)
    process.start()


if __name__ == "__main__":
    run_spider()
