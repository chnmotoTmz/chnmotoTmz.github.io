import asyncio
import re
import os
from playwright.async_api import async_playwright

async def capture():
    async with async_playwright() as p:
        # Launch browser in non-headless mode so user can interact
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Opening note.com...")
        await page.goto("https://note.com/login")
        
        print("\n!!! PLEASE LOGIN MANUALLY IN THE OPENED BROWSER WINDOW !!!")
        print("The session will be saved automatically once you are logged in and redirected to your home/dashboard.")
        
        try:
            # Wait for the user to reach a page that indicates a successful login
            # note.com redirect to /home or /my after login
            await page.wait_for_url(re.compile(r"note\.com/(home|notemagazine|my/|.*n/|.*m/).*"), timeout=300000)
            print(f"Login detected: {page.url}")
            
            # Wait a bit for cookies to settle
            await asyncio.sleep(5)
            
            # Save storage state
            await context.storage_state(path="note_storage_state.json")
            print("SUCCESS: note.com session saved to note_storage_state.json")
        except Exception as e:
            print(f"ERROR: Capture failed: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
