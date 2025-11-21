import asyncio
import os
import random
import subprocess
import sys
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


async def _new_context(browser: Browser) -> BrowserContext:
    ua = os.getenv("USER_AGENT") or DEFAULT_USER_AGENT
    # light randomization to avoid looking fully static
    viewport = {
        "width": random.choice([1280, 1366, 1440, 1600]),
        "height": random.choice([720, 768, 900]),
    }
    return await browser.new_context(
        user_agent=ua,
        ignore_https_errors=True,
        viewport=viewport,
    )


@asynccontextmanager
async def browser_context(headless: bool = True):
    async with async_playwright() as p:
        browser = await _launch_with_fallback(p, headless=headless)
        context = await _new_context(browser)
        try:
            yield context
        finally:
            await context.close()
            await browser.close()


async def new_page(context: BrowserContext) -> Page:
    page = await context.new_page()
    page.set_default_timeout(int(os.getenv("PAGE_TIMEOUT_MS", "20000")))
    return page


async def gentle_scroll(page: Page, steps: int = 8, delay: int = 250):
    for i in range(steps):
        await page.mouse.wheel(0, 1000)
        await asyncio.sleep(delay / 1000)


async def _launch_with_fallback(p, headless: bool = True) -> Browser:
    """
    Launch Chromium, and if the cached browser is missing (e.g., Render cache
    evicted), install it on the fly, then retry once.
    """

    args = ["--disable-blink-features=AutomationControlled", "--no-sandbox"]

    try:
        return await p.chromium.launch(headless=headless, args=args)
    except Exception as exc:  # PlaywrightError is not exported at top-level
        msg = str(exc)
        if "Executable doesn't exist" not in msg:
            raise
        _install_chromium_browser()
        # Retry once after install
        return await p.chromium.launch(headless=headless, args=args)


def _install_chromium_browser():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )
