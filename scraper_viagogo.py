import json
import os
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains

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
        time.sleep(8)
        
        # 0. Anti-bot / Lazy load behavior
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 500);")
            time.sleep(1)
            body_el = driver.find_element(By.TAG_NAME, 'body')
            body_el.send_keys(Keys.HOME) 
        except: pass

        # 1. Debug: Check where we actually are
        page_title = driver.title
        
        if 'pardon' in page_title.lower() or 'denied' in page_title.lower() or 'robot' in page_title.lower():
             print(f"      ⚠️ BLOCK DETECTED: {page_title}")
             return {}

        prices = {}
        
        # ---------------------------------------------------------
        # STRATEGY 0: Check "Select Category/Section" Buttons (High Precision)
        # ---------------------------------------------------------
        try:
            # Look for buttons that specifically say "Select Category X - $Price" or "Select Section X"
            # We use a broad searching XPath to catch any button with "Select" and "$" in label
            cat_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Select') and (contains(@aria-label, '$') or contains(@aria-label, '₪'))]")
            
            for btn in cat_buttons:
                try:
                    aria_txt = btn.get_attribute('aria-label')
                    # Regex: Matches "Select (Category|Section) (101) ... ($)(500)"
                    m = re.search(r'(Category|Section|Block)\s+([A-Z0-9]+).*?(\$|₪)\s*([\d,]+)', aria_txt, re.I)
                    
                    if m:
                        type_label = m.group(1).lower() # category, section...
                        id_label = m.group(2) # 1, 101, CS2
                        sym = m.group(3)
                        val = float(m.group(4).replace(',', ''))
                        
                        if sym == '₪': val = round(val * ILS_TO_USD, 2)
                        
                        final_cat = None
                        if 'category' in type_label:
                            final_cat = f'Category {id_label}'
                        else:
                            # Map Section/Block to Category
                            clean_id = id_label
                            digits = ''.join(filter(str.isdigit, clean_id))
                            sec_int = int(digits) if digits else 0
                            lower_id = clean_id.lower()
                            
                            if 'cs' in lower_id or 'club' in lower_id or 'vip' in lower_id: final_cat = 'Category 1'
                            elif 'w' in lower_id: final_cat = 'Category 1'
                            elif 't' in lower_id: final_cat = 'Category 4'
                            elif sec_int > 0:
                                if 100 <= sec_int < 200: final_cat = 'Category 1'
                                elif 200 <= sec_int < 300: final_cat = 'Category 2'
                                elif 300 <= sec_int < 400: final_cat = 'Category 2'
                                elif 400 <= sec_int < 500: final_cat = 'Category 3'
                                else: final_cat = 'Category 4'
                            else:
                                final_cat = 'Category 4'
                        
                        if final_cat:
                             if final_cat not in prices or val < prices[final_cat]:
                                 prices[final_cat] = val
                except: pass
        except: pass
        
        if len(prices) > 0:
            return prices # Found golden data, return immediately

        # ---------------------------------------------------------
        # STRATEGY -1: "Simple HTML" (User Request)
        # Search for text "Category 1", "Category 2"... and find price sibling
        # ---------------------------------------------------------
        try:
             # Find explicit text nodes "Category X"
             for i in range(1, 5):
                 cat_name = f"Category {i}"
                 try:
                     cat_els = driver.find_elements(By.XPATH, f"//*[contains(text(), '{cat_name}')]")
                     for el in cat_els:
                         try:
                             parent = el.find_element(By.XPATH, "..")
                             full_text = parent.text
                             m_price = re.search(r'(\$|₪)\s*([\d,]+)', full_text)
                             if m_price:
                                 val = float(m_price.group(2).replace(',', ''))
                                 if m_price.group(1) == '₪': val = round(val * ILS_TO_USD, 2)
                                 
                                 if cat_name not in prices or val < prices[cat_name]:
                                     prices[cat_name] = val
                         except: pass
                 except: pass
        except: pass
        
        if len(prices) > 0:
            return prices
            
        # ---------------------------------------------------------
        # STRATEGY 1: Listing Buttons (Standard View)
        # ---------------------------------------------------------
        # Attempt to dismiss popups (generic)
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'], div[class*='modal'], button[aria-label='Close']")
            if len(overlays) > 0:
                  driver.execute_script("arguments[0].click();", overlays[0])
                  time.sleep(1)
        except: pass

        prices = {}
        
        # 2. General strategy: Find any element detailing a "Category" OR "Section"
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Category') or contains(text(), 'Section')]")
        
        if not elements:
            # Fallback 2: BRUTE FORCE. Get all potential listing containers.
            price_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '$') or contains(text(), '₪')]")
            elements = []
            for pel in price_elements:
                 try:
                     parent = pel.find_element(By.XPATH, "./..")
                     elements.append(parent)
                     elements.append(parent.find_element(By.XPATH, "./.."))
                 except: pass

        count_found = 0
        if not elements: print("   [DEBUG] Parsing: No specific elements found.")
        
        for el in elements:
            try:
                txt = el.text.strip()
                if not txt: continue
                
                lines = txt.split('\n')
                cat_num = None; price_val = None
                section_name = None
                
                for line in lines:
                    # Check for explicit Category
                    cat_m = re.search(r'Category\s+(\d)', line, re.I)
                    if cat_m: 
                        cat_num = cat_m.group(1)
                    
                    # Check for Section 
                    if not cat_num:
                        words = line.split()
                        for w in words:
                             w_clean = w.strip('.,-')
                             if re.match(r'^[A-Z]*\d{3}[A-Z]*$', w_clean, re.I):
                                  if w_clean == '2026': continue
                                  section_name = w_clean
                                  break 
                        
                        if not section_name:
                             sec_m = re.search(r'(?:Section|Block)\s*([A-Z]*\d{1,3}[A-Z]*)', line, re.I)
                             if sec_m: section_name = sec_m.group(1)

                    # Check Price
                    if '$' in line:
                        m = re.search(r'\$\s*([\d,]+)', line)
                        if m: price_val = float(m.group(1).replace(',', ''))
                    elif '₪' in line and price_val is None:
                        m = re.search(r'₪([\d,]+)', line)
                        if m: 
                            val = float(m.group(1).replace(',', ''))
                            price_val = round(val * ILS_TO_USD, 2)
                
                # Logic to determine final category label
                final_cat = None
                if cat_num: 
                    final_cat = f'Category {cat_num}'
                elif section_name:
                    # MAP SECTIONS TO CATEGORIES (Standard WC logic)
                    digits = ''.join(filter(str.isdigit, section_name))
                    sec_int = int(digits) if digits else 0
                    
                    lower_sec = section_name.lower()
                    if 'cs' in lower_sec or 'club' in lower_sec or 'vip' in lower_sec:
                        final_cat = 'Category 1'
                    elif 't' in lower_sec: 
                         final_cat = 'Category 4'
                    elif 'w' in lower_sec: 
                         final_cat = 'Category 1'
                    elif sec_int > 0:
                        if 100 <= sec_int < 200: final_cat = 'Category 1'
                        elif 200 <= sec_int < 300: final_cat = 'Category 2' 
                        elif 300 <= sec_int < 400: final_cat = 'Category 2'
                        elif 400 <= sec_int < 500: final_cat = 'Category 3' 
                        else: final_cat = 'Category 4' 
                    else:
                        final_cat = 'Category 4' 

                    if 'club' in txt.lower() or 'vip' in txt.lower(): final_cat = 'Category 1'

                if final_cat and price_val:
                     if final_cat not in prices or price_val < prices[final_cat]:
                         prices[final_cat] = price_val
                         count_found += 1
            except: continue
        
        # 3. Last Resort: Body Scan (Line-by-Line with Context)
        if count_found == 0:
             try:
                 main_list = driver.find_element(By.ID, 'grid-container') 
                 full_text = main_list.text
             except:
                 full_text = driver.find_element(By.TAG_NAME, 'body').text
            
             lines = full_text.split('\n')
             for i, line in enumerate(lines):
                 if 'row' in line.lower() or 'match' in line.lower(): continue

                 cat_m = re.search(r'Category\s+(\d)', line, re.I)
                 
                 words = line.split()
                 sec_match = None
                 for w in words:
                      clean = w.strip('.,-')
                      if re.match(r'^[A-Z]*\d{3}[A-Z]*$', clean, re.I):
                           if clean != '2026': 
                               sec_match = clean
                               break
                 
                 found_key = None
                 if cat_m:
                     found_key = f'Category {cat_m.group(1)}'
                 elif sec_match:
                     candidate = sec_match
                     if True: 
                         # Map Section to Category
                         digits = ''.join(filter(str.isdigit, candidate))
                         sec_int = int(digits) if digits else 0
                         lower_sec = candidate.lower()
                         
                         if 'cs' in lower_sec or 'club' in lower_sec or 'vip' in lower_sec: found_key = 'Category 1'
                         elif 'w' in lower_sec: found_key = 'Category 1'
                         elif 't' in lower_sec: found_key = 'Category 4'
                         elif sec_int > 0:
                            if 100 <= sec_int < 200: found_key = 'Category 1'
                            elif 200 <= sec_int < 300: found_key = 'Category 2'
                            elif 300 <= sec_int < 400: found_key = 'Category 2'
                            elif 400 <= sec_int < 500: found_key = 'Category 3'
                            else: found_key = 'Category 4'
                         else:
                            found_key = 'Category 4'

                 if found_key:
                     found_price = None
                     search_window = lines[i:i+6] 
                     for pline in search_window:
                         m_price = re.search(r'(\$|₪)\s*([\d,]+)', pline)
                         if m_price:
                             val = float(m_price.group(2).replace(',', ''))
                             if m_price.group(1) == '₪': val = round(val * ILS_TO_USD, 2)
                             if val > 10: 
                                 found_price = val
                                 break
                     
                     if found_price:
                         if found_key not in prices or found_price < prices[found_key]:
                             prices[found_key] = found_price
                             count_found += 1

        # 4. Ultimate Fallback: Proximity Scan
        if count_found == 0:
             # Find all prices with their positions
             price_matches = [m for m in re.finditer(r'(?:US)?(\$|₪|USD)\s*([\d,]+)', full_text, re.IGNORECASE)]
             
             # Find all section candidates
             sec_matches = [m for m in re.finditer(r'\b([1-5]\d{2})(?:[A-Z])?\b', full_text)]
             
             for sm in sec_matches:
                 sec_pos = sm.end()     
                 sec_val = sm.group(1)  
                 
                 nearest_price = None
                 min_dist = 9999
                 
                 for pm in price_matches:
                     dist = pm.start() - sec_pos
                     if 0 < dist < 800:
                         if dist < min_dist:
                             min_dist = dist
                             val = float(pm.group(2).replace(',', ''))
                             if pm.group(1) == '₪': val = round(val * ILS_TO_USD, 2)
                             nearest_price = val
                 
                 if nearest_price and nearest_price > 10:
                     digits = ''.join(filter(str.isdigit, sec_val))
                     sec_int = int(digits)
                     final_cat = 'Category 4' 
                     
                     if 100 <= sec_int < 200: final_cat = 'Category 1'
                     elif 200 <= sec_int < 300: final_cat = 'Category 2'
                     elif 300 <= sec_int < 400: final_cat = 'Category 2'
                     elif 400 <= sec_int < 500: final_cat = 'Category 3'
                     
                     if final_cat not in prices or nearest_price < prices[final_cat]:
                         prices[final_cat] = nearest_price
                         count_found += 1
                         
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
                    options=options, 
                    version_main=None, 
                    browser_executable_path=browser_path, 
                    driver_executable_path=driver_path
                )
                driver.set_page_load_timeout(60)
                return driver
            except OSError as e:
                # Catch "Text file busy" specifically
                if 'Text file busy' in str(e):
                    print(f'   ⚠️ Driver file busy (attempt {attempt+1}/3). Waiting...')
                    time.sleep(5)
                else:
                    raise e
    except Exception as e:
        print(f'❌ [ERROR] Failed to start Chrome Driver: {e}')
        return None

def run_scraper_cycle():
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING...')
    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found! Cannot scrape.')
        return

    with open(GAMES_FILE, 'r') as f: games = json.load(f)

    # Initial Driver
    driver = get_driver()
    
    timestamp = datetime.now().isoformat()
    success_count = 0; new_records_buffer = []

    try:
        for i, game in enumerate(games, 1):
             # 🔄 BATCH RESTART
            if i > 1 and i % 10 == 0:
                print(f'   🔄 Scheduled Batch Restart (Match {i})...')
                try: driver.quit()
                except: pass
                driver = None

             # check driver health
            if driver is None:
                print('   🔄 Restarting Driver...')
                driver = get_driver()
                if not driver: continue

            match_name = game['match_name']
            url = game['url']
            clean_url = url.split('&Currency')[0].split('?Currency')[0]
            target_url = url + ('&Currency=USD' if '?' in url else '?Currency=USD')
            
            print(f'[{i}/{len(games)}] {match_name[:30]}... ', end='', flush=True)
            
            # Retry loop for page load
            for attempt in range(3):
                try:
                    driver.get(target_url)
                    
                    # Check for 502/Server Errors
                    if '502' in driver.title or 'Bad Gateway' in driver.title:
                        print(f'   ⚠️ Server Error (Attempt {attempt+1}/3). Waiting...')
                        time.sleep(5)
                        continue
                        
                    prices = extract_prices(driver)
                    if prices:
                        for cat, price in prices.items():
                            new_records_buffer.append({
                                'match_url': clean_url, 'match_name': match_name,
                                'category': cat, 'price': price, 'currency': 'USD', 'timestamp': timestamp
                            })
                        success_count += 1
                        print(f'✅ Found {len(prices)}')
                        break # Success, exit retry loop
                    else:
                        # -------------------------------------------------------------
                        # STRATEGY 6: CLICK FALLBACK (Interactive)
                        # -------------------------------------------------------------
                        print('   ⚠️ No passive data. Attempting interactive click...')
                        try:
                            interact_success = False
                            for k in range(101, 130): 
                                try:
                                    els = driver.find_elements(By.XPATH, f"//*[normalize-space(text())='{k}']")
                                    for el in els:
                                        if el.is_displayed() and el.is_enabled():
                                            driver.execute_script("arguments[0].click();", el)
                                            time.sleep(2.5) 
                                            interact_success = True
                                            break
                                except: pass
                                if interact_success: break
                            
                            if interact_success:
                                print('   🔄 Content updated? Retrying extraction...')
                                prices = extract_prices(driver)
                        except: pass

                        if prices:
                            for cat, price in prices.items():
                                new_records_buffer.append({
                                    'match_url': clean_url, 'match_name': match_name,
                                    'category': cat, 'price': price, 'currency': 'USD', 'timestamp': timestamp
                                })
                            success_count += 1
                            print(f'✅ Found {len(prices)} (after click)')
                            break
                        
                        print('❌ No data found.')
                        # DEBUG
                        try:
                            with open(f'debug_failed_scrape_{i}.html', 'w', encoding='utf-8') as f:
                                f.write(driver.page_source)
                        except: pass

                        # DEBUG: Why no data?
                        title = driver.title
                        current_url = driver.current_url
                        body = driver.find_element(By.TAG_NAME, 'body').text[:300].replace('\n', ' ')
                        print(f"   [DEBUG] Title: {title}")
                        print(f"   [DEBUG] URL: {current_url}")
                        print(f"   [DEBUG] Body Snippet: {body}...")
                        break 
                        
                except Exception as e: 
                    print(f'❌ Error: {e}')
                    msg = str(e).lower()
                    if 'crashed' in msg or 'disconnected' in msg or 'timeout' in msg:
                        raise e # Critical error, let outer loop handle driver restart
                    time.sleep(2)
            time.sleep(1) 

        if new_records_buffer: append_data(DATA_FILE_VIAGOGO, new_records_buffer)
            
        print(f'   ... Waiting for scanners to finish ...')
        
        # Stability Cooldown
        time.sleep(1.0)
        
    except Exception as e: print(f'🔥 Error: {e}')
    finally:
        try: driver.quit()
        except: pass
        print(f'[{datetime.now().strftime("%H:%M")}] 💤 VIAGOGO CYCLE COMPLETE.')

if __name__ == '__main__':
    run_scraper_cycle()