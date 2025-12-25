import json
import os
import re
import time
import sys
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OUTPUT_FILE = 'prices.json'
GAMES_FILE = 'all_games_to_scrape.json'

# ==========================================
# UTILS
# ==========================================
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

# ==========================================
# PRICE EXTRACTION - Simple HTML/DOM approach
# ==========================================
def extract_prices_simple(driver):
    """
    Simple, direct approach: Get HTML from browser and extract prices from DOM elements.
    Works better locally than network interception.
    """
    prices = {}
    start_time = time.time()
    
    try:
        print("      ➡️ Starting simple HTML extraction...", flush=True)
        
        # Wait for page to be ready
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # Strategy 1: Find elements with aria-label containing "Category" and price
        # This is the most reliable method - Viagogo uses aria-labels for accessibility
        try:
            driver.implicitly_wait(2)  # Short wait
            aria_elements = driver.find_elements(By.XPATH, "//*[@aria-label]")
            
            for elem in aria_elements[:50]:  # Limit to first 50 to avoid hanging
                try:
                    aria_text = elem.get_attribute('aria-label') or ''
                    if not aria_text:
                        continue
                    
                    # Look for "Category X" or "Cat X" pattern
                    cat_match = re.search(r'(?:Category|Cat)\s+([1-4])\b', aria_text, re.I)
                    if not cat_match:
                        continue
                    
                    cat_num = cat_match.group(1)
                    cat_name = f"Category {cat_num}"
                    
                    # Skip if already found
                    if cat_name in prices:
                        continue
                    
                    # Extract price from aria-label (page should be in USD)
                    price_match = re.search(r'(?:\$|USD)?\s*([\d,]{2,})', aria_text)
                    if price_match:
                        try:
                            price_val = float(price_match.group(1).replace(',', ''))
                            if 35 <= price_val <= 50000:
                                # Keep minimum price per category
                                if cat_name not in prices or price_val < prices[cat_name]:
                                    prices[cat_name] = price_val
                                    print(f"      ✅ Found {cat_name}: ${price_val} (aria-label)", flush=True)
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            print(f"      ⚠️ Aria-label search error: {str(e)[:50]}", flush=True)
        
        # Strategy 2: Find price elements and look for category labels nearby
        # This handles cases where aria-label doesn't have the price
        if len(prices) < 4:
            try:
                # Find all elements containing price-like text
                price_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '$') or contains(@aria-label, '$')]")
                
                for price_elem in price_elements[:100]:  # Limit to avoid hanging
                    try:
                        # Get text content
                        elem_text = price_elem.text or price_elem.get_attribute('textContent') or ''
                        if not elem_text:
                            continue
                        
                        # Extract price
                        price_match = re.search(r'(?:\$|USD)?\s*([\d,]{2,})', elem_text)
                        if not price_match:
                            continue
                        
                        try:
                            price_val = float(price_match.group(1).replace(',', ''))
                            if not (35 <= price_val <= 50000):
                                continue
                        except:
                            continue
                        
                        # Now look for category label - check parent elements
                        category_found = None
                        current = price_elem
                        
                        for level in range(5):  # Check up to 5 levels up
                            try:
                                # Get parent's text
                                parent_text = current.get_attribute('textContent') or current.text or ''
                                
                                # Look for "Category X" or "Cat X" in parent text
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
                                print(f"      ✅ Found {category_found}: ${price_val} (DOM traversal)", flush=True)
                    except:
                        continue
            except Exception as e:
                print(f"      ⚠️ Price element search error: {str(e)[:50]}", flush=True)
        
        # Strategy 3: Simple text scan for remaining categories
        if len(prices) < 3 or 'Category 1' not in prices:
            try:
                print("      🔍 Trying text scan for missing categories...", flush=True)
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                
                # Limit text length to avoid memory issues
                if len(body_text) > 50000:
                    body_text = body_text[:50000]
                
                for cat_num in ['1', '2', '3', '4']:
                    cat_name = f"Category {cat_num}"
                    if cat_name in prices:
                        continue
                    
                    # Find "Category X" or "Cat X" followed by price within reasonable distance
                    pattern = rf"(?:Category|Cat)\s+{cat_num}\b[^$]*?(?:\$|USD)?\s*([\d,]{{2,}})"
                    matches = list(re.finditer(pattern, body_text, re.I | re.DOTALL))
                    
                    best_price = None
                    for match in matches[:5]:  # Limit matches
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
                        print(f"      ✅ Found {cat_name}: ${best_price} (text scan)", flush=True)
            except Exception as e:
                print(f"      ⚠️ Text scan error: {str(e)[:50]}", flush=True)
        
        elapsed = time.time() - start_time
        print(f"      ✅ Extraction complete in {elapsed:.1f}s: found {len(prices)} categories", flush=True)
        return prices
        
    except Exception as e:
        elapsed = time.time() - start_time
        msg = str(e).lower()
        if 'crashed' in msg or 'disconnected' in msg:
            print(f"      🔥 Critical error after {elapsed:.1f}s: {msg[:50]}", flush=True)
            raise e
        print(f"      ⚠️ Extraction error after {elapsed:.1f}s: {str(e)[:50]}", flush=True)
        return prices  # Return what we have

# ==========================================
# DRIVER SETUP - Simple for local use
# ==========================================
def get_driver():
    """Get a Chrome driver instance - optimized for local use"""
    import random
    
    # Add small random delay to prevent both scrapers from initializing at exact same time
    time.sleep(random.uniform(0.5, 2.0))
    
    try:
        # Windows: Detect Chrome path (handle 32-bit vs 64-bit)
        if sys.platform == 'win32':
            # Try 32-bit Chrome first (Program Files x86)
            browser_path = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
            if not os.path.exists(browser_path):
                # Try 64-bit Chrome
                browser_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
            if not os.path.exists(browser_path):
                browser_path = None
            # Try to use manually downloaded ChromeDriver (32-bit for 32-bit Chrome)
            driver_path = r'C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe'
            if not os.path.exists(driver_path):
                driver_path = None  # Fall back to auto-download
        else:
            browser_path = None
            driver_path = None
        options = uc.ChromeOptions()
        
        # Basic options for local use (no headless needed)
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Optional: Block images to save resources
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        
        options.page_load_strategy = 'eager'
        
        for attempt in range(5):  # Increased retries
            try:
                driver = uc.Chrome(
                    use_subprocess=False,  # Avoid subprocess issues on Windows 7
                    options=options, 
                    version_main=None,
                    browser_executable_path=browser_path,  # Explicitly set Chrome path
                    driver_executable_path=driver_path  # Use manually downloaded ChromeDriver if available
                )
                driver.set_page_load_timeout(60)
                driver.implicitly_wait(5)
                driver.set_script_timeout(30)
                return driver
            except OSError as e:
                error_str = str(e)
                # Handle Windows file lock errors
                if 'Text file busy' in error_str or 'WinError 32' in error_str or 'WinError 183' in error_str or 'being used by another process' in error_str or 'already exists' in error_str:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s, 8s, 10s
                    print(f'      ⚠️ Driver file locked by another process (attempt {attempt+1}/5). Waiting {wait_time}s...', flush=True)
                    time.sleep(wait_time)
                    if attempt < 4:
                        continue
                    else:
                        raise e
                else:
                    raise e
            except Exception as e:
                error_msg = str(e).lower()
                if 'cannot reuse' in error_msg or 'chromeoptions' in error_msg:
                    wait_time = (attempt + 1) * 1.5
                    print(f'      ⚠️ Options reuse error (attempt {attempt+1}/5). Retrying in {wait_time:.1f}s...', flush=True)
                    time.sleep(wait_time)
                    continue
                # Check for file lock errors in exception message too
                error_str = str(e)
                if 'WinError 32' in error_str or 'WinError 183' in error_str or 'being used by another process' in error_str:
                    wait_time = (attempt + 1) * 2
                    print(f'      ⚠️ File lock error (attempt {attempt+1}/5). Waiting {wait_time}s...', flush=True)
                    time.sleep(wait_time)
                    if attempt < 4:
                        continue
                raise e
    except Exception as e:
        print(f'❌ [ERROR] Failed to start Chrome Driver: {e}', flush=True)
        return None

# ==========================================
# MAIN SCRAPER
# ==========================================
def run():
    start_time = time.time()
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING (SIMPLE HTML APPROACH)...', flush=True)
    
    games = load_json(GAMES_FILE, [])
    if not games:
        print("ERROR: No games file found", flush=True)
        return

    print(f"   Target: {len(games)} games...", flush=True)

    driver = None
    timestamp = datetime.now().isoformat()
    results = []

    try:
        for i, game in enumerate(games, 1):
            # Restart driver every 5 matches to prevent crashes (more frequent restarts)
            if i > 1 and i % 5 == 1:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                    time.sleep(2)  # Wait before restart
                
                print(f"   [RESTART] Scheduled driver restart (match {i})...", flush=True)
            
            # Check if driver is still alive before using it
            if driver:
                try:
                    # Quick health check
                    driver.current_url
                except Exception as health_check:
                    print(f"   ⚠️ Driver unhealthy, restarting... ({str(health_check)[:50]})", flush=True)
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
            
            if not driver:
                driver = get_driver()
                if not driver:
                    print(f"   ❌ Failed to get driver, skipping match {i}", flush=True)
                    continue
            
            match_name = game.get('match_name', 'Unknown Match')
            url = game['url']
            clean_url = url.split('&Currency')[0].split('?Currency')[0]
            
            # Ensure USD currency in URL
            target_url = url + ('&Currency=USD' if '?' in url else '?Currency=USD')
            
            print(f'[{i}/{len(games)}] {match_name[:40]}... ', end='', flush=True)
            
            for attempt in range(2):  # 2 attempts per match
                try:
                    # Load page
                    try:
                        driver.get(target_url)
                    except Exception as load_error:
                        if 'timeout' in str(load_error).lower():
                            try:
                                driver.execute_script("window.stop();")
                            except:
                                pass
                        else:
                            raise load_error
                    
                    # Wait for page to load
                    time.sleep(8)
                    
                    # Extract prices with simple HTML method
                    prices = extract_prices_simple(driver)
                    
                    if prices:
                        # Save results
                        for cat, price in prices.items():
                            results.append({
                                'match_url': clean_url,
                                'match_name': match_name,
                                'category': cat,
                                'price': price,
                                'currency': 'USD',
                                'timestamp': timestamp
                            })
                        
                        print(f'✅ {json.dumps(prices)}', flush=True)
                        break  # Success, move to next match
                    else:
                        if attempt == 0:
                            # Try clicking listings button on first attempt
                            try:
                                listings_els = driver.find_elements(By.XPATH, 
                                    "//*[contains(text(), 'listings') and string-length(text()) < 30]")
                                for le in listings_els[:3]:
                                    if le.is_displayed():
                                        try:
                                            driver.execute_script("arguments[0].click();", le)
                                            time.sleep(2)
                                            prices = extract_prices_simple(driver)
                                            if prices:
                                                break
                                        except:
                                            continue
                            except:
                                pass
                        
                        if not prices:
                            print('❌ No data found', flush=True)
                            if attempt == 1:
                                break  # Give up after 2 attempts
                
                except Exception as e:
                    msg = str(e).lower()
                    error_str = str(e)
                    print(f"      ⚠️ Error (attempt {attempt+1}/2): {msg[:80]}", flush=True)
                    
                    # Check if critical error requiring restart (including connection pool errors)
                    is_critical = any(keyword in msg or keyword in error_str.lower() for keyword in [
                        'crashed', 'disconnected', 'tab crashed', 'target closed',
                        'chrome not reachable', 'timeout: timed out receiving message',
                        'httpconnectionpool', 'connectionpool', 'max retries exceeded',
                        'connection refused', 'connection aborted', 'broken pipe',
                        'localhost', 'port 6'  # Chrome DevTools Protocol port errors
                    ])
                    
                    if is_critical:
                        print(f"      🔥 Critical driver error detected, restarting driver...", flush=True)
                        try:
                            driver.quit()
                        except:
                            pass
                        driver = None
                        time.sleep(3)  # Wait longer before restart
                        driver = get_driver()
                        if not driver:
                            print(f"      ❌ Failed to restart driver, skipping match {i}", flush=True)
                            break  # Skip this match
                        # Continue to retry with new driver
                        if attempt == 0:
                            continue  # Retry with new driver
                    
                    if attempt == 1:
                        break  # Move to next match after 2 attempts
            
            time.sleep(0.5)  # Brief pause between matches
        
    except KeyboardInterrupt:
        print(f"\n[WARN] Scraper interrupted by user", flush=True)
    except Exception as e: 
        print(f"ERROR: Fatal error in scraper: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        try:
            if driver:
                driver.quit()
        except:
            pass

    if results:
        try:
            append_json(OUTPUT_FILE, results)
            print(f"\n[OK] Saved {len(results)} rows to {OUTPUT_FILE}", flush=True)
        except Exception as save_err:
            print(f"\n[ERROR] Error saving results: {str(save_err)[:50]}", flush=True)
    
    runtime = time.time() - start_time
    print(f'[{datetime.now().strftime("%H:%M")}] [DONE] VIAGOGO SCRAPER COMPLETE (runtime: {int(runtime)}s).', flush=True)

# =========================
if __name__ == "__main__":
    run()
