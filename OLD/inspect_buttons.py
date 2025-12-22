import undetected_chromedriver as uc  
from selenium.webdriver.common.by import By
import time
import sys

URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

sys.stdout.reconfigure(encoding='utf-8')

print("Inspecting ALL button text...", flush=True)

options = uc.ChromeOptions()
driver = uc.Chrome(options=options, version_main=None)

driver.get(URL)
time.sleep(15)

buttons = driver.find_elements(By.TAG_NAME, "button")
print(f"\nFound {len(buttons)} buttons\n", flush=True)

for i, btn in enumerate(buttons):
    try:
        txt = btn.text.strip()
        if txt and len(txt) > 5:  # Skip empty or very short text
            print(f"\n--- Button {i} ---", flush=True)
            print(txt[:200], flush=True)  # First 200 chars
    except:
        pass

driver.quit()
