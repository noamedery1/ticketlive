import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import json
import os
from collections import defaultdict
from datetime import datetime

EUR_TO_USD = 1.05  # Approximate rate

def scrape_ftn_single(url, match_name):
    print(f'   Scraping {match_name[:30]}...')
    
    try:
        options = uc.ChromeOptions()
        if os.environ.get('HEADLESS') == 'true':
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
        driver = uc.Chrome(options=options)
    except Exception as e:
        print(f'❌ [ERROR] Chrome Driver init failed: {e}')
        return []

    prices_found_for_match = defaultdict(lambda: float('inf'))

    try:
        driver.get(url)
        time.sleep(8) 
        
        try:
            body_text = driver.find_element(By.TAG_NAME, 'body').text
        except:
            print('      ❌ Could not read page body')
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
        print(f'      🔥 Error: {e}')
        return []
    finally:
        try: driver.quit()
        except: pass

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
    
    existing_data = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f: existing_data = json.load(f)
        except: pass
    
    for i, game in enumerate(games):
        new_records = scrape_ftn_single(game['url'], game['match_name'])
        if new_records:
            existing_data.extend(new_records)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(existing_data, f, indent=2)
        
        time.sleep(2) 
    
    print(f'[{datetime.now().strftime("%H:%M")}] 💤 FTN CYCLE COMPLETE.')

if __name__ == '__main__':
    run_ftn_scraper_cycle()