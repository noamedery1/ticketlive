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
    """Extract category+price pairs from patterns"""
    lines = []
    
    # Patterns for category:price or category - price
    # Note: dash must be escaped or at end of character class to avoid being interpreted as range
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
            'lines': [{'category': str, 'price': float, 'currency': str}],
            'parse_status': 'ok' or 'partial',
            'warnings': [str]
        }
    """
    warnings = []
    
    # Normalize text
    normalized = normalize_text(raw)
    normalized = remove_commas_from_numbers(normalized)
    
    # Extract match number
    match_num = extract_match_number(normalized)
    if match_num is None:
        warnings.append('No match number found')
    
    # Extract category/price pairs
    lines = extract_category_price_pairs(normalized)
    if not lines:
        warnings.append('No valid category/price pairs found')
    
    # Detect currency
    currency = detect_currency(normalized)
    
    # Apply currency to all lines
    for line in lines:
        line['currency'] = currency
    
    # Determine parse status
    parse_status = 'ok'
    if not match_num or not lines:
        parse_status = 'partial'
    
    # Extract event name if present (optional)
    event = None
    event_patterns = [
        r'(world\s+cup\s+\d{4})',
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

