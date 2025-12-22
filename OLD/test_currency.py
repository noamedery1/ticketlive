import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import sys

# Match 1 URL
URL = "https://www.viagogo.com/il/Sports-Tickets/Soccer/Soccer-Tournament/World-Cup-Tickets/E-153033405?quantity=1"

# Force flush
sys.stdout.reconfigure(encoding='utf-8')

print("TEST: Checking if ?Currency=USD works...", flush=True)

options = uc.ChromeOptions()
driver = uc.Chrome(options=options)

# 1. Go to URL with Currency param
driver.get(URL + "&Currency=USD")
print("Navigated to URL + &Currency=USD", flush=True)

time.sleep(10)

# Check buttons
buttons = driver.find_elements(By.TAG_NAME, "button")
print(f"Found {len(buttons)} buttons.", flush=True)

found_usd = False
for btn in buttons:
    txt = btn.text
    if "Category" in txt:
        print(f"Button text: {txt.replace('\n', ' ')}", flush=True)
        if "$" in txt:
            print("✅ FOUND DOLLAR SIGN!", flush=True)
            found_usd = True

if not found_usd:
    print("❌ NO DOLLAR sign found. Currency switch failed.", flush=True)
else:
    print("🎉 SUCCESS! Currency switch worked.", flush=True)

driver.quit()
