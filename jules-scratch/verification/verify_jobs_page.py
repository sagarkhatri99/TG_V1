from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.goto("http://localhost:5173/login")
    page.wait_for_selector("#email", timeout=30000)
    page.screenshot(path="jules-scratch/verification/login_page.png")
    page.locator("#email").fill("test@example.com")
    page.locator("#password").fill("password")
    page.locator("button[type='submit']").click()
    page.wait_for_url("http://localhost:5173/")

    page.goto("http://localhost:5173/jobs")
    page.wait_for_selector("text=Job ID")
    page.screenshot(path="jules-scratch/verification/verification.png")

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)