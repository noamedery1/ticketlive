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
PAUSE = (6, 12)     # seconds between page loads, be nice to the site
DRIVER_TIMEOUT = 120  # seconds for Chrome to start
BLOCKED = 'blocked'  # scrape_event result when the site shows its bot check
FALLBACK_CATEGORY = 'Cheapest (team page)'


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
    result = {}

    def start():
        try:
            result['driver'] = uc.Chrome(
                options=options,
                version_main=int(os.environ['CHROME_MAJOR']) if os.environ.get('CHROME_MAJOR') else None,
                browser_executable_path=browser_path,
                driver_executable_path=driver_path,
                use_subprocess=False,
            )
        except Exception as e:
            result['error'] = e

    # Chrome that never comes up leaves chromedriver waiting forever: give up after DRIVER_TIMEOUT.
    import threading
    t = threading.Thread(target=start, daemon=True)
    t.start()
    t.join(DRIVER_TIMEOUT)
    if 'driver' in result:
        result['driver'].set_page_load_timeout(90)
        return result['driver']
    log(f'   ❌ Chrome did not start: {result.get("error") or f"no response after {DRIVER_TIMEOUT} s"}')
    return None


def with_currency(url, currency):
    return f'{url}{"&" if "?" in url else "?"}currency={currency}' if currency else url


def is_challenge(html):
    """Cloudflare's "verify you are human" page (any language)."""
    return 'challenges.cloudflare.com' in html or 'cf-turnstile' in html or '<title>Just a moment' in html


def wait_for(driver, predicate):
    """Poll page_source until predicate(html) is truthy. Returns html, BLOCKED or None."""
    end = time.time() + PAGE_TIMEOUT
    html = ''
    while time.time() < end:
        html = driver.page_source
        if predicate(html):
            return html
        time.sleep(1)
    return BLOCKED if is_challenge(html) else None


MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def parse_team_page(html, slug, all_games):
    """Upcoming games on a team page: [{url, match_name, date, from_price}].

    Each card reads like "Oct | 24 | Sat | 15:00 | vs | Arsenal vs Everton | Premier League | From £118.99".
    """
    games, seen = [], set()
    for card in re.split(r'class="UpcomingMatchesSection-module__\w+__matchItem(?!Footer)', html)[1:]:
        card = card[:6000]
        m = re.search(r'href="(/[a-z0-9-]+/([a-z0-9-]+)/event/\d+)', card)
        if not m or m.group(1) in seen:
            continue
        if not all_games and not m.group(2).startswith(f'{slug}-vs-'):
            continue
        seen.add(m.group(1))
        text = re.sub(r'\s*(<[^>]+>\s*)+', ' | ', card)
        name = re.search(r'\| ([^|<>]+? vs [^|<>]+?) \|', text)
        day = re.search(r'\| (\w{3}) \| (\d{1,2}) \|', text)
        price = re.search(r'From\s*\D{0,3}?([\d,]+(?:\.\d+)?)', text)
        date = None
        if day and day.group(1).lower() in MONTHS:
            today = datetime.now()
            month, d = MONTHS[day.group(1).lower()], int(day.group(2))
            year = today.year + (1 if month < today.month - 1 else 0)  # the list has no year
            date = f'{d:02d}/{month:02d}/{year}'
        games.append({
            'url': BASE + m.group(1),
            'match_name': name.group(1).strip() if name else m.group(2),
            'date': date,
            'from_price': float(price.group(1).replace(',', '')) if price else None,
        })
    return games


def fetch_plain(url):
    """Team pages are not behind the bot check, so a plain request works when Chrome is challenged."""
    import requests
    try:
        r = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'})
        return r.text if r.ok else None
    except Exception as e:
        log(f'   ⚠️ {e}')
        return None


def list_events(driver, team):
    """Upcoming games from the team page (home games only unless all_games)."""
    team_url = team['team_url'].split('/filter/')[0]
    slug = team_url.rstrip('/').rsplit('/', 1)[-1].replace('-football-tickets', '')
    driver.get(with_currency(team_url, team.get('currency')))
    html = wait_for(driver, lambda h: '/event/' in h)
    if html == BLOCKED:
        html = fetch_plain(with_currency(team_url, team.get('currency')))
    if html in (None, BLOCKED) or '/event/' not in html:
        log(f'   ❌ No games on {team_url} (bot check page or layout changed)')
        return []
    games = parse_team_page(html, slug, team.get('all_games'))
    log(f'   📋 {len(games)} upcoming {"games" if team.get("all_games") else "home games"}')
    return games


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
    if html == BLOCKED:
        return BLOCKED
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


DETAIL_MAX_AGE_HOURS = 24   # categories are refreshed at least this often (fewer loads = fewer bot checks)
HUMAN_WAIT_MINUTES = 20     # with email alerts on: keep the check open this long for a person to click
ALERT_FILE = 'alert_email.json'  # gitignored, see SCRAPER_SETUP.md
BACKOFF_MINUTES = (4, 8)     # the bot check cleared after ~4 min in practice
COOLDOWN_MINUTES = 60        # after giving up, no game pages (any team) for this long
COOLDOWN_FILE = 'blocked_until.txt'
DETAIL_PRIORITY = ['new game', 'price changed', 'refresh', None]
SHARED_FIELDS = ('match_name', 'opponent', 'date', 'start', 'competition', 'currency', 'latest_prices', 'last_detail')


def hours_since(ts):
    try:
        return (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
    except (TypeError, ValueError):
        return float('inf')


def detail_reason(game, ev):
    """Why this game's own page should be loaded this run, or None to use the team page price."""
    if not game or not game.get('last_detail'):
        return 'new game'
    history = game.get('price_history') or []
    last = min(history[-1]['prices'].values()) if history and history[-1].get('prices') else None
    if ev['from_price'] is not None and last is not None and abs(ev['from_price'] - last) > 0.005:
        return 'price changed'
    if hours_since(game['last_detail']) >= DETAIL_MAX_AGE_HOURS:
        return 'refresh'
    return None


def recent_detail_elsewhere(data, team_key, url, max_age_hours=2):
    """Same game already scraped in full for another team this cycle (e.g. a CL home game)."""
    for key, team in data.items():
        if key == team_key or not isinstance(team, dict):
            continue
        for g in team.get('games', []):
            if g.get('url') == url and g.get('latest_prices') and hours_since(g.get('last_detail')) < max_age_hours:
                return g
    return None


def send_alert(subject, body):
    """Email via SMTP settings in ALERT_FILE. Returns False when not set up or sending failed."""
    try:
        with open(ALERT_FILE, encoding='utf-8-sig') as f:  # -sig: Notepad on Windows 7 adds a BOM
            cfg = json.load(f)
    except OSError:
        return False  # not set up: alerts are optional
    except ValueError as e:
        log(f'      ⚠️ {ALERT_FILE} is not valid JSON (line {getattr(e, "lineno", "?")}) - no email sent')
        return False
    if cfg.get('ntfy_topic'):
        # No SMTP (blocked on some networks): ntfy.sh over HTTPS, it forwards the message by email.
        import requests
        try:
            r = requests.post(f'https://ntfy.sh/{cfg["ntfy_topic"]}', data=body.encode('utf-8'),
                              headers={'Title': subject, 'Email': cfg['to']}, timeout=30)
            if r.ok:
                return True
            log(f'      ⚠️ Alert failed: ntfy said {r.status_code} {r.text[:200]}')
        except requests.RequestException as e:
            log(f'      ⚠️ Alert failed: {type(e).__name__}')
        return False
    import smtplib
    import socket
    from email.message import EmailMessage
    msg = EmailMessage()
    msg['Subject'], msg['From'], msg['To'] = subject, cfg['user'], cfg['to']
    msg.set_content(body)
    host = cfg.get('host', 'smtp.gmail.com')

    def deliver(s):
        s.login(cfg['user'], cfg['password'])
        s.send_message(msg)

    try:
        try:
            with smtplib.SMTP(host, cfg.get('port', 587), timeout=30) as s:
                s.starttls()
                deliver(s)
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, ConnectionError, socket.timeout) as e:
            # Some networks/antivirus cut port 587: try implicit TLS on 465.
            log(f'      ⚠️ port {cfg.get("port", 587)}: {type(e).__name__} {e} - trying 465')
            with smtplib.SMTP_SSL(host, 465, timeout=30) as s:
                deliver(s)
        return True
    except smtplib.SMTPAuthenticationError:
        log('      ⚠️ Alert email failed: wrong user / app password')  # never log e: may echo the login
    except smtplib.SMTPResponseException as e:
        log(f'      ⚠️ Alert email failed: server said {e.smtp_code}')
    except Exception as e:
        log(f'      ⚠️ Alert email failed: {type(e).__name__} {e}')  # connection errors: no secrets in them
    return False


HUMAN_ASKED = []  # one email per team run, so a check that keeps coming back doesn't spam
ALERT_LOG = 'alerts_sent.txt'  # gitignored: one line per email sent (ISO time)
ALERT_HOURS = (9, 18)          # emails only from 09:00 to 18:00...
ALERT_NO_DAYS = (4, 5)         # ...not on Friday / Saturday (Monday = 0)
ALERTS_PER_DAY = 2


def alert_allowed(now=None):
    now = now or datetime.now()
    if now.weekday() in ALERT_NO_DAYS or not ALERT_HOURS[0] <= now.hour < ALERT_HOURS[1]:
        return False
    try:
        with open(ALERT_LOG, encoding='utf-8') as f:
            today = sum(1 for line in f if line.startswith(now.date().isoformat()))
    except OSError:
        today = 0
    return today < ALERTS_PER_DAY


def wait_for_human(driver, url):
    """Email, then keep the check open until someone clicks it (remote desktop) or time runs out."""
    if HUMAN_ASKED or not alert_allowed() or not send_alert(
            'TicketLive: bot check is waiting for a click',
            f'Open the server (remote desktop) and click the check in the Chrome window.\n'
            f'Waiting {HUMAN_WAIT_MINUTES} min, then it continues with cheapest prices only.\n\n{url}'):
        return False
    HUMAN_ASKED.append(url)
    with open(ALERT_LOG, 'a', encoding='utf-8') as f:
        f.write(datetime.now().isoformat() + '\n')
    log(f'      📧 Email sent - waiting up to {HUMAN_WAIT_MINUTES} min for someone to click the check')
    end = time.time() + HUMAN_WAIT_MINUTES * 60
    while time.time() < end:
        time.sleep(15)
        if not is_challenge(driver.page_source):
            log('      👍 Check cleared')
            return True
    return False


def scrape_with_backoff(driver, url, currency):
    """Game page; on the bot check ask a person (email) or wait it out, and retry. Returns info, None or BLOCKED."""
    time.sleep(random.uniform(*PAUSE))
    try:
        info = scrape_event(driver, url, currency)
    except Exception as e:
        log(f'      ⚠️ {e}')
        return None
    if info != BLOCKED:
        return info
    waits = BACKOFF_MINUTES
    if wait_for_human(driver, url):
        waits = (0,)  # cleared by hand: retry right away, once
    for wait in waits:
        if wait:
            log(f'      ⏳ Bot check page - waiting {wait} min, then retrying')
            time.sleep(wait * 60)
        try:
            info = scrape_event(driver, url, currency)
        except Exception as e:
            log(f'      ⚠️ {e}')
            return None
        if info != BLOCKED:
            return info
    return BLOCKED


def cooling_down():
    """True while a recent run gave up on the bot check: skip game pages, don't knock again."""
    try:
        with open(COOLDOWN_FILE, encoding='utf-8') as f:
            return datetime.now() < datetime.fromisoformat(f.read().strip())
    except (OSError, ValueError):
        return False


def start_cooldown():
    from datetime import timedelta
    with open(COOLDOWN_FILE, 'w', encoding='utf-8') as f:
        f.write((datetime.now() + timedelta(minutes=COOLDOWN_MINUTES)).isoformat())


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
        events = list_events(driver, team)
        if not events:
            log('❌ No games found - not saving')
            return False

        team_data = data.setdefault(team_key, {'games': []})
        team_data['team_name'] = team.get('team_name', team_key)
        team_data['team_url'] = team['team_url']
        games = {g['url']: g for g in team_data.get('games', [])}
        now = datetime.now().isoformat()
        scraped = 0

        # Load game pages only where they add something, most valuable first.
        for ev in events:
            ev['why'] = detail_reason(games.get(ev['url']), ev)
        events.sort(key=lambda ev: DETAIL_PRIORITY.index(ev['why']))
        gave_up = cooling_down()
        if gave_up:
            log(f'   ⏸ Bot check seen recently - cheapest prices only until {open(COOLDOWN_FILE).read().strip()[11:16]}')
        for i, ev in enumerate(events, 1):
            url = ev['url']
            log(f'   [{i}/{len(events)}] {url.split("/")[-3]}' + (f' ({ev["why"]})' if ev['why'] else ''))
            game = games.setdefault(url, {'url': url, 'price_history': []})
            info = None
            if ev['why']:
                shared = recent_detail_elsewhere(data, team_key, url)
                if shared:
                    info = {k: shared.get(k) for k in SHARED_FIELDS}
                    log('      ♻ same game scraped minutes ago for another team')
                elif not gave_up:
                    info = scrape_with_backoff(driver, url, team.get('currency'))
                    if info == BLOCKED:
                        log(f'      🛑 Still blocked - cheapest prices only for the next {COOLDOWN_MINUTES} min')
                        gave_up, info = True, None
                        start_cooldown()
            if info:
                prices = info.pop('latest_prices')
                game.update(info)
                game['latest_prices'] = prices
                game['last_detail'] = info.get('last_detail') or now
                snapshot = {c: v['min'] for c, v in prices.items()}
                if snapshot:
                    log(f'      ✅ {len(prices)} categories, from {min(snapshot.values()):,.2f} {game.get("currency")}')
                else:
                    log('      ⚠️ No tickets listed')
            elif ev['from_price']:
                # Only the cheapest price, from the team page.
                for k in ('match_name', 'date'):
                    game.setdefault(k, ev[k])
                game.setdefault('currency', team.get('currency'))
                snapshot = {FALLBACK_CATEGORY: ev['from_price']}
                log(f'      ↪ cheapest only: {ev["from_price"]:,.2f}')
            else:
                if not game.get('match_name'):
                    del games[url]
                continue
            game['team'] = team.get('team_name', team_key)
            game['last_scraped'] = now
            if snapshot:
                game['price_history'].append({'timestamp': now, 'prices': snapshot})
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
        log(f'✅ Saved {scraped}/{len(events)} games' + (' (cheapest only after the bot check)' if gave_up else ''))
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
