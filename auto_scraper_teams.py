"""
Auto Scraper for FTN Teams

One cycle: git pull -> scrape every team in teams_list.json -> one commit -> push.
Railway redeploys the site from the push.

    python auto_scraper_teams.py          # loop every SCRAPE_INTERVAL_HOURS
    python auto_scraper_teams.py --once   # one cycle, exit code 0/1 (for Task Scheduler)
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
SCRAPE_INTERVAL_HOURS = 3.0
TEAM_TIMEOUT_MINUTES = 45   # a hung Chrome gets killed after this
OUTPUT_FILE = 'ftn_teams_data.json'
TEAMS_LIST_FILE = 'teams_list.json'
PYTHON_CMD = sys.executable or ('py' if shutil.which('py') else 'python')


def log(msg):
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}', flush=True)


def git(*args):
    """Run git, return (ok, output)."""
    r = subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def git_sync():
    """Rebase onto the remote. On any problem, abort and report - never guess at a merge."""
    ok, out = git('pull', '--rebase', '--autostash')
    if not ok:
        git('rebase', '--abort')
        log(f'[ERROR] git pull failed, fix the repo by hand:\n{out}')
    return ok


def load_teams():
    with open(TEAMS_LIST_FILE, 'r', encoding='utf-8') as f:
        teams = json.load(f).get('teams', [])
    return [{'key': t['team_key'], 'name': t.get('team_name', t['team_key'])} for t in teams if t.get('team_key')]


def kill_tree(pid):
    """Kill the scraper and the Chrome/chromedriver processes it started."""
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/f', '/t', '/pid', str(pid)], capture_output=True)
    else:
        try:
            os.killpg(pid, 9)
        except Exception:
            pass


def run_team_scraper(team_key):
    log(f'[ACTION] Scraping {team_key}...')
    kwargs = {} if sys.platform == 'win32' else {'start_new_session': True}
    process = subprocess.Popen(
        [PYTHON_CMD, 'scraper_ftn_teams.py', team_key],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace', bufsize=1, **kwargs,
    )
    timed_out = threading.Event()

    def on_timeout():
        timed_out.set()
        kill_tree(process.pid)

    watchdog = threading.Timer(TEAM_TIMEOUT_MINUTES * 60, on_timeout)
    watchdog.start()
    try:
        for line in process.stdout:
            print(line.rstrip(), flush=True)
        process.wait()
    finally:
        watchdog.cancel()

    if timed_out.is_set():
        log(f'[ERROR] {team_key}: killed after {TEAM_TIMEOUT_MINUTES} min')
        return False
    if process.returncode != 0:
        log(f'[ERROR] {team_key}: scraper exited with code {process.returncode}')
        return False
    log(f'[OK] {team_key} done')
    return True


def commit_and_push(ok_teams, failed_teams):
    ok, out = git('add', OUTPUT_FILE)
    if not ok:
        log(f'[ERROR] git add failed: {out}')
        return False
    if git('diff', '--cached', '--quiet')[0]:
        log('[INFO] No price changes to commit')
        return True
    msg = f'Auto-update team prices - {datetime.now():%Y-%m-%d %H:%M}'
    if failed_teams:
        msg += f' (failed: {", ".join(failed_teams)})'
    ok, out = git('commit', '-m', msg)
    if not ok:
        log(f'[ERROR] git commit failed: {out}')
        return False
    for attempt in (1, 2):
        if not git_sync():
            return False
        ok, out = git('push')
        if ok:
            log(f'[OK] Pushed ({", ".join(ok_teams)})')
            return True
        log(f'[WARN] push attempt {attempt} failed: {out}')
    log('[ERROR] push failed, the commit stays local and goes out next cycle')
    return False


def run_cycle():
    log('=' * 50)
    log('[START] Teams scraper cycle')
    if not git_sync():
        return False
    try:
        teams = load_teams()
    except Exception as e:
        log(f'[ERROR] Cannot read {TEAMS_LIST_FILE}: {e}')
        return False

    ok_teams, failed_teams = [], []
    for i, team in enumerate(teams, 1):
        log(f'[{i}/{len(teams)}] {team["name"]}')
        (ok_teams if run_team_scraper(team['key']) else failed_teams).append(team['key'])
        time.sleep(5)  # be nice to the site

    pushed = commit_and_push(ok_teams, failed_teams) if ok_teams else False
    log(f'[SUMMARY] ok: {ok_teams or "-"}  failed: {failed_teams or "-"}  pushed: {pushed}')
    return pushed and not failed_teams


def main():
    if '--once' in sys.argv:
        sys.exit(0 if run_cycle() else 1)
    while True:
        run_cycle()
        log(f'[WAIT] Next run in {SCRAPE_INTERVAL_HOURS} hours')
        time.sleep(SCRAPE_INTERVAL_HOURS * 3600)


if __name__ == '__main__':
    main()
