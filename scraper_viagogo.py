import json
import os
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
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

def extract_prices_clean(driver):
    """
    Clean, robust strategy to find 'Category X' labels and fallback to Section Mapping.
    """
    prices = {}
    try:
        # 1. Wait for "Category" text or "Section" text
        for _ in range(5):
            body_txt = driver.find_element(By.TAG_NAME, 'body').text
            if 'Category' in body_txt or 'Cat ' in body_txt or '101' in body_txt:
                break
            time.sleep(1)

        # ------------------------------------------------------------------
        # APPROACH 1: "Anchor & Context" (Category Labels)
        # ------------------------------------------------------------------
        for i in range(1, 5):
            cat_name = f"Category {i}"
            
            # Find all elements containing this text
            anchors = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(text()), '{cat_name}')]")
            if not anchors:
                 anchors = driver.find_elements(By.XPATH, f"//*[contains(normalize-space(text()), 'Cat {i}')]")
            
            # DEBUG: Why is Cat 1 missing?
            if i == 1 and not anchors:
                print("      ⚠️ No 'Category 1' anchors found.")

            best_price = None
            
            for anchor in anchors:
                try:
                    container = anchor
                    valid_price = None
                    
                    # Check Anchor, Parent, Grandparent
                    for level in range(3):
                        txt = container.text.replace('\n', ' ').strip()
                        if i == 1:
                            print(f"      [DEBUG CAT1] '{txt[:50]}'")
                        
                        price_matches = re.finditer(r'(?:\$|₪|USD|ILS|NIS)?\s*([\d,]{2,})', txt)
                        min_p = float('inf')
                        found = False
                        
                        for pm in price_matches:
                            try:
                                p_str = pm.group(1)
                                full_match = pm.group(0)
                                val = float(p_str.replace(',', ''))
                                
                                if val < 35: continue 
                                if val > 50000: continue 
                                
                                is_ils = '₪' in full_match or 'ILS' in full_match or 'NIS' in full_match
                                if not is_ils and ('₪' in txt or 'ILS' in txt or 'NIS' in txt): is_ils = True
                                if is_ils: val = round(val * ILS_TO_USD, 2)
                                
                                if val < min_p:
                                    min_p = val
                                    found = True
                            except: pass
                        
                        if found:
                            valid_price = min_p
                            break 
                        
                        try: container = container.find_element(By.XPATH, "..")
                        except: break

                    if valid_price:
                        if best_price is None or valid_price < best_price:
                            best_price = valid_price
                except: pass
            
            # Fallback ONLY for Category 1 if best_price is missing
            if not best_price and i == 1:
                try:
                     print("      🔍 Checking fallback for Category 1...")
                     aria_pills = driver.find_elements(By.XPATH, "//*[@aria-label and contains(@aria-label, 'Category 1')]")
                     for el in aria_pills:
                         txt = el.get_attribute('aria-label')
                         m = re.search(r'(?:\$|₪|USD)?\s*([\d,]{2,})', txt)
                         if m:
                             p = float(m.group(1).replace(',', ''))
                             if '₪' in txt: p = round(p * ILS_TO_USD, 2)
                             if p > 35:
                                 best_price = p
                                 print(f"      ✅ Fallback found Cat 1: {best_price}")
                                 break
                except: pass

            if best_price:
                prices[cat_name] = best_price

        # ------------------------------------------------------------------
        # APPROACH 2: Interactive Section Mapping (Fallback if No Categories Found)
        # ------------------------------------------------------------------
        if not prices:
            # Map of Section Series -> Category
            series_map = {'1': 'Category 1', '2': 'Category 2', '3': 'Category 3', '4': 'Category 4'}
            
            for prefix, cat_label in series_map.items():
                if cat_label in prices: continue 
                
                # Check typical sections: 101, 102, 103...
                for suffix in ['01', '02', '03', '04', '05', '10']: 
                    sec_id = f"{prefix}{suffix}"
                    try:
                        els = driver.find_elements(By.XPATH, f"//*[contains(text(), '{sec_id}')]")
                        target_el = None
                        for el in els:
                            t = el.text.strip()
                            if t == sec_id or t == f"Section {sec_id}":
                                target_el = el
                                break
                        
                        if target_el and target_el.is_displayed():
                            print(f"      🖱️ Mapping Section {sec_id} -> {cat_label}...")
                            try: driver.execute_script("arguments[0].click();", target_el)
                            except: target_el.click()
                            time.sleep(3.0) 
                            
                            # Scan body for NEW price
                            body_txt = driver.find_element(By.TAG_NAME, 'body').text
                            pm = re.findall(r'(?:\$|₪|USD)?\s*([\d,]{2,})', body_txt)
                            found_p = None
                            curr_min = float('inf')
                            
                            for p_str in pm:
                                try:
                                    v = float(p_str.replace(',', ''))
                                    if v < 35: 
                                        # print(f"         ⚠️ Saw {v} but < 35 (ignored)")
                                        continue
                                    if v > 50000: continue
                                    if '₪' in body_txt: v = round(v * ILS_TO_USD, 2)
                                    if v < curr_min:
                                        curr_min = v
                                        found_p = v
                                except: pass
                                
                            if found_p:
                                prices[cat_label] = found_p
                                print(f"      ✅ Mapped: {cat_label} = {found_p}")
                                break # Done with this category
                    except: pass

        return prices

    except Exception as e:
        print(f"      ⚠️ Extract Error: {e}")
        return {}

def get_driver():
    try:
        options = uc.ChromeOptions()
        # NOTE: When using pyvirtualdisplay / xvfb, we DO NOT use --headless.
        # This makes the browser "think" it is visible, avoiding detection.
        
        # options.add_argument('--headless') # <--- REMOVED for anti-detection
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        # options.add_argument('--disable-software-rasterizer') # optional
        options.add_argument('--disable-extensions')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
        options.page_load_strategy = 'eager' 

        browser_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
        driver_path = '/usr/bin/chromedriver' if os.path.exists('/usr/bin/chromedriver') else None

        for attempt in range(3):
            try:
                driver = uc.Chrome(options=options, version_main=None, browser_executable_path=browser_path, driver_executable_path=driver_path)
                driver.set_page_load_timeout(60)
                return driver
            except OSError as e:
                time.sleep(5)
                if attempt == 2: raise e
    except Exception as e:
        print(f'❌ [ERROR] Failed to start Chrome Driver: {e}')
        return None

def run_scraper_cycle():
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING (CLEAN ANCHOR STRATEGY)...')
    
    # START VIRTUAL DISPLAY IF HEADLESS (DOCKER/LINUX)
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
        if display: display.stop()
        return

    with open(GAMES_FILE, 'r') as games_f: 
        games = json.load(games_f)

    driver = get_driver()
    timestamp = datetime.now().isoformat()
    new_records_buffer = []

    try:
        for i, game in enumerate(games, 1):
            if i > 1 and i % 3 == 0:
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
                        
                    # 1. Try standard extract (Includes Section Fallback)
                    prices = extract_prices_clean(driver)
                    
                    # 2. Interactive: Click "Listings" summary if no data found
                    if not prices:
                        try:
                            listings_clicked = False
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
                        
                        # SAVE IMMEDIATELY
                        if new_records_buffer:
                             append_data(DATA_FILE_VIAGOGO, new_records_buffer)
                             new_records_buffer = [] 
                        break 
                    else:
                        print('❌ No data found.')
                        # Debug logic hidden to keep logs clean
                        break
                        
                except Exception as e: 
                    msg = str(e).lower()
                    if 'crashed' in msg or 'disconnected' in msg: raise e 
                    time.sleep(2)
            time.sleep(1) 
        
        time.sleep(1.0)
        
    except Exception as e: print(f'🔥 Error: {e}')
    finally:
        try: driver.quit()
        except: pass
        if display:
            try: display.stop()
            except: pass
        print(f'[{datetime.now().strftime("%H:%M")}] 💤 VIAGOGO CYCLE COMPLETE.')

if __name__ == '__main__':
    run_scraper_cycle()