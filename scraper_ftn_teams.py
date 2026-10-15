"""
FTN team scraper (FootballTicketNet, site layout from 2026).

    python scraper_ftn_teams.py <team_key>

Team page   /<slug>-football-tickets  -> "Upcoming matches" links to /<comp>/<home>-vs-<away>-.../event/<id>
Event page  JSON-LD SportsEvent (name, startDate, performers, priceCurrency)
            + a "zones" list in the page data: per category lowest_price and listing count.

Only home games are kept (event slug starts with "<team slug>-vs-"), unless the team in
teams_list.json has "all_games": true (e.g. a tournament page like the Champions League).
Exit code 0 = saved, 1 = failed (nothing written).
"""
import json
import os
import random
import re
import sys
import time
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE = 'https://www.footballticketnet.com'
OUTPUT_FILE = 'ftn_teams_data.json'
TEAMS_LIST_FILE = 'teams_list.json'
PAGE_TIMEOUT = 30   # seconds to wait for a page's data
PAUSE = (3, 6)      # seconds between page loads, be nice to the site


def log(msg):
    print(msg, flush=True)


def load_team(team_key):
    with open(TEAMS_LIST_FILE, 'r', encoding='utf-8') as f:
        for t in json.load(f).get('teams', []):
            if t.get('team_key') == team_key:
                return t
    return None


def get_driver():
    """Chrome via undetected_chromedriver. CHROME_MAJOR pins the driver (109 on Windows 7)."""
    browser_path = driver_path = None
    if sys.platform == 'win32':
        for p in (r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                  r'C:\Program Files\Google\Chrome\Application\chrome.exe'):
            if os.path.exists(p):
                browser_path = p
                break
        p = r'C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe'
        driver_path = p if os.path.exists(p) else None
    options = uc.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    try:
        driver = uc.Chrome(
            options=options,
            version_main=int(os.environ['CHROME_MAJOR']) if os.environ.get('CHROME_MAJOR') else None,
            browser_executable_path=browser_path,
            driver_executable_path=driver_path,
            use_subprocess=False,
        )
        driver.set_page_load_timeout(90)
        return driver
    except Exception as e:
        log(f'   ❌ Driver init failed: {e}')
        return None


def with_currency(url, currency):
    return f'{url}{"&" if "?" in url else "?"}currency={currency}' if currency else url


def wait_for(driver, predicate):
    """Poll page_source until predicate(html) is truthy. Returns html or None."""
    end = time.time() + PAGE_TIMEOUT
    while time.time() < end:
        html = driver.page_source
        if predicate(html):
            return html
        time.sleep(1)
    return None


def list_events(driver, team):
    """Upcoming event URLs from the team page (home games only unless all_games)."""
    team_url = team['team_url'].split('/filter/')[0]
    slug = team_url.rstrip('/').rsplit('/', 1)[-1].replace('-football-tickets', '')
    driver.get(with_currency(team_url, team.get('currency')))
    if not wait_for(driver, lambda h: '/event/' in h):
        log(f'   ❌ No event links on {team_url} (blocked or layout changed)')
        return []
    links = driver.find_elements(By.CSS_SELECTOR, '[class*="UpcomingMatchesSection"] a[href*="/event/"]')
    if not links:  # section class renamed: fall back to every event link on the page
        links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/event/"]')
    urls = []
    for a in links:
        href = (a.get_attribute('href') or '').split('?')[0]
        m = re.match(r'https://www\.footballticketnet\.com/[a-z0-9-]+/([a-z0-9-]+)/event/\d+$', href)
        if not m or href in urls:
            continue
        if team.get('all_games') or m.group(1).startswith(f'{slug}-vs-'):
            urls.append(href)
    log(f'   📋 {len(urls)} upcoming {"games" if team.get("all_games") else "home games"}')
    return urls


ZONES_RE = re.compile(r'"zones":(\[[^\[\]]*\])')


def parse_event(html):
    """(event_info, zones) from an event page, or (None, None) if the data is missing."""
    event = None
    for block in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        if isinstance(data, dict) and data.get('@type') == 'SportsEvent':
            event = data
            break
    m = ZONES_RE.search(html.replace('\\"', '"'))
    if not event or not m:
        return None, None
    try:
        zones = json.loads(m.group(1))
    except ValueError:
        return None, None
    return event, zones


def scrape_event(driver, url, currency):
    driver.get(with_currency(url, currency))
    html = wait_for(driver, lambda h: 'SportsEvent' in h and 'zones' in h)
    if not html:
        log('      ⚠️ Page data not found')
        return None
    event, zones = parse_event(html)
    if not event:
        log('      ⚠️ Could not parse page data')
        return None
    start = datetime.fromisoformat(event['startDate'].replace('Z', '+00:00'))  # 3.8 has no 'Z'
    performers = [p.get('name') for p in event.get('performer', []) if isinstance(p, dict)]
    latest = {}
    for z in zones:
        price = z.get('lowest_price')
        if z.get('name') and isinstance(price, (int, float)) and price > 0:
            latest[z['name']] = {'min': price, 'count': z.get('count', 0)}
    return {
        'match_name': event.get('name'),
        'opponent': performers[1] if len(performers) > 1 else None,
        'date': start.strftime('%d/%m/%Y'),
        'start': event['startDate'],
        'competition': (event.get('organizer') or {}).get('name'),
        'currency': (event.get('offers') or {}).get('priceCurrency') or currency,
        'latest_prices': latest,
    }


def run_team_scraper(team_key):
    team = load_team(team_key)
    if not team:
        log(f'❌ Team "{team_key}" not in {TEAMS_LIST_FILE}')
        return False
    log(f'\n🚀 {team.get("team_name", team_key)}')

    data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            # Never fall back to {} here: saving would wipe every other team's history.
            log(f'❌ {OUTPUT_FILE} is unreadable ({e}). Restore it from git, then rerun.')
            return False

    driver = get_driver()
    if not driver:
        return False
    try:
        urls = list_events(driver, team)
        if not urls:
            log('❌ No games found - not saving')
            return False

        team_data = data.setdefault(team_key, {'games': []})
        team_data['team_name'] = team.get('team_name', team_key)
        team_data['team_url'] = team['team_url']
        games = {g['url']: g for g in team_data.get('games', [])}
        now = datetime.now().isoformat()
        scraped = 0

        for i, url in enumerate(urls, 1):
            time.sleep(random.uniform(*PAUSE))
            log(f'   [{i}/{len(urls)}] {url.split("/")[-3]}')
            try:
                info = scrape_event(driver, url, team.get('currency'))
            except Exception as e:
                log(f'      ⚠️ {e}')
                continue
            if not info:
                continue
            game = games.setdefault(url, {'url': url, 'price_history': []})
            prices = info.pop('latest_prices')
            game.update(info)
            game['team'] = team.get('team_name', team_key)
            game['latest_prices'] = prices
            game['last_scraped'] = now
            if prices:
                game['price_history'].append({'timestamp': now, 'prices': {c: v['min'] for c, v in prices.items()}})
                cheapest = min(v['min'] for v in prices.values())
                log(f'      ✅ {len(prices)} categories, from {cheapest:,.2f} {info["currency"]}')
            else:
                log('      ⚠️ No tickets listed')
            scraped += 1

        if not scraped:
            log('❌ No game page could be read - not saving')
            return False

        team_data['games'] = list(games.values())
        team_data['last_updated'] = now
        tmp = OUTPUT_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, OUTPUT_FILE)  # atomic: a crash never leaves a half-written file
        log(f'✅ Saved {scraped}/{len(urls)} games')
        return True
    except Exception as e:
        log(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(0 if run_team_scraper(sys.argv[1] if len(sys.argv) > 1 else 'arsenal') else 1)
