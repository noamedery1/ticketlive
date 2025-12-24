"""
Railway Server - No Scrapers
Only serves the API and frontend, reads from prices.json and prices_ftn.json
"""
import uvicorn
import json
import os
import re
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import subprocess

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
PORT = int(os.environ.get('PORT', 8000))

# ==========================================
# FastAPI App
# ==========================================
app = FastAPI()

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
        print(f'[INFO] Returning {len(matches_list)} matches')
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
    # Mount assets directory
    assets_path = f'{client_dist}/assets'
    if os.path.exists(assets_path):
        try:
            app.mount('/assets', StaticFiles(directory=assets_path), name='assets')
            print('[OK] Static assets mounted at /assets')
        except Exception as e:
            print(f'[WARN] Failed to mount assets: {e}')
    else:
        print(f'[WARN] Assets directory not found: {assets_path}')
    
    # Mount other static files (vite.svg, etc.) from dist root
    try:
        app.mount('/static', StaticFiles(directory=client_dist), name='static')
        print('[OK] Static files mounted at /static')
    except Exception as e:
        print(f'[WARN] Failed to mount static files: {e}')
else:
    print(f'[ERROR] Frontend dist directory not found: {client_dist}')

# API routes must be defined before catch-all route
@app.get('/')
async def serve_root():
    """Serve root path - React app"""
    index_path = f'{client_dist}/index.html'
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type='text/html')
    return {'message': 'Build Not Found.', 'dist_path': client_dist, 'exists': os.path.exists(client_dist)}

# Catch-all route for React SPA - MUST be last
@app.get('/{full_path:path}')
async def serve_react_app(full_path: str):
    """Serve React app for all non-API routes (SPA routing)"""
    # Don't interfere with API routes
    if full_path in ['matches', 'history'] or full_path.startswith('matches/') or full_path.startswith('history/'):
        return {'error': 'Not found'}
    
    # Don't serve API routes
    if full_path.startswith('api/'):
        return {'error': 'Not found'}
    
    # Serve index.html for all other routes (React Router handles routing)
    index_path = f'{client_dist}/index.html'
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type='text/html')
    return {'message': 'Build Not Found.', 'path': full_path, 'dist_exists': os.path.exists(client_dist)}

if __name__ == '__main__':
    print('\n' + '='*60)
    print(f'  [START] VIAGOGO MONITOR - SERVER ONLY (NO SCRAPERS)')
    print(f'  [PORT] {PORT}')
    print(f'  [DATA] Loading from {DATA_FILE_VIAGOGO} and {DATA_FILE_FTN}')
    print('='*60 + '\n')
    
    # Load data once at startup to verify
    v_data = load_data(DATA_FILE_VIAGOGO)
    f_data = load_data(DATA_FILE_FTN)
    print(f'[INFO] Startup: {len(v_data)} Viagogo records, {len(f_data)} FTN records\n')
    
    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='info')

