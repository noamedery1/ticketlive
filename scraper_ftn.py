import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

# Fix encoding for Windows (cp1252 can't handle emojis)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

EUR_TO_USD = 1.05  # Approximate rate

def get_driver():
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
            browser_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else None
            driver_path = '/usr/bin/chromedriver' if os.path.exists('/usr/bin/chromedriver') else None

        for attempt in range(5):  # Increased retries
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
                    driver_executable_path=driver_path,
                    use_subprocess=False  # Avoid subprocess issues on Windows 7
                )
                print(f'   ✅ Driver initialized successfully (attempt {attempt+1})', flush=True)
                return driver
            except OSError as e:
                error_str = str(e)
                # Handle Windows file lock errors
                if 'Text file busy' in error_str or 'WinError 32' in error_str or 'WinError 183' in error_str or 'being used by another process' in error_str or 'already exists' in error_str:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s, 8s, 10s
                    print(f'   ⚠️ Driver file locked by another process (attempt {attempt+1}/5). Waiting {wait_time}s...', flush=True)
                    time.sleep(wait_time)
                    if attempt < 4:
                        continue
                    else:
                        raise e
                else:
                    raise e
            except Exception as e:
                error_msg = str(e).lower()
                error_str = str(e)
                if 'cannot reuse' in error_msg or 'chromeoptions' in error_msg:
                    wait_time = (attempt + 1) * 1.5
                    print(f'   ⚠️ Options reuse error (attempt {attempt+1}/5). Retrying in {wait_time:.1f}s...', flush=True)
                    time.sleep(wait_time)
                    continue
                # Check for file lock errors in exception message too
                if 'WinError 32' in error_str or 'WinError 183' in error_str or 'being used by another process' in error_str:
                    wait_time = (attempt + 1) * 2
                    print(f'   ⚠️ File lock error (attempt {attempt+1}/5). Waiting {wait_time}s...', flush=True)
                    time.sleep(wait_time)
                    if attempt < 4:
                        continue
                raise e
        print(f'❌ [ERROR] Chrome Driver init failed after all retries', flush=True)
        return None
    except Exception as e:
        print(f'❌ [ERROR] Chrome Driver init failed: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return None

def scrape_ftn_single(driver, url, match_name):
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
            print(f'      ✅ Found prices: {dict(prices_found_for_match)}', flush=True)
            # Note: timestamp will be set by caller to use single run timestamp
            for cat, price in prices_found_for_match.items():
                records.append({
                    'match_url': url,
                    'match_name': match_name,
                    'category': cat,
                    'price': price,
                    'currency': 'USD',
                    'source': 'FootballTicketNet',
                    'timestamp': ''  # Will be set by caller with single run timestamp
                })
        else:
            print('      ❌ No valid prices found.', flush=True)
            
        return records

    except Exception as e:
        msg = str(e).lower()
        if 'crashed' in msg or 'disconnected' in msg or 'timeout' in msg:
            print(f'      🔥 Critical Driver Error: {e}', flush=True)
            return None # Signal to restart driver
        print(f'      ❌ Error: {e}', flush=True)
        return []

def run_ftn_scraper_cycle():
    GAMES_FILE = 'all_games_ftn_to_scrape.json'
    OUTPUT_FILE = 'prices_ftn.json'
    
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 FTN SCRAPER STARTING...', flush=True)
    
    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found. Run get_ftn_urls.py first.', flush=True)
        return

    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)
        
    print(f'   Target: {len(games)} games...', flush=True)
    
    # Initialize driver
    print('   Initializing Chrome driver...', flush=True)
    driver = get_driver()
    
    if not driver:
        print('   ❌ [ERROR] Failed to initialize driver at startup. Exiting.', flush=True)
        return
    
    print('   ✅ Driver initialized successfully', flush=True)
    
    # Create single timestamp for entire scraper run (like Viagogo)
    run_timestamp = datetime.now().isoformat()
    print(f'   📅 Run timestamp: {run_timestamp}', flush=True)
    
    try:
        existing_data = []
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, 'r') as f: existing_data = json.load(f)
            except: pass
        
        all_new_records = []  # Collect all records, save at end
        
        for i, game in enumerate(games, 1):
            # 🔄 BATCH RESTART: Proactively restart driver every 10 games to free memory
            if i > 1 and i % 10 == 1:
                print(f'   🔄 Scheduled Batch Restart (Match {i})...', flush=True)
                try: 
                    driver.quit()
                    print(f'   ✅ Old driver closed', flush=True)
                except Exception as quit_err:
                    print(f'   ⚠️ Error closing driver: {quit_err}', flush=True)
                driver = None
                time.sleep(1)  # Brief pause before getting new driver

            # 1. Check if driver is alive/healthy before starting
            if driver is None:
                print(f'   [RESTART] Getting new driver for match {i}...', flush=True)
                driver = get_driver()
                if not driver:
                    print(f'   ❌ Could not restart driver for match {i}, skipping...', flush=True)
                    continue
            
            # Show progress
            match_name = game.get('match_name', 'Unknown')
            print(f'   [{i}/{len(games)}] Scraping {match_name[:40]}...', flush=True)
            
            # 2. Scrape with retry/recovery logic
            try:
                new_records = scrape_ftn_single(driver, game['url'], game['match_name'])
                
                # If None returned (signal for critical error), force restart
                if new_records is None:
                    raise Exception("Critical Driver Error detected in worker")

                if new_records:
                    # Set single timestamp for all records in this run
                    for record in new_records:
                        record['timestamp'] = run_timestamp
                    all_new_records.extend(new_records)
                    print(f'      ✅ Collected {len(new_records)} price records', flush=True)
                else:
                    print(f'      ⚠️ No prices found for this match', flush=True)
            
            except Exception as e:
                print(f'   ⚠️ Driver Unstable ({e}). Restarting...', flush=True)
                try: 
                    driver.quit()
                except: 
                    pass
                driver = None # Force create new one next loop
                continue
            
            time.sleep(2) 
            
    except Exception as e:
        print(f'🔥 Fatal Error in FTN Cycle: {e}', flush=True)
        import traceback
        traceback.print_exc()
    finally:
        # Save all collected records at once at the end (like Viagogo does)
        if all_new_records:
            try:
                existing_data.extend(all_new_records)
                with open(OUTPUT_FILE, 'w') as f:
                    json.dump(existing_data, f, indent=2)
                print(f'\n[OK] Saved {len(all_new_records)} total price records to {OUTPUT_FILE}', flush=True)
            except Exception as save_err:
                print(f'\n[ERROR] Error saving results: {str(save_err)[:50]}', flush=True)
        
        if driver:
            try:
                driver.quit()
                print('   ✅ Driver closed', flush=True)
            except: 
                pass
    
    print(f'[{datetime.now().strftime("%H:%M")}] 💤 FTN CYCLE COMPLETE.', flush=True)

if __name__ == '__main__':
    run_ftn_scraper_cycle()