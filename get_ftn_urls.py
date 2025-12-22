import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import re

BASE_URL = 'https://www.footballticketnet.com'
OUTPUT_FILE = 'all_games_ftn_to_scrape.json'
PAGES_TO_SCRAPE = 5

def get_all_match_urls():
    print(f'🚀 Getting FTN Match URLs (Pages 1-{PAGES_TO_SCRAPE})...')
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)
    all_game_links = []
    unique_urls = set()

    try:
        for page_num in range(1, PAGES_TO_SCRAPE + 1):
            url = f'{BASE_URL}/world-cup-2026-football-tickets?page={page_num}'
            print(f'   📄 Scraping Page {page_num}: {url}')
            driver.get(url)
            time.sleep(5) 
            
            links = driver.find_elements(By.TAG_NAME, 'a')
            
            page_count = 0
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/world-cup-2026/match-' in href:
                         
                         full_url = href
                         if full_url in unique_urls:
                             continue
                             
                         match_name = link.text.strip()
                         if not match_name or 'Tickets' in match_name or 'Buy' in match_name:
                             slug = href.split('/')[-1]
                             parts = slug.replace('-', ' ').replace('match', 'Match').split('?')[0]
                             match_name = parts.title()

                         unique_urls.add(full_url)
                         all_game_links.append({
                             'match_name': match_name,
                             'url': full_url
                         })
                         page_count += 1
                except:
                    continue
            
            print(f'      ✅ Found {page_count} matches on page {page_num}')
            time.sleep(2)

        print(f'\n✨ Total unique matches found: {len(all_game_links)}')
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(all_game_links, f, indent=2)
        print(f'💾 Saved to {OUTPUT_FILE}')

    except Exception as e:
        print(f'❌ Error: {e}')
    finally:
        driver.quit()

if __name__ == '__main__':
    get_all_match_urls()
