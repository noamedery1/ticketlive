import json
import os
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime

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

def extract_prices_clean(driver):
    """
    Clean, robust strategy to find 'Category X' labels and associated prices.
    Strategy: Find 'Category X' text -> Check Container -> Find Price.
    """
    prices = {}
    try:
        # 0. Trigger visual rendering
        driver.execute_script("window.scrollBy(0, 200);")
        time.sleep(1)

        # ------------------------------------------------------------------
        # APPROACH 1: "Anchor & Context" (Robust)
        # ------------------------------------------------------------------
        # We look for explicit Category labels: 1, 2, 3, 4
        for i in range(1, 5):
            cat_name = f"Category {i}"
            
            # Find all elements containing this specific text
            anchors = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(text()), '{cat_name}')]")
            if not anchors:
                 anchors = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(text()), 'Cat {i}')]")
            
            best_price = None
            
            for anchor in anchors:
                try:
                    # 1. Get the container (Button or Div)
                    # We climb up 3 levels maximum to find a meaningful container
                    # e.g. span -> div -> button
                    container = anchor
                    valid_price = None
                    
                    # Check Anchor, Parent, Grandparent
                    for level in range(3):
                        txt = container.text.replace('\n', ' ').strip()
                        
                        # Look for price pattern with optional currency
                        # We try to capture the symbol if present
                        price_matches = re.finditer(r'(?:\$|₪|USD|ILS|NIS)?\s*([\d,]{2,})', txt)
                        
                        min_p = float('inf')
                        found = False
                        
                        for pm in price_matches:
                            try:
                                p_str = pm.group(1)
                                full_match = pm.group(0)
                                
                                val = float(p_str.replace(',', ''))
                                
                                # Filter out garbage
                                if val < 35: continue 
                                if val > 50000: continue 
                                
                                # Currency Conversion Logic
                                # 1. Check direct symbol capture
                                is_ils = '₪' in full_match or 'ILS' in full_match or 'NIS' in full_match
                                # 2. Check context if symbol missing 
                                if not is_ils and ('₪' in txt or 'ILS' in txt or 'NIS' in txt):
                                     is_ils = True
                                
                                if is_ils: val = round(val * ILS_TO_USD, 2)
                                
                                if val < min_p:
                                    min_p = val
                                    found = True
                            except: pass
                        
                        if found:
                            valid_price = min_p
                            break # Found a price in this container level, stop climbing
                        
                        # Climb up one level
                        try: container = container.find_element(By.XPATH, "..")
                        except: break

                    if valid_price:
                        if best_price is None or valid_price < best_price:
                            best_price = valid_price
                            # print(f"      [DEBUG] Found {cat_name}: ${best_price} in context: '{txt[:30]}...'")
                            
                except: pass
            
            if best_price:
                prices[cat_name] = best_price

        # ------------------------------------------------------------------
        # APPROACH 2: Aria-Label Scan (Backup for Screen Readers)
        # ------------------------------------------------------------------
        if not prices:
            aria_els = driver.find_elements(By.XPATH, "//*[@aria-label]")
            for el in aria_els:
                try:
                    txt = el.get_attribute('aria-label')
                    if 'Category' in txt:
                        m_cat = re.search(r'Category\s+(\d)', txt, re.I)
                        m_price = re.search(r'(\$|₪|USD)\s*([\d,]+)', txt)
                        
                        if m_cat and m_price:
                            c = m_cat.group(1)
                            p = float(m_price.group(2).replace(',', ''))
                            if '₪' in txt: p = round(p * ILS_TO_USD, 2)
                            
                            key = f"Category {c}"
                            if int(c) <= 4:
                                prices[key] = p
                except: pass

        if not prices:
            # DEBUG: Print Body snippet to see what's actually there
            try:
                page_title = driver.title
                print(f"      [DEBUG TITLE] {page_title}")
                
                body_txt = driver.find_element(By.TAG_NAME, 'body').text
                clean_body = body_txt[:500].replace('\n', ' | ')
                print(f"      [DEBUG BODY] {clean_body}...")
                
                # Check if "Category" exists ANYWHERE
                if 'Category' not in body_txt:
                     print("      ⚠️ 'Category' word NOT found in body text.")
            except: pass

        return prices

    except Exception as e:
        print(f"      ⚠️ Extract Error: {e}")
        return {}

def get_driver():
    try:
        options = uc.ChromeOptions()
        if os.environ.get('HEADLESS') == 'true':
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-extensions')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
            options.page_load_strategy = 'eager' 

        browser_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
        driver_path = '/usr/bin/chromedriver' if os.path.exists('/usr/bin/chromedriver') else None

        for attempt in range(3):
            try:
                driver = uc.Chrome(
                    options=options, version_main=None, 
                    browser_executable_path=browser_path, driver_executable_path=driver_path
                )
                driver.set_page_load_timeout(60)
                return driver
            except OSError as e:
                if 'Text file busy' in str(e): time.sleep(5)
                else: raise e
    except Exception as e:
        print(f'❌ [ERROR] Failed to start Chrome Driver: {e}')
        return None

def run_scraper_cycle():
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING (CLEAN ANCHOR STRATEGY)...')
    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found!')
        return

    with open(GAMES_FILE, 'r') as games_f: 
        games = json.load(games_f)

    driver = get_driver()
    timestamp = datetime.now().isoformat()
    new_records_buffer = []

    try:
        for i, game in enumerate(games, 1):
            if i > 1 and i % 10 == 0:
                try: driver.quit()
                except: pass
                driver = get_driver()

            if driver is None: driver = get_driver()
            if not driver: continue

            match_name = game['match_name']
            url = game['url']
            clean_url = url.split('&Currency')[0].split('?Currency')[0]
            target_url = url + ('&Currency=USD' if '?' in url else '?Currency=USD')
            
            print(f'[{i}/{len(games)}] {match_name[:30]}... ', end='', flush=True)
            
            for attempt in range(3):
                try:
                    driver.get(target_url)
                    if '502' in driver.title:
                        time.sleep(5); continue
                        
                    # 1. Try standard extract
                    prices = extract_prices_clean(driver)
                    
                    # 2. Interactive: Click "Listings" summary if no data found
                    if not prices:
                        try:
                            listings_clicked = False
                            # Look for clickable "X listings" text
                            list_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'listings')]")
                            for le in list_els:
                                if 'ticket' not in le.text.lower() and len(le.text) < 30 and le.is_displayed():
                                     print(f"      🖱️ Clicking Listing Summary: '{le.text}'")
                                     try: driver.execute_script("arguments[0].click();", le)
                                     except: le.click()
                                     time.sleep(3)
                                     listings_clicked = True
                                     break
                                     
                            if listings_clicked:
                                print('   🔄 Listings expanded. Retrying extraction...')
                                prices = extract_prices_clean(driver)
                        except: pass

                    if prices:
                        for cat, price in prices.items():
                            new_records_buffer.append({
                                'match_url': clean_url, 'match_name': match_name,
                                'category': cat, 'price': price, 'currency': 'USD', 'timestamp': timestamp
                            })
                        print(f'✅ Found {json.dumps(prices)}')
                        break 
                    else:
                        print('❌ No data found.')
                        try:
                            with open(f'debug_failed_scrape_{i}.html', 'w', encoding='utf-8') as f: f.write(driver.page_source)
                        except: pass
                        break
                        
                except Exception as e: 
                    msg = str(e).lower()
                    if 'crashed' in msg or 'disconnected' in msg: raise e 
                    time.sleep(2)
            time.sleep(1) 

        if new_records_buffer: append_data(DATA_FILE_VIAGOGO, new_records_buffer)
        
        time.sleep(1.0)
        
    except Exception as e: print(f'🔥 Error: {e}')
    finally:
        try: driver.quit()
        except: pass
        print(f'[{datetime.now().strftime("%H:%M")}] 💤 VIAGOGO CYCLE COMPLETE.')

if __name__ == '__main__':
    run_scraper_cycle()