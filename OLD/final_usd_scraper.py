"""
FINAL USD SCRAPER
Forces proper currency and scrapes specific button format
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import sqlite3
import time
import re
import json
from datetime import datetime

DB_NAME = "prices.db"
GAMES_FILE = "all_games_to_scrape.json"

def set_usd_currency(driver):
    """Force the browser to use USD currency"""
    print("      Setting currency to USD...", end='', flush=True)
    try:
        # Method 1: URL Parameter injection
        current_url = driver.current_url
        if "Currency=USD" not in current_url:
            separator = "&" if "?" in current_url else "?"
            driver.get(current_url + separator + "Currency=USD")
            time.sleep(3)
        print(" Done.")
    except Exception as e:
        print(f" Failed ({e}).")

def extract_prices(driver):
    time.sleep(8)
    
    # 1. Ensure USD
    set_usd_currency(driver)
    
    # 2. Extract buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")
    
    prices = {}
    for btn in buttons:
        try:
            txt = btn.text
            # Look for "Category" and "$"
            if "Category" in txt and "$" in txt:
                lines = txt.split('\n')
                cat_num = None
                price_usd = None
                
                for line in lines:
                    cat_m = re.search(r'Category\s+(\d)', line)
                    if cat_m:
                        cat_num = cat_m.group(1)
                    
                    price_m = re.search(r'\$\s*([\d,]+)', line)
                    if price_m:
                        price_usd = float(price_m.group(1).replace(',', ''))
                
                if cat_num and price_usd:
                    prices[f"Category {cat_num}"] = price_usd
        except:
            pass
            
    return prices

def scrape_all():
    with open(GAMES_FILE) as f:
        games = json.load(f)
    
    print("="*70)
    print("  ✅ FINAL USD SCRAPER")
    print("="*70)
    print(f"\n📋 Games: {len(games)}")
    print(f"💰 Currency: FORCED USD")
    print(f"⏱  Time: ~35 minutes\n")
    
    opts = uc.ChromeOptions()
    opts.add_argument('--start-maximized')
    driver = uc.Chrome(options=opts, version_main=None)
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    ts = datetime.now().isoformat()
    
    ok = fail = 0
    
    try:
        # Scrape Match 1 first to verify
        print("🔍 Verifying Match 1...")
        g1 = games[51] # Match 1 is usually index 51 (Mexico vs South Africa)
        # Find exact Match 1
        for g in games:
            if "Match 1)" in g['match_name']:
                g1 = g
                break
        
        driver.get(g1['url'])
        p1 = extract_prices(driver)
        print(f"   Match 1 Results: {p1}")
        if not p1:
            print("   ⚠ WARNING: Could not extract Match 1 prices!")
        else:
            print("   ✅ Verified! Proceeding with full scrape...")
            
        print("\nStarting full scrape...\n")
        
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
                    print(f"✓ {len(prices)} prices")
                else:
                    fail += 1
                    print("✗ No prices")
                
                if i % 10 == 0:
                    print(f"      📊 {ok} OK, {fail} fail")
            except:
                fail += 1
                print("✗ Error")
                
    finally:
        driver.quit()
        conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ DONE! {ok}/104")
    print(f"{'='*70}")

if __name__ == '__main__':
    scrape_all()
