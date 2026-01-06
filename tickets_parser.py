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


def parse_ticket_message(raw: str) -> Dict[str, Any]:
    """
    Parse raw WhatsApp-style message into structured data
    Supports:
    1. Single lines with match info: "Match 50 x2 Cat 1..."
    2. Header-based format:
       "Match 02"
       "Cat 1..."
       "Match 04"
       "Cat 2..."
    """
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
        is_header = False
        if header_match is not None:
            # If line is short and strictly match declaration
            # or if it starts with match/game
            if len(line_clean) < 20 and ('match' in line_clean or 'game' in line_clean or line_clean.startswith('m')):
                 # It's likely a header
                 current_match = header_match
                 is_header = True
            elif re.search(r'^(match|game)\s*#?\d+\s*$', line_clean):
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
    
    # Post-processing: Apply global currency if missing, set top-level match if consistent
    final_match_num = None
    all_matches = set()
    
    for line in lines_found:
        if not line.get('currency'):
            line['currency'] = global_currency
        
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

