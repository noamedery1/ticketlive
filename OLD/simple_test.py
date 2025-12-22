import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import sys

URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

sys.stdout.reconfigure(encoding='utf-8')

print("Starting Match 1 test...", flush=True)
print("Opening Chrome...", flush=True)

options = uc.ChromeOptions()
driver = uc.Chrome(options=options, version_main=None)

print("Chrome opened!", flush=True)
print(f"Navigating to: {URL}", flush=True)

driver.get(URL)
print("Page loaded, waiting 15 seconds...", flush=True)
time.sleep(15)

print("Getting buttons...", flush=True)
buttons = driver.find_elements(By.TAG_NAME, "button")
print(f"Found {len(buttons)} buttons", flush=True)

prices = {}
for i, btn in enumerate(buttons):
    try:
        txt = btn.text
        if "Category" in txt and "$" in txt:
            print(f"\nButton {i}: {txt[:100]}", flush=True)
            
            cat = re.search(r'Category\s+(\d)', txt)
            prc = re.search(r'\$\s*([\d,]+)', txt)
            
            if cat and prc:
                c = f"Category {cat.group(1)}"
                p = float(prc.group(1).replace(',', ''))
                prices[c] = p
                print(f"  => {c} = ${p:,.0f}", flush=True)
    except:
        pass

print(f"\n\nFINAL: {prices}", flush=True)
print(f"Success: {len(prices)}/4 categories", flush=True)

driver.quit()
print("Done!", flush=True)
