"""
PERIODIC AUTOMATED SCRAPER
Runs the automated scraper every X minutes for timeline data
FULLY AUTOMATIC - SET IT AND FORGET IT
"""
import time
import subprocess
import sys
from datetime import datetime, timedelta

INTERVAL_MINUTES = 30  # Run every 30 minutes

def run_scraper():
    """Execute the automated scraper"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n{'='*70}")
    print(f"🕐 [{timestamp}] Starting automated scrape cycle")
    print(f"{'='*70}\n")
    
    try:
        # Run the automated scraper
        result = subprocess.run(
            [sys.executable, 'automated_scraper.py'],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"\n✅ Cycle completed successfully at {timestamp}")
        else:
            print(f"\n⚠ Cycle finished with errors at {timestamp}")
            
    except Exception as e:
        print(f"\n❌ Error running scraper: {e}")
    
    next_run = datetime.now() + timedelta(minutes=INTERVAL_MINUTES)
    print(f"\n⏰ Next scrape: {next_run.strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")

def main():
    print("="*70)
    print("  �� AUTOMATED PERIODIC PRICE MONITOR")
    print("="*70)
    print(f"\n📊 Interval: Every {INTERVAL_MINUTES} minutes")
    print(f"🔄 Mode: Fully automated with anti-detection")
    print(f"💾 Database: prices.db")
    print(f"\nPress Ctrl+C to stop\n")
    
    cycle = 0
    
    try:
        while True:
            cycle += 1
            print(f"\n{'#'*70}")
            print(f"  CYCLE #{cycle}")
            print(f"{'#'*70}")
            
            run_scraper()
            
            # Wait for next interval
            wait_seconds = INTERVAL_MINUTES * 60
            print(f"😴 Sleeping for {INTERVAL_MINUTES} minutes...")
            
            for remaining in range(wait_seconds, 0, -60):
                mins = remaining // 60
                print(f"   ⏱ {mins} minutes remaining...", end='\r')
                time.sleep(60)
            
            print()  # New line
            
    except KeyboardInterrupt:
        print("\n\n⏹ Periodic monitor stopped by user. Goodbye!")

if __name__ == '__main__':
    main()
