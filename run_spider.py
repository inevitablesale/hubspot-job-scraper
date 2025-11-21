import asyncio
import logging
import os

from playwright_crawler.runner import run_all

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

if __name__ == "__main__":
    asyncio.run(run_all())
