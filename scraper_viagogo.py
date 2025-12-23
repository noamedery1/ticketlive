import json
import os
import re
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timezone

# =========================
# CONFIG
# =========================
GAMES_FILE = "all_games_to_scrape.json"
OUTPUT_FILE = "prices.json"
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
    """Get Chrome driver with network logging enabled"""
    options = uc.ChromeOptions()

    # Check if running in Docker/headless environment
    if os.environ.get('HEADLESS') == 'true' or not os.path.exists('/usr/bin/chromium'):
        options.add_argument("--headless=new")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    
    # Block images to save resources
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    browser_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
    driver_path = '/usr/bin/chromedriver' if os.path.exists('/usr/bin/chromedriver') else None
    
    driver = uc.Chrome(
        options=options,
        browser_executable_path=browser_path,
        driver_executable_path=driver_path
    )
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    
    # Enable performance logging BEFORE page loads (required for get_log to work)
    try:
        # Enable logging capabilities
        driver.execute_cdp_cmd("Performance.enable", {})
        driver.execute_cdp_cmd("Network.enable", {})
    except:
        # If CDP fails, we'll use DOM fallback
        pass
    
    return driver

# =========================
# API EXTRACTION
# =========================
def extract_prices_from_network(driver):
    """Extract prices by intercepting network API calls, with DOM fallback"""
    prices = {}
    api_urls = set()
    
    # Try network extraction first
    try:
        logs = driver.get_log("performance")
        for entry in logs:
            try:
                msg = json.loads(entry["message"])["message"]
                if msg["method"] == "Network.responseReceived":
                    url = msg["params"]["response"]["url"]
                    # Look for Viagogo API endpoints
                    if any(k in url.lower() for k in ["inventory", "eventlisting", "listings", "tickets", "api"]):
                        # Only add Viagogo domains
                        if "viagogo.com" in url.lower() or "viagogo" in url.lower():
                            api_urls.add(url)
            except:
                continue
    except Exception as e:
        # Performance logs not available, use DOM fallback
        print(f"      Performance logs not available: {str(e)[:50]}")
        print("      Using DOM-based extraction...")
        return extract_prices_from_dom(driver)

    if not api_urls:
        print("      No API URLs found in network logs. Using DOM extraction...")
        return extract_prices_from_dom(driver)

    print(f"      Found {len(api_urls)} potential API URLs")

    # Get user agent from driver
    try:
        user_agent = driver.execute_script("return navigator.userAgent;")
    except:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": driver.current_url
    }

    for api_url in api_urls:
            try:
                print(f"      Trying API: {api_url[:80]}...")
                r = requests.get(api_url, headers=headers, timeout=10)
                if r.status_code != 200:
                    continue

                data = r.json()
                items = []

                # Handle multiple API response formats
                if isinstance(data, dict):
                    for key in ["listings", "inventory", "items", "rows", "data", "results"]:
                        if key in data and isinstance(data[key], list):
                            items = data[key]
                            break
                    # Also check nested structures
                    if not items and "data" in data and isinstance(data["data"], dict):
                        for key in ["listings", "inventory", "items", "rows"]:
                            if key in data["data"] and isinstance(data["data"][key], list):
                                items = data["data"][key]
                                break
                elif isinstance(data, list):
                    items = data

                if not items:
                    continue

                print(f"      Found {len(items)} items in API response")

                for item in items:
                    try:
                        # Try multiple field names for category
                        cat = (
                            item.get("category")
                            or item.get("ticketClass")
                            or item.get("sectionCategory")
                            or item.get("section")
                            or item.get("tier")
                            or str(item.get("categoryId", ""))
                        )

                        # Try multiple field names for price
                        price = (
                            item.get("price")
                            or item.get("displayPrice")
                            or item.get("amount")
                            or item.get("minPrice")
                            or item.get("pricePerTicket")
                        )

                        # Try multiple field names for currency
                        currency = (
                            item.get("currency")
                            or item.get("currencyCode")
                            or item.get("currencySymbol")
                            or "USD"
                        )

                        if not cat or price is None:
                            continue

                        # Extract category number (1-4)
                        cat_match = re.search(r"([1-4])", str(cat))
                        if not cat_match:
                            continue

                        category = f"Category {cat_match.group(1)}"
                        
                        # Convert price to float
                        try:
                            price = float(price)
                        except:
                            continue

                        # Validate price range (page is already in USD)
                        if not (35 <= price <= 50000):
                            continue

                        # Keep minimum price per category
                        if category not in prices or price < prices[category]:
                            prices[category] = price
                            print(f"      Found {category}: ${price}")

                    except Exception as e:
                        continue

            except requests.exceptions.RequestException:
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"      API error: {str(e)[:50]}")
                continue
    
    return prices

def extract_prices_from_dom(driver):
    """Fallback: Extract prices from DOM if API extraction fails"""
    prices = {}
    
    try:
        # Wait for page to load
        time.sleep(3)
        
        # Try to find price elements in the DOM
        # Look for elements with aria-label containing Category and price
        try:
            aria_elements = driver.find_elements(By.XPATH, "//*[@aria-label]")
            
            for elem in aria_elements[:100]:  # Limit to avoid hanging
                try:
                    aria_text = elem.get_attribute('aria-label') or ''
                    if not aria_text:
                        continue
                    
                    # Look for "Category X" pattern
                    cat_match = re.search(r'(?:Category|Cat)\s+([1-4])\b', aria_text, re.I)
                    if not cat_match:
                        continue
                    
                    cat_num = cat_match.group(1)
                    cat_name = f"Category {cat_num}"
                    
                    # Skip if already found
                    if cat_name in prices:
                        continue
                    
                    # Extract price from aria-label (page is already in USD)
                    price_match = re.search(r'(?:\$|USD)?\s*([\d,]{2,})', aria_text)
                    if price_match:
                        try:
                            price_val = float(price_match.group(1).replace(',', ''))
                            if 35 <= price_val <= 50000:
                                # Keep minimum price per category
                                if cat_name not in prices or price_val < prices[cat_name]:
                                    prices[cat_name] = price_val
                                    print(f"      Found {cat_name}: ${price_val} (DOM)")
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            print(f"      DOM extraction error: {str(e)[:50]}")
    
    except Exception as e:
        print(f"      DOM fallback error: {str(e)[:50]}")
    
    return prices

# =========================
# MAIN
# =========================
def run():
    games = load_json(GAMES_FILE, [])
    if not games:
        print("ERROR: No games file found")
        return

    driver = get_driver()
    results = []
    timestamp = datetime.now(timezone.utc).isoformat()

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
                print("   No prices found")
                continue

            print("   SUCCESS:", prices)

            for cat, price in prices.items():
                # Clean URL (remove Currency parameter)
                clean_url = url.split("&Currency")[0].split("?Currency")[0]
                
                results.append({
                    "match_name": name,
                    "match_url": clean_url,
                    "category": cat,
                    "price": price,
                    "currency": "USD",
                    "timestamp": timestamp
                })

    finally:
        driver.quit()

    if results:
        append_json(OUTPUT_FILE, results)
        print(f"\nSaved {len(results)} rows to {OUTPUT_FILE}")

# =========================
if __name__ == "__main__":
    run()
