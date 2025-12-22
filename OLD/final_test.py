import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import sys

# ILS to USD conversion rate (approximate)
ILS_TO_USD = 0.27

URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

sys.stdout.reconfigure(encoding='utf-8')

print("FINAL TEST - Extract & Convert ILS to USD", flush=True)

options = uc.ChromeOptions()
driver = uc.Chrome(options=options, version_main=None)

driver.get(URL)
time.sleep(15)

buttons = driver.find_elements(By.TAG_NAME, "button")

prices = {}
for i, btn in enumerate(buttons):
    try:
        txt = btn.text
        if "Category" in txt and "" in txt:
            cat_match = re.search(r'Category\s+(\d)', txt)
            price_match = re.search(r'([\d,]+)', txt)
            
            if cat_match and price_match:
                cat = f"Category {cat_match.group(1)}"
                ils_price = float(price_match.group(1).replace(',', ''))
                usd_price = ils_price * ILS_TO_USD
                prices[cat] = round(usd_price, 2)
                print(f"{cat}: {ils_price:,.0f} => ${usd_price:,.2f}", flush=True)
    except:
        pass

print(f"\nFINAL USD PRICES: {prices}", flush=True)
print(f"\nExpected Match 1:")
print("Cat1=$4,740, Cat2=$3,900, Cat3=$2,679, Cat4=$3,950", flush=True)

driver.quit()
