"""Offline check of auto_scraper_teams.py (no git, no Chrome): python test_runner.py"""
import json
import os
import shutil
import sys
import tempfile
import time

import auto_scraper_teams as r

r.cleanup_chrome = lambda: None  # never touch real processes from a test
os.chdir(tempfile.mkdtemp())

# A fake scraper that prints like the real one.
with open('scraper_ftn_teams.py', 'w', encoding='utf-8') as f:
    f.write('''import sys, time
sys.stdout.reconfigure(encoding='utf-8')  # as the real scraper does on Windows
if sys.argv[1] == 'hang':
    time.sleep(600)
print("      \\u2705 12 categories, from 157.98 GBP", flush=True)
print("      \\u21aa cheapest only: 160.48", flush=True)
print("      \\u21aa cheapest only: 99.00", flush=True)
sys.exit(1 if sys.argv[1] == 'bad' else 0)
''')

assert r.run_team_scraper('good') is True
assert r.COUNTS['good'] == {'full': 1, 'cheapest_only': 2}
assert r.run_team_scraper('bad') is False

# Watchdog kills a hung scraper.
r.TEAM_TIMEOUT_MINUTES = 0.05  # 3 s
t = time.time()
assert r.run_team_scraper('hang') is False
assert time.time() - t < 30

# Status file the site reads.
with open(r.COOLDOWN_FILE, 'w') as f:
    f.write('2999-01-01T00:00:00')
r.write_status('2026-10-15T10:00:00', ['good'], ['bad', 'hang'])
st = json.load(open(r.STATUS_FILE, encoding='utf-8'))
assert st['ok'] == ['good'] and st['failed'] == ['bad', 'hang']
assert st['games_full'] == 1 and st['games_cheapest_only'] == 2
assert st['bot_check_until'] == '2999-01-01T00:00:00'
os.remove(r.COOLDOWN_FILE)
r.write_status('2026-10-15T10:00:00', ['good'], [])
assert json.load(open(r.STATUS_FILE, encoding='utf-8'))['bot_check_until'] is None

os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])) or '.')
print('ok')
