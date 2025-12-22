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

def extract_prices(driver):
    try:
        time.sleep(5)
        
        # 0. Anti-bot / Lazy load behavior
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
        except: pass

        # 1. Debug: Check where we actually are
        page_title = driver.title
        if 'pardon' in page_title.lower() or 'denied' in page_title.lower() or 'robot' in page_title.lower():
             print(f"      ⚠️ BLOCK DETECTED: {page_title}")
             return {}

        prices = {}
        
        # ---------------------------------------------------------
        # STRATEGY 0: "Category Pill" Scan (Golden Path)
        # Matches the screenshot: "Category 1 $1,296" pills above map.
        # We look for ANY element containing "Category X" and a price.
        # ---------------------------------------------------------
        try:
            # 0. Scroll to trigger lazy loading of pills
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(1)

            # 1. Aria-Label Scan (Broad)
            # Catches <div role="button" aria-label="Category 1 $500">
            aria_els = driver.find_elements(By.XPATH, "//*[@aria-label]")
            for el in aria_els:
                try:
                    aria_txt = el.get_attribute('aria-label')
                    if 'Category' in aria_txt:
                        m = re.search(r'Category\s+(\d+)', aria_txt, re.I)
                        m_price = re.search(r'(\$|₪|USD)\s*([\d,]+)', aria_txt)
                        
                        if m and m_price:
                             cat_key = f"Category {m.group(1)}"
                             val = float(m_price.group(2).replace(',', ''))
                             if '₪' in m_price.group(0): val = round(val * ILS_TO_USD, 2)
                             
                             if m.group(1) in ['1','2','3','4']:
                                 if cat_key not in prices or val < prices[cat_key]:
                                     prices[cat_key] = val
                except: pass

            # 2. visual Text Scan (Pills)
            potential_pills = driver.find_elements(By.XPATH, "//*[contains(text(), 'Category')]")
            
            for el in potential_pills:
                try:
                    txt = el.text.strip().replace('\n', ' ')
                    if len(txt) > 200: continue # Skip huge bodies
                    
                    # Regex: Allow stricter (with currency) first
                    m = re.search(r'Category\s+(\d+).*?(\$|₪)\s*([\d,]+)', txt, re.I)
                    
                    # Fallback Regex: Loose (just number looking like price near category)
                    if not m:
                        m = re.search(r'Category\s+(\d+).*?\s+([\d,]{3,})', txt, re.I) # e.g. "Category 1 1,500"

                    # Check Parent if direct text failed
                    if not m:
                        try:
                            parent = el.find_element(By.XPATH, "..")
                            p_txt = parent.text.strip().replace('\n', ' ')
                            if len(p_txt) < 200:
                                m = re.search(r'Category\s+(\d+).*?(\$|₪)\s*([\d,]+)', p_txt, re.I)
                        except: pass

                    if m:
                        cat_str = m.group(1)
                        if cat_str in ['1','2','3','4']:
                            cat_key = f"Category {cat_str}"
                            # Group 3 is price in strict regex, Group 2 in loose fallback. logic needed.
                            raw_price = m.group(3) if len(m.groups()) >= 3 else m.group(2)
                            if raw_price:
                                val = float(raw_price.replace(',', ''))
                                if '₪' in txt or '₪' in (p_txt if 'p_txt' in locals() else ''): 
                                     val = round(val * ILS_TO_USD, 2)
                                
                                # Sanity check for price
                                if val > 10:
                                    if cat_key not in prices or val < prices[cat_key]:
                                        prices[cat_key] = val
                except: pass
        except: pass
        
        if len(prices) > 0: return prices
        
        # ---------------------------------------------------------
        # STRATEGY 1: Strict Section Mapping (Passive)
        # ---------------------------------------------------------
        try:
             price_els = driver.find_elements(By.XPATH, "//*[contains(text(), '$') or contains(text(), '₪')]")
             for pel in price_els:
                 try:
                     txt = pel.text.strip()
                     parent_txt = pel.find_element(By.XPATH, "..").text.strip()
                     full_line = (parent_txt + " " + txt).replace('\n', ' ')
                     
                     m_price = re.search(r'(\$|₪)\s*([\d,]+)', full_line)
                     if not m_price: continue
                     
                     val = float(m_price.group(2).replace(',', ''))
                     if m_price.group(1) == '₪': val = round(val * ILS_TO_USD, 2)

                     sec_m = re.search(r'\b([A-Z]*\d{3}[A-Z]*)\b', full_line)
                     if sec_m:
                         sec_str = sec_m.group(1)
                         digits = ''.join(filter(str.isdigit, sec_str))
                         if not digits: continue
                         sec_int = int(digits)
                         if sec_int > 600: continue 
                         
                         cat_key = 'Category 4' 
                         if 100 <= sec_int < 200: cat_key = 'Category 1'
                         elif 200 <= sec_int < 300: cat_key = 'Category 2'
                         elif 300 <= sec_int < 400: cat_key = 'Category 2'
                         elif 400 <= sec_int < 500: cat_key = 'Category 3'
                         
                         if val > 10:
                             if cat_key not in prices or val < prices[cat_key]:
                                 prices[cat_key] = val
                 except: pass
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
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING (INTELLIGENT MAPPING)...')
    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found!')
        return

    with open(GAMES_FILE, 'r') as f: games = json.load(f)

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
                        
                    prices = extract_prices(driver)
                    
                    # -------------------------------------------------------------
                    # INTERACTIVE FALLBACK:
                    # If strict extraction fails, we MUST click sections to reveal prices.
                    # BUT we will map them strictly to Categories.
                    # -------------------------------------------------------------
                    if not prices:
                        try:
                            # 1. Search for Listings Count
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
                            
                            # 2. Search for Sections (Hidden Categories)
                            # We search for "101", "201" etc.
                            interact_success = False
                            targets = list(range(101, 121)) + list(range(201, 211))
                            
                            for k in targets:
                                try:
                                    els = driver.find_elements(By.XPATH, f"//*[contains(text(), '{k}')]")
                                    for el in els:
                                        txt = el.text.strip()
                                        if len(txt) < 25 and (txt == str(k) or f"Section {k}" in txt or f"Sec {k}" in txt):
                                            print(f"      🖱️ Clicking Section: '{txt}'")
                                            try: driver.execute_script("arguments[0].click();", el)
                                            except: el.click()
                                            time.sleep(3.5)
                                            interact_success = True
                                            
                                            # CONTEXT SCAN IS CRITICAL HERE
                                            # We just clicked "101". Any price we see now is "Category 1".
                                            body_text = driver.find_element(By.TAG_NAME, 'body').text
                                            price_matches = re.findall(r'(?:\$|₪)\s*([\d,]+)', body_text)
                                            if price_matches:
                                                 sec_int = int(k)
                                                 cat_map = 'Category 4'
                                                 if 100 <= sec_int < 200: cat_map = 'Category 1'
                                                 elif 200 <= sec_int < 300: cat_map = 'Category 2'
                                                 elif 300 <= sec_int < 400: cat_map = 'Category 2'
                                                 elif 400 <= sec_int < 500: cat_map = 'Category 3'
                                                 
                                                 # Find cheapest new price
                                                 for pstr in price_matches:
                                                     val = float(pstr.replace(',', ''))
                                                     if val > 10:
                                                         if '₪' in body_text: val = round(val * ILS_TO_USD, 2)
                                                         if cat_map not in prices or val < prices[cat_map]:
                                                             prices[cat_map] = val
                                            break
                                except: pass
                                if interact_success: break # Stop after one successful click
                                
                        except: pass

                    if prices:
                        for cat, price in prices.items():
                            new_records_buffer.append({
                                'match_url': clean_url, 'match_name': match_name,
                                'category': cat, 'price': price, 'currency': 'USD', 'timestamp': timestamp
                            })
                        print(f'✅ Found {len(prices)} Categories')
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