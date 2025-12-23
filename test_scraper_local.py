"""
Test script to verify scraper_viagogo.py works locally and data format matches dashboard expectations
"""
import json
import os
from scraper_viagogo import run, OUTPUT_FILE, load_json

def test_data_format():
    """Test that saved data matches dashboard format"""
    print("=" * 60)
    print("Testing Data Format")
    print("=" * 60)
    
    # Check if prices.json exists
    if not os.path.exists(OUTPUT_FILE):
        print(f"ERROR: {OUTPUT_FILE} not found. Run scraper first.")
        return False
    
    data = load_json(OUTPUT_FILE, [])
    if not data:
        print(f"ERROR: {OUTPUT_FILE} is empty")
        return False
    
    print(f"Found {len(data)} records in {OUTPUT_FILE}")
    
    # Check required fields
    required_fields = ["match_name", "match_url", "category", "price", "currency", "timestamp"]
    
    for i, record in enumerate(data[:5]):  # Check first 5 records
        print(f"\nRecord {i+1}:")
        missing_fields = []
        for field in required_fields:
            if field not in record:
                missing_fields.append(field)
            else:
                print(f"  OK {field}: {record[field]}")
        
        if missing_fields:
            print(f"  ERROR Missing fields: {missing_fields}")
            return False
        
        # Validate category format
        if not record["category"].startswith("Category "):
            print(f"  ERROR Invalid category format: {record['category']}")
            return False
        
        # Validate price is numeric
        try:
            float(record["price"])
        except:
            print(f"  ERROR Invalid price: {record['price']}")
            return False
    
    print("\nAll format checks passed!")
    return True

def test_scraper_run():
    """Test running the scraper (limited to 1 game for testing)"""
    print("\n" + "=" * 60)
    print("Testing Scraper Execution")
    print("=" * 60)
    
    # Backup existing prices.json if it exists
    backup_file = OUTPUT_FILE + ".backup"
    if os.path.exists(OUTPUT_FILE):
        import shutil
        shutil.copy(OUTPUT_FILE, backup_file)
        print(f"📦 Backed up {OUTPUT_FILE} to {backup_file}")
    
    # Modify games file temporarily to test with 1 game
    games_file = "all_games_to_scrape.json"
    if os.path.exists(games_file):
        games = load_json(games_file, [])
        if games:
            # Create test games file with just first game
            test_games = [games[0]]
            test_file = games_file + ".test"
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(test_games, f, indent=2)
            
            # Temporarily replace games file
            import shutil
            shutil.copy(games_file, games_file + ".orig")
            shutil.copy(test_file, games_file)
            
            print(f"📝 Created test games file with 1 game")
            print(f"   Game: {test_games[0].get('match_name', 'Unknown')}")
            
            try:
                # Run scraper
                print("\n🚀 Running scraper...")
                run()
                
                # Check results
                if os.path.exists(OUTPUT_FILE):
                    data = load_json(OUTPUT_FILE, [])
                    if data:
                        print(f"\nSUCCESS: Scraper completed! Found {len(data)} records")
                        return True
                    else:
                        print("\nWARNING: Scraper completed but no data found")
                        return False
                else:
                    print("\nERROR: Scraper completed but no output file created")
                    return False
            finally:
                # Restore original games file
                if os.path.exists(games_file + ".orig"):
                    shutil.copy(games_file + ".orig", games_file)
                    os.remove(games_file + ".orig")
                if os.path.exists(test_file):
                    os.remove(test_file)
                # Restore backup if exists
                if os.path.exists(backup_file):
                    shutil.copy(backup_file, OUTPUT_FILE)
                    os.remove(backup_file)
        else:
            print("ERROR: No games found in games file")
            return False
    else:
        print(f"ERROR: {games_file} not found")
        return False

if __name__ == "__main__":
    print("\nTesting Viagogo Scraper\n")
    
    # Test 1: Check data format (if file exists)
    format_ok = test_data_format()
    
    # Test 2: Run scraper (optional - comment out if you don't want to run it)
    # run_ok = test_scraper_run()
    
    print("\n" + "=" * 60)
    if format_ok:
        print("Format test: PASSED")
    else:
        print("Format test: FAILED")
    print("=" * 60)

