import asyncio
import os
import re
import yaml
from playwright.async_api import async_playwright

class NotePublisher:
    def __init__(self, storage_state="note_storage_state.json"):
        self.storage_state = storage_state

    async def publish_markdown(self, filepath, publish=False):
        if not os.path.exists(self.storage_state):
            print(f"Error: {self.storage_state} not found. Please run capture_note_session.py first.")
            return

        # Parse Markdown and Frontmatter
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple frontmatter parser
        title = "Untitled"
        body = content
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                title = metadata.get('title', title)
                body = parts[2].strip()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False) # Headless=False to see the magic
            context = await browser.new_context(storage_state=self.storage_state)
            page = await context.new_page()

            print(f"Navigating to Note editor...")
            await page.goto("https://note.com/notes/new")
            
            # Wait for editor to load
            # Note uses different selectors sometimes, try to be flexible
            try:
                await page.wait_for_selector('textarea[placeholder="記事タイトル"]', timeout=30000)
                title_input = page.locator('textarea[placeholder="記事タイトル"]')
            except:
                await page.wait_for_selector('.v-text-field__slot textarea', timeout=10000)
                title_input = page.locator('.v-text-field__slot textarea').first
            
            print(f"Setting title: {title}")
            await title_input.click()
            await title_input.fill(title)
            await page.screenshot(path="debug_1_title.png")

            print("Setting body content...")
            editor = page.locator('.ProseMirror')
            await editor.click()
            await asyncio.sleep(1)
            
            # Clear and Focus
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await asyncio.sleep(0.5)
            
            # Paste body via clipboard
            await page.evaluate(f"navigator.clipboard.writeText(`{body}`)")
            await page.keyboard.press("Control+V")
            await asyncio.sleep(2)
            
            # Fallback: If still empty, try typing a small part
            await page.keyboard.type(" ") # Trigger event
            
            await page.screenshot(path="debug_2_content.png")

            print("Attempting manual save...")
            save_clicked = False
            try:
                save_selectors = ['button:has-text("保存")', 'button:has-text("下書き保存")', '.p-noteHeader__save']
                for selector in save_selectors:
                    btn = page.locator(selector)
                    if await btn.is_visible():
                        await btn.click()
                        print(f"Clicked save button: {selector}")
                        save_clicked = True
                        await asyncio.sleep(2)
                        break
            except Exception as e:
                print(f"Save button error: {e}")

            await page.screenshot(path="debug_3_final.png")
            
            print("Waiting for final sync...")
            await asyncio.sleep(5)
            await browser.close()
            print(f"Done. Screenshots saved as debug_*.png. Save clicked: {save_clicked}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python post_to_note.py <markdown_file>")
        sys.exit(1)
        
    publisher = NotePublisher()
    asyncio.run(publisher.publish_markdown(sys.argv[1]))
