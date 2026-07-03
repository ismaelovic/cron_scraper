"""
Temporary test script — verifies the full alert pipeline fires correctly.
Run with: uv run python _test_alert.py
Delete after testing.
"""
import asyncio
import monitor_apartment
from monitor_apartment import check_project

# Point the test project at findbolig.nu homepage — it has no "Lukket for opskrivning",
# so is_closed=False will be detected and all three alert branches will trigger.
monitor_apartment.BASE_URL = "https://www.findbolig.nu/da-dk/{id}"
TEST_PROJECT = {"id": "", "name": "TEST PROJECT"}


async def run():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Simulate: was_closed=True (i.e. was closed last run → triggers alerts on change)
        result = await check_project(browser, TEST_PROJECT, {"is_closed": True})
        await browser.close()
    print("\nFinal result:", result)

asyncio.run(run())
