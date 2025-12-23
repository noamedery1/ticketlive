import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import json
import os
from collections import defaultdict
from datetime import datetime

EUR_TO_USD = 1.05  # Approximate rate

def get_driver():
    try:
        browser_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
        driver_path = '/usr/bin/chromedriver' if os.path.exists('/usr/bin/chromedriver') else None

        for attempt in range(3):
            try:
                # Create fresh options object each time to avoid reuse error
                options = uc.ChromeOptions()
                if os.environ.get('HEADLESS') == 'true':
                    options.add_argument('--headless')
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    options.add_argument('--disable-gpu')
                    options.add_argument('--disable-software-rasterizer')
                    options.add_argument('--disable-extensions')
                
                driver = uc.Chrome(
                    options=options, 
                    version_main=None, 
                    browser_executable_path=browser_path, 
                    driver_executable_path=driver_path
                )
                return driver
            except OSError as e:
                if 'Text file busy' in str(e):
                    print(f'   ⚠️ Driver file busy (attempt {attempt+1}/3). Waiting...')
                    time.sleep(5)
                else:
                    raise e
            except Exception as e:
                error_msg = str(e).lower()
                if 'cannot reuse' in error_msg or 'chromeoptions' in error_msg:
                    # Options reuse error - wait and retry with fresh options
                    print(f'   ⚠️ Options reuse error (attempt {attempt+1}/3). Retrying...')
                    time.sleep(3)
                    continue
                raise e
        return None
    except Exception as e:
        print(f'❌ [ERROR] Chrome Driver init failed: {e}')
        return None

def scrape_ftn_single(driver, url, match_name):
    print(f'   Scraping {match_name[:30]}...')
    prices_found_for_match = defaultdict(lambda: float('inf'))

    try:
        driver.get(url)
        time.sleep(8) 
        
        try:
            body_text = driver.find_element(By.TAG_NAME, 'body').text
        except Exception as body_err:
            error_msg = str(body_err).lower()
            print(f'      ❌ Could not read page body: {error_msg[:50]}')
            # Check if it's a critical error that requires driver restart
            if 'crashed' in error_msg or 'disconnected' in error_msg or 'target closed' in error_msg or 'tab crashed' in error_msg:
                print('      🔥 Critical error detected, signal for driver restart')
                return None  # Signal for driver restart
            return []

        lines = body_text.split('\n')
        
        for i, line in enumerate(lines):
            if 'Category' in line:
                category = line.strip()
                cat_match = re.search(r'Category\s+(1\s+Premium|1|2|3|4)', category, re.IGNORECASE)
                
                if cat_match:
                    normalized_cat = f'Category {cat_match.group(1).title()}'
                    
                    if i > 0:
                        prev_line = lines[i-1].strip()
                        price_match = re.search(r'([€$£])\s*([\d,]+\.?\d*)', prev_line)
                        if price_match:
                            currency_sym = price_match.group(1)
                            raw_val = float(price_match.group(2).replace(',', ''))
                            
                            price_usd = raw_val
                            if '€' in currency_sym:
                                price_usd = round(raw_val * EUR_TO_USD, 2)
                            
                            if price_usd < prices_found_for_match[normalized_cat]:
                                prices_found_for_match[normalized_cat] = price_usd

        records = []
        if prices_found_for_match:
            print(f'      ✅ Found prices: {dict(prices_found_for_match)}')
            timestamp = datetime.now().isoformat()
            for cat, price in prices_found_for_match.items():
                records.append({
                    'match_url': url,
                    'match_name': match_name,
                    'category': cat,
                    'price': price,
                    'currency': 'USD',
                    'source': 'FootballTicketNet',
                    'timestamp': timestamp
                })
        else:
            print('      ❌ No valid prices found.')
            
        return records

    except Exception as e:
        msg = str(e).lower()
        if 'crashed' in msg or 'disconnected' in msg or 'timeout' in msg:
            print(f'      🔥 Critical Driver Error: {e}')
            return None # Signal to restart driver
        print(f'      ❌ Error: {e}')
        return []

def run_ftn_scraper_cycle():
    GAMES_FILE = 'all_games_ftn_to_scrape.json'
    OUTPUT_FILE = 'prices_ftn.json'
    
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 FTN SCRAPER STARTING...')
    
    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found. Run get_ftn_urls.py first.')
        return

    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)
        
    print(f'   Target: {len(games)} games...')
    
    # Initialize driver
    driver = get_driver()
    
    try:
        existing_data = []
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, 'r') as f: existing_data = json.load(f)
            except: pass
        
        for i, game in enumerate(games):
            # 🔄 BATCH RESTART: Proactively restart driver every 10 games to free memory
            if i > 0 and i % 10 == 0:
                print(f'   🔄 Scheduled Batch Restart (Match {i})...')
                try: driver.quit()
                except: pass
                driver = None

            # 1. Check if driver is alive/healthy before starting
            if driver is None:
                driver = get_driver()
                if not driver:
                    print('   ❌ Could not restart driver, skipping...')
                    continue
            
            # 2. Scrape with retry/recovery logic
            try:
                new_records = scrape_ftn_single(driver, game['url'], game['match_name'])
                
                # If None returned (signal for critical error), force restart
                if new_records is None:
                    raise Exception("Critical Driver Error detected in worker")

                if new_records:
                    existing_data.extend(new_records)
                    with open(OUTPUT_FILE, 'w') as f:
                        json.dump(existing_data, f, indent=2)
            
            except Exception as e:
                print(f'   ⚠️ Driver Unstable ({e}). Restarting...')
                try: driver.quit()
                except: pass
                driver = None # Force create new one next loop
                continue
            
            time.sleep(2) 
            
    except Exception as e:
        print(f'🔥 Fatal Error in FTN Cycle: {e}')
    finally:
        if driver:
            try: driver.quit()
            except: pass
    
    print(f'[{datetime.now().strftime("%H:%M")}] 💤 FTN CYCLE COMPLETE.')

if __name__ == '__main__':
    run_ftn_scraper_cycle()