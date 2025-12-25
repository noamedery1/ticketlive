"""
Download correct 32-bit ChromeDriver for Windows 7
"""
import urllib.request
import json
import zipfile
import os
import shutil
import sys

def get_chrome_version():
    """Get Chrome version from command line, registry, or user"""
    # Check command line argument
    if len(sys.argv) > 1:
        return sys.argv[1]
    
    # Try registry first
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        return version
    except:
        pass
    
    # Ask user
    print("Please enter your Chrome version:")
    print("  1. Open Chrome")
    print("  2. Go to: chrome://version")
    print("  3. Note the version number (e.g., 109.0.5414.120)")
    version = input("\nEnter Chrome version: ").strip()
    return version

def download_chromedriver(chrome_version):
    """Download matching 32-bit ChromeDriver"""
    # Extract major version
    major_version = chrome_version.split('.')[0]
    print(f"\n[INFO] Chrome major version: {major_version}")
    
    # For older Chrome versions (like 109), use the legacy download method
    if int(major_version) < 115:
        print(f"[INFO] Using legacy ChromeDriver for version {major_version}")
        # Legacy ChromeDriver URLs (for versions < 115)
        # Try latest version for this major version first (more reliable)
        try:
            print(f"[INFO] Getting latest ChromeDriver for Chrome {major_version}...")
            list_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
            print(f"[INFO] Checking: {list_url}")
            with urllib.request.urlopen(list_url, timeout=10) as f:
                latest_version = f.read().decode('utf-8').strip()
            driver_url = f"https://chromedriver.storage.googleapis.com/{latest_version}/chromedriver_win32.zip"
            print(f"[INFO] Found version: {latest_version}")
            print(f"[INFO] Downloading: {driver_url}")
            urllib.request.urlretrieve(driver_url, 'chromedriver.zip')
            print("[OK] Download complete")
        except Exception as e:
            print(f"[WARNING] Latest version method failed: {e}")
            print(f"[INFO] Trying exact version: {chrome_version}")
            # Try exact version
            try:
                driver_url = f"https://chromedriver.storage.googleapis.com/{chrome_version}/chromedriver_win32.zip"
                print(f"[INFO] Downloading: {driver_url}")
                urllib.request.urlretrieve(driver_url, 'chromedriver.zip')
                print("[OK] Download complete")
            except Exception as e2:
                print(f"[ERROR] Exact version also failed: {e2}")
                print(f"\n[INFO] ChromeDriver for version {chrome_version} may not be available")
                print(f"[INFO] Please download manually from:")
                print(f"      https://chromedriver.chromium.org/downloads")
                print(f"      Or search for: ChromeDriver {major_version}")
                return False
    else:
        # New Chrome for Testing method (for versions >= 115)
        print(f"[INFO] Using Chrome for Testing API for version {major_version}")
        try:
            url = f"https://googlechromelabs.github.io/chrome-for-testing/LatestVersions/win32/versions.json"
            print(f"[INFO] Fetching version info from: {url}")
            with urllib.request.urlopen(url) as f:
                data = json.loads(f.read())
            latest = data['channels']['Stable']['version']
            print(f"[INFO] Latest stable: {latest}")
            driver_url = f"https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/{latest}/win32/chromedriver-win32.zip"
            print(f"[INFO] Downloading: {driver_url}")
            urllib.request.urlretrieve(driver_url, 'chromedriver.zip')
            print("[OK] Download complete")
        except Exception as e:
            print(f"[ERROR] Failed: {e}")
            return False
    
    # Extract
    print("[INFO] Extracting ChromeDriver...")
    try:
        with zipfile.ZipFile('chromedriver.zip', 'r') as zip_ref:
            zip_ref.extractall('.')
        os.remove('chromedriver.zip')
        print("[OK] Extraction complete")
    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        return False
    
    # Find chromedriver.exe
    chromedriver_exe = None
    for root, dirs, files in os.walk('.'):
        if 'chromedriver.exe' in files:
            chromedriver_exe = os.path.join(root, 'chromedriver.exe')
            break
    
    if not chromedriver_exe:
        print("[ERROR] chromedriver.exe not found in extracted files")
        return False
    
    # Move to venv Scripts
    venv_scripts = r'C:\PythonEnvs\ticketlive\Scripts'
    if not os.path.exists(venv_scripts):
        print(f"[ERROR] Virtual environment Scripts folder not found: {venv_scripts}")
        return False
    
    dst = os.path.join(venv_scripts, 'chromedriver.exe')
    print(f"[INFO] Moving ChromeDriver to: {dst}")
    try:
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(chromedriver_exe, dst)
        
        # Clean up extracted folder
        extracted_dir = os.path.dirname(chromedriver_exe)
        if extracted_dir and os.path.exists(extracted_dir) and extracted_dir != '.':
            shutil.rmtree(extracted_dir, ignore_errors=True)
        
        print(f"[OK] ChromeDriver installed to: {dst}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to move ChromeDriver: {e}")
        return False

def main():
    print("=" * 60)
    print("DOWNLOAD CHROMEDRIVER FOR WINDOWS 7")
    print("=" * 60)
    print()
    
    chrome_version = get_chrome_version()
    if not chrome_version:
        print("[ERROR] Chrome version required")
        return 1
    
    print(f"\n[INFO] Chrome version: {chrome_version}")
    
    if download_chromedriver(chrome_version):
        print("\n" + "=" * 60)
        print("SUCCESS! ChromeDriver downloaded and installed")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("FAILED! Please download manually")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())

