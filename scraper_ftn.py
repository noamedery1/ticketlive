import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

EUR_TO_USD = 1.05  # Approximate rate

def get_driver():
    import random
    time.sleep(random.uniform(0.5, 2.0))
    
    try:
        if sys.platform == 'win32':
            browser_path = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
            if not os.path.exists(browser_path):
                browser_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
            if not os.path.exists(browser_path):
                browser_path = None
            driver_path = r'C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe'
            if not os.path.exists(driver_path):
                driver_path = None
        else:
            browser_path = '/usr/bin/chromium'
            driver_path = '/usr/bin/chromedriver'

        for attempt in range(3):
            try:
                options = uc.ChromeOptions()
                if os.environ.get('HEADLESS') == 'true':
                    options.add_argument('--headless')
                
                driver = uc.Chrome(
                    options=options, 
                    version_main=None, 
                    browser_executable_path=browser_path, 
                    driver_executable_path=driver_path,
                    use_subprocess=False
                )
                print(f'   ✅ Driver initialized', flush=True)
                return driver
            except Exception as e:
                print(f'   ⚠️ Driver init error: {e}. Retrying...', flush=True)
                time.sleep(2)
        return None
    except Exception as e:
        print(f'❌ [ERROR] Chrome Driver init failed: {e}', flush=True)
        return None

def scrape_ftn_single(driver, url, match_name):
    """
    Robust scraping of a single match page on FTN.
    Uses DOM parsing with multiple fallback strategies.
    """
    prices_found_for_match = defaultdict(lambda: float('inf'))

    try:
        driver.get(url)
        time.sleep(5) # Initial load
        
        # Scroll to load everything
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
             driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
             time.sleep(2)
             new_height = driver.execute_script("return document.body.scrollHeight")
             if new_height == last_height:
                 break
             last_height = new_height
        
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # Strategy 0: JSON Data (Most Reliable)
        json_found = 0
        try:
            page_source = driver.page_source
            match = re.search(r'var event_object\s*=\s*({.*?});', page_source, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                currency_symbol = data.get('currency', '')
                cats = data.get('category_statistic', {})
                
                if cats:
                    print(f'      ✨ Found JSON data with {len(cats)} categories', flush=True)
                    
                for k, v in cats.items():
                    raw_name = v.get('name', '')
                    min_price = v.get('min_price')
                    
                    # Normalize category name
                    cat_match = re.search(r'Category\s+(1\s+Premium|1|2|3|4)', raw_name, re.IGNORECASE)
                    if cat_match:
                        category = f'Category {cat_match.group(1).title()}'
                    elif 'best available' in raw_name.lower():
                        continue # Skip best available
                    else:
                        category = raw_name # Keep original if not standard pattern
                        
                    # Process Price
                    try:
                         val = float(str(min_price).replace(',', ''))
                         
                         # Currency Conversion based on JSON currency symbol
                         if 'euro' in currency_symbol.lower() or '€' in currency_symbol:
                             val *= EUR_TO_USD
                         elif 'pound' in currency_symbol.lower() or '£' in currency_symbol:
                             val *= 1.25
                             
                         if val < prices_found_for_match[category]:
                             prices_found_for_match[category] = round(val, 2)
                             json_found += 1
                    except:
                        pass
        except Exception as e:
            print(f'      ⚠️ JSON extraction failed: {e}', flush=True)

        if json_found > 0:
             print(f'      ✅ Extracted {json_found} prices from JSON', flush=True)

        # Strategy 1: DOM Elements (Most Reliable)
        listings = []
        selectors = ["div.inner_price", ".ticket-listing", "[data-price]", ".listing-row"]
        
        for sel in selectors:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if found:
                listings.extend(found)
        
        # Remove duplicates
        listings = list(set(listings))
        
        if not listings:
             # Fallback to broader search
             listings = driver.find_elements(By.XPATH, "//*[contains(@class, 'row') or contains(@class, 'listing')]")

        dom_found = 0
        for listing in listings:
            try:
                text = listing.text.lower()
                
                # Extract Category
                cat_match = re.search(r'Category\s+(1\s+Premium|1|2|3|4)', text, re.IGNORECASE)
                if not cat_match:
                    # Try finding class name or attributes
                    inner_html = listing.get_attribute('innerHTML').lower()
                    cat_match = re.search(r'category\s+(1\s+premium|1|2|3|4)', inner_html, re.IGNORECASE)
                
                if cat_match:
                    category = f'Category {cat_match.group(1).title()}'
                    
                    # Extract Price
                    price = float('inf')
                    
                    # Try data-price attribute
                    price_attr = listing.get_attribute('data-price')
                    if price_attr:
                        try:
                            price = float(price_attr.replace(',', ''))
                        except: pass
                    
                    # Try finding price text in element
                    if price == float('inf'):
                        price_match = re.search(r'([€$£])\s*([\d,]+\.?\d*)', text)
                        if price_match:
                             currency_sym = price_match.group(1)
                             val = float(price_match.group(2).replace(',', ''))
                             # Convert to USD if needed
                             if '€' in currency_sym: val *= EUR_TO_USD
                             if '£' in currency_sym: val *= 1.25 # Approx GBP
                             price = val
                    
                    if price != float('inf'):
                        if price < prices_found_for_match[category]:
                             prices_found_for_match[category] = round(price, 2)
                             dom_found += 1
            except:
                continue

        # Strategy 2: Text Fallback (if DOM failed)
        if dom_found == 0 or not prices_found_for_match:
            print(f'      ⚠️ No prices from DOM, trying text fallback...', flush=True)
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            lines = body_text.split('\n')
            
            for i, line in enumerate(lines):
                if 'Category' in line:
                    cat_match = re.search(r'Category\s+(1\s+Premium|1|2|3|4)', line, re.IGNORECASE)
                    if cat_match:
                        category = f'Category {cat_match.group(1).title()}'
                        
                        # Search nearby lines for price
                        price_found = False
                        # Check current line and previous/next few lines
                        search_range = lines[max(0, i-2):min(len(lines), i+3)]
                        
                        for check_line in search_range:
                            # Avoid confusing match numbers with prices
                            if 'match' in check_line.lower(): continue
                            
                            price_match = re.search(r'([€$£])\s*([\d,]+\.?\d*)', check_line)
                            if price_match:
                                currency_sym = price_match.group(1)
                                val = float(price_match.group(2).replace(',', ''))
                                if '€' in currency_sym: val *= EUR_TO_USD
                                if '£' in currency_sym: val *= 1.25
                                
                                if val < prices_found_for_match[category]:
                                    prices_found_for_match[category] = round(val, 2)
                                    price_found = True
                        
        records = []
        if prices_found_for_match:
            print(f'      ✅ Found prices: {dict(prices_found_for_match)}', flush=True)
            for cat, price in prices_found_for_match.items():
                records.append({
                    'match_url': url,
                    'match_name': match_name,
                    'category': cat,
                    'price': price,
                    'currency': 'USD',
                    'source': 'FootballTicketNet',
                    'timestamp': '' 
                })
        else:
            print('      ❌ No valid prices found.', flush=True)
            
        return records

    except Exception as e:
        print(f'      ❌ Error: {e}', flush=True)
        return []

def run_ftn_scraper_cycle():
    GAMES_FILE = 'all_games_ftn_to_scrape.json'
    OUTPUT_FILE = 'prices_ftn.json'
    
    print(f'\n[{datetime.now().strftime("%H:%M")}] 🚀 FTN SCRAPER STARTING...', flush=True)
    
    if not os.path.exists(GAMES_FILE):
        print(f'❌ [ERROR] {GAMES_FILE} not found.', flush=True)
        return

    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)
        
    driver = get_driver()
    if not driver: return
    
    run_timestamp = datetime.now().isoformat()
    print(f'   📅 Run timestamp: {run_timestamp}', flush=True)
    
    existing_data = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f: existing_data = json.load(f)
        except: pass
    
    all_new_records = []
    
    try:
        for i, game in enumerate(games, 1):
            if i > 1 and i % 10 == 1:
                driver.quit()
                driver = get_driver()
            
            print(f'   [{i}/{len(games)}] Scraping {game.get("match_name", "Unknown")[:40]}...', flush=True)
            new_records = scrape_ftn_single(driver, game['url'], game.get('match_name'))
            
            if new_records:
                for r in new_records: r['timestamp'] = run_timestamp
                all_new_records.extend(new_records)
            
            time.sleep(2)
            
    finally:
        if all_new_records:
            existing_data.extend(all_new_records)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(existing_data, f, indent=2)
            print(f'\n[OK] Saved {len(all_new_records)} records.', flush=True)
        
        if driver: driver.quit()

if __name__ == '__main__':
    run_ftn_scraper_cycle()