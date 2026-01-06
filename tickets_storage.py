"""
Storage modules for Ticket Offers Manager
Handles JSON file operations for sellers, offers, and index
"""
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import hashlib

# Base directory for ticket data
BASE_DIR = Path('./data/tickets')
BASE_DIR.mkdir(parents=True, exist_ok=True)

SELLERS_FILE = BASE_DIR / 'sellers.json'
INDEX_FILE = BASE_DIR / 'index.json'


def get_iso_week(date_obj: datetime) -> str:
    """Get ISO week string (YYYY-Www) from datetime"""
    year, week, _ = date_obj.isocalendar()
    return f"{year}-W{week:02d}"


def get_weekly_file_path(created_at: datetime) -> Path:
    """Get weekly JSONL file path based on creation date"""
    week_str = get_iso_week(created_at)
    return BASE_DIR / f"offers_{week_str}.jsonl"


def slugify(text: str) -> str:
    """Create a slug from text"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def generate_offer_id(seller: str, raw: str, created_at: datetime) -> str:
    """Generate unique offer ID"""
    timestamp = created_at.isoformat()
    content = f"{seller}|{raw[:100]}|{timestamp}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]


# ==========================================
# Sellers Store
# ==========================================
def load_sellers() -> Dict[str, Any]:
    """Load sellers from JSON file"""
    if not SELLERS_FILE.exists():
        return {"sellers": []}
    
    try:
        with open(SELLERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'[ERROR] Failed to load sellers: {e}')
        return {"sellers": []}


def save_sellers(data: Dict[str, Any]) -> bool:
    """Save sellers to JSON file atomically"""
    try:
        temp_file = SELLERS_FILE.with_suffix('.json.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(SELLERS_FILE)
        return True
    except Exception as e:
        print(f'[ERROR] Failed to save sellers: {e}')
        if temp_file.exists():
            temp_file.unlink()
        return False


def get_seller_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get seller by name (case-insensitive)"""
    sellers_data = load_sellers()
    name_lower = name.lower().strip()
    for seller in sellers_data.get('sellers', []):
        if seller.get('name', '').lower() == name_lower:
            return seller
    return None


def create_seller(name: str) -> Dict[str, Any]:
    """Create a new seller with deduplication"""
    sellers_data = load_sellers()
    sellers = sellers_data.get('sellers', [])
    
    # Check if exists (case-insensitive)
    existing = get_seller_by_name(name)
    if existing:
        return existing
    
    # Create new seller
    seller_id = slugify(name)
    now = datetime.utcnow()
    new_seller = {
        'id': seller_id,
        'name': name.strip(),
        'created_at': now.isoformat()
    }
    
    sellers.append(new_seller)
    sellers_data['sellers'] = sellers
    save_sellers(sellers_data)
    
    return new_seller


# ==========================================
# Offers Store
# ==========================================
def save_offer(offer: Dict[str, Any]) -> bool:
    """Save offer to weekly JSONL file and update index"""
    try:
        # Parse created_at or use current time
        if 'created_at' in offer:
            created_at = datetime.fromisoformat(offer['created_at'])
        else:
            created_at = datetime.utcnow()
            offer['created_at'] = created_at.isoformat()
        
        # Ensure offer has ID
        if 'id' not in offer:
            offer['id'] = generate_offer_id(
                offer.get('seller', ''),
                offer.get('raw', ''),
                created_at
            )
        
        # Get weekly file path
        weekly_file = get_weekly_file_path(created_at)
        
        # Append to JSONL
        with open(weekly_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(offer, ensure_ascii=False) + '\n')
        
        # Update index
        update_index_with_offer(offer)
        
        return True
    except Exception as e:
        print(f'[ERROR] Failed to save offer: {e}')
        import traceback
        traceback.print_exc()
        return False


def load_offers_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load offers from a JSONL file, ignoring corrupt lines"""
    offers = []
    if not file_path.exists():
        return offers
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    offer = json.loads(line)
                    offers.append(offer)
                except json.JSONDecodeError:
                    print(f'[WARN] Skipping corrupt line {line_num} in {file_path.name}')
                    continue
    except Exception as e:
        print(f'[ERROR] Failed to load offers from {file_path}: {e}')
    
    return offers


def get_offer_by_id(offer_id: str) -> Optional[Dict[str, Any]]:
    """Get offer by ID using index"""
    index_data = load_index()
    offers_by_id = index_data.get('offers_by_id', {})
    
    if offer_id not in offers_by_id:
        return None
    
    file_name = offers_by_id[offer_id].get('file')
    if not file_name:
        return None
    
    file_path = BASE_DIR / file_name
    offers = load_offers_from_file(file_path)
    
    for offer in offers:
        if offer.get('id') == offer_id:
            return offer
    
    return None


# ==========================================
# Index Store
# ==========================================
def load_index() -> Dict[str, Any]:
    """Load index from JSON file"""
    if not INDEX_FILE.exists():
        return {
            'offers_by_id': {},
            'match': {},
            'seller': {},
            'category': {},
            'updated_at': None
        }
    
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'[ERROR] Failed to load index: {e}')
        return {
            'offers_by_id': {},
            'match': {},
            'seller': {},
            'category': {},
            'updated_at': None
        }


def save_index(data: Dict[str, Any]) -> bool:
    """Save index to JSON file atomically"""
    try:
        data['updated_at'] = datetime.utcnow().isoformat()
        temp_file = INDEX_FILE.with_suffix('.json.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(INDEX_FILE)
        return True
    except Exception as e:
        print(f'[ERROR] Failed to save index: {e}')
        if temp_file.exists():
            temp_file.unlink()
        return False


def update_index_with_offer(offer: Dict[str, Any]) -> bool:
    """Update index with a new offer"""
    index_data = load_index()
    offer_id = offer.get('id')
    if not offer_id:
        return False
    
    # Get weekly file name
    created_at = datetime.fromisoformat(offer.get('created_at', datetime.utcnow().isoformat()))
    weekly_file = get_weekly_file_path(created_at)
    file_name = weekly_file.name
    
    # Update offers_by_id
    if 'offers_by_id' not in index_data:
        index_data['offers_by_id'] = {}
    index_data['offers_by_id'][offer_id] = {'file': file_name}
    
    # Update match index
    matches_to_index = set()
    
    # Top level match
    match_num = offer.get('match')
    if match_num is not None:
        matches_to_index.add(match_num)
        
    # Matches in lines
    lines = offer.get('lines', [])
    for line in lines:
        line_match = line.get('match')
        if line_match is not None:
            matches_to_index.add(line_match)
            
    if 'match' not in index_data:
        index_data['match'] = {}
        
    for m in matches_to_index:
        match_key = str(m)
        if match_key not in index_data['match']:
            index_data['match'][match_key] = []
        if offer_id not in index_data['match'][match_key]:
            index_data['match'][match_key].append(offer_id)
    
    # Update seller index
    seller_id = offer.get('seller_id')
    if seller_id:
        if 'seller' not in index_data:
            index_data['seller'] = {}
        if seller_id not in index_data['seller']:
            index_data['seller'][seller_id] = []
        if offer_id not in index_data['seller'][seller_id]:
            index_data['seller'][seller_id].append(offer_id)
    
    # Update category index
    lines = offer.get('lines', [])
    for line in lines:
        category = line.get('category')
        if category is not None:
            if 'category' not in index_data:
                index_data['category'] = {}
            cat_key = str(category)
            if cat_key not in index_data['category']:
                index_data['category'][cat_key] = []
            if offer_id not in index_data['category'][cat_key]:
                index_data['category'][cat_key].append(offer_id)
    
    return save_index(index_data)


def rebuild_index() -> bool:
    """Rebuild index by scanning all weekly JSONL files"""
    print('[INFO] Rebuilding index...')
    index_data = {
        'offers_by_id': {},
        'match': {},
        'seller': {},
        'category': {},
        'updated_at': None
    }
    
    # Find all weekly offer files
    offer_files = list(BASE_DIR.glob('offers_*.jsonl'))
    print(f'[INFO] Found {len(offer_files)} weekly files')
    
    for file_path in offer_files:
        offers = load_offers_from_file(file_path)
        print(f'[INFO] Processing {file_path.name}: {len(offers)} offers')
        for offer in offers:
            update_index_with_offer(offer)
    
    print('[OK] Index rebuild complete')
    return True

