"""
Railway Server - No Scrapers
Only serves the API and frontend, reads from prices.json and prices_ftn.json
"""
import uvicorn
import json
import os
import re
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import subprocess
from starlette.middleware.base import BaseHTTPMiddleware

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
DATA_FILE_VIAGOGO = 'prices.json'
DATA_FILE_FTN = 'prices_ftn.json'
GAMES_FILE = 'all_games_to_scrape.json'
TEAMS_DATA_FILE = 'ftn_teams_data.json'
# Railway sets PORT dynamically - use whatever Railway provides
# Railway will set PORT environment variable automatically
PORT = int(os.environ.get('PORT', '8000'))  # Railway always sets PORT, but keep default for local dev

# ==========================================
# FastAPI App
# ==========================================
from contextlib import asynccontextmanager

# Lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Startup - Railway handles port/IP configuration
    print('[STARTUP] FastAPI application started', flush=True)
    try:
        yield
    finally:
        # Shutdown (if needed)
        print('[SHUTDOWN] FastAPI application shutting down', flush=True)

app = FastAPI(title="Viagogo Monitor API", lifespan=lifespan)

# Request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f'[REQUEST] {request.method} {request.url.path}')
        response = await call_next(request)
        print(f'[RESPONSE] {request.method} {request.url.path} -> {response.status_code}')
        return response

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ---------------------------------------------------------
# JSON Data Utility
# ---------------------------------------------------------
def load_data(file_path):
    if not os.path.exists(file_path): 
        print(f'[WARN] File not found: {file_path}')
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f: 
            data = json.load(f)
            print(f'[INFO] Loaded {len(data)} records from {file_path}')
            return data
    except Exception as e:
        print(f'[ERROR] Failed to load {file_path}: {e}')
        return []

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get('/matches')
def get_matches():
    try:
        print('[API] /matches endpoint called')
        if not os.path.exists(GAMES_FILE): 
            print(f'[WARN] {GAMES_FILE} not found')
            return []
        with open(GAMES_FILE, 'r', encoding='utf-8') as f: 
            games = json.load(f)
        
        def get_match_number(match_name):
            m = re.search(r'Match (\d+)', match_name)
            return int(m.group(1)) if m else 9999

        matches_list = [{'match_name': g['match_name'], 'match_url': g['url']} for g in games]
        matches_list.sort(key=lambda x: get_match_number(x['match_name']))
        print(f'[API] Returning {len(matches_list)} matches')
        return matches_list
    except Exception as e:
        print(f'[ERROR] API Error: {e}')
        import traceback
        traceback.print_exc()
        return []

@app.get('/history')
def get_history(match_url: str):
    try:
        print(f"[API] History Request for URL: {match_url[:50]}...")
        
        # 1. LOAD VIAGOGO DATA
        viagogo_data = load_data(DATA_FILE_VIAGOGO)
        v_match_data = []
        
        # Extract ID from requested URL
        # e.g. .../World-Cup-Tickets/E-153033506?Currency=... -> E-153033506
        req_id = None
        match = re.search(r'/(E-\d+)', match_url)
        if match: 
            req_id = match.group(1)
        
        print(f"[API] Looking for Viagogo ID: {req_id}")

        for row in viagogo_data:
            # Extract ID from stored URL (remove query params for comparison)
            stored_url = row.get('match_url', '').split('?')[0].split('&')[0]
            stored_id = None
            m_stored = re.search(r'/(E-\d+)', stored_url)
            if m_stored: 
                stored_id = m_stored.group(1)
            
            # Clean request URL too
            clean_req_url = match_url.split('?')[0].split('&')[0]
            
            # Match by ID if possible (most reliable)
            if req_id and stored_id:
                if req_id == stored_id:
                    v_match_data.append(row)
                    continue
            
            # Match by URL (exact or partial)
            if clean_req_url in stored_url or stored_url in clean_req_url:
                v_match_data.append(row)
                continue
            
            # Match by match number in match_name
            match_name = row.get('match_name', '')
            match_num = re.search(r'Match (\d+)', match_name)
            if match_num:
                url_match_num = re.search(r'Match (\d+)', match_url, re.IGNORECASE)
                if url_match_num and match_num.group(1) == url_match_num.group(1):
                    v_match_data.append(row)
                    continue
                 
        print(f"[API] Found {len(v_match_data)} Viagogo records.")
        v_match_data.sort(key=lambda x: x.get('timestamp', ''))

        # 2. IDENTIFY MATCH FOR FTN
        ftn_data = load_data(DATA_FILE_FTN)
        f_match_data = []
        
        match_number = None
        m = re.search(r'Match (\d+)', match_url, re.IGNORECASE)
        
        # New fallback: Look in GAMES_FILE if URL does not have match number
        if not m and os.path.exists(GAMES_FILE):
             try:
                 with open(GAMES_FILE, 'r', encoding='utf-8') as f: 
                     games = json.load(f)
                 # Find game with this URL (ignoring query params)
                 clean_input_url = match_url.split('?')[0]
                 
                 for g in games:
                     if g['url'].split('?')[0] == clean_input_url:
                         m = re.search(r'Match (\d+)', g['match_name'], re.IGNORECASE)
                         break
             except Exception as e:
                 print(f'[ERROR] Error loading games file: {e}')

        if not m and v_match_data:
             m = re.search(r'Match (\d+)', v_match_data[0].get('match_name', ''), re.IGNORECASE)
        
        if m:
            match_number = m.group(1)
            # Find FTN records for this Match #
            f_match_data = [d for d in ftn_data if f'Match {match_number}' in d.get('match_name', '')]
            f_match_data.sort(key=lambda x: x.get('timestamp', ''))
            print(f"[API] Found {len(f_match_data)} FTN records for Match {match_number}")
        
        def process_source_data(data_list):
            if not data_list: 
                return {}, []
            categories = sorted(list(set(d.get('category', '') for d in data_list if d.get('category'))))
            result_data = {}
            for cat in categories:
                cat_rows = [d for d in data_list if d.get('category') == cat]
                result_data[cat] = [{'timestamp': d.get('timestamp', ''), 'price': d.get('price', 0)} for d in cat_rows]
            return result_data, categories

        v_processed, v_cats = process_source_data(v_match_data)
        f_processed, f_cats = process_source_data(f_match_data)

        result = {
            'viagogo': {'categories': v_cats, 'data': v_processed},
            'ftn': {'categories': f_cats, 'data': f_processed},
            'currency': 'USD'
        }
        
        print(f"[API] Returning: Viagogo categories: {v_cats}, FTN categories: {f_cats}")
        return result

    except Exception as e:
        print(f'[ERROR] History Error: {e}')
        import traceback
        traceback.print_exc()
        return {'viagogo': {'categories': [], 'data': {}}, 'ftn': {'categories': [], 'data': {}}}

# ---------------------------------------------------------
# Auto-Build Frontend
# ---------------------------------------------------------
client_dist = 'frontend/dist'

def build_frontend():
    print('[INFO] Building frontend...')
    try:
        if not os.path.exists('frontend'):
            print('[ERROR] Frontend folder missing!')
            return False
            
        npm_cmd = 'npm.cmd' if os.name == 'nt' else 'npm'
        
        # Install dependencies
        print('[INFO] Installing npm dependencies...')
        result = subprocess.run(
            [npm_cmd, 'install'], 
            cwd='frontend', 
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f'[WARN] npm install had issues: {result.stderr[:200]}')
        
        # Build
        print('[INFO] Building frontend...')
        result = subprocess.run(
            [npm_cmd, 'run', 'build'], 
            cwd='frontend', 
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print('[OK] Frontend build complete!')
            return True
        else:
            print(f'[ERROR] Build failed: {result.stderr[:500]}')
            return False
    except Exception as e:
        print(f'[ERROR] Build Failed: {e}')
        import traceback
        traceback.print_exc()
        return False

# Build frontend if needed
if not os.path.exists(f'{client_dist}/index.html'):
    print('[WARN] Frontend build not found. Building now...')
    if not build_frontend():
        print('[ERROR] Frontend build failed! Dashboard may not work.')
else:
    print('[OK] Frontend build found.')
    # Verify it's a valid build
    if not os.path.exists(f'{client_dist}/index.html'):
        print('[ERROR] Frontend dist/index.html missing!')
    else:
        print(f'[OK] Frontend index.html found at {client_dist}/index.html')

# Mount static files - MUST be done before catch-all route
if os.path.exists(client_dist):
    # Mount assets directory (JS, CSS files)
    assets_path = f'{client_dist}/assets'
    if os.path.exists(assets_path):
        try:
            app.mount('/assets', StaticFiles(directory=assets_path, html=False), name='assets')
            # List files in assets for debugging
            asset_files = os.listdir(assets_path)
            print(f'[OK] Static assets mounted at /assets ({len(asset_files)} files)')
            for f in asset_files[:5]:  # Show first 5 files
                print(f'      - {f}')
        except Exception as e:
            print(f'[WARN] Failed to mount assets: {e}')
            import traceback
            traceback.print_exc()
    else:
        print(f'[WARN] Assets directory not found: {assets_path}')
        print(f'[INFO] Contents of {client_dist}: {os.listdir(client_dist) if os.path.exists(client_dist) else "N/A"}')
    
    print('[OK] Static file routes configured')
else:
    print(f'[ERROR] Frontend dist directory not found: {client_dist}')

# Serve vite.svg from root (referenced in index.html)
@app.get('/teams')
def get_teams():
    """Get list of available teams"""
    try:
        if not os.path.exists(TEAMS_DATA_FILE):
            return []
        with open(TEAMS_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        teams = []
        for team_key, team_data in data.items():
            teams.append({
                'key': team_key,
                'name': team_data.get('team_name', team_key.title()),
                'url': team_data.get('team_url', ''),
                'last_updated': team_data.get('last_updated'),
                'game_count': len(team_data.get('games', []))
            })
        return teams
    except Exception as e:
        print(f'[ERROR] /teams error: {e}')
        return []

@app.get('/teams/{team_key}')
def get_team_games(team_key: str):
    """Get all games for a specific team"""
    try:
        if not os.path.exists(TEAMS_DATA_FILE):
            return []
        with open(TEAMS_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if team_key not in data:
            return []
        team_data = data[team_key]
        games = []
        for game in team_data.get('games', []):
            games.append({
                'url': game.get('url'),
                'match_name': game.get('match_name'),
                'opponent': game.get('opponent'),
                'date': game.get('date'),
                'latest_prices': game.get('latest_prices', {}),
                'last_scraped': game.get('last_scraped'),
                'price_history_count': len(game.get('price_history', []))
            })
        return games
    except Exception as e:
        print(f'[ERROR] /teams/{team_key} error: {e}')
        return []

@app.get('/teams/{team_key}/game/{game_index}')
def get_game_prices(team_key: str, game_index: int):
    """Get price history for a specific game"""
    try:
        if not os.path.exists(TEAMS_DATA_FILE):
            return {'prices': [], 'game': None}
        with open(TEAMS_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if team_key not in data:
            return {'prices': [], 'game': None}
        games = data[team_key].get('games', [])
        if game_index < 0 or game_index >= len(games):
            return {'prices': [], 'game': None}
        game = games[game_index]
        return {
            'game': {
                'match_name': game.get('match_name'),
                'url': game.get('url'),
                'opponent': game.get('opponent'),
                'date': game.get('date')
            },
            'prices': game.get('price_history', []),
            'latest_prices': game.get('latest_prices', {})
        }
    except Exception as e:
        print(f'[ERROR] /teams/{team_key}/game/{game_index} error: {e}')
        return {'prices': [], 'game': None}

@app.get('/vite.svg')
async def serve_vite_svg():
    vite_svg_path = f'{client_dist}/vite.svg'
    if os.path.exists(vite_svg_path):
        return FileResponse(vite_svg_path, media_type='image/svg+xml')
    return {'error': 'vite.svg not found'}

# Test endpoint to verify server is working - lightweight, no data loading
@app.get('/health')
def health_check():
    """Lightweight health check for Railway"""
    return {'status': 'ok', 'message': 'Server is running'}

# Catch-all route for React SPA - MUST be last (after API routes)
# FastAPI matches routes in order, so specific routes above will be matched first
@app.get('/{full_path:path}')
async def serve_react_app(full_path: str, request: Request):
    """Serve React app for all non-API routes (SPA routing)"""
    # Explicitly exclude API routes and static assets
    # These should never reach here if routes are defined correctly above
    excluded_paths = ['matches', 'history', 'teams', 'health', 'assets', 'vite.svg']
    if any(full_path.startswith(excluded) for excluded in excluded_paths):
        # This shouldn't happen if routes are defined correctly, but just in case
        raise HTTPException(status_code=404, detail="API route not found")
    
    # Serve index.html for all other routes (React Router handles routing)
    index_path = f'{client_dist}/index.html'
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            media_type='text/html',
            headers={'Cache-Control': 'no-cache'}
        )
    return {'message': 'Build Not Found.'}

if __name__ == '__main__':
    try:
        import time
        startup_time = time.time()
        
        print('\n' + '='*60, flush=True)
        print(f'  [START] VIAGOGO MONITOR - SERVER ONLY (NO SCRAPERS)', flush=True)
        print(f'  [PORT] {PORT}', flush=True)
        print(f'  [DATA] Loading from {DATA_FILE_VIAGOGO} and {DATA_FILE_FTN}', flush=True)
        print('='*60 + '\n', flush=True)
        
        # Quick check - don't load full data at startup, just verify files exist
        print('[INFO] Verifying data files exist...', flush=True)
        if os.path.exists(DATA_FILE_VIAGOGO):
            file_size = os.path.getsize(DATA_FILE_VIAGOGO)
            print(f'[OK] {DATA_FILE_VIAGOGO} exists ({file_size} bytes)', flush=True)
        else:
            print(f'[WARN] {DATA_FILE_VIAGOGO} not found', flush=True)
        
        if os.path.exists(DATA_FILE_FTN):
            file_size = os.path.getsize(DATA_FILE_FTN)
            print(f'[OK] {DATA_FILE_FTN} exists ({file_size} bytes)', flush=True)
        else:
            print(f'[WARN] {DATA_FILE_FTN} not found', flush=True)
        
        # Verify frontend build exists
        print('[INFO] Verifying frontend build...', flush=True)
        if not os.path.exists(client_dist):
            print(f'[ERROR] Frontend dist directory not found: {client_dist}', flush=True)
        elif not os.path.exists(f'{client_dist}/index.html'):
            print(f'[ERROR] Frontend index.html not found at {client_dist}/index.html', flush=True)
        else:
            print(f'[OK] Frontend build verified: {client_dist}/index.html', flush=True)
        
        elapsed = time.time() - startup_time
        print(f'[INFO] Startup checks completed in {elapsed:.2f}s', flush=True)
        
        print(f'[INFO] Starting server on 0.0.0.0:{PORT}...', flush=True)
        print(f'[INFO] Railway PORT env: {os.environ.get("PORT", "NOT SET")}', flush=True)
        print('[INFO] Server starting now...', flush=True)
        
        # Start uvicorn server - this blocks until server stops
        uvicorn.run(
            app, 
            host='0.0.0.0', 
            port=PORT, 
            log_level='info'
        )
    except KeyboardInterrupt:
        print('\n[INFO] Server stopped by user', flush=True)
    except Exception as e:
        print(f'[FATAL] Server startup failed: {e}', flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

