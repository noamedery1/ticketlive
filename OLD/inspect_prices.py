"""
ADVANCED SCRAPER - Find Real Price Source
Strategy: Download full HTML + inspect for price data structures
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import json

MATCH1_URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

print("="*70)
print("  🔍 DEEP INSPECTION - Finding Real Price Source")
print("="*70)

options = uc.ChromeOptions()
options.add_argument('--start-maximized')
driver = uc.Chrome(options=options)

try:
    print("\n📥 Loading Match 1 page...")
    driver.get(MATCH1_URL)
    
    print("⏳ Waiting for full page load (15 seconds)...")
    time.sleep(15)
    
    # Get full HTML
    html = driver.page_source
    
    print(f"\n📄 Page HTML size: {len(html):,} characters")
    
    # Save HTML for analysis
    with open("match1_full_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Saved to: match1_full_page.html")
    
    # Strategy 1: Look for JSON data in script tags
    print("\n🔎 Strategy 1: Searching for JSON price data...")
    script_tags = driver.find_elements(By.TAG_NAME, "script")
    
    for i, script in enumerate(script_tags):
        content = script.get_attribute("innerHTML") or ""
        if "category" in content.lower() and ("4740" in content or "3900" in content or "price" in content.lower()):
            print(f"\n✅ Found potential price data in script tag #{i}")
            sample = content[:500]
            print(f"Sample: {sample}...")
            
            # Save this script
            with open(f"script_tag_{i}.txt", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Saved to: script_tag_{i}.txt")
    
    # Strategy 2: Look for specific price patterns in HTML
    print("\n🔎 Strategy 2: Searching HTML for price patterns...")
    
    # Look for the exact prices we know
    target_prices = ["4740", "3900", "2679", "3950", "4,740", "3,900", "2,679", "3,950"]
    
    for price in target_prices:
        if price in html:
            print(f"✅ Found price: {price}")
            # Get context around this price
            idx = html.find(price)
            context = html[max(0, idx-200):min(len(html), idx+200)]
            print(f"Context: ...{context}...")
            print()
    
    # Strategy 3: Look for data attributes
    print("\n🔎 Strategy 3: Checking for data-* attributes...")
    elements_with_data = driver.find_elements(By.XPATH, "//*[@data-price or @data-amount or @data-value]")
    
    if elements_with_data:
        print(f"Found {len(elements_with_data)} elements with data attributes")
        for elem in elements_with_data[:5]:
            attrs = driver.execute_script(
                "var items = {}; for (index = 0; index < arguments[0].attributes.length; ++index) { items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value }; return items;",
                elem
            )
            print(f"Element attributes: {attrs}")
    
    print("\n" + "="*70)
    print("📊 Inspection complete!")
    print("="*70)
    print("\n🔍 Next steps:")
    print("1. Check match1_full_page.html for price patterns")
    print("2. Check script_tag_*.txt files for JSON data")
    print("3. Use findings to create accurate scraper")
    
finally:
    input("\nPress Enter to close...")
    driver.quit()
