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
        buttons = driver.find_elements(By.TAG_NAME, 'button')
        prices = {}
        for btn in buttons:
            txt = btn.text
            if 'Category' not in txt: continue
            lines = txt.split('\n')
            cat_num = None; price_val = None
            for line in lines:
                cat_m = re.search(r'Category\s+(\d)', line, re.I)
                if cat_m: cat_num = cat_m.group(1)
                
                if '$' in line:
                    m = re.search(r'\$\s*([\d,]+)', line)
                    if m: price_val = float(m.group(1).replace(',', ''))
                elif '₪' in line and price_val is None:
                    m = re.search(r'₪([\d,]+)', line)
                    if m: 
                        val = float(m.group(1).replace(',', ''))
                        price_val = round(val * ILS_TO_USD, 2)
            if cat_num and price_val: prices[f'Category {cat_num}'] = price_val
        return prices
    except: return {}

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
                else: print('❌ No data')
                
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