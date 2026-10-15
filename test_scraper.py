"""Offline check of scraper_ftn_teams.run_team_scraper with a fake browser: python test_scraper.py"""
import json
import os
import sys
import tempfile
import types

# The real browser libraries are not needed for this test.
sys.modules.setdefault('undetected_chromedriver', types.ModuleType('undetected_chromedriver'))
by = types.ModuleType('by')
by.By = None
for name in ('selenium', 'selenium.webdriver', 'selenium.webdriver.common'):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.modules.setdefault('selenium.webdriver.common.by', by)

import scraper_ftn_teams as s  # noqa: E402

BASE = s.BASE
EVENTS = {
    'a': {'url': f'{BASE}/premier-league/arsenal-vs-everton-x-football-tickets/event/1', 'match_name': 'Arsenal vs Everton',
          'date': '24/10/2026', 'from_price': 100.0},
    'b': {'url': f'{BASE}/premier-league/arsenal-vs-hull-x-football-tickets/event/2', 'match_name': 'Arsenal vs Hull',
          'date': '07/11/2026', 'from_price': 200.0},
}
page_loads = []
script = []  # what scrape_event returns, in order


def fake_scrape_event(driver, url, currency):
    page_loads.append(url)
    result = script.pop(0)
    if result == s.BLOCKED:
        return s.BLOCKED
    return {'match_name': 'x', 'opponent': 'y', 'date': '24/10/2026', 'start': '2026-10-24T15:00:00+01:00',
            'competition': 'PL', 'currency': 'GBP', 'latest_prices': {'Lower': {'min': result, 'count': 3}}}


class Driver:
    def quit(self):
        pass


s.get_driver = lambda: Driver()
s.scrape_event = fake_scrape_event
s.time.sleep = lambda _: None  # no real waiting
os.chdir(tempfile.mkdtemp())
json.dump({'teams': [{'team_key': 'arsenal', 'team_name': 'Arsenal', 'team_url': f'{BASE}/arsenal-football-tickets',
                      'currency': 'GBP'},
                     {'team_key': 'cl', 'team_name': 'CL', 'team_url': f'{BASE}/cl-football-tickets',
                      'currency': 'GBP', 'all_games': True}]}, open('teams_list.json', 'w'))
data = lambda: json.load(open('ftn_teams_data.json', encoding='utf-8'))  # noqa: E731

# 1) New games: first page blocked once, recovers after the back-off wait.
s.list_events = lambda d, t: [dict(EVENTS['a']), dict(EVENTS['b'])]
script[:] = [s.BLOCKED, 100.0, 200.0]
assert s.run_team_scraper('arsenal')
games = {g['url']: g for g in data()['arsenal']['games']}
assert len(page_loads) == 3
assert games[EVENTS['a']['url']]['latest_prices']['Lower']['min'] == 100.0

# 2) Same prices again, categories still fresh: no game pages at all.
page_loads.clear()
assert s.run_team_scraper('arsenal')
assert page_loads == []
assert data()['arsenal']['games'][0]['price_history'][-1]['prices'] == {s.FALLBACK_CATEGORY: 100.0}

# 3) One price changed: only that game's page is loaded.
s.list_events = lambda d, t: [dict(EVENTS['a'], from_price=90.0), dict(EVENTS['b'])]
script[:] = [90.0]
assert s.run_team_scraper('arsenal')
assert page_loads == [EVENTS['a']['url']]

# 4) Blocked through every retry: falls back to cheapest prices, still saves.
page_loads.clear()
s.list_events = lambda d, t: [dict(EVENTS['a'], from_price=80.0), dict(EVENTS['b'], from_price=150.0)]
script[:] = [s.BLOCKED] * (1 + len(s.BACKOFF_MINUTES))
assert s.run_team_scraper('arsenal')
assert len(page_loads) == 1 + len(s.BACKOFF_MINUTES)  # gave up after the retries, no more loads
last = {g['url']: g['price_history'][-1]['prices'] for g in data()['arsenal']['games']}
assert last[EVENTS['b']['url']] == {s.FALLBACK_CATEGORY: 150.0}

# 4b) Giving up started a cooldown: the next team loads no game pages and does not wait.
assert s.cooling_down()
page_loads.clear()
s.list_events = lambda d, t: [dict(EVENTS['a'], from_price=70.0)]
assert s.run_team_scraper('arsenal')
assert page_loads == []
os.remove(s.COOLDOWN_FILE)

# 5) Another team lists a game scraped minutes ago: reused, not loaded again.
page_loads.clear()
s.list_events = lambda d, t: [dict(EVENTS['b'], from_price=999.0)]  # "price changed" -> wants details
assert s.run_team_scraper('cl')
assert page_loads == []
assert data()['cl']['games'][0]['latest_prices']['Lower']['min'] == 200.0

print('ok')
