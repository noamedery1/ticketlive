import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import re
import os

URL = 'https://www.footballticketnet.com/world-cup-2026/match-85-group-b-winners-vs-group-e-f-g-i-j-third-place'

def test_scrape():
    print('🚀 Starting Test Scraper for Football Ticket Net...')
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)

    try:
        print(f'🔗 Navigating to: {URL}')
        driver.get(URL)
        
        print('⏳ Waiting for page to load (15s)...')
        time.sleep(15) 
        
        with open('debug_ftn.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print('💾 Saved page source to debug_ftn.html')

        print('🔍 Searching for pricing elements...')
        
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        lines = body_text.split('\n')
        
        print('\n--- EXTRACTED POTENTIAL MATCHES ---')
        for i, line in enumerate(lines):
            if 'Category' in line or '€' in line or '$' in line:
                if len(line) < 100: 
                    print(f'Line {i}: {line}')
                    
        print('-----------------------------------\n')

    except Exception as e:
        print(f'❌ Error: {e}')
    finally:
        driver.quit()
        print('✅ Test Complete.')

if __name__ == '__main__':
    test_scrape()
