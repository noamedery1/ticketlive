# Ticket Offers Manager

## Overview

The Ticket Offers Manager is a new module that allows you to manually insert WhatsApp-style ticket messages, parse them into structured data, and search through saved offers. All data is stored in local JSON files (no database required).

## Features

### Add Offer Tab
- **Seller Management**: Autocomplete dropdown with inline seller creation
- **Raw Message Input**: Large textarea for pasting WhatsApp messages
- **Parse Preview**: Shows parsed match number, categories, prices, and warnings
- **Save Offer**: Stores offer to weekly JSONL files and updates search index

### Search Offers Tab
- **Advanced Filters**: Match number, seller, category, price range, keyword search, time range
- **Results Table**: Displays offers with clickable rows for details
- **Detail Drawer**: Full view of offer with raw message and parsed data

## Access

Navigate to the Ticket Offers Manager by clicking the **🎫 Tickets** button in the sidebar, or access it directly at `/tickets` route.

## Data Storage

All data is stored in `./data/tickets/` directory:

- **`offers_YYYY-Www.jsonl`**: Weekly JSONL files containing all offers (one per line)
- **`sellers.json`**: List of all sellers
- **`index.json`**: Search index for fast lookups by match, seller, category

## API Endpoints

### Sellers
- `GET /api/tickets/sellers` - Get all sellers
- `POST /api/tickets/sellers` - Create new seller

### Offers
- `POST /api/tickets/offers/parse` - Parse raw message without saving
- `POST /api/tickets/offers` - Save offer
- `GET /api/tickets/offers/search` - Search offers with filters
- `GET /api/tickets/offers/{id}` - Get single offer by ID

### Index
- `POST /api/tickets/index/rebuild` - Rebuild search index

## Parsing Rules

The parser extracts:
- **Match Number**: From patterns like "match 32", "game 32", "m32"
- **Category/Price Pairs**: From patterns like "category 1: 2500", "cat2 1600"
- **Currency**: Detects USD, EUR, GBP from text or defaults to USD

## Example Message Format

```
Match 32
Category 1: 2500
Category 2: 1600
Category 3: 1200
```

## Mobile Support

The Ticket Offers Manager is fully responsive and optimized for mobile devices:
- Responsive tabs and filters
- Touch-friendly buttons and inputs
- Scrollable tables on small screens
- Full-screen detail drawer on mobile

## Files

- `tickets_storage.py` - Storage modules for sellers, offers, and index
- `tickets_parser.py` - Message parsing logic
- `frontend/src/TicketOffersManager.jsx` - React component
- `RUN_SERVER_ONLY.py` - API endpoints (added)

## Usage

1. **Add an Offer**:
   - Select or create a seller
   - Paste the WhatsApp message
   - Click "Parse" to preview
   - Click "Save Offer" to store

2. **Search Offers**:
   - Set filters (match, seller, category, price, keyword, time range)
   - Click "Search"
   - Click any row to view full details

3. **Rebuild Index** (if needed):
   - Call `POST /api/tickets/index/rebuild` to rebuild the search index

## Notes

- Offers are stored in weekly JSONL files based on ISO week number
- Index is automatically updated when saving offers
- If index is missing, search will scan all weekly files (slower)
- All data is stored locally - no external database required

