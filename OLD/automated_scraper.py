import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import sqlite3
import time
import json
import os
import re
from datetime import datetime

# Configuration
DB_NAME = "prices.db"
GAMES_FILE = "all_games_to_scrape.json"
ILS_TO_USD = 0.28

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def extract_prices_from_buttons(driver):
    try:
        time.sleep(8)
        buttons = driver.find_elements(By.TAG_NAME, "button")
        prices = {}
        for btn in buttons:
            try:
                txt = btn.text
                if "Category" in txt:
                    lines = txt.split('\n')
                    cat_num = None
                    price_val = None
                    
                    for line in lines:
                        cat_m = re.search(r'Category\s+(\d)', line, re.I)
                        if cat_m:
                            cat_num = cat_m.group(1)
                        
                        if '$' in line:
                            price_m = re.search(r'\$\s*([\d,]+)', line)
                            if price_m:
                                price_val = float(price_m.group(1).replace(',', ''))
                        elif '₪' in line and price_val is None:
                            price_m = re.search(r'₪([\d,]+)', line)
                            if price_m:
                                val = float(price_m.group(1).replace(',', ''))
                                price_val = round(val * ILS_TO_USD, 2)

                    if cat_num and price_val:
                        prices[f"Category {cat_num}"] = price_val
            except:
                continue
        return prices
    except Exception as e:
        print(f"Extraction error: {e}")
        return {}

def scrape_games():
    print("="*60)
    print("  🤖 AUTOMATED SCRAPER (APPEND MODE - History Enabled)")
    print("="*60)
    
    if not os.path.exists(GAMES_FILE):
        return
        
    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)

    print(f"📋 Games to scrape: {len(games)}")
    
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=None)
    driver.set_page_load_timeout(60)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    successful = 0

    try:
        for i, game in enumerate(games, 1):
            match_name = game['match_name']
            match_url = game['url']
            
            clean_url = match_url.split('&Currency')[0].split('?Currency')[0]
            if "Currency=USD" not in match_url:
                separator = "&" if "?" in match_url else "?"
                match_url += f"{separator}Currency=USD"

            print(f"[{i:3}/{len(games)}] {match_name[:40]:40} ", end='', flush=True)

            try:
                driver.get(match_url)
                prices = extract_prices_from_buttons(driver)

                if prices:
                    # REMOVED THE DELETE STATEMENT HERE!
                    # Now we simply INSERT new rows.
                    
                    for cat, price in prices.items():
                        cursor.execute("""
                            INSERT INTO price_history (match_url, match_name, category, price, currency, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (clean_url, match_name, cat, price, 'USD', timestamp))
                    
                    conn.commit()
                    successful += 1
                    print(f"✓ Found {len(prices)} prices (Saved to history)")
                else:
                    print("✗ No prices found")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"✗ Error: {e}")

    except Exception as e:
        print(f"\nFatal error: {e}")
    finally:
        driver.quit()
        conn.close()

    print("\n" + "="*60)
    print("✅ SCRAPING COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    scrape_games()
