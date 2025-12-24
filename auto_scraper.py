import subprocess
import time
import os
import sys
import shutil
from datetime import datetime
import json
import threading

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
PRICES_FTN_FILE = 'prices_ftn.json'
PRICES_VIAGOGO_FILE = 'prices.json'

# ==========================================
# Scraper Functions
# ==========================================
def run_scraper_ftn_thread(result_dict):
    """Run FTN scraper in a thread"""
    try:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ACTION] Starting FTN Scraper...', flush=True)
        # Use Popen to stream output in real-time and better error handling
        process = subprocess.Popen(
            [PYTHON_CMD, 'scraper_ftn.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace',
            cwd=os.getcwd()  # Ensure correct working directory
        )
        # Stream output line by line
        try:
            for line in process.stdout:
                if line:
                    print(line.rstrip(), flush=True)
        except Exception as stream_err:
            print(f'   [WARN] Output streaming error: {stream_err}', flush=True)
        
        process.wait(timeout=None)  # Wait indefinitely for process to complete
        if process.returncode == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [OK] FTN Scraper finished.', flush=True)
            result_dict['ftn'] = True
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] FTN Scraper exited with code {process.returncode}', flush=True)
            result_dict['ftn'] = False
    except subprocess.TimeoutExpired:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [WARN] FTN Scraper process timeout', flush=True)
        if 'process' in locals():
            process.kill()
        result_dict['ftn'] = False
    except Exception as e:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] FTN Scraper Error: {e}', flush=True)
        import traceback
        traceback.print_exc()
        result_dict['ftn'] = False

def run_scraper_viagogo_thread(result_dict):
    """Run Viagogo scraper in a thread"""
    try:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ACTION] Starting Viagogo Scraper...', flush=True)
        # Use Popen to stream output in real-time and better error handling
        process = subprocess.Popen(
            [PYTHON_CMD, 'scraper_viagogo.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding='utf-8',
            errors='replace',
            cwd=os.getcwd()  # Ensure correct working directory
        )
        # Stream output line by line
        try:
            for line in process.stdout:
                if line:
                    print(line.rstrip(), flush=True)
        except Exception as stream_err:
            print(f'   [WARN] Output streaming error: {stream_err}', flush=True)
        
        process.wait(timeout=None)  # Wait indefinitely for process to complete
        if process.returncode == 0:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [OK] Viagogo Scraper finished.', flush=True)
            result_dict['viagogo'] = True
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] Viagogo Scraper exited with code {process.returncode}', flush=True)
            result_dict['viagogo'] = False
    except subprocess.TimeoutExpired:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [WARN] Viagogo Scraper process timeout', flush=True)
        if 'process' in locals():
            process.kill()
        result_dict['viagogo'] = False
    except Exception as e:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] Viagogo Scraper Error: {e}', flush=True)
        import traceback
        traceback.print_exc()
        result_dict['viagogo'] = False

# ==========================================
# Git Functions
# ==========================================
def git_add_files(files):
    """Add files to git staging"""
    try:
        added_count = 0
        for file in files:
            if os.path.exists(file):
                result = subprocess.run(
                    ['git', 'add', file],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                if result.returncode == 0:
                    print(f'   [OK] Added {file} to git', flush=True)
                    added_count += 1
                else:
                    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                    print(f'   [WARN] Failed to add {file}: {error_msg}', flush=True)
            else:
                print(f'   [WARN] File {file} does not exist, skipping', flush=True)
        
        if added_count == 0:
            print(f'   [WARN] No files were added to git', flush=True)
            return False
        
        return True
    except Exception as e:
        print(f'   [ERROR] Git add error: {e}', flush=True)
        import traceback
        traceback.print_exc()
        return False

def git_commit(message):
    """Commit changes"""
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
            # Check if there are no changes to commit
            if 'nothing to commit' in result.stdout.lower() or 'nothing to commit' in result.stderr.lower():
                print(f'   [INFO] No changes to commit', flush=True)
                return True
            print(f'   [ERROR] Commit failed: {result.stderr}', flush=True)
            return False
    except Exception as e:
        print(f'   [ERROR] Git commit error: {e}', flush=True)
        return False

def git_push():
    """Push to remote repository"""
    try:
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
            print(f'   [ERROR] Push failed: {result.stderr}', flush=True)
            return False
    except Exception as e:
        print(f'   [ERROR] Git push error: {e}', flush=True)
        return False

def commit_and_push_prices():
    """Commit and push price files"""
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [ACTION] Committing and pushing price files...', flush=True)
    
    # Files to commit
    price_files = [PRICES_FTN_FILE, PRICES_VIAGOGO_FILE]
    
    # Check if files exist
    files_to_commit = []
    for file in price_files:
        if os.path.exists(file):
            files_to_commit.append(file)
            print(f'   [INFO] Found file: {file}', flush=True)
        else:
            print(f'   [WARN] File not found: {file}', flush=True)
    
    if not files_to_commit:
        print(f'   [ERROR] No price files found to commit', flush=True)
        return False
    
    # Check git status before adding
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'] + files_to_commit,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.stdout.strip():
            print(f'   [INFO] Files have changes: {result.stdout.strip()}', flush=True)
        else:
            print(f'   [INFO] Checking if files are untracked...', flush=True)
    except:
        pass
    
    # Add files
    print(f'   [INFO] Adding files to git...', flush=True)
    if not git_add_files(files_to_commit):
        print(f'   [ERROR] Failed to add files to git', flush=True)
        return False
    
    # Verify files were added
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'] + files_to_commit,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        staged_files = [line for line in result.stdout.strip().split('\n') if line.startswith('A ') or line.startswith('M ')]
        if staged_files:
            print(f'   [OK] {len(staged_files)} file(s) staged for commit', flush=True)
        else:
            print(f'   [WARN] No files staged - they may already be committed', flush=True)
    except:
        pass
    
    # Create commit message with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_message = f"Auto-update prices - {timestamp}"
    
    # Commit
    print(f'   [INFO] Committing changes...', flush=True)
    if not git_commit(commit_message):
        print(f'   [ERROR] Commit failed', flush=True)
        return False
    
    # Push
    print(f'   [INFO] Pushing to remote...', flush=True)
    if not git_push():
        print(f'   [ERROR] Push failed', flush=True)
        return False
    
    print(f'[{datetime.now().strftime("%H:%M:%S")}] [OK] Successfully committed and pushed price files', flush=True)
    return True

# ==========================================
# Main Loop
# ==========================================
def run_cycle():
    """Run one complete cycle: scrape -> commit -> push"""
    cycle_start = time.time()
    print(f'\n{"="*60}', flush=True)
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] [START] STARTING PARALLEL SCRAPERS...', flush=True)
    print(f'{"="*60}\n', flush=True)
    
    # Verify scraper files exist
    if not os.path.exists('scraper_ftn.py'):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] scraper_ftn.py not found!', flush=True)
        return
    if not os.path.exists('scraper_viagogo.py'):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [ERROR] scraper_viagogo.py not found!', flush=True)
        return
    
    # Shared result dictionary for thread communication
    results = {'ftn': None, 'viagogo': None}
    
    # Launch both scrapers in parallel using threads
    ftn_thread = threading.Thread(target=run_scraper_ftn_thread, args=(results,), daemon=False)
    viagogo_thread = threading.Thread(target=run_scraper_viagogo_thread, args=(results,), daemon=False)
    
    ftn_thread.start()
    viagogo_thread.start()
    
    # Wait for both to complete
    ftn_thread.join()
    viagogo_thread.join()
    
    ftn_success = results.get('ftn', False)
    viagogo_success = results.get('viagogo', False)
    
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [INFO] Scraper results - FTN: {ftn_success}, Viagogo: {viagogo_success}', flush=True)
    
    # Check if at least one scraper succeeded
    if ftn_success is None and viagogo_success is None:
        print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [ERROR] Both scrapers did not complete.', flush=True)
        # Still try to commit if files exist (they might have been partially updated)
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [INFO] Checking for price files to commit anyway...', flush=True)
    elif not ftn_success and not viagogo_success:
        print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [ERROR] Both scrapers failed.', flush=True)
        # Still try to commit if files exist (they might have been partially updated)
        print(f'[{datetime.now().strftime("%H:%M:%S")}] [INFO] Checking for price files to commit anyway...', flush=True)
    else:
        print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [OK] At least one scraper succeeded.', flush=True)
    
    # Always try to commit and push if price files exist (they might have been updated even if scraper reported failure)
    commit_and_push_prices()
    
    cycle_time = time.time() - cycle_start
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [DONE] CYCLE COMPLETE (runtime: {int(cycle_time)}s)', flush=True)
    print(f'{"="*60}\n', flush=True)

def main():
    """Main loop - run cycles continuously"""
    print(f'\n{"="*60}')
    print(f'  [START] AUTO SCRAPER - PRICE MONITORING & AUTO COMMIT')
    print(f'  [INTERVAL] Running every {SCRAPE_INTERVAL_HOURS} hours')
    print(f'  [FILES] {PRICES_FTN_FILE}, {PRICES_VIAGOGO_FILE}')
    print(f'{"="*60}\n')
    
    # Run first cycle immediately
    run_cycle()
    
    # Then run on interval
    while True:
        try:
            wait_seconds = SCRAPE_INTERVAL_HOURS * 3600
            wait_hours = SCRAPE_INTERVAL_HOURS
            next_run = datetime.now().timestamp() + wait_seconds
            next_run_str = datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S")
            
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [WAIT] Next run in {wait_hours} hours ({next_run_str})', flush=True)
            time.sleep(wait_seconds)
            
            run_cycle()
            
        except KeyboardInterrupt:
            print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [STOP] Interrupted by user. Exiting...', flush=True)
            break
        except Exception as e:
            print(f'\n[{datetime.now().strftime("%H:%M:%S")}] [ERROR] Unexpected error: {e}', flush=True)
            import traceback
            traceback.print_exc()
            # Wait a bit before retrying
            print(f'[{datetime.now().strftime("%H:%M:%S")}] [WAIT] Waiting 5 minutes before retry...', flush=True)
            time.sleep(300)

if __name__ == '__main__':
    main()

