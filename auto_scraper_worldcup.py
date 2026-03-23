"""
Auto Scraper for World Cup (Viagogo + FTN)
Runs both viagogo and FTN scrapers for World Cup games and pushes to git server
"""
import subprocess
import time
import os
import sys
import shutil
from datetime import datetime
import json

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Detect Python command (py or python)
def get_python_cmd():
    """Detect which Python command works: py or python"""
    if shutil.which('py'):
        return 'py'
    elif shutil.which('python'):
        return 'python'
    else:
        # Default to py on Windows
        return 'py' if sys.platform == 'win32' else 'python'

PYTHON_CMD = get_python_cmd()

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
SCRAPE_INTERVAL_HOURS = 2.0  # Run every 2 hours
PRICES_VIAGOGO_FILE = 'prices.json.gz'  # Viagogo World Cup prices file
PRICES_FTN_FILE = 'prices_ftn.json.gz'  # FTN World Cup prices file

# ==========================================
# Git Functions
# ==========================================
def git_add_files(files):
    """Add files to git staging"""
    try:
        for file in files:
            result = subprocess.run(
                ['git', 'add', file],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                print(f'   [WARN] Failed to add {file}: {result.stderr}', flush=True)
        return True
    except Exception as e:
        print(f'   [ERROR] Git add error: {e}', flush=True)
        return False

def git_commit(message):
    """Commit staged changes"""
    try:
        result = subprocess.run(
            ['git', 'commit', '-m', message],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            print(f'   [OK] Committed: {message}', flush=True)
            return True
        else:
            if 'nothing to commit' in result.stdout.lower() or 'nothing to commit' in result.stderr.lower():
                print(f'   [INFO] Nothing to commit (files already up to date)', flush=True)
                return True  # Not an error
            print(f'   [ERROR] Commit failed: {result.stderr}', flush=True)
            return False
    except Exception as e:
        print(f'   [ERROR] Git commit error: {e}', flush=True)
        return False

def git_pull():
    """Pull latest changes from remote repository"""
    try:
        print(f'   [INFO] Pulling latest changes from remote...', flush=True)
        result = subprocess.run(
            ['git', 'pull', '--no-edit', '--no-rebase'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            if 'Already up to date' in result.stdout or 'Already up to date' in result.stderr:
                print(f'   [INFO] Repository already up to date', flush=True)
            else:
                print(f'   [OK] Pulled latest changes from remote', flush=True)
            return True
        else:
            print(f'   [WARN] Pull failed: {result.stderr}', flush=True)
            return True  # Continue anyway
    except Exception as e:
        print(f'   [WARN] Git pull error: {e}', flush=True)
        return True  # Continue anyway

def git_push():
    """Push to remote repository (with pull first to sync)"""
    try:
        # First, pull to sync with remote
        git_pull()
        
        # Now try to push
        result = subprocess.run(
            ['git', 'push'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            print(f'   [OK] Pushed to remote repository', flush=True)
            return True
        else:
            # If push still fails, try pull again and retry
            if 'non-fast-forward' in result.stderr or 'rejected' in result.stderr:
                print(f'   [INFO] Push rejected, pulling again and retrying...', flush=True)
                git_pull()
                # Retry push
                retry_result = subprocess.run(
                    ['git', 'push'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                if retry_result.returncode == 0:
                    print(f'   [OK] Pushed to remote repository (after retry)', flush=True)
                    return True
                else:
                    print(f'   [ERROR] Push failed after retry: {retry_result.stderr}', flush=True)
                    return False
            else:
                print(f'   [ERROR] Push failed: {result.stderr}', flush=True)
                return False
    except Exception as e:
        print(f'   [ERROR] Git push error: {e}', flush=True)
        return False

def commit_and_push_worldcup_data():
    """Commit and push World Cup data files (both Viagogo and FTN) - with pull first to sync"""
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [ACTION] Committing and pushing World Cup data (Viagogo + FTN)...', flush=True)
    
    # Pull first to sync with remote
    print(f'   [INFO] Syncing with remote repository...', flush=True)
    git_pull()
    
    # Files to commit
    files_to_commit = []
    
    # Add Viagogo file if it exists
    if os.path.exists(PRICES_VIAGOGO_FILE):
        files_to_commit.append(PRICES_VIAGOGO_FILE)
    
    # Add FTN file if it exists
    if os.path.exists(PRICES_FTN_FILE):
        files_to_commit.append(PRICES_FTN_FILE)
    
    # Also check for game list files if they exist
    if os.path.exists('all_games_to_scrape.json'):
        files_to_commit.append('all_games_to_scrape.json')
    if os.path.exists('all_games_ftn_to_scrape.json'):
        files_to_commit.append('all_games_ftn_to_scrape.json')
    
    # Check if files exist
    existing_files = []
    for file in files_to_commit:
        if os.path.exists(file):
            existing_files.append(file)
            print(f'   [INFO] Found file: {file}', flush=True)
        else:
            print(f'   [WARN] File not found: {file}', flush=True)
    
    if not existing_files:
        print(f'   [ERROR] No files found to commit', flush=True)
        return False
    
    # Add files
    print(f'   [INFO] Adding files to git...', flush=True)
    if not git_add_files(existing_files):
        print(f'   [ERROR] Failed to add files to git', flush=True)
        return False
    
    # Create commit message with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Auto-update World Cup prices (Viagogo + FTN) - {timestamp}"
    
    # Commit
    print(f'   [INFO] Committing changes...', flush=True)
    if not git_commit(commit_message):
        print(f'   [ERROR] Commit failed', flush=True)
        return False
    
    # Push (which will also pull again before pushing)
    print(f'   [INFO] Pushing to remote...', flush=True)
    if not git_push():
        print(f'   [ERROR] Push failed', flush=True)
        return False
    
    print(f'[{datetime.now().strftime("%H:%M:%S")}] [OK] Successfully committed and pushed World Cup data', flush=True)
    return True

# ==========================================
# Scraper Functions
# ==========================================
def run_scraper(script_name, scraper_name):
    """Run a scraper script"""
    try:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ACTION] Starting {scraper_name} scraper...', flush=True)
        
        process = subprocess.Popen(
            [PYTHON_CMD, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace',
            cwd=os.getcwd()
        )
        
        # Stream output line by line
        try:
            for line in process.stdout:
                if line:
                    print(line.rstrip(), flush=True)
        except Exception as stream_err:
            print(f'   [WARN] Output streaming error: {stream_err}', flush=True)
        
        process.wait(timeout=None)
        
        if process.returncode == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [OK] {scraper_name} scraper finished.', flush=True)
            return True
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] {scraper_name} scraper exited with code {process.returncode}', flush=True)
            return False
    except subprocess.TimeoutExpired:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [WARN] {scraper_name} scraper process timeout', flush=True)
        if 'process' in locals():
            process.kill()
        return False
    except Exception as e:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] {scraper_name} scraper error: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return False

def run_worldcup_scrapers():
    """Run both Viagogo and FTN World Cup scrapers"""
    results = {}
    
    # Run Viagogo scraper
    print(f'\n{"="*60}', flush=True)
    print(f'[{datetime.now().strftime("%H:%M:%S")}] [1/2] Running Viagogo World Cup scraper...', flush=True)
    print(f'{"="*60}', flush=True)
    results['viagogo'] = run_scraper('scraper_viagogo.py', 'Viagogo')
    
    # Wait between scrapers
    if results['viagogo']:
        print(f'\n   [INFO] Waiting 5 seconds before next scraper...', flush=True)
        time.sleep(5)
    
    # Run FTN scraper
    print(f'\n{"="*60}', flush=True)
    print(f'[{datetime.now().strftime("%H:%M:%S")}] [2/2] Running FTN World Cup scraper...', flush=True)
    print(f'{"="*60}', flush=True)
    results['ftn'] = run_scraper('scraper_ftn.py', 'FTN')
    
    return results

# ==========================================
# Main Loop
# ==========================================
def run_cycle():
    """Run one complete cycle: scrape both Viagogo and FTN -> commit -> push"""
    print(f'\n{"="*60}', flush=True)
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [START] STARTING WORLD CUP SCRAPERS (Viagogo + FTN)...', flush=True)
    print(f'{"="*60}\n', flush=True)
    
    results = run_worldcup_scrapers()
    
    # Summary
    print(f'\n{"="*60}', flush=True)
    print(f'[{datetime.now().strftime("%H:%M:%S")}] [SUMMARY] Scraping Results:', flush=True)
    print(f'{"="*60}', flush=True)
    for scraper_name, success in results.items():
        status = 'SUCCESS' if success else 'FAILED'
        print(f'   {scraper_name}: {status}', flush=True)
    print(f'{"="*60}', flush=True)
    
    # Commit and push
    print(f'\n{"="*60}', flush=True)
    commit_and_push_worldcup_data()
    print(f'{"="*60}\n', flush=True)
    
    all_success = all(results.values())
    if all_success:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [OK] World Cup scrapers completed successfully', flush=True)
    else:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [WARN] Some World Cup scrapers had errors, but data was still pushed', flush=True)
    
    return all_success

def main():
    """Main entry point"""
    print(f'\n{"="*60}', flush=True)
    print(f'[START] AUTO SCRAPER - WORLD CUP PRICE MONITORING & AUTO COMMIT (Viagogo + FTN)', flush=True)
    print(f'[INTERVAL] Running every {SCRAPE_INTERVAL_HOURS} hours', flush=True)
    print(f'[FILES] {PRICES_VIAGOGO_FILE}, {PRICES_FTN_FILE}', flush=True)
    print(f'{"="*60}\n', flush=True)
    
    # Run immediately on start
    run_cycle()
    
    # Then run on interval
    while True:
        wait_seconds = SCRAPE_INTERVAL_HOURS * 3600
        next_run = datetime.now().timestamp() + wait_seconds
        next_run_str = datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S")
        print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [WAIT] Next run in {SCRAPE_INTERVAL_HOURS} hours ({next_run_str})', flush=True)
        time.sleep(wait_seconds)
        run_cycle()

if __name__ == '__main__':
    # Check if running as one-time or continuous
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once and exit
        run_cycle()
    else:
        # Run continuously
        main()

