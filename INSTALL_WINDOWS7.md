# Installation Guide for Windows 7

## Step 1: Install Python 3.7

1. Download Python 3.7.9 (last version compatible with Windows 7):
   - **64-bit**: https://www.python.org/downloads/release/python-379/
   - Choose: "Windows x86-64 executable installer"

2. Run the installer:
   - ✅ **IMPORTANT**: Check "Add Python 3.7 to PATH"
   - Click "Install Now"

3. Verify installation:
   ```cmd
   python --version
   ```
   Should show: `Python 3.7.9`

## Step 2: Install Required Packages

### Option A: Automatic Setup (Recommended)

1. Double-click `setup_windows7.bat`
2. Wait for installation to complete
3. Done!

### Option B: Manual Installation

Open Command Prompt and run:

```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Or install individually:

```cmd
python -m pip install undetected-chromedriver selenium requests
```

## Step 3: Verify Installation

Test if packages are installed:

```cmd
python -c "import undetected_chromedriver; print('OK')"
python -c "import selenium; print('OK')"
python -c "import requests; print('OK')"
```

## Step 4: Run the Scraper

```cmd
python auto_scraper.py
```

## Troubleshooting

### Error: "python is not recognized"
- Python is not in PATH
- Reinstall Python and check "Add Python to PATH"
- Or use full path: `C:\Python37\python.exe`

### Error: "pip is not recognized"
- Run: `python -m pip install --upgrade pip`

### Error: "ModuleNotFoundError"
- Run: `python -m pip install -r requirements.txt`

### Error: "SSL Certificate" or "Connection" errors
- Your Windows 7 might need security updates
- Try: `python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`

## Required Files

Make sure these files exist:
- `auto_scraper.py`
- `scraper_ftn.py`
- `scraper_viagogo.py`
- `all_games_to_scrape.json`
- `all_games_ftn_to_scrape.json`
- `requirements.txt`

## Notes

- Windows 7 and Python 3.7 are end-of-life (no security updates)
- For better security, consider upgrading to Windows 10/11 and Python 3.11+
- The scraper needs Chrome browser installed on your system

