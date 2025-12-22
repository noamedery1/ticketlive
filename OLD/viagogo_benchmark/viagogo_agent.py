import json
import re
import time
from playwright.sync_api import sync_playwright

def convert_to_usd(price, currency_symbol):
    rates = {
        chr(36): 1.0, 'USD': 1.0, 'US'+chr(36): 1.0, 
        '?': 1.05, 'EUR': 1.05,
        '?': 1.27, 'GBP': 1.27,
        '?': 0.28, 'ILS': 0.28
    }
    rate = rates.get(currency_symbol, 1.0)
    return price * rate

def process_match(page, match):
    url = match['url']
    print(f"Navigating to: {url}")
    try:
        page.goto(url, timeout=60000)
        time.sleep(8)
    except Exception as e:
        print(f"Navigation error: {e}")
        return []

    print(f"Title: {page.title()}")
    content_text = page.locator("body").inner_text()
    match_name = match['match_name']
    title_parts = page.title().split('|')
    if len(title_parts) > 0:
        match_name = title_parts[0].strip()

    extracted = []
    dollar_char = chr(36)
    syms = [re.escape(dollar_char), 'USD', 'EUR', 'ILS', 'GBP']
    sym_group = '|'.join(syms)
    patt = f"({sym_group})\\s*([\\d,]+)|([\\d,]+)\\s*({sym_group})"
    currency_pattern = re.compile(patt, re.I)

    matches_found = 0
    for m in currency_pattern.finditer(content_text):
        matches_found += 1
        price_str = m.group(0)
        
        val_str = (m.group(2) or m.group(3)).replace(',', '')
        try:
            val = float(val_str)
        except:
            continue
            
        currency = m.group(1) or m.group(4)
        val_usd = convert_to_usd(val, currency)
        
        start, end = m.span()
        buffer_start = max(0, start - 300)
        buffer = content_text[buffer_start:start]
        
        cat_match = re.search(r"(Category|Section|Block|Row)\s+([A-Za-z0-9\-]+)", buffer, re.I)
        cat_name = "General"
        if cat_match:
            cat_name = cat_match.group(0)
            
        if val > 10:
             extracted.append({
                 "match_name": match_name,
                 "category": cat_name,
                 "price": val_usd,
                 "currency": "USD",
                 "raw": price_str
             })
             
    print(f"Regex matches: {matches_found}")
    
    min_prices = {}
    for item in extracted:
        cat = item['category']
        price = item['price']
        if cat not in min_prices or price < min_prices[cat]['price']:
            min_prices[cat] = item
            
    return list(min_prices.values())

