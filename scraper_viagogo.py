import json
import os
import re
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# =========================
# CONFIG
# =========================
GAMES_FILE = "all_games_to_scrape.json"
OUTPUT_FILE = "prices.json"
ILS_TO_USD = 0.28
PAGE_LOAD_TIMEOUT = 40

# =========================
# UTILS
# =========================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def append_json(path, rows):
    data = load_json(path, [])
    data.extend(rows)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# =========================
# DRIVER
# =========================
def get_driver():
    options = uc.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")

    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    # Enable network logging
    driver.execute_cdp_cmd("Network.enable", {})
    return driver

# =========================
# API EXTRACTION
# =========================
def extract_prices_from_network(driver):
    prices = {}

    logs = driver.get_log("performance")
    api_urls = set()

    for entry in logs:
        try:
            msg = json.loads(entry["message"])["message"]
            if msg["method"] == "Network.responseReceived":
                url = msg["params"]["response"]["url"]
                if any(k in url.lower() for k in ["inventory", "eventlisting", "listings"]):
                    api_urls.add(url)
        except:
            continue

    if not api_urls:
        return prices

    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Accept": "application/json"
    }

    for api_url in api_urls:
        try:
            r = requests.get(api_url, headers=headers, timeout=15)
            if r.status_code != 200:
                continue

            data = r.json()
            items = []

            # Handle multiple API response formats
            if isinstance(data, dict):
                for key in ["listings", "inventory", "items", "rows"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
            elif isinstance(data, list):
                items = data

            for item in items:
                try:
                    cat = (
                        item.get("category")
                        or item.get("ticketClass")
                        or item.get("sectionCategory")
                    )

                    price = (
                        item.get("price")
                        or item.get("displayPrice")
                        or item.get("amount")
                    )

                    currency = (
                        item.get("currency")
                        or item.get("currencyCode")
                        or "USD"
                    )

                    if not cat or not price:
                        continue

                    cat_match = re.search(r"([1-4])", str(cat))
                    if not cat_match:
                        continue

                    category = f"Category {cat_match.group(1)}"
                    price = float(price)

                    if currency in ["ILS", "NIS", "₪"]:
                        price = round(price * ILS_TO_USD, 2)

                    if category not in prices or price < prices[category]:
                        prices[category] = price

                except:
                    continue

        except:
            continue

    return prices

# =========================
# MAIN
# =========================
def run():
    games = load_json(GAMES_FILE, [])
    if not games:
        print("❌ No games file found")
        return

    driver = get_driver()
    results = []
    timestamp = datetime.utcnow().isoformat()

    try:
        for idx, game in enumerate(games, 1):
            url = game["url"]
            name = game.get("match_name", "Unknown Match")

            print(f"[{idx}/{len(games)}] {name}")

            if "Currency=USD" not in url:
                url += "&Currency=USD" if "?" in url else "?Currency=USD"

            driver.get(url)

            # Allow XHRs to load
            time.sleep(10)

            prices = extract_prices_from_network(driver)

            if not prices:
                print("   ❌ No prices found")
                continue

            print("   ✅", prices)

            for cat, price in prices.items():
                results.append({
                    "match_name": name,
                    "match_url": url.split("&Currency")[0],
                    "category": cat,
                    "price": price,
                    "currency": "USD",
                    "timestamp": timestamp
                })

    finally:
        driver.quit()

    if results:
        append_json(OUTPUT_FILE, results)
        print(f"\n💾 Saved {len(results)} rows")

# =========================
if __name__ == "__main__":
    run()
