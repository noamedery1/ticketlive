import json
import re
import time
from playwright.sync_api import sync_playwright

def convert_to_usd(price, currency_symbol):
    rates = {
        chr(36): 1.0, 'USD': 1.0, 'US'+chr(36): 1.0, 
        chr(8364): 1.05, 'EUR': 1.05,
        chr(163): 1.27, 'GBP': 1.27,
        chr(8362): 0.28, 'ILS': 0.28,
        'NIS': 0.28
    }
    currency_symbol = currency_symbol.strip()
    rate = rates.get(currency_symbol, 1.0)
    return price * rate

def process_match(page, match):
    url = match['url']
    has_quantity = "quantity=" in url
    quantity = 2  # Default quantity
    
    if not has_quantity:
        if "?" in url:
            url += "&quantity=2"
        else:
            url += "?quantity=2"
    else:
        # Extract quantity from URL
        import re as url_re
        qty_match = url_re.search(r'quantity=(\d+)', url)
        if qty_match:
            quantity = int(qty_match.group(1))

    print(f"Navigating to: {url} (quantity={quantity})")
    try:
        page.goto(url, timeout=60000)
    except Exception as e:
        print(f"Navigation error: {e}")
        return []

    time.sleep(5)  # Wait for page load
    
    # Try to click "See Tickets" to get to actual ticket listings
    try:
        see_tickets = page.locator("text=See Tickets").first
        if see_tickets.is_visible(timeout=5000):
            print("  Clicking 'See Tickets' to view ticket listings...")
            see_tickets.click()
            time.sleep(8)  # Wait for ticket page to load
    except:
        print("  Already on ticket page or 'See Tickets' not found")
    
    match_name = match['match_name']
    try:
        title = page.title()
        parts = title.split('|')
        if len(parts) > 0:
            match_name = parts[0].strip()
    except:
        pass

    # Scroll to load all ticket listings
    try:
        print("  Scrolling to load all ticket listings...")
        for _ in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)
    except:
        pass

    content_text = page.locator("body").inner_text()
    
    extracted = []
    dollar_char = chr(36)
    syms = [re.escape(dollar_char), 'USD', 'EUR', 'ILS', 'GBP', 'NIS', chr(8364), chr(163), chr(8362)]
    sym_group = '|'.join(syms)
    
    # Improved pattern: Avoid matching single digits (like "1" from "Category 1")
    # Pattern 1: Currency symbol followed by number (at least 2 digits)
    # Pattern 2: Number (at least 2 digits) followed by currency symbol
    # Use word boundaries to avoid partial matches
    
    # Pattern for currency before number: $1,234.56 or $1234 (handles commas, minimum 3 digits)
    # Matches: $4,222, $2,435, $3,472
    pattern1 = re.compile(
        f"({sym_group})\\s*([1-9]\\d{{0,2}}(?:,\\d{{3}})+|\\d{{3,}})(?:\\.\\d{{2}})?",
        re.I
    )
    
    # Pattern for number before currency: 1,234.56 USD or 1234 EUR (handles commas, minimum 3 digits)
    # Matches: 4,222 USD, 2,435 EUR
    pattern2 = re.compile(
        f"([1-9]\\d{{0,2}}(?:,\\d{{3}})+|\\d{{3,}})(?:\\.\\d{{2}})?\\s*({sym_group})",
        re.I
    )

    # Collect all price matches with their positions
    price_matches = []
    
    # Find pattern 1 matches (currency before number)
    for m in pattern1.finditer(content_text):
        currency = (m.group(1) or '').strip()
        val_str = m.group(2).replace(',', '')
        try:
            val = float(val_str)
            if val >= 500:  # Minimum reasonable ticket price (per ticket after division)
                price_matches.append({
                    'price': val,
                    'currency': currency,
                    'position': m.start(),
                    'match': m
                })
        except:
            continue
    
    # Find pattern 2 matches (number before currency)
    for m in pattern2.finditer(content_text):
        val_str = m.group(1).replace(',', '')
        currency = (m.group(2) or '').strip()
        try:
            val = float(val_str)
            if val >= 500:  # Minimum reasonable ticket price (per ticket after division)
                price_matches.append({
                    'price': val,
                    'currency': currency,
                    'position': m.start(),
                    'match': m
                })
        except:
            continue
    
    # Sort by position to process in order
    price_matches.sort(key=lambda x: x['position'])
    
    # For each price, find associated category
    # Look for the closest category before each price
    for pm in price_matches:
        start_pos = pm['position']
        # Look backwards for category (but not too far to avoid false matches)
        buffer_len = 500  # Increased to find category
        buffer_start = max(0, start_pos - buffer_len)
        buffer = content_text[buffer_start:start_pos]
        
        # Find all category matches in buffer, get the closest one
        cat_matches = list(re.finditer(r"Category\s+([1-4])\b", buffer, re.I))
        
        if cat_matches:
            # Get the last (closest) category match before the price
            cat_match = cat_matches[-1]
            cat_num = int(cat_match.group(1))
            price_val = pm['price']
            
            # If price is exactly the category number, skip (likely false match)
            if abs(price_val - cat_num) < 0.01:
                continue
            
            # Check if there's text between category and price (should be minimal)
            cat_end_pos = cat_match.end()
            text_between = buffer[cat_end_pos:].strip()
            
            # If there's too much text between category and price, might be wrong match
            # But allow some flexibility for formatting
            if len(text_between) > 200:  # Too far apart
                continue
            
            cat_name = f"Category {cat_num}"
            val_usd = convert_to_usd(pm['price'], pm['currency'])
            
            # Prices on Viagogo are shown per ticket, not total
            # So we don't need to divide by quantity
            # (Removed division - prices are already per ticket)
            
            extracted.append({
                "match_name": match_name,
                "category": cat_name,
                "price": val_usd,
                "currency": "USD", 
                "raw_price": pm['price'],
                "raw_currency": pm['currency']
            })

    # Deduplicate: Keep min price per category
    min_prices = {}
    for item in extracted:
        cat = item['category']
        if cat not in min_prices or item['price'] < min_prices[cat]['price']:
            min_prices[cat] = item
            
    return list(min_prices.values())

def generate_report(results):
    dollar_sign = chr(36)
    
    grouped = {}
    for r in results:
        m = r['match_name']
        if m not in grouped: grouped[m] = []
        grouped[m].append(r)

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Viagogo Benchmark Report</title>
<style>
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background-color: #f4f4f9; }
h1 { color: #333; }
.match-container { margin-bottom: 10px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 5px; overflow: hidden; }
summary { padding: 15px; cursor: pointer; background-color: #007bff; color: white; font-weight: bold; list-style: none; display: flex; justify-content: space-between; align-items: center; }
summary::-webkit-details-marker { display: none; }
summary:hover { background-color: #0056b3; }
summary:after { content: '+'; font-size: 1.5em; font-weight: bold; }
details[open] summary:after { content: '-'; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
th { background-color: #f8f9fa; color: #333; }
tr:nth-child(even) { background-color: #f9f9f9; }
.price { color: #28a745; font-weight: bold; }
.meta { font-size: 0.9em; color: #666; }
.min-price-badge { background: white; color: #007bff; padding: 2px 8px; border-radius: 10px; font-size: 0.9em; margin-left: 10px;}
</style>
</head>
<body>
<h1>Viagogo Prices (USD Est.)</h1>
<p>Generated on: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
"""

    for match_name, listings in grouped.items():
        listings.sort(key=lambda x: x['price'])
        if not listings: continue
        
        min_price = listings[0]['price']
        min_price_display = "{}{:.2f}".format(dollar_sign, min_price)
        
        html += f"""
<div class="match-container">
<details>
<summary>
    <span>{match_name}</span>
    <span class="min-price-badge">From {min_price_display}</span>
</summary>
<table>
<tr><th>Category</th><th>Price (USD)</th></tr>
"""
        for r in listings:
            price_display = "{}{:.2f}".format(dollar_sign, r['price'])
            html += f"<tr><td>{r['category']}</td><td class='price'>{price_display}</td></tr>"
            
        html += """</table></details></div>"""

    html += "</body></html>"
    
    with open('report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Generated report.html")

def main():
    try:
        with open('input.json', 'r') as f: matches = json.load(f)
    except Exception as e:
        print(f"Error loading input.json: {e}")
        return

    all_results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            viewport={'width': 1366, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        for match in matches:
            if not match.get('url'): continue
            data = process_match(page, match)
            if data: all_results.extend(data)
            time.sleep(2)
            
        browser.close()

    if all_results:
        generate_report(all_results)
        print(f"Total listings found: {len(all_results)}")
    else:
        print("No listings found.")

if __name__ == "__main__":
    main()