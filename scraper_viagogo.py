import json
import os
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
try:
    from pyvirtualdisplay import Display
except ImportError:
    pass

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
DATA_FILE_VIAGOGO = 'prices.json'
GAMES_FILE = 'all_games_to_scrape.json'
ILS_TO_USD = 0.28
# ==========================================

def load_data(file_path):
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except: return []

def append_data(file_path, new_records):
    data = load_data(file_path)
    data.extend(new_records)
    with open(file_path, 'w') as f: json.dump(data, f)

def extract_prices_simple(driver):
    """
    Simple, direct approach: Find price elements, then find their category labels.
    Much faster and more reliable than the complex fallback approach.
    """
    prices = {}
    start_time = time.time()
    
    try:
        print("      ➡️ Starting simple extraction...", flush=True)
        
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
                    
                    # Look for "Category X" pattern
                    cat_match = re.search(r'Category\s+([1-4])\b', aria_text, re.I)
                    if not cat_match:
                        continue
                    
                    cat_num = cat_match.group(1)
                    cat_name = f"Category {cat_num}"
                    
                    # Skip if already found
                    if cat_name in prices:
                        continue
                    
                    # Extract price from aria-label
                    price_match = re.search(r'(?:\$|₪|USD|ILS)?\s*([\d,]{2,})', aria_text)
                    if price_match:
                        try:
                            price_val = float(price_match.group(1).replace(',', ''))
                            if 35 <= price_val <= 50000:
                                # Check if ILS currency
                                if '₪' in aria_text or 'ILS' in aria_text or 'NIS' in aria_text:
                                    price_val = round(price_val * ILS_TO_USD, 2)
                                
                                # Keep minimum price per category
                                if cat_name not in prices or price_val < prices[cat_name]:
                                    prices[cat_name] = price_val
                                    print(f"      ✅ Found {cat_name}: ${price_val} (aria-label)", flush=True)
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            print(f"      ⚠️ Aria-label search error: {str(e)[:50]}")
        
        # Strategy 2: Find price elements and look for category labels nearby
        # This handles cases where aria-label doesn't have the price
        if len(prices) < 4:
            try:
                # Find all elements containing price-like text
                price_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '$') or contains(text(), '₪') or contains(@aria-label, '$')]")
                
                for price_elem in price_elements[:100]:  # Limit to avoid hanging
                    try:
                        # Get text content
                        elem_text = price_elem.text or price_elem.get_attribute('textContent') or ''
                        if not elem_text:
                            continue
                        
                        # Extract price
                        price_match = re.search(r'(?:\$|₪|USD|ILS)?\s*([\d,]{2,})', elem_text)
                        if not price_match:
                            continue
                        
                        try:
                            price_val = float(price_match.group(1).replace(',', ''))
                            if not (35 <= price_val <= 50000):
                                continue
                            
                            # Check if ILS
                            is_ils = '₪' in elem_text or 'ILS' in elem_text or 'NIS' in elem_text
                            if is_ils:
                                price_val = round(price_val * ILS_TO_USD, 2)
                        except:
                            continue
                        
                        # Now look for category label - check parent elements
                        category_found = None
                        current = price_elem
                        
                        for level in range(5):  # Check up to 5 levels up
                            try:
                                # Get parent's text
                                parent_text = current.get_attribute('textContent') or current.text or ''
                                
                                # Look for "Category X" in parent text
                                cat_match = re.search(r'Category\s+([1-4])\b', parent_text, re.I)
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
                            cat_match = re.search(r'Category\s+([1-4])\b', aria_label, re.I)
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
                print(f"      ⚠️ Price element search error: {str(e)[:50]}")
        
        # Strategy 3: Simple text scan for remaining categories (only if we have < 2 categories)
        if len(prices) < 2:
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
                    
                    # Find "Category X" followed by price within reasonable distance
                    pattern = rf"Category\s+{cat_num}\b[^$]*?(?:\$|₪|USD|ILS)?\s*([\d,]{{2,}})"
                    matches = list(re.finditer(pattern, body_text, re.I | re.DOTALL))
                    
                    best_price = None
                    for match in matches[:5]:  # Limit matches
                        try:
                            price_str = match.group(1)
                            price_val = float(price_str.replace(',', ''))
                            if 35 <= price_val <= 50000:
                                # Check context for currency
                                context = body_text[max(0, match.start()-100):match.end()+100]
                                if '₪' in context or 'ILS' in context or 'NIS' in context:
                                    price_val = round(price_val * ILS_TO_USD, 2)
                                
                                if best_price is None or price_val < best_price:
                                    best_price = price_val
                        except:
                            continue
                    
                    if best_price:
                        prices[cat_name] = best_price
                        print(f"      ✅ Found {cat_name}: ${best_price} (text scan)", flush=True)
            except Exception as e:
                print(f"      ⚠️ Text scan error: {str(e)[:50]}")
        
        elapsed = time.time() - start_time
        print(f"      ✅ Extraction complete in {elapsed:.1f}s: found {len(prices)} categories", flush=True)
        return prices
        
    except Exception as e:
        elapsed = time.time() - start_time
        msg = str(e).lower()
        if 'crashed' in msg or 'disconnected' in msg:
            print(f"      🔥 Critical error after {elapsed:.1f}s: {msg[:50]}")
            raise e
        print(f"      ⚠️ Extraction error after {elapsed:.1f}s: {str(e)[:50]}")
        return prices  # Return what we have

def _create_chrome_options():
    """Create a fresh ChromeOptions object with stability flags"""
    options = uc.ChromeOptions()
    
    # Essential flags for Docker/server
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Stability flags
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-session-crashed-bubble')
    options.add_argument('--disable-crash-reporter')
    options.add_argument('--js-flags=--max-old-space-size=2048')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-renderer-backgrounding')
    
    # Block images to save resources
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    options.page_load_strategy = 'eager'
    return options

def get_driver():
    """Get a fresh Chrome driver instance"""
    try:
        browser_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
        driver_path = '/usr/bin/chromedriver' if os.path.exists('/usr/bin/chromedriver') else None

        for attempt in range(3):
            try:
                options = _create_chrome_options()
                driver = uc.Chrome(
                    options=options, 
                    version_main=None, 
                    browser_executable_path=browser_path, 
                    driver_executable_path=driver_path
                )
                driver.set_page_load_timeout(60)
                driver.implicitly_wait(5)
                driver.set_script_timeout(30)
                return driver
            except OSError as e:
                if 'Text file busy' in str(e):
                    print(f'      ⚠️ Driver file busy (attempt {attempt+1}/3). Waiting...')
                    time.sleep(3)
                    if attempt == 2:
                        raise e
                else:
                    raise e
            except Exception as e:
                error_msg = str(e).lower()
                if 'cannot reuse' in error_msg:
                    print(f'      ⚠️ Options reuse error (attempt {attempt+1}/3). Retrying...')
                    time.sleep(2)
                    continue
                raise e
    except Exception as e:
        print(f'❌ [ERROR] Failed to start Chrome Driver: {e}')
        return None

def run_scraper_cycle():
    """Main scraper cycle - processes all games"""
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING (SIMPLE APPROACH)...')
    
    # Start virtual display if needed
    display = None
    if os.environ.get('HEADLESS') == 'true':
        try:
            print("      🖥️ Starting Virtual Display (XVFB)...")
            display = Display(visible=0, size=(1920, 1080))
            display.start()
        except Exception as e:
            print(f"      ⚠️ Failed to start XVFB: {e}")

    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found!')
        if display:
            display.stop()
        return

    with open(GAMES_FILE, 'r') as games_f:
        games = json.load(games_f)

    driver = None
    timestamp = datetime.now().isoformat()
    new_records_buffer = []

    try:
        for i, game in enumerate(games, 1):
            # Restart driver before EACH match for fresh state
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                time.sleep(1)
            
            driver = get_driver()
            if not driver:
                print(f"      ❌ Failed to get driver, skipping match {i}", flush=True)
                continue
            
            match_name = game['match_name']
            url = game['url']
            clean_url = url.split('&Currency')[0].split('?Currency')[0]
            target_url = url + ('&Currency=USD' if '?' in url else '?Currency=USD')
            
            print(f'[{i}/{len(games)}] {match_name[:40]}... ', end='', flush=True)
            
            for attempt in range(2):  # Reduced retries - simpler approach
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
                    
                    # Wait for page to load, then stop heavy resources
                    time.sleep(8)  # Reduced wait time
                    try:
                        driver.execute_script("window.stop();")
                    except:
                        pass
                    
                    # Extract prices with simple method
                    prices = extract_prices_simple(driver)
                    
                    if prices:
                        # Save results
                        for cat, price in prices.items():
                            new_records_buffer.append({
                                'match_url': clean_url,
                                'match_name': match_name,
                                'category': cat,
                                'price': price,
                                'currency': 'USD',
                                'timestamp': timestamp
                            })
                        
                        print(f'✅ Found {json.dumps(prices)}')
                        
                        # Save immediately
                        if new_records_buffer:
                            append_data(DATA_FILE_VIAGOGO, new_records_buffer)
                            new_records_buffer = []
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
                    print(f"      ⚠️ Error (attempt {attempt+1}/2): {msg[:80]}")
                    
                    # Check if critical error requiring restart
                    is_critical = any(keyword in msg for keyword in [
                        'crashed', 'disconnected', 'tab crashed', 'target closed',
                        'chrome not reachable', 'timeout: timed out receiving message'
                    ])
                    
                    if is_critical:
                        try:
                            driver.quit()
                        except:
                            pass
                        time.sleep(2)
                        driver = get_driver()
                        if not driver:
                            break  # Skip this match
                    
                    if attempt == 1:
                        break  # Move to next match after 2 attempts
            
            time.sleep(0.5)  # Brief pause between matches
        
    except Exception as e:
        print(f'🔥 Fatal Error: {e}')
    finally:
        try:
            if driver:
                driver.quit()
        except:
            pass
        if display:
            try:
                display.stop()
            except:
                pass
        print(f'[{datetime.now().strftime("%H:%M")}] 💤 VIAGOGO CYCLE COMPLETE.')

if __name__ == '__main__':
    run_scraper_cycle()
