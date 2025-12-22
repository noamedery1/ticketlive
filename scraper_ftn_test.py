import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import json
import os

URL = 'https://www.footballticketnet.com/world-cup-2026/match-85-group-b-winners-vs-group-e-f-g-i-j-third-place'
EUR_TO_USD = 1.05

def scrape_ftn_single():
    print('🚀 Starting FTN Scraper (Single URL)...')
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)

    try:
        driver.get(URL)
        print('⏳ Waiting for load...')
        time.sleep(15)
        
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        lines = body_text.split('\n')
        
        prices_found = []
        
        for i, line in enumerate(lines):
            if 'Category' in line:
                category = line.strip()
                if i > 0:
                    prev_line = lines[i-1].strip()
                    price_match = re.search(r'[€$£]\s*([\d,]+\.?\d*)', prev_line)
                    if price_match:
                        raw_price = float(price_match.group(1).replace(',', ''))
                        currency = 'EUR' if '€' in prev_line else 'USD'
                        final_price = raw_price
                        if currency == 'EUR':
                            final_price = round(raw_price * EUR_TO_USD, 2)
                            
                        print(f'✅ Found: {category} -> {currency} {raw_price} (USD {final_price})')
                        
                        prices_found.append({
                            'match_name': 'Match 85 Test',
                            'category': category,
                            'price': final_price,
                            'currency': 'USD',
                            'source': 'FootballTicketNet',
                            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S')
                        })
        
        with open('prices_ftn_test.json', 'w') as f:
            json.dump(prices_found, f, indent=2)
        print(f'💾 Saved {len(prices_found)} records to prices_ftn_test.json')

    except Exception as e:
        print(f'❌ Error: {e}')
    finally:
        driver.quit()

if __name__ == '__main__':
    scrape_ftn_single()
