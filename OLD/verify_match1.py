"""
SINGLE GAME VERIFICATION - Match 1
Compare scraped prices vs real Viagogo screenshot
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re

MATCH1_URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

REAL_PRICES = {
    "Category 1": 4740,
    "Category 2": 3900,
    "Category 3": 2679,
    "Category 4": 3950
}

def extract_prices(driver):
    """Extract prices from page"""
    time.sleep(10)
    page_text = driver.find_element(By.TAG_NAME, "body").text
    
    prices = {}
    lines = page_text.split('\n')
    
    for i, line in enumerate(lines):
        for cat_num in [1, 2, 3, 4]:
            if re.search(rf'Category\s+{cat_num}\b', line, re.I):
                for j in range(i, min(i+10, len(lines))):
                    price_match = re.search(r'\$\s*([\d,]+)', lines[j])
                    if price_match:
                        try:
                            price = float(price_match.group(1).replace(',', ''))
                            if 100 < price < 15000:
                                prices[f'Category {cat_num}'] = price
                                break
                        except:
                            continue
    
    return prices

print("="*70)
print("  🔍 MATCH 1 VERIFICATION - Single Game Test")
print("="*70)
print("\n📋 Expected Prices (from your screenshot):")
for cat, price in REAL_PRICES.items():
    print(f"   {cat}: ${price:,.0f}")

print("\n🌐 Opening Viagogo page...")

options = uc.ChromeOptions()
options.add_argument('--start-maximized')
driver = uc.Chrome(options=options)

try:
    driver.get(MATCH1_URL)
    print("⏳ Extracting prices...")
    
    scraped_prices = extract_prices(driver)
    
    print("\n💻 Scraped Prices:")
    if scraped_prices:
        for cat, price in sorted(scraped_prices.items()):
            print(f"   {cat}: ${price:,.0f}")
    else:
        print("   ❌ No prices found!")
    
    print("\n" + "="*70)
    print("📊 COMPARISON:")
    print("="*70)
    
    all_match = True
    for cat in ["Category 1", "Category 2", "Category 3", "Category 4"]:
        expected = REAL_PRICES.get(cat, 0)
        actual = scraped_prices.get(cat, 0)
        
        if actual:
            diff = abs(expected - actual)
            match = "✅" if diff < 10 else "⚠"
            print(f"{match} {cat}: Expected ${expected:,.0f} | Got ${actual:,.0f}")
            if diff >= 10:
                all_match = False
        else:
            print(f"❌ {cat}: Expected ${expected:,.0f} | MISSING")
            all_match = False
    
    print("="*70)
    if all_match:
        print("✅ SUCCESS! Prices match perfectly!")
    else:
        print("⚠ MISMATCH! Scraper not getting exact prices.")
    print("="*70)
    
finally:
    input("\nPress Enter to close browser...")
    driver.quit()
