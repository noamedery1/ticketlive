"""
PRODUCTION SCRAPER - Working button extraction method!
Extracts ILS prices and converts to USD
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import sqlite3
import time
import re
import json
from datetime import datetime

DB_NAME = "prices.db"
GAMES_FILE = "all_games_to_scrape.json"
ILS_TO_USD = 0.27  # Approximate conversion

def extract_prices(driver):
    time.sleep(12)
    buttons = driver.find_elements(By.TAG_NAME, "button")
    
    prices = {}
    for btn in buttons:
        try:
            txt = btn.text
            if "Category" in txt and "" in txt:
                lines = txt.split('\n')
                cat_num = price_ils = None
                
                for line in lines:
                    cat_m = re.search(r'Category\s+(\d)', line)
                    if cat_m:
                        cat_num = cat_m.group(1)
                    
                    price_m = re.search(r'([\d,]+)', line)
                    if price_m:
                        price_ils = float(price_m.group(1).replace(',', ''))
                
                if cat_num and price_ils:
                    prices[f"Category {cat_num}"] = round(price_ils * ILS_TO_USD, 2)
        except:
            pass
    
    return prices

def scrape_all():
    with open(GAMES_FILE) as f:
        games = json.load(f)
    
    print("="*70)
    print("  🎯 PRODUCTION SCRAPER - WORKING METHOD!")
    print("="*70)
    print(f"\n📋 Games: {len(games)}")
    print(f"💱 ILS→USD conversion: {ILS_TO_USD}")
    print(f"⏱  Time: ~25 minutes\n")
    
   opts = uc.ChromeOptions()
    opts.add_argument('--start-maximized')
    driver = uc.Chrome(options=opts, version_main=None)
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    ts = datetime.now().isoformat()
    
    ok = fail = 0
    
    try:
        for i, g in enumerate(games, 1):
            name, url = g['match_name'], g['url']
            print(f"[{i:3}/104] {name[:40]:40} ", end='', flush=True)
            
            try:
                driver.get(url)
                prices = extract_prices(driver)
                
                if prices:
                    cur.execute('DELETE FROM price_history WHERE match_url=?', (url,))
                    for cat, price in prices.items():
                        cur.execute('INSERT INTO price_history VALUES(NULL,?,?,?,?,?,?)',
                                  (url, name, cat, price, 'USD', ts))
                    conn.commit()
                    ok += 1
                    print(f"✓ {len(prices)}")
                else:
                    fail += 1
                    print("✗")
                
                time.sleep(3)
                if i % 10 == 0:
                    print(f"      📊 {ok} OK, {fail} fail")
            except:
                fail += 1
                print("✗")
    finally:
        driver.quit()
        conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ DONE! {ok}/104 ({ok*100//104}%)")
    print(f"{'='*70}")

if __name__ == '__main__':
    scrape_all()
