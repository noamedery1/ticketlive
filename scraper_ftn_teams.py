"""
FTN Team-Specific Scraper
Scrapes team pages (e.g., /arsenal-football-tickets) to get home games only
and collects prices for each game.
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

EUR_TO_USD = 1.05
OUTPUT_FILE = 'ftn_teams_data.json'

def discover_teams_from_files():
    """Discover teams from existing *_prices.json files"""
    teams_dict = {}
    
    # Look for all *_prices.json files
    import glob
    pattern = '*_prices.json'
    team_files = glob.glob(pattern)
    
    print(f'   🔍 Discovering teams from {pattern} files...', flush=True)
    
    for file_path in team_files:
        try:
            # Extract team_key from filename (e.g., "arsenal_prices.json" -> "arsenal")
            team_key = os.path.basename(file_path).replace('_prices.json', '')
            
            # Read team_name and team_url from the file
            # Try to parse JSON, but if it fails, try to extract just the needed fields
            team_name = None
            team_url = None
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    team_data = json.load(f)
                    team_name = team_data.get('team_name', team_key.title())
                    team_url = team_data.get('team_url', '')
            except json.JSONDecodeError as json_err:
                # If JSON parsing fails, try to extract team_name and team_url manually
                print(f'      ⚠️ JSON parse error in {file_path}, trying to extract team info...', flush=True)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Try to find team_name and team_url using regex
                        name_match = re.search(r'"team_name"\s*:\s*"([^"]+)"', content)
                        url_match = re.search(r'"team_url"\s*:\s*"([^"]+)"', content)
                        
                        if name_match:
                            team_name = name_match.group(1)
                        else:
                            team_name = team_key.title()
                        
                        if url_match:
                            team_url = url_match.group(1)
                        else:
                            print(f'      ⚠️ Could not extract team_url from {file_path}', flush=True)
                except Exception as extract_err:
                    print(f'      ⚠️ Failed to extract team info: {extract_err}', flush=True)
                    continue
            
            if team_url:
                teams_dict[team_key] = {
                    'url': team_url,
                    'name': team_name or team_key.title()
                }
                print(f'      ✅ Found: {team_name or team_key.title()} ({team_key})', flush=True)
            else:
                print(f'      ⚠️ Skipping {team_key}: missing team_url', flush=True)
        except Exception as e:
            print(f'      ⚠️ Error reading {file_path}: {e}', flush=True)
            continue
    
    if not teams_dict:
        print(f'   ⚠️ No teams found. Using fallback config...', flush=True)
        # Fallback to default config
        return {
            'arsenal': {
                'url': 'https://www.footballticketnet.com/arsenal-football-tickets/filter/home_away/home-matches',
                'name': 'Arsenal'
            }
        }
    
    print(f'   ✅ Discovered {len(teams_dict)} team(s)', flush=True)
    return teams_dict

def get_teams_config():
    """Get teams config (cached)"""
    if not hasattr(get_teams_config, '_cache'):
        get_teams_config._cache = discover_teams_from_files()
    return get_teams_config._cache

def get_driver():
    """Get Chrome driver instance"""
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
            browser_path = None
            driver_path = None

        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
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
        print(f'   ❌ Driver init failed: {e}', flush=True)
        return None

def extract_games_from_current_page(driver, team_name, team_url_slug, seen_urls):
    """Extract game URLs from the current page by finding 'View Tickets' buttons/links"""
    page_games = []
    
    try:
        # Scroll to ensure all content is loaded
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Find "View Tickets" buttons/links - these ARE the game page links
        # Try multiple approaches to find these elements
        view_tickets_elements = []
        
        # Method 1: Direct <a> tags with "View Tickets" text
        try:
            elements = driver.find_elements(By.XPATH, 
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view tickets')] | "
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'buy tickets')]"
            )
            view_tickets_elements.extend(elements)
        except:
            pass
        
        # Method 2: Buttons with "View Tickets" text (might wrap <a> or have onclick)
        try:
            elements = driver.find_elements(By.XPATH,
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view tickets')] | "
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'buy tickets')]"
            )
            view_tickets_elements.extend(elements)
        except:
            pass
        
        # Method 3: Any element with "View Tickets" text (broader search)
        try:
            elements = driver.find_elements(By.XPATH,
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view tickets')] | "
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'buy tickets')]"
            )
            # Filter to only links and buttons
            view_tickets_elements.extend([e for e in elements if e.tag_name.lower() in ['a', 'button', 'div', 'span']])
        except:
            pass
        
        # Remove duplicates
        seen_elements = set()
        unique_elements = []
        for elem in view_tickets_elements:
            try:
                elem_id = elem.id
                if elem_id not in seen_elements:
                    seen_elements.add(elem_id)
                    unique_elements.append(elem)
            except:
                unique_elements.append(elem)
        
        view_tickets_elements = unique_elements
        print(f'   🔍 Found {len(view_tickets_elements)} "View Tickets" elements', flush=True)
        
        # Extract URLs from View Tickets buttons/links
        # Each "View Tickets" button IS the href link to the game page
        for elem in view_tickets_elements:
            try:
                href = None
                tag_name = elem.tag_name.lower()
                elem_text = elem.text.strip()
                
                # Method 1: If it's an <a> tag, get href directly
                if tag_name == 'a':
                    href = elem.get_attribute('href')
                
                # Method 2: If it's not an <a>, find the parent <a> tag (button inside link)
                if not href:
                    try:
                        # Look for closest parent <a> tag
                        parent_a = elem.find_element(By.XPATH, './ancestor::a[1]')
                        href = parent_a.get_attribute('href')
                    except:
                        pass
                
                # Method 3: Try to find the <a> tag that wraps this element or is nearby
                if not href:
                    try:
                        # Get the parent container and find all <a> tags in it
                        # The "View Tickets" button should be near or inside the game link
                        parent = elem.find_element(By.XPATH, './ancestor::*[position()<=10][1]')
                        all_links = parent.find_elements(By.TAG_NAME, 'a')
                        # Find the link that contains the team URL slug and is not a filter
                        for link in all_links:
                            link_href = link.get_attribute('href')
                            if link_href and team_url_slug in link_href.lower() and '/filter/' not in link_href:
                                href = link_href
                                break
                    except:
                        pass
                
                # Method 5: Use JavaScript to get href if element is clickable
                if not href:
                    try:
                        # Try to get href via JavaScript
                        js_href = driver.execute_script("""
                            var elem = arguments[0];
                            if (elem.tagName === 'A') {
                                return elem.href;
                            }
                            var parent = elem.closest('a');
                            if (parent) {
                                return parent.href;
                            }
                            // Look for <a> tag in parent container
                            var container = elem.closest('[class*="match"], [class*="event"], [class*="game"], [class*="card"], [class*="row"]');
                            if (container) {
                                var link = container.querySelector('a[href*="' + arguments[1] + '"]:not([href*="/filter/"])');
                                if (link) {
                                    return link.href;
                                }
                            }
                            return null;
                        """, elem, team_url_slug)
                        if js_href:
                            href = js_href
                    except:
                        pass
                
                # Method 4: Try onclick or data attributes as last resort
                if not href:
                    onclick = elem.get_attribute('onclick')
                    if onclick:
                        url_match = re.search(r'https?://[^\s\'"]+', onclick)
                        if url_match:
                            href = url_match.group(0)
                    
                    if not href:
                        href = elem.get_attribute('data-href') or elem.get_attribute('data-url')
                
                if not href:
                    print(f'      ⚠️ No href found for: {tag_name}, text: "{elem_text[:50]}"', flush=True)
                    continue
                
                # Normalize href
                if href.startswith('/'):
                    href = 'https://www.footballticketnet.com' + href
                elif not href.startswith('http'):
                    continue
                
                # Check if it's a game URL
                # Pattern 1: /[team-url-slug]/[game] (old pattern)
                # Pattern 2: /[competition]/[team]-vs-[opponent] (new pattern like /carabao-cup/arsenal-vs-chelsea)
                # Must contain team URL slug or team name and "vs" or be a team-football-tickets URL
                # Must NOT be a filter page
                is_game_url = False
                if '/filter/' not in href.lower():
                    if f'/{team_url_slug}/' in href.lower():
                        is_game_url = True
                    elif team_url_slug.split('-')[0] in href.lower() and ('vs' in href.lower() or '-vs-' in href.lower()):
                        is_game_url = True
                
                if is_game_url:
                    # Skip if we've seen this URL
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    # Try to get match name from nearby elements (parent container)
                    match_name = None
                    opponent = None
                    date = None
                    
                    try:
                        # Look for match name in parent container (the match card/row)
                        parent = elem.find_element(By.XPATH, './ancestor::*[contains(@class, "match") or contains(@class, "event") or contains(@class, "game") or contains(@class, "card") or contains(@class, "row")][1]')
                        parent_text = parent.text
                        
                        # Extract match name (Arsenal vs Opponent)
                        vs_match = re.search(rf'{re.escape(team_name)}\s+vs\s+(.+)', parent_text, re.IGNORECASE)
                        if vs_match:
                            match_name = vs_match.group(0).strip()
                            opponent = vs_match.group(1).strip()
                            # Clean up opponent (remove extra text after opponent name)
                            opponent = opponent.split('\n')[0].split('|')[0].strip()
                        
                        # Extract date (format: 27/12/25 or similar)
                        date_patterns = [
                            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                            r'(\d{1,2}\s+\w+\s+\d{4})'
                        ]
                        for pattern in date_patterns:
                            date_match = re.search(pattern, parent_text)
                            if date_match:
                                date = date_match.group(1)
                                break
                    except:
                        pass
                    
                    # If no match name found, extract from URL
                    if not match_name:
                        url_parts = href.split('/')
                        if len(url_parts) > 0:
                            last_part = url_parts[-1].split('?')[0]
                            match_name = last_part.replace('-', ' ').title()
                            # Try to extract opponent from URL
                            if '-vs-' in last_part.lower():
                                parts = last_part.split('-vs-')
                                if len(parts) > 1:
                                    opponent_parts = parts[1].split('-')[:3]
                                    opponent = ' '.join(opponent_parts).title()
                    
                    game_info = {
                        'url': href,
                        'match_name': match_name or f'{team_name} vs {opponent or "Opponent"}',
                        'team': team_name,
                        'opponent': opponent or 'Unknown',
                        'date': date,
                        'is_home': True
                    }
                    
                    page_games.append(game_info)
                    print(f'      ✅ Found: {game_info["match_name"]} -> {href[:100]}...', flush=True)
                    
            except Exception as e:
                continue
        
        # Method 2: Fallback - find all links with arsenal in URL
        if len(page_games) == 0:
            print(f'   ⚠️ No games found via View Tickets, trying fallback method...', flush=True)
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if not href:
                        continue
                    
                    # Normalize href
                    if href.startswith('/'):
                        href = 'https://www.footballticketnet.com' + href
                    elif not href.startswith('http'):
                        continue
                    
                    # Check if it's a game URL
                    if f'/{team_url_slug}/' in href.lower() and '/filter/' not in href:
                        if href in seen_urls:
                            continue
                        seen_urls.add(href)
                        
                        # Extract match name from text or URL
                        match_name = text if text and len(text) > 5 else None
                        if not match_name:
                            url_parts = href.split('/')
                            if len(url_parts) > 0:
                                last_part = url_parts[-1].split('?')[0]
                                match_name = last_part.replace('-', ' ').title()
                        
                        # Extract opponent
                        opponent = None
                        if match_name:
                            vs_match = re.search(rf'{re.escape(team_name)}\s+vs\s+(.+)', match_name, re.IGNORECASE)
                            if vs_match:
                                opponent = vs_match.group(1).strip()
                        
                        if 'vs' in (match_name or '').lower() or 'vs' in href.lower():
                            game_info = {
                                'url': href,
                                'match_name': match_name or f'{team_name} vs Opponent',
                                'team': team_name,
                                'opponent': opponent or 'Unknown',
                                'date': None,
                                'is_home': True
                            }
                            page_games.append(game_info)
                            print(f'      ✅ Found (fallback): {game_info["match_name"]} -> {href[:100]}...', flush=True)
                except:
                    continue
        
        return page_games
        
    except Exception as e:
        print(f'   ⚠️ Error extracting from page: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return []

def extract_home_game_urls(driver, team_url, team_name):
    """
    Extract all home game URLs from filtered home matches page.
    Tries to click "View All" button first to show all games on one page.
    """
    print(f'   📋 Extracting home games from {team_url}...', flush=True)
    home_games = []
    seen_urls = set()
    
    try:
        driver.get(team_url)
        time.sleep(6)  # Wait for page to load
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Try to find and click "View All" button to show all games at once
        view_all_clicked = False
        try:
            view_all_selectors = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view all')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view all')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view all')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'show all')]"
            ]
            
            for selector in view_all_selectors:
                try:
                    view_all_btn = driver.find_element(By.XPATH, selector)
                    if view_all_btn.is_displayed() and view_all_btn.is_enabled():
                        print(f'   🔘 Clicking "View All" button to show all games...', flush=True)
                        driver.execute_script("arguments[0].scrollIntoView(true);", view_all_btn)
                        time.sleep(1)
                        view_all_btn.click()
                        time.sleep(5)  # Wait for all games to load
                        view_all_clicked = True
                        break
                except:
                    continue
        except Exception as e:
            print(f'   ⚠️ Could not find "View All" button: {e}', flush=True)
        
        # Scroll to bottom to ensure all content is loaded
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        
        # Extract team URL slug from team_url (e.g., "fc-barcelona-football-tickets" from URL)
        team_url_slug = None
        url_parts = team_url.split('/')
        for part in url_parts:
            if 'football-tickets' in part:
                team_url_slug = part
                break
        if not team_url_slug:
            # Fallback: extract from URL path
            for part in url_parts:
                if part and part != 'filter' and 'home-matches' not in part:
                    team_url_slug = part
                    break
        
        # Extract all games from the page (now all should be visible)
        print(f'   📄 Extracting all games from page...', flush=True)
        page_games = extract_games_from_current_page(driver, team_name, team_url_slug, seen_urls)
        home_games.extend(page_games)
        print(f'   ✅ Found {len(home_games)} home games total', flush=True)
        
        return home_games
        
    except Exception as e:
        print(f'   ❌ Error extracting games: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return []

def scrape_game_prices(driver, game_url, game_name):
    """
    Scrape prices for a single game.
    Filters by "Up To 2 Seats Together" and groups lowest prices by block/category.
    """
    # Structure: {category: {block: min_price}}
    prices_by_block = defaultdict(lambda: defaultdict(lambda: float('inf')))
    
    try:
        driver.get(game_url)
        time.sleep(8)  # Wait for page to fully load
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Try to filter by "Up To 2 Seats Together"
        try:
            # Look for filter buttons/options
            filter_selectors = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'seating in singles')]",
                "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'seating in singles')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'up to 2 seats together')]",
                "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '2 seats together')]"
            ]
            
            for selector in filter_selectors:
                try:
                    filter_btn = driver.find_element(By.XPATH, selector)
                    if filter_btn.is_displayed():
                        # Check if it's already selected, if not click it
                        classes = filter_btn.get_attribute('class') or ''
                        if 'active' not in classes.lower() and 'selected' not in classes.lower():
                            print(f'      🔘 Clicking filter: "Up To 2 Seats Together"...', flush=True)
                            driver.execute_script("arguments[0].scrollIntoView(true);", filter_btn)
                            time.sleep(1)
                            filter_btn.click()
                            time.sleep(3)  # Wait for filter to apply
                            break
                except:
                    continue
        except:
            pass  # Continue even if filter not found
        
        # Scroll to load all tickets
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        try:
            body_text = driver.find_element(By.TAG_NAME, 'body').text
        except Exception as body_err:
            error_msg = str(body_err).lower()
            print(f'      ❌ Could not read page body: {error_msg[:50]}', flush=True)
            return {}
        
        lines = body_text.split('\n')
        
        # Parse ticket listings to extract: Category, Block, Price, and "Up To 2 Seats Together"
        current_category = None
        current_block = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Look for category/location names (like "Shortside Upper Level", "Category 3", etc.)
            if any(keyword in line_lower for keyword in ['category', 'longside', 'shortside', 'club level', 'executive', 'vip']):
                # Check if this looks like a category name (not just containing the word)
                if len(line.strip()) < 50 and not any(char.isdigit() for char in line.strip()[:5]):
                    current_category = line.strip()
                    current_block = None  # Reset block when new category found
            
            # Look for block information (Block: 105,100,102,106)
            block_match = re.search(r'block[:\s]+([\d,\s]+)', line, re.IGNORECASE)
            if block_match:
                blocks_str = block_match.group(1)
                # Extract individual block numbers
                block_numbers = re.findall(r'\d+', blocks_str)
                if block_numbers:
                    current_block = ','.join(block_numbers)
            
            # Look for "Up To 2 Seats Together" or similar
            if 'up to 2 seats together' in line_lower or '2 seats together' in line_lower:
                # Look for price nearby (check next few lines)
                for offset in range(1, 5):
                    if i + offset < len(lines):
                        check_line = lines[i + offset].strip()
                        price_match = re.search(r'([€$£])\s*([\d,]+\.?\d*)', check_line)
                        if price_match:
                            currency_sym = price_match.group(1)
                            raw_val = float(price_match.group(2).replace(',', ''))
                            
                            price_usd = raw_val
                            if '€' in currency_sym:
                                price_usd = round(raw_val * EUR_TO_USD, 2)
                            
                            # Store price by category and block
                            if current_category:
                                block_key = current_block if current_block else 'Unknown'
                                if price_usd < prices_by_block[current_category][block_key]:
                                    prices_by_block[current_category][block_key] = price_usd
                            break
            
            # Also look for prices directly (might be in table format)
            price_match = re.search(r'([€$£])\s*([\d,]+\.?\d*)', line)
            if price_match and current_category:
                # Check if previous/next lines mention "Up To 2 Seats Together"
                context_lines = ' '.join(lines[max(0, i-3):min(len(lines), i+3)]).lower()
                if 'up to 2 seats together' in context_lines or '2 seats together' in context_lines:
                    currency_sym = price_match.group(1)
                    raw_val = float(price_match.group(2).replace(',', ''))
                    
                    price_usd = raw_val
                    if '€' in currency_sym:
                        price_usd = round(raw_val * EUR_TO_USD, 2)
                    
                    block_key = current_block if current_block else 'Unknown'
                    if price_usd < prices_by_block[current_category][block_key]:
                        prices_by_block[current_category][block_key] = price_usd
        
        # Convert to final format: {category: {block: price}}
        result = {}
        for category, blocks in prices_by_block.items():
            result[category] = dict(blocks)
        
        # If no block-specific prices found, try to get category-level prices
        if not result:
            # Fallback to simple category-based extraction
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
                                if normalized_cat not in result:
                                    result[normalized_cat] = {}
                                if 'Unknown' not in result[normalized_cat] or price_usd < result[normalized_cat].get('Unknown', float('inf')):
                                    result[normalized_cat]['Unknown'] = price_usd
        
        return result
        
    except Exception as e:
        print(f'      ❌ Error scraping prices: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return {}

def run_team_scraper(team_key='arsenal'):
    """Main scraper function for a team"""
    TEAMS_CONFIG = get_teams_config()
    if team_key not in TEAMS_CONFIG:
        print(f'❌ Team "{team_key}" not found in config', flush=True)
        return
    
    team_config = TEAMS_CONFIG[team_key]
    team_url = team_config['url']
    team_name = team_config['name']
    
    print(f'\n🚀 Starting FTN Team Scraper for {team_name}...', flush=True)
    print(f'   URL: {team_url}', flush=True)
    
    # Load existing data
    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                existing_data = json.load(f)
        except:
            existing_data = {}
    
    # Initialize team data if not exists
    if team_key not in existing_data:
        # Try to load from individual team file first (if manually created)
        team_specific_file = f'{team_key}_prices.json'
        if os.path.exists(team_specific_file):
            try:
                with open(team_specific_file, 'r') as f:
                    team_file_data = json.load(f)
                    existing_data[team_key] = {
                        'team_name': team_file_data.get('team_name', team_name),
                        'team_url': team_file_data.get('team_url', team_url),
                        'games': team_file_data.get('games', []),
                        'last_updated': team_file_data.get('last_updated')
                    }
                    print(f'   📂 Loaded existing data from {team_specific_file}', flush=True)
            except Exception as e:
                print(f'   ⚠️ Error loading {team_specific_file}: {e}', flush=True)
                existing_data[team_key] = {
                    'team_name': team_name,
                    'team_url': team_url,
                    'games': [],
                    'last_updated': None
                }
        else:
            existing_data[team_key] = {
                'team_name': team_name,
                'team_url': team_url,
                'games': [],
                'last_updated': None
            }
    
    driver = get_driver()
    if not driver:
        print('❌ Failed to initialize driver', flush=True)
        return
    
    try:
        # Step 1: Extract all home game URLs from team page (with pagination)
        current_games = extract_home_game_urls(driver, team_url, team_name)
        
        # Step 2: Update game list
        # - Add new games
        # - Remove games that no longer exist (but keep history)
        existing_games = {g['url']: g for g in existing_data[team_key]['games']}
        current_urls = {g['url']: g for g in current_games}
        
        # Add new games
        for game in current_games:
            if game['url'] not in existing_games:
                existing_games[game['url']] = {
                    **game,
                    'price_history': []
                }
                print(f'   ➕ Added new game: {game["match_name"]}', flush=True)
        
        # Mark games for removal (but keep history)
        removed_games = []
        for url, game in existing_games.items():
            if url not in current_urls:
                removed_games.append(game['match_name'])
                print(f'   ➖ Game no longer on site (keeping history): {game["match_name"]}', flush=True)
        
        # Step 3: Scrape prices for all current games
        run_timestamp = datetime.now().isoformat()
        print(f'\n   📅 Run timestamp: {run_timestamp}', flush=True)
        print(f'   📊 Scraping prices for {len(current_urls)} games...\n', flush=True)
        
        for i, (url, game) in enumerate(current_urls.items(), 1):
            game_data = existing_games[url]
            print(f'   [{i}/{len(current_urls)}] {game_data["match_name"]}...', flush=True)
            
            prices = scrape_game_prices(driver, url, game_data['match_name'])
            
            if prices:
                # Count total blocks/categories
                total_blocks = sum(len(blocks) for blocks in prices.values())
                # Add price snapshot to history
                price_snapshot = {
                    'timestamp': run_timestamp,
                    'prices': prices  # Format: {category: {block: price}}
                }
                game_data['price_history'].append(price_snapshot)
                game_data['latest_prices'] = prices
                game_data['last_scraped'] = run_timestamp
                print(f'      ✅ Found {len(prices)} categories with {total_blocks} blocks', flush=True)
                # Show sample prices
                for cat, blocks in list(prices.items())[:3]:
                    for block, price in list(blocks.items())[:2]:
                        print(f'         {cat} - Block {block}: ${price:.2f}', flush=True)
            else:
                print(f'      ⚠️ No prices found', flush=True)
            
            time.sleep(3)  # Be nice to the server
        
        # Update existing data
        existing_data[team_key]['games'] = list(existing_games.values())
        existing_data[team_key]['last_updated'] = run_timestamp
        
        # Save to main teams file
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        # Also save team-specific file (for backward compatibility and easier access)
        team_specific_file = f'{team_key}_prices.json'
        team_data = existing_data[team_key]
        with open(team_specific_file, 'w') as f:
            json.dump(team_data, f, indent=2)
        print(f'   💾 Saved {team_name} data to {team_specific_file}', flush=True)
        
        print(f'\n✅ Scraper complete!', flush=True)
        print(f'   Total games: {len(existing_games)}', flush=True)
        print(f'   Active games: {len(current_urls)}', flush=True)
        print(f'   Removed games: {len(removed_games)}', flush=True)
        
    except Exception as e:
        print(f'❌ Error in scraper: {e}', flush=True)
        import traceback
        traceback.print_exc()
    finally:
        try:
            driver.quit()
        except:
            pass

if __name__ == '__main__':
    # Default to arsenal, can be overridden
    team = sys.argv[1] if len(sys.argv) > 1 else 'arsenal'
    run_team_scraper(team)
