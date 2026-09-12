from playwright.sync_api import Page, expect, sync_playwright
import os

def verify_design(page: Page):
    # Use absolute path for local file access
    current_dir = os.getcwd()
    target_file = f"file://{current_dir}/posts/news/2026-03-14-見えない軍隊が空を埋める日-1円玉より軽い0-2gの羽ばたきが書き換えるステルスの定義.html"

    page.goto(target_file)
    page.wait_for_timeout(1000)

    # Verify title is visible and correctly styled (now without inline style in HTML, but class-based)
    h1 = page.locator("main.premium-article h1")
    expect(h1).to_be_visible()

    # Check that there are no nested <article> tags inside .post-content
    # (The grep check already confirmed this, but let's be sure in the browser)
    nested_articles = page.locator(".post-content article")
    expect(nested_articles).to_have_count(0)

    # Check sidebar styling (ranking numbers)
    ranking_numbers = page.locator(".ranking-number")
    expect(ranking_numbers.first).to_be_visible()

    page.screenshot(path="/home/jules/verification/verification_final.png", full_page=True)
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    os.makedirs("/home/jules/verification/video", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir="/home/jules/verification/video")
        page = context.new_page()
        try:
            verify_design(page)
        finally:
            context.close()
            browser.close()
