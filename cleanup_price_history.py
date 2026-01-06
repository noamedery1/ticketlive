"""
Cleanup script to remove old block-based price data from team JSON files.
Keeps only main category prices (Category 1, Category 2, etc.) in the new format: {category: lowest_price}
"""
import json
import os
import re
import sys
import io
from pathlib import Path
from typing import Dict, Any, List

# Fix encoding for Windows (cp1252 can't handle emojis)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def is_new_format_price(price_data: Any) -> bool:
    """Check if price data is in the new format: {category: lowest_price}"""
    # New format: price_data is a flat number
    return isinstance(price_data, (int, float))

def is_block_based_format(price_data: Any) -> bool:
    """Check if price data is in old block-based format: {block: price}"""
    # Old format: price_data is a dict with block keys (like "Unknown", "105,100,102,106", etc.)
    if not isinstance(price_data, dict):
        return False
    
    # Check if keys look like block identifiers (not structured data like min/max/count)
    for key in price_data.keys():
        # Block keys are usually strings like "Unknown", "105,100,102,106", "14", etc.
        # Structured data keys are usually "min", "max", "count", "_price", etc.
        if key in ['min', 'max', 'count', '_price']:
            return False
    
    return True

def clean_price_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any] | None:
    """Clean a single price snapshot, keeping only main category prices in new format"""
    if not snapshot.get('prices') or not isinstance(snapshot['prices'], dict):
        return None
    
    prices = snapshot['prices']
    cleaned_prices = {}
    
    for category, price_data in prices.items():
        # Check format
        if is_new_format_price(price_data):
            # Already in new format: {category: lowest_price} - keep as is
            cleaned_prices[category] = price_data
        elif isinstance(price_data, dict):
            # Check if it's block-based format or structured format
            if is_block_based_format(price_data):
                # Old block-based format: {category: {block: price}}
                # Extract minimum price from all blocks
                all_prices = []
                for block, block_price in price_data.items():
                    if isinstance(block_price, (int, float)):
                        all_prices.append(block_price)
                    elif isinstance(block_price, dict) and 'min' in block_price:
                        # Nested format with min/max/count
                        all_prices.append(block_price['min'])
                
                if all_prices:
                    # Store only the lowest price (new format)
                    cleaned_prices[category] = min(all_prices)
            else:
                # Structured format: {category: {min, max, count}} - extract min
                if 'min' in price_data:
                    cleaned_prices[category] = price_data['min']
                elif '_price' in price_data:
                    cleaned_prices[category] = price_data['_price']
    
    # Return snapshot only if it has cleaned prices
    if cleaned_prices:
        return {
            'timestamp': snapshot['timestamp'],
            'prices': cleaned_prices
        }
    return None

def clean_game_data(game: Dict[str, Any]) -> Dict[str, Any]:
    """Clean price history and latest_prices for a single game"""
    cleaned_game = game.copy()
    
    # Clean price_history
    if 'price_history' in cleaned_game and isinstance(cleaned_game['price_history'], list):
        cleaned_history = []
        for snapshot in cleaned_game['price_history']:
            cleaned_snapshot = clean_price_snapshot(snapshot)
            if cleaned_snapshot:
                cleaned_history.append(cleaned_snapshot)
        cleaned_game['price_history'] = cleaned_history
    
    # Clean latest_prices
    if 'latest_prices' in cleaned_game and isinstance(cleaned_game['latest_prices'], dict):
        latest_prices = cleaned_game['latest_prices']
        cleaned_latest = {}
        
        for category, price_data in latest_prices.items():
            # Check format - keep ALL categories, just convert format
            if is_new_format_price(price_data):
                # Already in new format - keep as is
                cleaned_latest[category] = price_data
            elif isinstance(price_data, dict):
                # Check if it's block-based format or structured format
                if is_block_based_format(price_data):
                    # Block-based format - find minimum
                    all_prices = []
                    for block, block_price in price_data.items():
                        if isinstance(block_price, (int, float)):
                            all_prices.append(block_price)
                        elif isinstance(block_price, dict) and 'min' in block_price:
                            all_prices.append(block_price['min'])
                    if all_prices:
                        cleaned_latest[category] = min(all_prices)
                else:
                    # Structured format: {min, max, count} - extract min
                    if 'min' in price_data:
                        cleaned_latest[category] = price_data['min']
                    elif '_price' in price_data:
                        cleaned_latest[category] = price_data['_price']
        
        cleaned_game['latest_prices'] = cleaned_latest
    
    return cleaned_game

def clean_team_data(team_data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean all games in a team's data"""
    cleaned_team = team_data.copy()
    
    if 'games' in cleaned_team and isinstance(cleaned_team['games'], list):
        cleaned_games = []
        for game in cleaned_team['games']:
            cleaned_game = clean_game_data(game)
            cleaned_games.append(cleaned_game)
        cleaned_team['games'] = cleaned_games
    
    return cleaned_team

def clean_file(file_path: Path) -> tuple[int, int]:
    """Clean a single JSON file, returns (games_cleaned, snapshots_removed)"""
    print(f'\n📄 Processing: {file_path.name}')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f'   ❌ Error reading file: {e}')
        return 0, 0
    
    games_cleaned = 0
    snapshots_removed = 0
    
    # Handle different file structures
    if isinstance(data, dict):
        # Check if it's the main teams file (ftn_teams_data.json)
        if any(key in data for key in ['arsenal', 'barcelona', 'real-madrid']):
            # Main teams file: {team_key: {team_data}}
            for team_key, team_data in data.items():
                if isinstance(team_data, dict) and 'games' in team_data:
                    original_snapshots = sum(
                        len(game.get('price_history', [])) 
                        for game in team_data.get('games', [])
                    )
                    
                    cleaned_team = clean_team_data(team_data)
                    data[team_key] = cleaned_team
                    
                    new_snapshots = sum(
                        len(game.get('price_history', [])) 
                        for game in cleaned_team.get('games', [])
                    )
                    
                    games_cleaned += len(cleaned_team.get('games', []))
                    snapshots_removed += (original_snapshots - new_snapshots)
        elif 'games' in data:
            # Individual team file: {team_name, team_url, games: [...]}
            original_snapshots = sum(
                len(game.get('price_history', [])) 
                for game in data.get('games', [])
            )
            
            cleaned_data = clean_team_data(data)
            new_snapshots = sum(
                len(game.get('price_history', [])) 
                for game in cleaned_data.get('games', [])
            )
            
            games_cleaned = len(cleaned_data.get('games', []))
            snapshots_removed = (original_snapshots - new_snapshots)
            data = cleaned_data
    
    # Save cleaned data
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f'   ✅ Cleaned: {games_cleaned} games, removed {snapshots_removed} old snapshots')
        return games_cleaned, snapshots_removed
    except Exception as e:
        print(f'   ❌ Error saving file: {e}')
        return 0, 0

def main():
    """Main cleanup function"""
    import argparse
    parser = argparse.ArgumentParser(description='Clean up price history JSON files')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    print('=' * 80)
    print('🧹 Cleaning Price History Files')
    print('=' * 80)
    print('\nRemoving old block-based price data...')
    print('Keeping only main category prices (Category 1, Category 2, etc.)')
    print('Format: {category: lowest_price}')
    print()
    
    # Find all team JSON files
    files_to_clean = []
    
    # Main teams file
    main_file = Path('ftn_teams_data.json')
    if main_file.exists():
        files_to_clean.append(main_file)
    
    # Individual team files
    for team_file in Path('.').glob('*_prices.json'):
        if team_file.name != 'ftn_teams_data.json':
            files_to_clean.append(team_file)
    
    if not files_to_clean:
        print('⚠️  No team JSON files found!')
        return
    
    print(f'Found {len(files_to_clean)} file(s) to clean:\n')
    for f in files_to_clean:
        print(f'   - {f.name}')
    
    # Confirm (unless --yes flag)
    if not args.yes:
        print('\n' + '=' * 80)
        try:
            response = input('Proceed with cleanup? (yes/no): ').strip().lower()
            if response not in ['yes', 'y']:
                print('❌ Cleanup cancelled.')
                return
        except (EOFError, KeyboardInterrupt):
            print('\n❌ Cleanup cancelled.')
            return
    
    # Clean all files
    total_games = 0
    total_snapshots_removed = 0
    
    for file_path in files_to_clean:
        games, snapshots = clean_file(file_path)
        total_games += games
        total_snapshots_removed += snapshots
    
    print('\n' + '=' * 80)
    print('✅ Cleanup Complete!')
    print('=' * 80)
    print(f'   Total games processed: {total_games}')
    print(f'   Total old snapshots removed: {total_snapshots_removed}')
    print(f'   Files cleaned: {len(files_to_clean)}')
    print()

if __name__ == '__main__':
    main()

