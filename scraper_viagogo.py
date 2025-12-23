import json
import os
import re
import time
import threading
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
    try:
        # Check for Chromium/Chrome paths (Render might not have them)
        browser_path = None
        driver_path = None
        
        # Try common paths
        chromium_paths = ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']
        for path in chromium_paths:
            if os.path.exists(path):
                browser_path = path
                break
        
        chromedriver_paths = ['/usr/bin/chromedriver', '/usr/local/bin/chromedriver']
        for path in chromedriver_paths:
            if os.path.exists(path):
                driver_path = path
                break
        
        print(f"   Initializing Chrome driver...", flush=True)
        print(f"   Browser path: {browser_path or 'auto-detect'}", flush=True)
        print(f"   Driver path: {driver_path or 'auto-detect'}", flush=True)
        
        # Try to initialize driver with retries and timeout protection
        driver = None
        for attempt in range(3):
            try:
                print(f"   Attempt {attempt + 1}/3 to initialize driver...", flush=True)
                
                # Create FRESH ChromeOptions for each attempt (cannot reuse!)
                options = uc.ChromeOptions()

                # Always use headless on server environments (Render, Docker, etc.)
                # Render doesn't have display, so headless is required
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--lang=en-US")
                options.add_argument("--disable-software-rasterizer")
                options.add_argument("--disable-extensions")

                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-features=IsolateOrigins,site-per-process")
                
                # Additional stability flags for Render
                options.add_argument("--disable-session-crashed-bubble")
                options.add_argument("--disable-crash-reporter")
                options.add_argument("--js-flags=--max-old-space-size=2048")
                options.add_argument("--disable-background-timer-throttling")
                options.add_argument("--disable-renderer-backgrounding")
                
                # Block images to save resources
                prefs = {"profile.managed_default_content_settings.images": 2}
                options.add_experimental_option("prefs", prefs)
                
                options.page_load_strategy = 'eager'
                
                # Use threading to add timeout for driver initialization (prevents hanging)
                init_result = {'driver': None, 'error': None, 'done': False}
                
                def init_worker():
                    try:
                        init_result['driver'] = uc.Chrome(
                            options=options,
                            browser_executable_path=browser_path,
                            driver_executable_path=driver_path,
                            version_main=None,
                            use_subprocess=True  # Use subprocess to avoid connection issues
                        )
                        init_result['done'] = True
                    except Exception as e:
                        init_result['error'] = e
                        init_result['done'] = True
                
                init_thread = threading.Thread(target=init_worker, daemon=True)
                init_thread.start()
                init_thread.join(timeout=45)  # 45 second timeout for initialization
                
                if init_thread.is_alive():
                    print(f"   ERROR: Driver initialization timed out after 45s", flush=True)
                    if attempt < 2:
                        wait_time = 5 * (attempt + 1)
                        print(f"   Retrying in {wait_time} seconds...", flush=True)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception("Driver initialization timed out after 3 attempts")
                
                if init_result['error']:
                    raise init_result['error']
                
                driver = init_result['driver']
                if not driver:
                    raise Exception("Driver is None after initialization")
                
                # Test if driver is actually working
                driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                driver.implicitly_wait(5)
                driver.set_script_timeout(30)
                
                # Quick test to ensure driver is responsive
                try:
                    test_result = driver.execute_script("return 'test';")
                    if test_result != 'test':
                        raise Exception("Driver test failed - wrong result")
                except Exception as test_err:
                    print(f"   Driver test failed: {str(test_err)[:50]}", flush=True)
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                    driver = None
                    if attempt < 2:
                        time.sleep(3)
                        continue
                    raise test_err
                
                # Enable performance logging BEFORE page loads (required for get_log to work)
                try:
                    driver.execute_cdp_cmd("Performance.enable", {})
                    driver.execute_cdp_cmd("Network.enable", {})
                    print(f"   CDP logging enabled", flush=True)
                except Exception as e:
                    print(f"   CDP logging not available (will use DOM): {str(e)[:50]}", flush=True)
                
                print(f"   ✅ Driver initialized successfully", flush=True)
                return driver
                
            except Exception as e:
                error_msg = str(e)
                print(f"   Attempt {attempt + 1} failed: {error_msg[:150]}", flush=True)
                
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                
                # If it's a connection/timeout error, wait and retry
                if any(keyword in error_msg.lower() for keyword in ["httpconnectionpool", "timeout", "connection", "timed out", "read timeout"]):
                    if attempt < 2:
                        wait_time = 5 * (attempt + 1)  # Increasing wait time: 5s, 10s
                        print(f"   Connection/timeout error detected. Retrying in {wait_time} seconds...", flush=True)
                        time.sleep(wait_time)
                        continue
                
                # If it's the last attempt, raise the error
                if attempt == 2:
                    raise e
        
        return None
        
    except Exception as e:
        print(f"   ❌ ERROR: Failed to initialize driver after 3 attempts: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        return None

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
        print(f"      Retrieved {len(logs)} performance log entries", flush=True)
        
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
        # Performance logs not available, use DOM fallback (this is normal in some environments)
        error_msg = str(e)[:80]
        if "HTTPConnectionPool" in error_msg or "performance" in error_msg.lower():
            # This is expected - CDP not available, use DOM
            print("      Performance logs not available, using DOM extraction...", flush=True)
        else:
            print(f"      Log error: {error_msg}", flush=True)
        return extract_prices_from_dom(driver)

    if not api_urls:
        print("      No API URLs found in network logs. Using DOM extraction...", flush=True)
        return extract_prices_from_dom(driver)

    print(f"      Found {len(api_urls)} potential API URLs", flush=True)

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
            print(f"      Trying API: {api_url[:80]}...", flush=True)
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

            print(f"      Found {len(items)} items in API response", flush=True)

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
                        print(f"      Found {category}: ${price}", flush=True)

                except Exception as e:
                    continue

        except requests.exceptions.RequestException:
            continue
        except json.JSONDecodeError:
            continue
        except Exception as e:
            print(f"      API error: {str(e)[:50]}", flush=True)
            continue
    
    return prices

def extract_prices_from_dom(driver):
    """Fallback: Extract prices from DOM if API extraction fails"""
    prices = {}
    
    try:
        # Wait for page to stabilize
        time.sleep(2)
        
        # Strategy 1: Look for elements with aria-label containing Category and price
        try:
            driver.implicitly_wait(2)
            aria_elements = driver.find_elements(By.XPATH, "//*[@aria-label]")
            driver.implicitly_wait(10)
            
            if len(aria_elements) > 0:
                print(f"      Found {len(aria_elements)} elements with aria-label", flush=True)
            
            # Process elements
            for elem in aria_elements[:50]:  # Increased back to 50 for better coverage
                try:
                    aria_text = elem.get_attribute('aria-label') or ''
                    if not aria_text or len(aria_text) < 5:
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
                                    print(f"      Found {cat_name}: ${price_val} (aria-label)", flush=True)
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            print(f"      Aria-label search error: {str(e)[:50]}", flush=True)
        
        # Strategy 2: If we don't have all categories, try finding price elements and looking for category nearby
        if len(prices) < 4:
            try:
                print(f"      Trying price element search (found {len(prices)}/4 categories)...", flush=True)
                # Find elements containing price-like text
                price_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '$') or contains(@aria-label, '$')]")
                
                print(f"      Found {len(price_elements)} price-like elements", flush=True)
                
                for price_elem in price_elements[:100]:
                    try:
                        # Get text content
                        elem_text = price_elem.text or price_elem.get_attribute('textContent') or ''
                        if not elem_text:
                            continue
                        
                        # Extract price
                        price_match = re.search(r'\$\s*([\d,]{2,})', elem_text)
                        if not price_match:
                            continue
                        
                        try:
                            price_val = float(price_match.group(1).replace(',', ''))
                            if not (35 <= price_val <= 50000):
                                continue
                        except:
                            continue
                        
                        # Look for category label - check parent elements
                        category_found = None
                        current = price_elem
                        
                        for level in range(5):  # Check up to 5 levels up
                            try:
                                parent_text = current.get_attribute('textContent') or current.text or ''
                                
                                # Look for "Category X" in parent text
                                cat_match = re.search(r'(?:Category|Cat)\s+([1-4])\b', parent_text, re.I)
                                if cat_match:
                                    cat_num = cat_match.group(1)
                                    category_found = f"Category {cat_num}"
                                    break
                                
                                # Try to go up one level
                                current = current.find_element(By.XPATH, "..")
                            except:
                                break
                        
                        # Also check aria-label of price element itself
                        if not category_found:
                            aria_label = price_elem.get_attribute('aria-label') or ''
                            cat_match = re.search(r'(?:Category|Cat)\s+([1-4])\b', aria_label, re.I)
                            if cat_match:
                                category_found = f"Category {cat_match.group(1)}"
                        
                        if category_found:
                            # Keep minimum price per category
                            if category_found not in prices or price_val < prices[category_found]:
                                prices[category_found] = price_val
                                print(f"      Found {category_found}: ${price_val} (DOM traversal)", flush=True)
                    except:
                        continue
            except Exception as e:
                print(f"      Price element search error: {str(e)[:50]}", flush=True)
        
        # Strategy 3: Simple text scan for remaining categories
        if len(prices) < 2:
            try:
                print(f"      Trying text scan (found {len(prices)}/4 categories)...", flush=True)
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                
                # Limit text length
                if len(body_text) > 50000:
                    body_text = body_text[:50000]
                
                for cat_num in ['1', '2', '3', '4']:
                    cat_name = f"Category {cat_num}"
                    if cat_name in prices:
                        continue
                    
                    # Find "Category X" followed by price
                    pattern = rf"(?:Category|Cat)\s+{cat_num}\b[^$]*?\$\s*([\d,]{{2,}})"
                    matches = list(re.finditer(pattern, body_text, re.I | re.DOTALL))
                    
                    best_price = None
                    for match in matches[:5]:
                        try:
                            price_str = match.group(1)
                            price_val = float(price_str.replace(',', ''))
                            if 35 <= price_val <= 50000:
                                if best_price is None or price_val < best_price:
                                    best_price = price_val
                        except:
                            continue
                    
                    if best_price:
                        prices[cat_name] = best_price
                        print(f"      Found {cat_name}: ${best_price} (text scan)", flush=True)
            except Exception as e:
                print(f"      Text scan error: {str(e)[:50]}", flush=True)
    
    except Exception as e:
        print(f"      DOM fallback error: {str(e)[:50]}", flush=True)
    
    return prices

# =========================
# MAIN
# =========================
def run():
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING...', flush=True)
    
    games = load_json(GAMES_FILE, [])
    if not games:
        print("ERROR: No games file found", flush=True)
        return

    print(f"   Target: {len(games)} games...", flush=True)

    print(f"   Initializing Chrome driver...", flush=True)
    driver = get_driver()
    if not driver:
        print("ERROR: Failed to initialize driver - cannot continue", flush=True)
        return
    
    print(f"   ✅ Driver ready, starting to process games...", flush=True)
    results = []
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        for idx, game in enumerate(games, 1):
            print(f"   Processing match {idx}/{len(games)}...", flush=True)
            # Restart driver every 5 matches to prevent slowdowns
            if idx > 1 and idx % 5 == 1:
                print(f"   🔄 Restarting driver (match {idx})...", flush=True)
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(2)
                driver = get_driver()
                if not driver:
                    print(f"   ERROR: Failed to restart driver, skipping", flush=True)
                    continue
            
            url = game["url"]
            name = game.get("match_name", "Unknown Match")

            print(f"[{idx}/{len(games)}] {name}", flush=True)

            if "Currency=USD" not in url:
                url += "&Currency=USD" if "?" in url else "?Currency=USD"

            try:
                print(f"   Loading page...", flush=True)
                # Check driver health before loading
                try:
                    driver.current_url
                except Exception as health_err:
                    print(f"   ERROR: Driver unhealthy before page load: {str(health_err)[:50]}", flush=True)
                    # Try to restart driver
                    try:
                        driver.quit()
                    except:
                        pass
                    time.sleep(2)
                    driver = get_driver()
                    if not driver:
                        print(f"   ERROR: Failed to restart driver, skipping match", flush=True)
                        continue
                
                driver.get(url)
            except Exception as e:
                error_msg = str(e).lower()
                print(f"   ERROR: Failed to load page: {str(e)[:100]}", flush=True)
                
                # Check if it's a critical error requiring driver restart
                is_critical = any(keyword in error_msg for keyword in [
                    'httpconnectionpool', 'timeout', 'connection', 'disconnected', 
                    'crashed', 'target closed', 'chrome not reachable'
                ])
                
                if is_critical:
                    print(f"   🔥 Critical Driver Error: {str(e)[:100]}", flush=True)
                    print(f"   ⚠️ Driver Unstable (Critical Driver Error detected in worker). Restarting...", flush=True)
                    try:
                        driver.quit()
                    except:
                        pass
                    time.sleep(3)
                    driver = get_driver()
                    if not driver:
                        print(f"   ERROR: Failed to restart driver, skipping match", flush=True)
                        continue
                
                continue

            # Allow XHRs to load (reduced to 6s for speed)
            print(f"   Waiting for page to load...", flush=True)
            time.sleep(6)

            print(f"   Extracting prices...", flush=True)
            extraction_start = time.time()
            
            # Add timeout protection for extraction (max 30 seconds)
            extraction_result = {'prices': {}, 'done': False, 'error': None}
            
            def extract_worker():
                try:
                    extraction_result['prices'] = extract_prices_from_network(driver)
                    extraction_result['done'] = True
                except Exception as e:
                    extraction_result['error'] = e
                    extraction_result['done'] = True
            
            extract_thread = threading.Thread(target=extract_worker, daemon=True)
            extract_thread.start()
            extract_thread.join(timeout=30)
            
            if extract_thread.is_alive():
                print(f"   ERROR: Extraction exceeded 30s timeout, aborting...", flush=True)
                prices = {}
            elif extraction_result['error']:
                print(f"   ERROR: Extraction error: {str(extraction_result['error'])[:80]}", flush=True)
                prices = {}
            else:
                prices = extraction_result['prices']
            
            extraction_time = time.time() - extraction_start
            
            if extraction_time > 10:
                print(f"   WARNING: Extraction took {extraction_time:.1f}s (slow)", flush=True)

            if not prices:
                print(f"   ❌ No prices found for {name} (tried network + DOM)", flush=True)
                # Try one more time with a longer wait if first attempt failed
                if idx == 1:  # Only retry for first match
                    print(f"   Retrying first match with longer wait...", flush=True)
                    time.sleep(5)
                    prices = extract_prices_from_network(driver)
                    if prices:
                        print(f"   ✅ Found prices on retry: {prices}", flush=True)
                    else:
                        print(f"   ❌ Still no prices after retry", flush=True)
                        continue
                else:
                    continue

            print(f"   ✅ Found prices: {prices}", flush=True)

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
                        

    except Exception as e: 
        print(f"ERROR: Fatal error in scraper: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        try:
            driver.quit()
        except:
            pass

    if results:
        append_json(OUTPUT_FILE, results)
        print(f"\nSaved {len(results)} rows to {OUTPUT_FILE}", flush=True)
    
    print(f'[{datetime.now().strftime("%H:%M")}] 💤 VIAGOGO SCRAPER COMPLETE.', flush=True)

# =========================
if __name__ == "__main__":
    run()
