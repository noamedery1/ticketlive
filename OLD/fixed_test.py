import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import sys

ILS_TO_USD = 0.27

URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

sys.stdout.reconfigure(encoding='utf-8')

print("FIXED TEST - Proper price extraction", flush=True)

options = uc.ChromeOptions()
driver = uc.Chrome(options=options, version_main=None)

driver.get(URL)
time.sleep(15)

buttons = driver.find_elements(By.TAG_NAME, "button")

prices = {}
for i, btn in enumerate(buttons):
    try:
        txt = btn.text
        
        #  Text looks like: "Category 1\n12,838"
        # Need to extract BOTH parts separately
        
        if "Category" in txt and "" in txt:
            lines = txt.split('\n')
            
            cat_num = None
            price_ils = None
            
            for line in lines:
                # Find category number
                cat_match = re.search(r'Category\s+(\d)', line)
                if cat_match:
                    cat_num = cat_match.group(1)
                
                # Find price
                price_match = re.search(r'([\d,]+)', line)
                if price_match:
                    price_ils = float(price_match.group(1).replace(',', ''))
            
            if cat_num and price_ils:
                cat = f"Category {cat_num}"
                usd_price = round(price_ils * ILS_TO_USD, 2)
                prices[cat] = usd_price
                print(f"{cat}: {price_ils:,.0f} => ${usd_price:,.2f}", flush=True)
    except:
        pass

print(f"\nFINAL: {prices}", flush=True)

driver.quit()
