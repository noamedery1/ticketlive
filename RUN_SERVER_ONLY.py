"""
Railway Server - No Scrapers
Serves the API and the built frontend. Reads team prices from ftn_teams_data.json.
"""
import uvicorn
import json
import os
import re
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import subprocess
import threading

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
TEAMS_DATA_FILE = 'ftn_teams_data.json'
from dotenv import load_dotenv
load_dotenv()

PORT = int(os.environ.get('PORT', '8000'))  # Railway sets PORT

# ==========================================
# FastAPI App
# ==========================================
app = FastAPI(title="TicketLive API")

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'same-origin',
}


@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        response.headers.setdefault(k, v)
    return response

# ---------------------------------------------------------
# JSON Data Utility
# ---------------------------------------------------------
_DATA_CACHE: dict[str, dict[str, object]] = {}
_DATA_CACHE_LOCK = threading.Lock()

def load_data(file_path, default=None):
    """Load JSON, cached by file mtime so updated datasets refresh."""
    if not os.path.exists(file_path):
        print(f'[WARN] File not found: {file_path}')
        return default
    try:
        mtime = os.path.getmtime(file_path)
        with _DATA_CACHE_LOCK:
            cached = _DATA_CACHE.get(file_path)
            if cached and cached['mtime'] == mtime:
                return cached['data']
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        with _DATA_CACHE_LOCK:
            _DATA_CACHE[file_path] = {'mtime': mtime, 'data': data}
        return data
    except Exception as e:
        print(f'[ERROR] Failed to load {file_path}: {e}')
        return default

# ---------------------------------------------------------
# Price helpers
# ---------------------------------------------------------
def _min_price(value):
    """Lowest price in any stored shape: number, {min,max,count}, or {block: price}."""
    if isinstance(value, (int, float)):
        return value if value > 0 else None
    if isinstance(value, dict):
        if 'min' in value:
            return _min_price(value['min'])
        found = [p for p in (_min_price(v) for v in value.values()) if p is not None]
        return min(found) if found else None
    return None


def _summarize_series(series, window_hours=24 * 7):
    """Current price, change vs `window_hours` before the latest reading, and a sparkline.

    The window is measured from the most recent reading (not wall-clock),
    so the change stays meaningful when scraping pauses.
    """
    from datetime import datetime, timedelta
    if not series:
        return None
    current_ts, current = series[-1]
    prev = None
    try:
        cutoff = datetime.fromisoformat(current_ts) - timedelta(hours=window_hours)
        for ts, p in reversed(series):
            if datetime.fromisoformat(ts) <= cutoff:
                prev = p
                break
    except ValueError:
        pass
    if prev is None:
        prev = series[0][1]

    change = current - prev
    pct = (change / prev * 100.0) if prev else 0.0

    prices = [p for _, p in series]
    if len(prices) > 30:
        step = len(prices) / 30.0
        prices = [prices[min(int(i * step), len(prices) - 1)] for i in range(30)]

    return {
        'current': current,
        'prev': prev,
        'change': round(change, 2),
        'pct': round(pct, 2),
        'spark': prices,
        'updated': current_ts,
        'points': len(series),
    }

# ---------------------------------------------------------
# Auto-Build Frontend
# ---------------------------------------------------------
client_dist = 'frontend/dist'

def build_frontend():
    print('[INFO] Building frontend...')
    if not os.path.exists('frontend'):
        print('[ERROR] Frontend folder missing!')
        return False
    npm_cmd = 'npm.cmd' if os.name == 'nt' else 'npm'
    try:
        for args in (['install'], ['run', 'build']):
            result = subprocess.run([npm_cmd, *args], cwd='frontend', capture_output=True, text=True)
            if result.returncode != 0:
                print(f'[ERROR] npm {" ".join(args)} failed: {result.stderr[:500]}')
                return False
        print('[OK] Frontend build complete!')
        return True
    except Exception as e:
        print(f'[ERROR] Build Failed: {e}')
        return False

if not os.path.exists(f'{client_dist}/index.html'):
    print('[WARN] Frontend build not found. Building now...')
    if not build_frontend():
        print('[ERROR] Frontend build failed! Dashboard may not work.')

assets_path = f'{client_dist}/assets'
if os.path.exists(assets_path):
    app.mount('/assets', StaticFiles(directory=assets_path, html=False), name='assets')
    print('[OK] Static assets mounted at /assets')
else:
    print(f'[WARN] Assets directory not found: {assets_path}')

# ---------------------------------------------------------
# Teams API
# ---------------------------------------------------------
def _team_currencies():
    data = load_data('teams_list.json', {}) or {}
    return {t.get('team_key'): t.get('currency', 'USD') for t in data.get('teams', [])}


def get_team_currency(team_key):
    return _team_currencies().get(team_key, 'USD')


def _teams_data():
    data = load_data(TEAMS_DATA_FILE, {})
    return data if isinstance(data, dict) else {}


def parse_game_date(date_str):
    """Parse 'DD/MM/YY' or 'DD/MM/YYYY' (FTN sends both) into a datetime, or None."""
    from datetime import datetime
    for fmt in ('%d/%m/%y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt)
        except (TypeError, ValueError):
            pass
    return None


def _today():
    from datetime import datetime
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def _upcoming_games(team_data):
    """Games from today on. Undated games count while they were scraped in the last 30 days.

    /teams/{key} and /teams/{key}/game/{index} both use this, so indexes line up.
    """
    from datetime import datetime, timedelta
    today = _today()
    out = []
    for game in team_data.get('games', []) or []:
        d = parse_game_date(game.get('date'))
        if d is None:
            try:
                d = datetime.fromisoformat(game.get('last_scraped') or '') + timedelta(days=30)
            except ValueError:
                continue
        if d >= today:
            out.append(game)
    return out


def _game_series(game):
    """Cheapest price per snapshot, oldest first."""
    series = []
    for snap in game.get('price_history', []) or []:
        p = _min_price(snap.get('prices'))
        if snap.get('timestamp') and p is not None:
            series.append((snap['timestamp'], p))
    series.sort()
    return series


@app.get('/teams')
def get_teams():
    currencies = _team_currencies()
    teams = []
    for key, team in _teams_data().items():
        if not isinstance(team, dict):
            continue
        teams.append({
            'key': key,
            'name': team.get('team_name', key.title()),
            'url': team.get('team_url', ''),
            'last_updated': team.get('last_updated'),
            'game_count': len(_upcoming_games(team)),
            'currency': currencies.get(key, 'USD'),
        })
    return teams


@app.get('/teams/overview')
def get_teams_overview():
    """Every upcoming game across all teams: cheapest price, 7-day change, sparkline."""
    currencies = _team_currencies()
    rows = []
    for key, team in _teams_data().items():
        if not isinstance(team, dict):
            continue
        for index, game in enumerate(_upcoming_games(team)):
            d = parse_game_date(game.get('date'))
            rows.append({
                'team_key': key,
                'team_name': team.get('team_name', key.title()),
                'index': index,
                'match_name': game.get('match_name'),
                'opponent': game.get('opponent'),
                'date': d.date().isoformat() if d else None,
                'url': game.get('url'),
                'currency': game.get('currency') or currencies.get(key, 'USD'),
                'summary': _summarize_series(_game_series(game)),
            })
    rows.sort(key=lambda r: (r['date'] is None, r['date'] or ''))
    return rows


@app.get('/teams/{team_key}')
def get_team_games(team_key: str):
    team = _teams_data().get(team_key)
    if not isinstance(team, dict):
        return []
    return [{
        'url': g.get('url'),
        'match_name': g.get('match_name'),
        'opponent': g.get('opponent'),
        'date': g.get('date'),
        'cheapest': _min_price(g.get('latest_prices', {})),
        'last_scraped': g.get('last_scraped'),
    } for g in _upcoming_games(team)]


@app.get('/teams/{team_key}/game/{game_index}')
def get_game_prices(team_key: str, game_index: int):
    empty = {'prices': [], 'game': None, 'currency': 'USD'}
    team = _teams_data().get(team_key)
    if not isinstance(team, dict):
        return empty
    games = _upcoming_games(team)
    if not 0 <= game_index < len(games):
        return empty
    game = games[game_index]
    return {
        'game': {
            'match_name': game.get('match_name'),
            'url': game.get('url'),
            'opponent': game.get('opponent'),
            'date': game.get('date'),
            'last_scraped': game.get('last_scraped'),
        },
        'prices': game.get('price_history', []),
        'latest_prices': game.get('latest_prices', {}),
        'summary': _summarize_series(_game_series(game)),
        'currency': game.get('currency') or get_team_currency(team_key),
    }

@app.get('/health')
def health_check():
    """Lightweight health check for Railway"""
    return {'status': 'ok', 'message': 'Server is running'}

# Catch-all route for React SPA - MUST be last (after API routes)
@app.get('/{full_path:path}')
async def serve_react_app(full_path: str):
    if full_path.startswith(('api/', 'teams', 'health', 'assets')):
        raise HTTPException(status_code=404, detail='Not found')
    # Serve real files from dist (favicon etc.), index.html for everything else.
    candidate = os.path.realpath(os.path.join(client_dist, full_path))
    if full_path and candidate.startswith(os.path.realpath(client_dist) + os.sep) and os.path.isfile(candidate):
        return FileResponse(candidate)
    index_path = f'{client_dist}/index.html'
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type='text/html', headers={'Cache-Control': 'no-cache'})
    return {'message': 'Build Not Found.'}

if __name__ == '__main__':
    print(f'[START] TicketLive server on 0.0.0.0:{PORT}', flush=True)
    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='info')
