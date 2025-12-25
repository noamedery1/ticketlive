"""
Quick test to see what "View Tickets" elements look like
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

url = 'https://www.footballticketnet.com/arsenal-football-tickets/filter/home_away/home-matches'

options = uc.ChromeOptions()
options.add_argument('--start-maximized')

if sys.platform == 'win32':
    browser_path = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    if not os.path.exists(browser_path):
        browser_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    driver_path = r'C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe'
else:
    browser_path = None
    driver_path = None

driver = uc.Chrome(
    options=options,
    browser_executable_path=browser_path,
    driver_executable_path=driver_path,
    use_subprocess=False
)

try:
    driver.get(url)
    time.sleep(6)
    
    # Find View Tickets elements
    elements = driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view tickets')] | //button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view tickets')]")
    
    print(f'Found {len(elements)} View Tickets elements\n')
    
    for i, elem in enumerate(elements[:5], 1):
        print(f'Element {i}:')
        print(f'  Tag: {elem.tag_name}')
        print(f'  Text: {elem.text.strip()[:50]}')
        print(f'  href: {elem.get_attribute("href")}')
        print(f'  onclick: {elem.get_attribute("onclick")[:100] if elem.get_attribute("onclick") else None}')
        print(f'  data-href: {elem.get_attribute("data-href")}')
        print(f'  class: {elem.get_attribute("class")[:50]}')
        
        # Try parent
        try:
            parent = elem.find_element(By.XPATH, './ancestor::a[1]')
            print(f'  Parent <a> href: {parent.get_attribute("href")}')
        except:
            print(f'  No parent <a> found')
        print()
    
finally:
    driver.quit()

