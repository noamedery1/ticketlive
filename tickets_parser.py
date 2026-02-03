"""
Parser for WhatsApp-style ticket messages
Extracts match number, category/price pairs, and currency
"""
import re
from typing import Dict, List, Any, Optional


def normalize_text(text: str) -> str:
    """Normalize text: lowercase, trim, collapse whitespace"""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def remove_commas_from_numbers(text: str) -> str:
    """Remove commas from numbers (2,500 -> 2500)"""
    def replace_comma(match):
        num = match.group(0)
        return num.replace(',', '')
    
    # Replace commas in numbers
    text = re.sub(r'\d{1,3}(?:,\d{3})+', replace_comma, text)
    return text


def extract_match_number(text: str) -> Optional[int]:
    """Extract match number from patterns: 'match 32', 'game 32', 'm32'"""
    patterns = [
        r'match\s+(\d+)',
        r'game\s+(\d+)',
        r'\bm(\d+)\b',
        r'match\s*#\s*(\d+)',
        r'game\s*#\s*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None


def extract_category_price_pairs(text: str) -> List[Dict[str, Any]]:
    """Extract category+price pairs from patterns, including quantity"""
    lines = []
    
    # Pattern 1: match quantity category price format: "3 x4 cat 3 - 1200$" or "86x4 cat 2 - 1300$"
    match_quantity_pattern = r'(\d+)\s*x\s*(\d+)(?:\s+(?:tickets|tix))?\s+cat\s*(\d+)(?:\s+(?:for\s+price|price))?\s*[:\s-]+\s*(\d+(?:\.\d+)?)\s*\$?'
    matches = re.finditer(match_quantity_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            match_num = int(match.group(1))
            quantity = int(match.group(2))
            category = match.group(3)
            price = float(match.group(4))
            lines.append({
                'match': match_num,
                'quantity': quantity,
                'category': category,
                'price': price,
                'currency': None  # Will be set later
            })
        except (ValueError, IndexError):
            continue

    # Pattern 1b: "Cat 3 X50 $1000" or "Cat 3 X 50 $1000"
    # Groups: 1=Category, 2=Quantity, 3=Price
    cat_x_qty_pattern = r'cat\s*(\d+)\s*x\s*(\d+)\s*[:\s-]?\s*[\$€£]?\s*(\d+(?:\.\d+)?)'
    matches = re.finditer(cat_x_qty_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            category = match.group(1)
            quantity = int(match.group(2))
            # Handle potential thousand separators if needed, but for now standard float
            price_str = match.group(3)
            # Simple heuristic: if price is 15.000, it's likely 15000 if Category 1
            if '.' in price_str and len(price_str.split('.')[1]) == 3 and float(price_str) < 100:
                 price_str = price_str.replace('.', '')
            
            price = float(price_str)
            
            lines.append({
                'match': None,
                'quantity': quantity,
                'category': category,
                'price': price,
                'currency': None
            })
        except (ValueError, IndexError):
            continue

    # Pattern 2: New format 'CAT 3 (40) - $325' or 'CAT 1 (4) - 500' (Quantity in parens)
    # Groups: 1=Category, 2=Quantity, 3=Price
    paren_qty_pattern = r'cat\s*(\d+)\s*\((\d+)\)\s*[:\s-]+\s*[\$€£]?\s*(\d+(?:\.\d+)?)'
    matches = re.finditer(paren_qty_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            category = match.group(1)
            quantity = int(match.group(2))
            price = float(match.group(3))
            lines.append({
                'match': None, # Match number usually in header for this format
                'quantity': quantity,
                'category': category,
                'price': price,
                'currency': None
            })
        except (ValueError, IndexError):
            continue
    
    # Pattern 3: "category 3 - 4 tickets €1.275ea"
    # Groups: 1=Category, 2=Quantity, 3=Price
    # We look for "tickets" or "ticket" to distinguish from simple "cat 3 - 400"
    cat_qty_tix_pattern = r'category\s*(\d+)\s*-\s*(\d+)\s*(?:tickets|ticket|tix)\s*.*?(?:€|£|\$|price)?\s*?(\d+(?:[\.,]\d+)?)'
    matches = re.finditer(cat_qty_tix_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            category = match.group(1)
            quantity = int(match.group(2))
            price_str = match.group(3)
            
            # clean price string
            price_str = price_str.replace(',', '')
            # Handle dot as thousands separator (e.g. 1.275 -> 1275)
            # If 3 decimal places and value < 100 (unlikely to be 1.275 dollars/euros for a ticket, usually > 10)
            # But 1.275 is 1,275.
            if '.' in price_str:
                parts = price_str.split('.')
                # If the last part is exactly 3 digits, treat as thousands separator
                if len(parts) > 1 and len(parts[-1]) == 3:
                     # Check if it looks like a small float (e.g. 1.250 could be 1.25 or 1250)
                     # Context: specific matching for this user who uses European format
                     price_str = price_str.replace('.', '')
            
            price = float(price_str)

            lines.append({
                'match': None, # rely on context
                'quantity': quantity,
                'category': category,
                'price': price,
                'currency': None
            })
        except (ValueError, IndexError):
            continue

    # If lines found with this specific pattern, we might want to skip the fallback
    # But we append to lines, so we just need to ensure we don't double count if we add a check?
    # actually the fallback runs only `if not lines`. So if we found something here, fallback won't run.
    
    # If no match-quantity patterns found, try simpler patterns (backward compatibility)
    if not lines:
        # Patterns for category:price or category - price (without quantity)
        patterns = [
            r'category\s+(\d+)\s*[:\s-]+\s*(\d+(?:\.\d+)?)',
            r'cat\s*(\d+)\s*[:\s-]+\s*(\d+(?:\.\d+)?)',
            r'cat\.\s*(\d+)\s*[:\s-]+\s*(\d+(?:\.\d+)?)',
            r'c\s*(\d+)\s*[:\s-]+\s*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    category = match.group(1)
                    price = float(match.group(2))
                    lines.append({
                        'category': category,
                        'price': price,
                        'quantity': None,  # No quantity specified
                        'currency': None  # Will be set later
                    })
                except (ValueError, IndexError):
                    continue
    
    return lines


def detect_currency(text: str) -> str:
    """Detect currency from text, default to USD"""
    text_lower = text.lower()
    
    # Check for dollar indicators
    dollar_indicators = ['$', 'usd', 'dollar', 'dollars']
    if any(indicator in text_lower for indicator in dollar_indicators):
        return 'USD'
    
    # Check for other currencies (can be extended)
    if 'eur' in text_lower or '€' in text or 'euro' in text_lower:
        return 'EUR'
    if 'gbp' in text_lower or '£' in text or 'pound' in text_lower:
        return 'GBP'
    
    # Default to USD
    return 'USD'



import os
import json
import google.generativeai as genai

def parse_with_gemini(text: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Parse ticket message using Gemini API
    """
    try:
        genai.configure(api_key=api_key)
        
        # Try a list of models, starting with experimental/flash ones that seem available
        # Including 'models/' prefix as returned by list_models()
        candidate_models = [
            'models/gemini-flash-latest', # Working reliably
            'models/gemini-1.5-flash',
            'gemini-1.5-flash',
            'gemini-2.0-flash-exp', # Rate limited often
            'models/gemini-2.0-flash-exp',
            'models/gemini-2.0-flash-001',
            'models/gemini-pro-latest',
            'models/gemini-exp-1206',
            'gemini-1.5-pro'
        ]

        prompt = f"""
        You are a smart ticket parser. Extract ticket information from the following text into a structured JSON format.
        
        Text:
        "{text}"
        
        Output JSON format:
        {{
            "match": int or null (extracted match number if available globally),
            "event": str or null (e.g. "World Cup 2026"),
            "lines": [
                {{
                    "match": int or null (specific match number for this line),
                    "quantity": int or null,
                    "category": str (e.g. "Category 1"),
                    "price": float (numeric price only),
                    "currency": str or null (e.g. "USD", "EUR", "GBP")
                }}
            ],
            "warnings": [str] (any issues encountered)
        }}
        
        Rules:
        1. If quantity is in format "3x4" it means 3 matches of 4 tickets, or 3 listings of 4 tickets. Usually "4x Cat 1" means 4 tickets of Cat 1.
        2. Handle format "Match X ... Category Y - Z tickets P" where Z is quantity and P is price (e.g. "Match 3 ... category 3 - 4 tickets €1.275").
        3. ALWAYS convert prices to USD if they are in another currency. Assume 1 EUR = 1.05 USD. Return price in USD.
        4. Return ONLY valid JSON, no markdown formatting.
        """
        
        # We need to try generating content with fallback models
        response = None
        last_error = None
        
        for m_name in candidate_models:
            try:
                print(f"   [Gemini] Attempting generation with {m_name}...", flush=True)
                active_model = genai.GenerativeModel(m_name)
                response = active_model.generate_content(prompt)
                print(f"   [Gemini] Success with {m_name}!", flush=True)
                break
            except Exception as e:
                print(f"   [Gemini] Failed {m_name}: {e}", flush=True)
                last_error = e
                continue
        
        if not response:
            raise last_error or Exception("No models worked")

        # Clean response (remove markdown code blocks if present)
        clean_text = response.text.strip()
        if clean_text.startswith('```json'):
            clean_text = clean_text[7:]
        if clean_text.startswith('```'):
            clean_text = clean_text[3:]
        if clean_text.endswith('```'):
            clean_text = clean_text[:-3]
            
        data = json.loads(clean_text.strip())
        data['parse_status'] = 'ok'
        if not data.get('lines'):
            data['parse_status'] = 'failed'
        
        return data
    except Exception as e:
        print(f"Gemini parsing failed: {e}")
        return None

def interpret_search_query(query: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Use Gemini to convert natural language search query into structured filter params.
    """
    try:
        genai.configure(api_key=api_key)
        
        # Same candidates as parse_with_gemini
        candidate_models = [
            'models/gemini-flash-latest', 
            'models/gemini-1.5-flash',
            'gemini-1.5-flash',
            'gemini-2.0-flash-exp',
            'models/gemini-2.0-flash-exp',
            'models/gemini-2.0-flash-001',
            'models/gemini-pro-latest',
            'models/gemini-exp-1206',
            'gemini-1.5-pro'
        ]
        
        prompt = f"""
        You are a search query interpreter for a World Cup ticket system.
        Convert the following natural language query into a JSON object representing search filters.
        
        Fields available:
        - match: int (match number)
        - category: str (e.g. "1", "2")
        - min_price: float
        - max_price: float
        - min_quantity: int
        - seller: str (seller name)
        - sort_by: str (options: 'price_asc' (for cheapest/lowest), 'price_desc', 'date_desc' (newest), 'date_asc')
        - limit: int (default 50)
        
        Query: "{query}"
        
        Rules:
        1. Return ONLY valid JSON.
        2. If "lowest price" or "cheapest" is asked, set sort_by='price_asc'.
        3. If specific match (e.g. "match 4", "m4") is found, extract it.
        4. If no clear filter found for a field, omit it.
        """
        
        response = None
        last_error = None
        
        for m_name in candidate_models:
            try:
                active_model = genai.GenerativeModel(m_name)
                response = active_model.generate_content(prompt)
                break
            except Exception as e:
                print(f"   [Gemini Search] Failed {m_name}: {e}", flush=True)
                last_error = e
                continue
                
        if not response:
             raise last_error or Exception("No search models worked")
        
        text = response.text.strip()
        
        # Clean markdown
        if text.startswith('```json'): text = text[7:]
        if text.startswith('```'): text = text[3:]
        if text.endswith('```'): text = text[:-3]
        
        return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini search interpretation failed: {e}")
        return None

def parse_ticket_message(raw: str, api_key: str = None) -> Dict[str, Any]:
    """
    Parse raw WhatsApp-style message into structured data.
    Tries Gemini API first if key provided or in env, falls back to regex.
    """
    # 1. Try Gemini
    # Check env var if no key passed (and strictly None, not just empty)
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        print("Attempting to parse with Gemini API...")
        gemini_result = parse_with_gemini(raw, api_key)
        if gemini_result and gemini_result.get('parse_status') == 'ok':
            print("Gemini parsing successful!")
            return gemini_result
        print("Gemini parsing failed or returned no lines, falling back to regex.")

    # 2. Regex Fallback (Original Logic)
    print("Parsing with Regex Logic...")
    warnings = []
    lines_found = []
    
    # Normalize text but keep lines structure for context parsing
    # We process line by line to handle "Match Headers"
    raw_lines = raw.strip().split('\n')
    
    current_match = None
    
    for line in raw_lines:
        line_clean = normalize_text(line)
        line_clean = remove_commas_from_numbers(line_clean)
        
        if not line_clean:
            continue
            
        # 1. Check if line is a Match Header
        # strict=True means strict match on the pattern to avoid false positives in mixed lines
        header_match = extract_match_number(line_clean)
        
        # Check if line seems to be ONLY a match header (short, contains match/game)
        # e.g. "Match 002" or "Game 004" or "Match #05"
        if header_match is not None:
            # If match number found, update context
            current_match = header_match
            is_header = True

        # If it was a header, we don't try to parse tickets from it (usually)
        # Unless it's a one-liner like "Match 10 Cat 1..." - but that is handled by line extraction logic below
        
        # 2. Try to extract ticket info from line
        # We use a helper that processes just this single line
        extracted = extract_category_price_pairs(line_clean)
        
        if extracted:
            for item in extracted:
                # If item has its own match number (e.g. "Match 50 x2..."), use it
                # Otherwise use the current context match
                if item.get('match'):
                    current_match = item['match'] # Update context too? Maybe not.
                else:
                    item['match'] = current_match
                
                # If we still don't have a specific currency, we'll detect global currency later or per line?
                # Currently extracting per-line currency is hard without context, 
                # but we can detect currency in the line itself if present.
                line_currency = detect_currency(line_clean)
                if line_currency != 'USD': # Assuming default might be USD
                    item['currency'] = line_currency
                
                lines_found.append(item)
    
    # Global currency detection (fallback)
    global_currency = detect_currency(normalize_text(raw))
    
    # Post-processing: Currency Conversion to USD
    all_matches = set() # Fix: Initialize before loop
    
    # helper for checking rates (simple cache in function attribute)
    if not hasattr(parse_ticket_message, "rates_cache"):
         parse_ticket_message.rates_cache = {'data': {}, 'ts': 0}
    
    # Fetch live rates if cache is old (1 hour)
    import time
    if time.time() - parse_ticket_message.rates_cache['ts'] > 3600:
        try:
            import requests # Import here to avoid top-level dependency issues if not installed, though it is requirements.txt
            # Fetch USD base rates. Ex: {"rates": {"EUR": 0.92, ...}} meaning 1 USD = 0.92 EUR
            resp = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=3)
            if resp.status_code == 200:
                parse_ticket_message.rates_cache['data'] = resp.json().get('rates', {})
                parse_ticket_message.rates_cache['ts'] = time.time()
                print("Updated live currency rates")
        except Exception as e:
            print(f"Failed to fetch live currency rates: {e}")
            
    live_rates = parse_ticket_message.rates_cache['data']

    for line in lines_found:
        if not line.get('currency'):
            line['currency'] = global_currency or 'USD' # Default to USD if undetectable
        
        curr = line.get('currency', 'USD').upper()
        
        if curr != 'USD':
            multiplier = None
            
            # 1. Try Live Rates (Base USD)
            # API returns matches for 1 USD. e.g. EUR=0.92. So 1 EUR = 1/0.92 USD.
            if live_rates and curr in live_rates:
                try:
                    rate = float(live_rates[curr])
                    if rate > 0:
                        multiplier = 1.0 / rate
                except:
                    pass
            
            # 2. Fallback to Static Rates
            if multiplier is None:
                # Static multipliers (Amount * X = USD)
                static_rates = {
                    'EUR': 1.05,
                    'GBP': 1.25,
                    'ILS': 0.28,
                    'AUD': 0.65,
                    'CAD': 0.74,
                    'CHF': 1.10
                }
                multiplier = static_rates.get(curr)
                
            if multiplier:
                line['original_price'] = line['price']
                line['original_currency'] = curr
                line['price'] = round(line['price'] * multiplier, 2)
                line['currency'] = 'USD'
            
        if line.get('match'):
            all_matches.add(line['match'])
    
    if len(all_matches) == 1:
        final_match_num = list(all_matches)[0]
    elif len(all_matches) > 1:
        final_match_num = None # Mixed matches
    
    # Extract event name
    event = None
    event_patterns = [
        r'(world\s+cup\s+\d{4})',
        r'(wc\s+\d{4})',
        r'(champions\s+league)',
        r'(premier\s+league)',
    ]
    normalized_full = normalize_text(raw)
    for pattern in event_patterns:
        match = re.search(pattern, normalized_full, re.IGNORECASE)
        if match:
            event = match.group(1).title()
            break

    parse_status = 'ok'
    if not lines_found:
        parse_status = 'failed'
        warnings.append('No ticket lines found')
    elif not all_matches and not final_match_num:
         # It's ok if some lines don't have matches if the whole message didn't specify one?
         # But usually we want a match number.
         parse_status = 'partial'
         warnings.append('No match number found for tickets')

    return {
        'match': final_match_num,
        'event': event,
        'lines': lines_found,
        'parse_status': parse_status,
        'warnings': warnings
    }

