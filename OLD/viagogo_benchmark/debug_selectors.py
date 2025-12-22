from playwright.sync_api import sync_playwright
import time

url = "https://www.viagogo.com/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?backUrl=%2FSports-Tickets%2FSoccer%2FSoccer-Tournament%2FWorld-Cup-Tickets"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    print("Navigating...")
    page.goto(url, timeout=60000)
    print("Waiting for load...")
    # Wait specifically for something that looks like a list
    time.sleep(10) # Simple wait for dynamic content
    
    content = page.content()
    with open("page_dump.html", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Dumped page content to page_dump.html")
    browser.close()
