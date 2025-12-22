import json
import os
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
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
        time.sleep(8)
        
        # 0. Anti-bot / Lazy load behavior
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(2)

        # 1. Debug: Check where we actually are
        page_title = driver.title
        
        if 'pardon' in page_title.lower() or 'denied' in page_title.lower() or 'robot' in page_title.lower():
             print(f"      ⚠️ BLOCK DETECTED: {page_title}")
             return {}

        # Attempt to dismiss popups (generic)
        try:
            # Common overlays/modals
            overlays = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog'], div[class*='modal'], button[aria-label='Close']")
            if len(overlays) > 0:
                  driver.execute_script("arguments[0].click();", overlays[0])
                  time.sleep(1)
        except: pass

        prices = {}
        
        # 2. General strategy: Find any element detailing a "Category" OR "Section"
        # This covers <div>, <span>, <button>, etc.
        # XPath searches for elements containing 'Category' or 'Section' (case insensitive-ish handling via Python regex later if needed, but text() is sensitive usually)
        # Using Translate for case-insensitivity in XPath 1.0 is messy, so we trust standard caps first.
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Category') or contains(text(), 'Section')]")
        
        # If no explicit 'Category' text found, try looking for general listing containers (fallback)
        if not elements:
             # Sometimes they just say "Section 105" etc. But we specifically want Categories for this app.
             pass

        count_found = 0
        for el in elements:
            try:
                # Get text of the element. If it's short, get the parent's text.
                txt = el.text.strip()
                if len(txt) < 10: # likely just "Category 1" without price
                     try: txt = el.find_element(By.XPATH, "./..").text.strip()
                     except: pass
                
                if len(txt) < 10: # still too short, go one more up
                     try: txt = el.find_element(By.XPATH, "./../..").text.strip()
                     except: pass

                lines = txt.split('\n')
                cat_num = None; price_val = None
                
                # Parse lines
                for line in lines:
                    # Check Category
                    cat_m = re.search(r'Category\s+(\d)', line, re.I)
                    if cat_m: cat_num = cat_m.group(1)
                    
                    # Check Price
                    if '$' in line:
                        m = re.search(r'\$\s*([\d,]+)', line)
                        if m: price_val = float(m.group(1).replace(',', ''))
                    elif '₪' in line and price_val is None:
                        m = re.search(r'₪([\d,]+)', line)
                        if m: 
                            val = float(m.group(1).replace(',', ''))
                            price_val = round(val * ILS_TO_USD, 2)
                            
                # Store if valid
                if cat_num and price_val:
                     key = f'Category {cat_num}'
                     # Keep lowest price found for this category
                     if key not in prices or price_val < prices[key]:
                         prices[key] = price_val
                         count_found += 1
            except: continue
            
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
            options.add_argument('--disable-extensions')
            options.add_argument('--window-size=1920,1080')

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
             # 🔄 BATCH RESTART: Proactively restart driver every 10 games
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
            try:
                driver.get(target_url)
                prices = extract_prices(driver)
                if prices:
                    for cat, price in prices.items():
                        new_records_buffer.append({
                            'match_url': clean_url, 'match_name': match_name,
                            'category': cat, 'price': price, 'currency': 'USD', 'timestamp': timestamp
                        })
                    success_count += 1
                    print(f'✅ Found {len(prices)}')
                else: 
                     print('❌ No data found.')
                     # DEBUG: Why no data?
                     title = driver.title
                     current_url = driver.current_url
                     body = driver.find_element(By.TAG_NAME, 'body').text[:300].replace('\n', ' ')
                     print(f"   [DEBUG] Title: {title}")
                     print(f"   [DEBUG] URL: {current_url}")
                     print(f"   [DEBUG] Body Snippet: {body}...")
                
                if len(new_records_buffer) > 20: 
                    append_data(DATA_FILE_VIAGOGO, new_records_buffer); new_records_buffer = []
                time.sleep(2)
            except Exception as e: 
                print(f'❌ Error: {e}')
                msg = str(e).lower()
                if 'crashed' in msg or 'disconnected' in msg or 'timeout' in msg or 'no such execution context' in msg:
                    print('   ⚠️ Critcal error. Rebooting driver...')
                    try: driver.quit()
                    except: pass
                    driver = None

        if new_records_buffer: append_data(DATA_FILE_VIAGOGO, new_records_buffer)
            
    except Exception as e: print(f'🔥 Error: {e}')
    finally:
        try: driver.quit()
        except: pass
        print(f'[{datetime.now().strftime("%H:%M")}] 💤 VIAGOGO CYCLE COMPLETE.')

if __name__ == '__main__':
    run_scraper_cycle()