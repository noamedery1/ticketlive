"""
TEST MATCH 1 - Verify button extraction method
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re

URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

print("="*70)
print("  🔍 MATCH 1 TEST - Button Extraction")
print("="*70)
print("\nExpected prices:")
print("  Category 1: $4,740")
print("  Category 2: $3,900")
print("  Category 3: $2,679")
print("  Category 4: $3,950")
print("\nOpening page...")

options = uc.ChromeOptions()
options.add_argument('--start-maximized')
driver = uc.Chrome(options=options)

try:
    driver.get(URL)
    print("Waiting 12 seconds for page to load...")
    time.sleep(12)
    
    # Get ALL buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    print(f"\nFound {len(buttons)} buttons on page")
    
    prices = {}
    
    for i, button in enumerate(buttons):
        try:
            text = button.text
            if "Category" in text and "$" in text:
                print(f"\n✅ Button #{i} contains price data:")
                print(f"   Full text: {text[:200]}")
                
                # Extract category and price
                cat_match = re.search(r'Category\s+(\d)', text)
                price_match = re.search(r'\$\s*([\d,]+)', text)
                
                if cat_match and price_match:
                    category = f"Category {cat_match.group(1)}"
                    price = float(price_match.group(1).replace(',', ''))
                    prices[category] = price
                    print(f"   Extracted: {category} = ${price:,.0f}")
        except:
            pass
    
    print(f"\n{'='*70}")
    print("FINAL RESULTS:")
    print("="*70)
    
    for cat in ["Category 1", "Category 2", "Category 3", "Category 4"]:
        if cat in prices:
            print(f"✅ {cat}: ${prices[cat]:,.0f}")
        else:
            print(f"❌ {cat}: MISSING")
    
    print("="*70)
    
    if len(prices) == 4:
        print("\n🎉 SUCCESS! All 4 prices extracted!")
    else:
        print(f"\n⚠ Only extracted {len(prices)}/4 prices")
    
finally:
    input("\nPress Enter to close...")
    driver.quit()
