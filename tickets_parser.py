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
    
    # Pattern for match quantity category price format: "3 x4 cat 3 - 1200$" or "86x4 cat 2 - 1300$"
    # Also handles "match 3 x4 tickets cat 3 for price - 1200$"
    # Groups:
    # 1: match number
    # 2: quantity
    # 3: category
    # 4: price
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
    
    Returns:
        {
            'match': int or None,
            'event': str or None,
            'lines': [{'category': str, 'price': float, 'quantity': int or None, 'currency': str, 'match': int or None}],
            'parse_status': 'ok' or 'partial',
            'warnings': [str]
        }
    """
    warnings = []
    
    # Normalize text
    normalized = normalize_text(raw)
    normalized = remove_commas_from_numbers(normalized)
    
    # Extract category/price pairs (may include match numbers and quantities)
    lines = extract_category_price_pairs(normalized)
    
    # If lines have match numbers embedded, extract them
    match_nums_from_lines = [line.get('match') for line in lines if line.get('match')]
    
    match_num = None
    if match_nums_from_lines:
        unique_matches = set(match_nums_from_lines)
        if len(unique_matches) == 1:
            # All lines have same match number
            match_num = match_nums_from_lines[0]
        else:
            # Multiple matches found - keep top level match as None (Mixed)
            match_num = None
            warnings.append(f'Multiple matches found: {sorted(list(unique_matches))}')
    else:
        # Try to extract match number from text (fallback)
        match_num = extract_match_number(normalized)
        if match_num is None:
            warnings.append('No match number found')
    
    if not lines:
        warnings.append('No valid category/price pairs found')
    
    # Detect currency
    currency = detect_currency(normalized)
    
    # Apply currency to all lines, and ensure match is set if not already
    for line in lines:
        line['currency'] = currency
        if 'match' not in line or line.get('match') is None:
            line['match'] = match_num
    
    # Determine parse status
    parse_status = 'ok'
    if (not match_num and not match_nums_from_lines) or not lines:
        parse_status = 'partial'
    
    # Extract event name if present (optional)
    event = None
    event_patterns = [
        r'(world\s+cup\s+\d{4})',
        r'(wc\s+\d{4})',
        r'(champions\s+league)',
        r'(premier\s+league)',
    ]
    for pattern in event_patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            event = match.group(1).title()
            break
    
    return {
        'match': match_num,
        'event': event,
        'lines': lines,
        'parse_status': parse_status,
        'warnings': warnings
    }

