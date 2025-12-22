import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import sys

# US URL for USD prices!
URL = "https://www.viagogo.com/us/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

sys.stdout.reconfigure(encoding='utf-8')

print("Testing US URL for USD prices...", flush=True)

options = uc.ChromeOptions()
driver = uc.Chrome(options=options, version_main=None)

driver.get(URL)
time.sleep(15)

buttons = driver.find_elements(By.TAG_NAME, "button")

prices = {}
for i, btn in enumerate(buttons):
    try:
        txt = btn.text
        if "Category" in txt:  # Changed: look for Category USD or 
            print(f"Button {i}: {txt[:100]}", flush=True)
            
            cat = re.search(r'Category\s+(\d)', txt)
            # Look for $ or 
            prc = re.search(r'[\$]\s*([\d,]+)', txt)
            
            if cat and prc:
                c = f"Category {cat.group(1)}"
                p = float(prc.group(1).replace(',', ''))
                prices[c] = p
                print(f"  => {c} = {p:,.0f}", flush=True)
    except:
        pass

print(f"\n\nEXTRACTED: {prices}", flush=True)
driver.quit()
