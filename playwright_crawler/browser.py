import asyncio
import os
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
)


async def _new_context(browser: Browser) -> BrowserContext:
    return await browser.new_context(
        user_agent=os.getenv("USER_AGENT", DEFAULT_USER_AGENT),
        ignore_https_errors=True,
        viewport={"width": 1366, "height": 768},
    )


@asynccontextmanager
async def browser_context(headless: bool = True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
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
