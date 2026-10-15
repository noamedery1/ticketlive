"""
Railway Server - No Scrapers
Serves the API and the built frontend. Reads team prices from ftn_teams_data.json.
"""
import uvicorn
import json
import os
import re
import sys
import base64
import secrets
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
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
# Password for the offers manager (/api/tickets/*). Unset = offers API disabled.
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')

# ==========================================
# FastAPI App
# ==========================================
app = FastAPI(title="TicketLive API")

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'same-origin',
}


def _authorized(request: Request) -> bool:
    """HTTP Basic auth; any username, password must equal ADMIN_PASSWORD."""
    header = request.headers.get('authorization', '')
    if not header.startswith('Basic '):
        return False
    try:
        _user, _, password = base64.b64decode(header[6:]).decode('utf-8').partition(':')
    except Exception:
        return False
    return secrets.compare_digest(password.encode(), ADMIN_PASSWORD.encode())


@app.middleware('http')
async def guard(request: Request, call_next):
    # Offers data (sellers, cost prices) is private.
    if request.url.path.startswith('/api/tickets'):
        if not ADMIN_PASSWORD:
            return JSONResponse({'detail': 'Offers manager disabled: set ADMIN_PASSWORD'}, status_code=503)
        if not _authorized(request):
            return JSONResponse({'detail': 'Authentication required'}, status_code=401,
                                headers={'WWW-Authenticate': 'Basic realm="TicketLive"'})
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
    """Parse 'DD/MM/YY' into a datetime, or None."""
    from datetime import datetime
    try:
        return datetime.strptime(date_str, '%d/%m/%y')
    except (TypeError, ValueError):
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
                'currency': currencies.get(key, 'USD'),
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
        'currency': get_team_currency(team_key),
    }

# ==========================================
# Ticket Offers Manager API
# ==========================================
from tickets_storage import (
    load_sellers, create_seller, get_seller_by_name,
    save_offer, get_offer_by_id, load_offers_from_file, rebuild_index,
    load_index, BASE_DIR
)
from tickets_parser import parse_ticket_message
from pathlib import Path
from datetime import datetime, timedelta

# Pydantic models for request/response
class CreateSellerRequest(BaseModel):
    name: str

class ParseOfferRequest(BaseModel):
    seller: str
    raw: str

class SaveOfferRequest(BaseModel):
    seller: str
    raw: str
    parsed: dict

@app.get('/api/tickets/sellers')
def get_sellers():
    """Return sellers list"""
    try:
        sellers_data = load_sellers()
        return sellers_data.get('sellers', [])
    except Exception as e:
        print(f'[ERROR] /api/tickets/sellers: {e}')
        return []

@app.post('/api/tickets/sellers')
def create_seller_endpoint(request: CreateSellerRequest):
    """Create seller with case-insensitive dedupe"""
    try:
        seller = create_seller(request.name)
        return seller
    except Exception as e:
        print(f'[ERROR] /api/tickets/sellers POST: {e}')
        raise HTTPException(status_code=500, detail='Internal server error')

@app.post('/api/tickets/offers/parse')
def parse_offer(request: ParseOfferRequest):
    """Parse raw text into structured data without saving"""
    try:
        print(f'[INFO] /api/tickets/offers/parse called with seller: {request.seller}, raw length: {len(request.raw) if request.raw else 0}')
        if not request.raw:
            raise HTTPException(status_code=400, detail='Raw text is required')
            
        parsed = parse_ticket_message(request.raw)
        
        print(f'[INFO] Parse result: match={parsed.get("match")}, lines={len(parsed.get("lines", []))}, status={parsed.get("parse_status")}')
        return parsed
    except HTTPException:
        raise
    except Exception as e:
        print(f'[ERROR] /api/tickets/offers/parse: {e}')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail='Internal server error')

@app.post('/api/tickets/offers')
def save_offer_endpoint(request: SaveOfferRequest):
    """Save offer to weekly JSONL and update index"""
    try:
        # Get or create seller
        seller_obj = get_seller_by_name(request.seller)
        if not seller_obj:
            seller_obj = create_seller(request.seller)
        
        # Create offer record
        now = datetime.utcnow()
        offer = {
            'seller': request.seller,
            'seller_id': seller_obj['id'],
            'match': request.parsed.get('match'),
            'event': request.parsed.get('event'),
            'lines': request.parsed.get('lines', []),
            'raw': request.raw,
            'parse_status': request.parsed.get('parse_status', 'ok'),
            'warnings': request.parsed.get('warnings', []),
            'created_at': now.isoformat()
        }
        
        # Save offer
        success = save_offer(offer)
        if not success:
            raise HTTPException(status_code=500, detail='Failed to save offer')
        
        return {'success': True, 'id': offer.get('id')}
    except Exception as e:
        print(f'[ERROR] /api/tickets/offers POST: {e}')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail='Internal server error')

@app.get('/api/tickets/offers/search')
def search_offers(
    match: Optional[int] = None,
    seller: Optional[str] = None,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
    keyword: Optional[str] = None,
    range: str = 'all'
):
    """Search offers using index.json and fallback scanning"""
    return _search_offers_logic(match, seller, category, min_price, max_price, min_quantity, max_quantity, keyword, range)

def _search_offers_logic(match, seller, category, min_price, max_price, min_quantity, max_quantity, keyword, range):
    try:
        # Debugging
        print(f"[SEARCH] Filters: match={match}, seller={seller}, cat={category}, price={min_price}-{max_price}", flush=True)
        
        index_data = load_index()
        # Ensure we have valid sets
        if 'match' not in index_data: index_data['match'] = {}
        if 'seller' not in index_data: index_data['seller'] = {}
        if 'category' not in index_data: index_data['category'] = {}
        if 'offers_by_id' not in index_data: index_data['offers_by_id'] = {}

        candidate_ids = None
        
        # Time range filter
        now = datetime.utcnow()
        if range == '7d':
            cutoff = now - timedelta(days=7)
        elif range == '30d':
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None
        
        # --- INDEX FILTERING ---
        used_index = False
        
        # Match Filter
        if match is not None:
            used_index = True
            match_key = str(match)
            # If match key exists, get IDs. If not, we get empty set, which is correct (no results).
            # But we must initialize candidate_ids.
            ids = set(index_data['match'].get(match_key, []))
            if candidate_ids is None:
                candidate_ids = ids
            else:
                candidate_ids &= ids

        # Seller Filter
        if seller:
            used_index = True
            seller_obj = get_seller_by_name(seller)
            if seller_obj:
                seller_id = seller_obj['id']
                ids = set(index_data['seller'].get(seller_id, []))
                if candidate_ids is None:
                    candidate_ids = ids
                else:
                    candidate_ids &= ids
            else:
                # Seller not found -> no results
                candidate_ids = set()
        
        # Category Filter (Skipping index for fuzzy matching capabilities)
        
        # --- FALLBACK ---
        # If candidate_ids IS NONE, it means no index filters were applied -> Search All.
        # If candidate_ids IS EMPTY SET (not None), it means index filters returned 0 results.
        
        if candidate_ids is None:
            # Fallback to all indexed offers
            candidate_ids = set(index_data['offers_by_id'].keys())
            
            # If index is empty/broken, try file scan?
            if not candidate_ids:
                 offer_files = list(BASE_DIR.glob('offers_*.jsonl'))
                 for file_path in offer_files:
                     offers = load_offers_from_file(file_path)
                     for offer in offers:
                         candidate_ids.add(offer.get('id'))

        if not candidate_ids:
             print("[SEARCH] No candidates found.", flush=True)
             return []

        # --- LOAD & FILTER ---
        results = []
        offers_by_id = index_data.get('offers_by_id', {})
        
        # Group by file to minimize IO
        file_groups = {}
        for oid in candidate_ids:
            if oid in offers_by_id:
                fname = offers_by_id[oid]['file']
                if fname not in file_groups: file_groups[fname] = []
                file_groups[fname].append(oid)
        
        print(f"[SEARCH] Scanning {len(file_groups)} files...", flush=True)

        for fname, oids in file_groups.items():
            file_path = BASE_DIR / fname
            if not file_path.exists(): continue
            
            file_offers = load_offers_from_file(file_path)
            target_ids = set(oids)
            
            for offer in file_offers:
                if offer.get('id') not in target_ids:
                    continue
                
                # Time Check
                if 'created_at' in offer:
                    created_at = datetime.fromisoformat(offer['created_at'])
                else:
                    created_at = now
                if cutoff and created_at < cutoff:
                    continue
                
                # Top Level Filters (Seller, Keyword)
                if seller and str(offer.get('seller', '')).lower() != str(seller).lower():
                    continue
                if keyword and keyword.lower() not in offer.get('raw', '').lower():
                    continue

                # Filter Lines to show specific matches users asked for
                lines = offer.get('lines', [])
                valid_lines = []
                
                # Check Global Match
                global_match_satisfies = False
                if match is not None:
                     if str(offer.get('match')) == str(match):
                         global_match_satisfies = True
                
                # Determine filters
                has_filters = (match is not None or category or min_price is not None or 
                               max_price is not None or min_quantity is not None or max_quantity is not None)
                
                if not has_filters:
                    results.append(offer)
                    continue

                for line in lines:
                    # Match Check
                    if match is not None:
                        l_match = line.get('match')
                        o_match = offer.get('match')
                        # Use line match if present, else fallback to offer match
                        effective_match = l_match if l_match is not None else o_match
                        
                        if effective_match is None or str(effective_match) != str(match):
                            continue
                    # Category
                    if category:
                        l_cat = str(line.get('category', '')).lower()
                        t_cat = str(category).lower()
                        if t_cat not in l_cat and l_cat not in t_cat:
                            continue
                    
                    # Price
                    price = float(line.get('price', 0))
                    if min_price is not None and price < min_price: continue
                    if max_price is not None and price > max_price: continue
                    
                    # Qty
                    qty = line.get('quantity')
                    if min_quantity is not None and (qty is None or qty < min_quantity): continue
                    if max_quantity is not None and (qty is None or qty > max_quantity): continue
                    
                    valid_lines.append(line)
                
                if valid_lines:
                    # Return copy with only valid lines
                    offer_copy = offer.copy()
                    offer_copy['lines'] = valid_lines
                    
                    # Optimization: If all lines are for the same match, promote it to top-level for UI clarity
                    if offer_copy.get('match') is None:
                         unique_matches = set(str(l.get('match')) for l in valid_lines if l.get('match'))
                         if len(unique_matches) == 1:
                             try:
                                offer_copy['match'] = int(list(unique_matches)[0])
                             except: pass

                    results.append(offer_copy)

        print(f"[SEARCH] Found {len(results)} results.", flush=True)
        return results

    except Exception as e:
        print(f'[ERROR] Search Logic: {e}')
        return []

def _excel_safe(value):
    """Stop pasted seller text like '=HYPERLINK(...)' from becoming an Excel formula."""
    if isinstance(value, str) and value[:1] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


@app.get('/api/tickets/export')
def export_tickets(
    match: Optional[int] = None,
    seller: Optional[str] = None,
    category: Optional[str] = None,
    range: str = 'all'
):
    """Export tickets to Excel"""
    try:
        import pandas as pd
        import io
        from fastapi.responses import StreamingResponse
        
        # Refactor search logic to reuse it or just duplicate simple logic
        # We'll use the search logic function extracted above
        offers = _search_offers_logic(match, seller, category, None, None, None, None, None, range)
        
        # Flatten data
        rows = []
        for offer in offers:
            seller_name = offer.get('seller', 'Unknown')
            offer_date = offer.get('created_at', '')
            top_match = offer.get('match')
            event = offer.get('event')
            
            for line in offer.get('lines', []):
                # Determine match for this line
                line_match = line.get('match')
                final_match = line_match if line_match else top_match
                
                # Strict Filtering for Export
                if match is not None:
                    try:
                        # Allow robust comparison (int/str)
                        if final_match is None or int(final_match) != int(match):
                            continue
                    except (ValueError, TypeError):
                        # If match is not a valid number (e.g. "None" or text), skip if we needed a specific match
                         continue
                
                if category:
                   if str(line.get('category')) != str(category):
                       continue

                rows.append({k: _excel_safe(v) for k, v in {
                    'Match': final_match,
                    'Event': event,
                    'Date': offer_date,
                    'Seller': seller_name,
                    'Category': line.get('category'),
                    'Quantity': line.get('quantity'),
                    'Cost Price': line.get('price'),
                    'My Price': line.get('my_price'),
                    'Currency': line.get('currency'),
                    'Raw': (offer.get('raw') or '')[:50] + '...'  # Truncate raw
                }.items()})
        
        if not rows:
             return {'error': 'No data found to export'}

        df = pd.DataFrame(rows)
        
        # Grouping/Breaking Logic
        # "Group by Match, Break by Seller"
        # Since Excel is a flat format (unless multiple sheets), we will sort.
        # Primary Sort: Match
        # Secondary Sort: Seller
        
        # Ensure Match is numeric for sorting if possible
        df['Match'] = pd.to_numeric(df['Match'], errors='coerce').fillna(999999)
        
        df = df.sort_values(by=['Match', 'Seller'])
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tickets')
            
            # Application of styles using openpyxl
            workbook = writer.book
            worksheet = writer.sheets['Tickets']
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            
            # Header Style
            header_font = Font(bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='2b5797', end_color='2b5797', fill_type='solid') # Nice Blue
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Column Widths
            worksheet.column_dimensions['A'].width = 10 # Match
            worksheet.column_dimensions['B'].width = 20 # Event
            worksheet.column_dimensions['C'].width = 20 # Date
            worksheet.column_dimensions['D'].width = 20 # Seller
            worksheet.column_dimensions['E'].width = 15 # Category
            worksheet.column_dimensions['F'].width = 10 # Qty
            worksheet.column_dimensions['G'].width = 12 # Cost
            worksheet.column_dimensions['H'].width = 12 # My Price
            worksheet.column_dimensions['I'].width = 8 # Curr
            worksheet.column_dimensions['J'].width = 50 # Raw
            
            # Data Styles (Alternating colors or logic)
            # Grouping visually by match: alternate background color when match changes?
            
            thin_border = Border(left=Side(style='thin'), 
                                 right=Side(style='thin'), 
                                 top=Side(style='thin'), 
                                 bottom=Side(style='thin'))
            
            current_match = None
            fill_color = 'FFFFFF'
            alt_fill_color = 'F2F2F2' # Light Gray
            current_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
            
            for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
                # Check match column (A is 0)
                match_val = row[0].value
                if match_val != current_match:
                    current_match = match_val
                    # Toggle color
                    fill_color = alt_fill_color if fill_color == 'FFFFFF' else 'FFFFFF'
                    current_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
                
                for cell in row:
                    cell.fill = current_fill
                    cell.border = thin_border
                    # Align numbers
                    if cell.col_idx in [1, 6, 7, 8]: # Match, Qty, Prices
                         cell.alignment = Alignment(horizontal='center')

        
        output.seek(0)
        
        filename = f"tickets_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return StreamingResponse(
            output, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers
        )

    except Exception as e:
        print(f'[ERROR] /api/tickets/export: {e}')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail='Internal server error')

@app.delete('/api/tickets/offers/{offer_id}')
def delete_offer(offer_id: str):
    """Delete an offer"""
    try:
        from tickets_storage import BASE_DIR, load_offers_from_file, load_index, save_index
        
        index_data = load_index()
        offers_by_id = index_data.get('offers_by_id', {})
        
        if offer_id not in offers_by_id:
             return {'success': False, 'msg': 'Offer not found'} # Idempotent-ish
             
        file_name = offers_by_id[offer_id]['file']
        file_path = BASE_DIR / file_name
        
        # Read and filter
        all_offers = load_offers_from_file(file_path)
        new_offers = [o for o in all_offers if o.get('id') != offer_id]
        
        # Write back
        temp_file = file_path.with_suffix('.jsonl.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            for offer in new_offers:
                f.write(json.dumps(offer, ensure_ascii=False) + '\n')
        temp_file.replace(file_path)
        
        # Update Index (Remove)
        del index_data['offers_by_id'][offer_id]
        
        # Cleanup other indexes? Ideally yes, but complex reverse lookup. 
        # Rebuilding index is safer or acceptable latency. 
        # For now, just removing from primary ID lookup effectively hides it.
        # Ideally trigger a bg index rebuild or do lazy cleanup.
        save_index(index_data)
        
        return {'success': True}
    except Exception as e:
        print(f'[ERROR] delete_offer: {e}')
        raise HTTPException(status_code=500, detail='Internal server error')

class UpdateOfferPriceRequest(BaseModel):
    lines: List[dict]

@app.put('/api/tickets/offers/{offer_id}')
def update_offer_prices(offer_id: str, request: UpdateOfferPriceRequest):
    """
    Update my_price for lines in an existing offer.
    We need to load the offer, update specific lines, and save it back (overwriting).
    Since we store in weekly files, this is tricky: we must read the weekly file, update, and rewrite.
    """
    try:
        from tickets_storage import BASE_DIR, load_offers_from_file, get_weekly_file_path, update_index_with_offer
        
        # 1. Locate the file containing the offer
        index_data = load_index()
        offers_by_id = index_data.get('offers_by_id', {})
        if offer_id not in offers_by_id:
             raise HTTPException(status_code=404, detail='Offer not found in index')
        
        file_name = offers_by_id[offer_id]['file']
        file_path = BASE_DIR / file_name
        
        # 2. Read all offers from that file
        all_offers = load_offers_from_file(file_path)
        
        target_offer_index = -1
        target_offer = None
        
        for i, offer in enumerate(all_offers):
            if offer.get('id') == offer_id:
                target_offer = offer
                target_offer_index = i
                break
        
        if target_offer_index == -1:
            raise HTTPException(status_code=404, detail='Offer not found in file')
        
        # 3. Update the lines
        # request.lines should contain objects with {_id (index or id), my_price}
        # In current storage, lines don't have stable IDs, only indices.
        # Frontend provides _id which is just index in the array usually.
        
        # Map incoming updates
        updates_map = {str(l.get('_id')): l.get('my_price') for l in request.lines}
        
        current_lines = target_offer.get('lines', [])
        updated_lines = []
        
        for idx, line in enumerate(current_lines):
            # Frontend uses index as _id usually initiated in frontend state
            # We assume the array order is stable.
            # However, careful: frontend generates _id = i. If we rely on index, we must match.
            # Let's assume frontend sends matching indices.
            
            s_idx = str(idx)
            if s_idx in updates_map:
                line['my_price'] = updates_map[s_idx]
            updated_lines.append(line)
            
        target_offer['lines'] = updated_lines
        all_offers[target_offer_index] = target_offer
        
        # 4. Rewrite the file
        # We use a temp file to be safe
        temp_file = file_path.with_suffix('.jsonl.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            for offer in all_offers:
                f.write(json.dumps(offer, ensure_ascii=False) + '\n')
        
        temp_file.replace(file_path)
        
        return {'success': True, 'msg': 'Offer updated'}

    except HTTPException:
        raise
    except Exception as e:
        print(f'[ERROR] update_offer_prices: {e}')
        raise HTTPException(status_code=500, detail='Internal server error')


@app.get('/api/tickets/offers/{offer_id}')
def get_offer(offer_id: str):
    """Return single offer by id"""
    try:
        offer = get_offer_by_id(offer_id)
        if not offer:
            raise HTTPException(status_code=404, detail='Offer not found')
        return offer
    except HTTPException:
        raise
    except Exception as e:
        print(f'[ERROR] /api/tickets/offers/{offer_id}: {e}')
        raise HTTPException(status_code=500, detail='Internal server error')

@app.post('/api/tickets/index/rebuild')
def rebuild_index_endpoint():
    """Rebuild index by scanning all weekly offers JSONL files"""
    try:
        success = rebuild_index()
        return {'success': success}
    except Exception as e:
        print(f'[ERROR] /api/tickets/index/rebuild: {e}')
        raise HTTPException(status_code=500, detail='Internal server error')

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
    if not ADMIN_PASSWORD:
        print('[WARN] ADMIN_PASSWORD not set - offers manager API is disabled', flush=True)
    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='info')
