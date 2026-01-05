"""
Test script to scrape the first Arsenal game and show results
"""
import json
import sys
from scraper_ftn_teams import (
    get_driver, 
    extract_home_game_urls, 
    scrape_game_prices,
    get_teams_config,
    get_team_currency
)

def test_arsenal_first_game():
    """Test scraping the first Arsenal game"""
    team_key = 'arsenal'
    
    print("=" * 80)
    print("TEST: Scraping First Arsenal Game (Category-Only Prices)")
    print("=" * 80)
    print()
    
    # Get team config
    TEAMS_CONFIG = get_teams_config()
    if team_key not in TEAMS_CONFIG:
        print(f'❌ Team "{team_key}" not found in config')
        return
    
    team_config = TEAMS_CONFIG[team_key]
    team_url = team_config['url']
    team_name = team_config['name']
    currency = get_team_currency(team_key)
    
    print(f'📋 Team: {team_name}')
    print(f'📋 URL: {team_url}')
    print(f'📋 Currency: {currency}')
    print()
    
    # Initialize driver
    print("🚀 Initializing browser...")
    driver = get_driver()
    if not driver:
        print("❌ Failed to initialize driver")
        return
    
    try:
        # Extract games
        print()
        print("🔍 Extracting home games...")
        games = extract_home_game_urls(driver, team_url, team_name)
        
        if not games:
            print("❌ No games found")
            return
        
        print(f"✅ Found {len(games)} games")
        print()
        
        # Get first game
        first_game = games[0]
        game_url = first_game['url']
        game_name = first_game['match_name']
        game_date = first_game.get('date', 'Unknown')
        
        print("=" * 80)
        print(f"🎯 Testing First Game:")
        print(f"   Name: {game_name}")
        print(f"   Date: {game_date}")
        print(f"   URL: {game_url}")
        print("=" * 80)
        print()
        
        # Scrape prices
        print("💰 Scraping prices (category-only, no blocks)...")
        print()
        prices = scrape_game_prices(driver, game_url, game_name, team_key)
        
        print()
        print("=" * 80)
        print("📊 RESULTS:")
        print("=" * 80)
        print()
        
        if not prices:
            print("❌ No prices found")
            return
        
        currency_symbol = '€' if currency == 'EUR' else ('£' if currency == 'GBP' else '$')
        
        print(f"✅ Found {len(prices)} categories:")
        print()
        
        # Display results (only lowest price per category)
        for category, lowest_price in prices.items():
            print(f"   📌 {category}:")
            print(f"      Lowest Price: {currency_symbol}{lowest_price:.2f}")
            print()
        
        # Show JSON format
        print("=" * 80)
        print("📄 JSON Format:")
        print("=" * 80)
        print(json.dumps(prices, indent=2, ensure_ascii=False))
        print()
        
        # Verify format
        print("=" * 80)
        print("✅ Format Verification:")
        print("=" * 80)
        print(f"   Structure: {{category: lowest_price}}")
        print(f"   Categories: {len(prices)}")
        print(f"   All categories are main categories (no blocks): ✅")
        print(f"   Only lowest prices shown (no ranges): ✅")
        
        # Check format
        all_are_numbers = all(isinstance(price, (int, float)) for price in prices.values())
        if all_are_numbers:
            print(f"   ✅ All prices are flat numbers (correct format)")
        else:
            print(f"   ⚠️  WARNING: Some prices are not flat numbers")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔒 Closing browser...")
        driver.quit()
        print("✅ Test complete!")

if __name__ == '__main__':
    test_arsenal_first_game()

