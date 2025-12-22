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
        # STRATEGY 0: "Category Button" Scan (The Golden Path)
        # We ONLY look for explicit "Category X" buttons or labels.
        # User defined structure: <button aria-label="Select Category 1 - $1,608"> 
        # OR <div/p>Category 1</p><p>$1,608</p>
        # ---------------------------------------------------------
        
        # Scan A: Look for Buttons with Aria Label (Best Match)
        try:
            # Wait briefly for these critical buttons
            for _ in range(5):
                golden_btns = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Category') and (contains(@aria-label, '$') or contains(@aria-label, '₪'))]")
                if golden_btns: break
                time.sleep(1)

            for btn in golden_btns:
                try:
                    aria_txt = btn.get_attribute('aria-label')
                    # Regex: Matches "Category 1 ... $500"
                    m = re.search(r'Category\s+(\d+).*?(\$|₪)\s*([\d,]+)', aria_txt, re.I)
                    if m:
                        cat_key = f"Category {m.group(1)}"
                        val = float(m.group(3).replace(',', ''))
                        if m.group(2) == '₪': val = round(val * ILS_TO_USD, 2)
                        
                        # Only keep strictly 1-4
                        if m.group(1) in ['1','2','3','4']:
                            if cat_key not in prices or val < prices[cat_key]:
                                prices[cat_key] = val
                except: pass
        except: pass

        # Scan B: Look for Text Structure (Category X ... $Price)
        # This handles cases where aria-label might be missing but text is visible
        try:
            # Find all elements containing "Category" text
            cat_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'Category')]")
            for el in cat_els:
                try:
                    # Check plain text of element and immediate parent
                    # We look for "Category X" and a price in the same container
                    txt = el.text.strip()
                    parent_txt = el.find_element(By.XPATH, "..").text.strip()
                    
                    full_txt = (txt + " " + parent_txt).replace('\n', ' ')
                    
                    # Regex for "Category X" followed by Price
                    m = re.search(r'Category\s+(\d+).*?(\$|₪)\s*([\d,]+)', full_txt, re.I)
                    if m:
                        cat_key = f"Category {m.group(1)}"
                        # Check matches 1-4
                        if m.group(1) in ['1','2','3','4']:
                            val = float(m.group(3).replace(',', ''))
                            if m.group(2) == '₪': val = round(val * ILS_TO_USD, 2)
                            
                            if cat_key not in prices or val < prices[cat_key]:
                                prices[cat_key] = val
                except: pass
        except: pass
        
        if len(prices) > 0:
            return prices

        # ---------------------------------------------------------
        # STRATEGY 1: Section Scan -> Strict Category Mapping (Fallback)
        # Use this ONLY if explicit Category buttons are missing (e.g. Match 79).
        # We find "Section 101" and map it to "Category 1".
        # We NEVER output "Section X".
        # ---------------------------------------------------------
        try:
             # Find elements with "$" or "₪"
             price_els = driver.find_elements(By.XPATH, "//*[contains(text(), '$') or contains(text(), '₪')]")
             for pel in price_els:
                 try:
                     # Get text of price + parent (context)
                     txt = pel.text.strip()
                     parent_txt = pel.find_element(By.XPATH, "..").text.strip()
                     full_line = (parent_txt + " " + txt).replace('\n', ' ')
                     
                     # Extract Price
                     m_price = re.search(r'(\$|₪)\s*([\d,]+)', full_line)
                     if not m_price: continue
                     
                     val = float(m_price.group(2).replace(',', ''))
                     if m_price.group(1) == '₪': val = round(val * ILS_TO_USD, 2)

                     # Look for Section Number
                     # Matches "101", "Section 101", "W105"
                     sec_m = re.search(r'\b([A-Z]*\d{3}[A-Z]*)\b', full_line)
                     if sec_m:
                         sec_str = sec_m.group(1)
                         digits = ''.join(filter(str.isdigit, sec_str))
                         if not digits: continue
                         sec_int = int(digits)
                         if sec_int > 600: continue # Likely not a section
                         
                         cat_key = 'Category 4' # Default
                         
                         # STRICT MAPPING LOGIC
                         if 100 <= sec_int < 200: cat_key = 'Category 1'
                         elif 200 <= sec_int < 300: cat_key = 'Category 2'
                         elif 300 <= sec_int < 400: cat_key = 'Category 2'
                         elif 400 <= sec_int < 500: cat_key = 'Category 3'
                         
                         # Override for Club/VIP
                         if 'club' in full_line.lower() or 'vip' in full_line.lower(): cat_key = 'Category 1'
                         
                         # Save ONLY if valid price
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
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 VIAGOGO SCRAPER STARTING (STRICT CATEGORY ONLY)...')
    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found!')
        return

    with open(GAMES_FILE, 'r') as f: games = json.load(f)

    driver = get_driver()
    timestamp = datetime.now().isoformat()
    new_records_buffer = []

    try:
        for i, game in enumerate(games, 1):
             # Batch restart
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
                    # INTERACTIVE FALLBACK (STRICT):
                    # Only try to reveal content, do NOT click parsing sections.
                    # -------------------------------------------------------------
                    if not prices:
                        try:
                            # Try Clicking "See Listings" found text (e.g. "14 listings")
                            # This might reveal the Category Buttons if they were hidden
                            list_els = driver.find_elements(By.XPATH, "//*[contains(text(), 'listings')]")
                            clicked = False
                            for le in list_els:
                                if 'ticket' not in le.text.lower() and len(le.text) < 30 and le.is_displayed():
                                     print(f"      🖱️ Clicking Listing Summary: '{le.text}'")
                                     try: driver.execute_script("arguments[0].click();", le)
                                     except: le.click()
                                     time.sleep(3)
                                     clicked = True
                                     break
                            
                            if clicked:
                                print('   🔄 Content updated? Retrying strict extraction...')
                                prices = extract_prices(driver)
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
                        print('❌ No Category buttons/labels found.')
                        # DEBUG
                        try:
                            with open(f'debug_failed_scrape_{i}.html', 'w', encoding='utf-8') as f:
                                f.write(driver.page_source)
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