from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to the frontend dev server
        page.goto("http://localhost:5173") # Default Vite port

        # Click the "Jobs" link in the sidebar
        page.get_by_role("link", name="Jobs").click()

        # Wait for the Jobs page to load by checking for the heading
        page.wait_for_selector('h4:has-text("Job Management")')

        # Take a screenshot of the page
        page.screenshot(path="jules-scratch/verification/verification.png")

        browser.close()

if __name__ == "__main__":
    run()
