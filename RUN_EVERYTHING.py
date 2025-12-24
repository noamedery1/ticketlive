import threading
import time
import uvicorn
import json
import os
import re
import sys
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import subprocess

# Fix encoding for Windows (cp1252 can't handle emojis)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
SCRAPE_INTERVAL_HOURS = 2.0
DATA_FILE_VIAGOGO = 'prices.json'
DATA_FILE_FTN = 'prices_ftn.json'
GAMES_FILE = 'all_games_to_scrape.json'
PORT = 8000
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
    if not os.path.exists(file_path): return []
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except: return []

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get('/matches')
def get_matches():
    try:
        if not os.path.exists(GAMES_FILE): return []
        with open(GAMES_FILE, 'r') as f: games = json.load(f)
        
        def get_match_number(match_name):
            m = re.search(r'Match (\d+)', match_name)
            return int(m.group(1)) if m else 9999

        matches_list = [{'match_name': g['match_name'], 'match_url': g['url']} for g in games]
        matches_list.sort(key=lambda x: get_match_number(x['match_name']))
        return matches_list
    except Exception as e:
        print(f'API Error: {e}')
        return []

@app.get('/history')
def get_history(match_url: str):
    try:
        # 1. LOAD VIAGOGO DATA
        viagogo_data = load_data(DATA_FILE_VIAGOGO)
        v_match_data = []
        
        # Extract ID from requested URL
        # e.g. .../World-Cup-Tickets/E-153033506?Currency=... -> E-153033506
        req_id = None
        match = re.search(r'/(E-\d+)', match_url)
        if match: req_id = match.group(1)
        
        print(f"[API] History Request for ID: {req_id} (URL: {match_url[:30]}...)")

        for row in viagogo_data:
            # Extract ID from stored URL
            stored_url = row.get('match_url', '')
            stored_id = None
            m_stored = re.search(r'/(E-\d+)', stored_url)
            if m_stored: stored_id = m_stored.group(1)
            
            # Match by ID if possible, else fallback to string string
            if req_id and stored_id:
                if req_id == stored_id:
                    v_match_data.append(row)
            elif match_url in stored_url or stored_url in match_url:
                 v_match_data.append(row)
                 
        print(f"[API] Found {len(v_match_data)} Viagogo records.")
        v_match_data.sort(key=lambda x: x['timestamp'])

        # 2. IDENTIFY MATCH FOR FTN
        ftn_data = load_data(DATA_FILE_FTN)
        f_match_data = []
        
        match_number = None
        m = re.search(r'Match (\d+)', match_url, re.IGNORECASE)
        
        # New fallback: Look in GAMES_FILE if URL does not have match number
        if not m and os.path.exists(GAMES_FILE):
             try:
                 with open(GAMES_FILE, 'r') as f: games = json.load(f)
                 # Find game with this URL (ignoring query params)
                 clean_input_url = match_url.split('?')[0]
                 
                 for g in games:
                     if g['url'].split('?')[0] == clean_input_url:
                         m = re.search(r'Match (\d+)', g['match_name'], re.IGNORECASE)
                         break
             except: pass

        if not m and v_match_data:
             m = re.search(r'Match (\d+)', v_match_data[0].get('match_name', ''), re.IGNORECASE)
        
        if m:
            match_number = m.group(1)
            # Find FTN records for this Match #
            f_match_data = [d for d in ftn_data if f'Match {match_number}' in d.get('match_name', '')]
            f_match_data.sort(key=lambda x: x['timestamp'])
        
        def process_source_data(data_list):
            if not data_list: return {}, []
            categories = sorted(list(set(d['category'] for d in data_list)))
            result_data = {}
            for cat in categories:
                cat_rows = [d for d in data_list if d['category'] == cat]
                result_data[cat] = [{'timestamp': d['timestamp'], 'price': d['price']} for d in cat_rows]
            return result_data, categories

        v_processed, v_cats = process_source_data(v_match_data)
        f_processed, f_cats = process_source_data(f_match_data)

        return {
            'viagogo': {'categories': v_cats, 'data': v_processed},
            'ftn': {'categories': f_cats, 'data': f_processed},
            'currency': 'USD'
        }

    except Exception as e:
        print(f'History Error: {e}')
        return {'viagogo': {'categories': [], 'data': {}}, 'ftn': {'categories': [], 'data': {}}}

# ---------------------------------------------------------
# Orchestrator Logic
# ---------------------------------------------------------
def run_scraper_viagogo():
    """Run Viagogo scraper in a thread"""
    try:
        print('   [ACTION] Starting Viagogo Scraper...', flush=True)
        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            ['python', 'scraper_viagogo.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace'  # Handle encoding errors gracefully
        )
        # Stream output line by line
        try:
            for line in process.stdout:
                if line:
                    print(line.rstrip(), flush=True)
        except Exception as stream_err:
            print(f'   [WARN] Output streaming error: {stream_err}', flush=True)
        
        process.wait(timeout=None)  # Wait indefinitely for process to complete
        if process.returncode == 0:
            print('   [OK] Viagogo Scraper finished.', flush=True)
        else:
            print(f'   [ERROR] Viagogo Scraper exited with code {process.returncode}', flush=True)
    except subprocess.TimeoutExpired:
        print('   [WARN] Viagogo Scraper process timeout', flush=True)
        process.kill()
    except Exception as e:
        print(f'   [ERROR] Viagogo Scraper Error: {e}', flush=True)
        import traceback
        traceback.print_exc()

def run_scraper_ftn():
    """Run FTN scraper in a thread"""
    try:
        print('   [ACTION] Starting FTN Scraper...')
        subprocess.run(['python', 'scraper_ftn.py'], check=True)
        print('   [OK] FTN Scraper finished.')
    except Exception as e:
        print(f'   [ERROR] FTN Scraper Error: {e}')

def run_scrapers_parallel():
    last_start_time = 0
    min_restart_interval = 300  # Minimum 5 minutes between restarts if scraper fails quickly
    
    while True:
        try:
            current_time = time.time()
            time_since_last_start = current_time - last_start_time
            
            # If scraper failed very quickly (< 2 minutes), wait before restarting
            if 0 < time_since_last_start < 120:
                wait_time = min_restart_interval - time_since_last_start
                if wait_time > 0:
                    print(f'[WARN] Previous scraper run was very short ({int(time_since_last_start)}s). Waiting {int(wait_time)}s before restart...', flush=True)
                    time.sleep(wait_time)
            
            last_start_time = time.time()
            print(f'\\n[{datetime.now().strftime("%H:%M")}] [START] STARTING PARALLEL SCAPERS...', flush=True)
            
            # Launch in parallel using threads
            viagogo_thread = threading.Thread(target=run_scraper_viagogo, daemon=False)
            ftn_thread = threading.Thread(target=run_scraper_ftn, daemon=False)
            
            viagogo_thread.start()
            ftn_thread.start()
            
            # Wait for both to complete
            viagogo_thread.join()
            ftn_thread.join()
            
            runtime = time.time() - last_start_time
            print(f'[{datetime.now().strftime("%H:%M")}] [OK] ALL SCRAPERS FINISHED (runtime: {int(runtime)}s).', flush=True)
            
        except Exception as e:
            print(f'Orchestrator Error: {e}', flush=True)
            import traceback
            traceback.print_exc()
            
        print(f'Next run in {SCRAPE_INTERVAL_HOURS} hours...', flush=True)
        time.sleep(SCRAPE_INTERVAL_HOURS * 3600)

# ---------------------------------------------------------
# Auto-Build Logic & Static Files
# ---------------------------------------------------------
client_dist = 'frontend/dist'

def build_frontend():
    print('[WARN] Frontend build not found. Building now... (This may take a minute)')
    try:
        if not os.path.exists('frontend'):
            print('[ERROR] Error: frontend folder missing!')
            return
            
        npm_cmd = 'npm.cmd' if os.name == 'nt' else 'npm'
        subprocess.check_call([npm_cmd, 'install'], cwd='frontend', shell=True)
        subprocess.check_call([npm_cmd, 'run', 'build'], cwd='frontend', shell=True)
        print('[OK] Build complete!')
    except Exception as e:
        print(f'[ERROR] Build Failed: {e}')

if not os.path.exists(f'{client_dist}/index.html'):
    build_frontend()

if os.path.exists(client_dist):
    app.mount('/assets', StaticFiles(directory=f'{client_dist}/assets'), name='assets')

@app.get('/{full_path:path}')
async def serve_react_app(full_path: str):
    if full_path.startswith('matches') or full_path.startswith('history'):
        return {'error': 'Not found'}
    index_path = f'{client_dist}/index.html'
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {'message': 'Build Not Found.'}

if __name__ == '__main__':
    t = threading.Thread(target=run_scrapers_parallel, daemon=True)
    t.start()
    print('\\n' + '='*50)
    print(f'  [START] VIAGOGO MONITOR (ORCHESTRATOR)')
    print(f'  [DASHBOARD] Dashboard: http://localhost:{PORT}')
    print('='*50 + '\\n')
    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='warning')