#!/usr/bin/env python3
"""Test if Playwright is working"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    print("Starting Playwright test...")
    playwright = await async_playwright().start()
    print("Playwright started")
    
    browser = await playwright.chromium.launch(headless=True)
    print("Browser launched")
    
    page = await browser.new_page()
    print("Page created")
    
    await page.goto("https://www.example.com", timeout=5000)
    print("Navigated to example.com")
    
    title = await page.title()
    print(f"Page title: {title}")
    
    await browser.close()
    await playwright.stop()
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test())