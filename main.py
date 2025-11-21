import asyncio
import logging
import os

from playwright_crawler.runner import run_all

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


def run():
    return asyncio.run(run_all())


if __name__ == "__main__":
    run()
