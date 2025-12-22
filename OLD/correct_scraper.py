"""
CORRECT SCRAPER - Using the exact div class you found!
Targets buttons within the category div to extract prices
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

def extract_prices_from_buttons(driver):
    """Extract prices from category buttons"""
    try:
        time.sleep(10)  # Wait for page load
        
        # Find the div with categories
        category_div_class = "bway-jYfgsR.bway-bosYga.bway-hhuFNE.bway-eeyksK.bway-fPSCSl.bway-krXxSs.bway-eLQLw.bway-eLQLh.bway-iMODif.bway-bYPHoc"
        
        # Get all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        
        prices = {}
        
        for button in buttons:
            try:
                button_text = button.text
                
                # Check if button contains "Category" and a price
                if "Category" in button_text and "$" in button_text:
                    # Parse: "Category 1\n$4,740" or similar
                    lines = button_text.split('\n')
                    
                    category = None
                    price = None
                    
                    for line in lines:
                        if "Category" in line:
                            # Extract category number
                            cat_match = re.search(r'Category\s+(\d)', line)
                            if cat_match:
                                category = f"Category {cat_match.group(1)}"
                        
                        if "$" in line:
                            # Extract price
                            price_match = re.search(r'\$\s*([\d,]+)', line)
                            if price_match:
                                price = float(price_match.group(1).replace(',', ''))
                    
                    if category and price:
                        prices[category] = price
                        
            except:
                continue
        
        return prices
        
    except Exception as e:
        print(f"Error: {e}")
        return {}

def scrape_all_games():
    """Scrape all 104 games with CORRECT method"""
    
    with open(GAMES_FILE, 'r') as f:
        games = json.load(f)
    
    print("="*70)
    print("  ✅ CORRECTED SCRAPER - Button Label Method")
    print("="*70)
    print(f"\n📋 Games: {len(games)}")
    print(f"🎯 Method: Extract prices from category buttons")
    print(f"⏱  Time: ~25 minutes\n")
    
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    # options.add_argument('--headless=new')  # Uncomment for headless
    
    driver = uc.Chrome(options=options)
    driver.set_page_load_timeout(60)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    successful = 0
    failed = []
    
    try:
        for idx, game in enumerate(games, 1):
            match_name = game['match_name']
            match_url = game['url']
            
            print(f"[{idx:3d}/104] {match_name[:45]:45} ", end='', flush=True)
            
            try:
                driver.get(match_url)
                prices = extract_prices_from_buttons(driver)
                
                if prices:
                    # Delete old prices
                    cursor.execute('DELETE FROM price_history WHERE match_url = ?', (match_url,))
                    
                    # Insert new prices
                    for category, price in prices.items():
                        cursor.execute('''
                            INSERT INTO price_history 
                            (match_url, match_name, category, price, currency, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (match_url, match_name, category, price, 'USD', timestamp))
                    
                    conn.commit()
                    successful += 1
                    print(f"✓ {len(prices)} prices")
                else:
                    failed.append(match_name)
                    print("✗ No prices")
                
                time.sleep(3)
                
                if idx % 10 == 0:
                    print(f"      📊 {successful} OK, {len(failed)} failed")
                    
            except Exception as e:
                failed.append(match_name)
                print(f"✗ Error")
                
    finally:
        driver.quit()
        conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE!")
    print(f"   Success: {successful}/104 ({successful*100//104}%)")
    print(f"   Failed: {len(failed)}/104")
    print(f"{'='*70}\n")
    
    return successful

if __name__ == '__main__':
    scrape_all_games()
