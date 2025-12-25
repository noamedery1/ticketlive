# Windows 7 Setup Guide

This guide will help you set up and run the ticket price scraper on Windows 7.

## ⚠️ Important: Python Version

**Windows 7 only supports Python 3.7.9 or earlier.** Python 3.8+ requires Windows 8.1 or later.

## 📥 Step 1: Install Python 3.7.9

1. **Download Python 3.7.9:**
   - Go to: https://www.python.org/downloads/release/python-379/
   - Download: `Windows x86-64 executable installer` (or x86 if you have 32-bit Windows)

2. **Install Python:**
   - Run the installer
   - ✅ **IMPORTANT:** Check "Add Python 3.7 to PATH"
   - Click "Install Now"
   - Wait for installation to complete

3. **Verify Installation:**
   ```cmd
   py --version
   ```
   Should show: `Python 3.7.9`

## 📦 Step 2: Install Required Packages

1. **Open Command Prompt** (cmd.exe) as Administrator

2. **Navigate to project folder:**
   ```cmd
   cd D:\noamdev\tikectlive
   ```

3. **Upgrade pip first:**
   ```cmd
   py -m pip install --upgrade pip
   ```

4. **Install pip first (if not already installed):**
   ```cmd
   QUICK_INSTALL_PIP.bat
   ```
   
   Or manually:
   - Download: https://bootstrap.pypa.io/get-pip.py
   - Save to: `D:\tikcetLive\get-pip.py`
   - Run: `py get-pip.py --no-warn-script-location --user`

5. **Install packages using Windows 7 compatible requirements:**
   ```cmd
   py -m pip install --no-warn-script-location -r requirements_win7.txt
   ```

   If you get errors, try installing individually:
   ```cmd
   py -m pip install undetected-chromedriver==3.5.4
   py -m pip install selenium==4.15.2
   py -m pip install requests==2.31.0
   ```

## 🌐 Step 3: Chrome Browser

1. **Install Google Chrome** (if not already installed)
   - Download from: https://www.google.com/chrome/
   - Install the latest version compatible with Windows 7

2. **ChromeDriver:**
   - `undetected-chromedriver` will automatically download the correct ChromeDriver version
   - No manual installation needed

## ✅ Step 4: Test the Setup

1. **Test Python:**
   ```cmd
   py --version
   ```

2. **Test imports:**
   ```cmd
   py -c "import undetected_chromedriver; import selenium; import requests; print('All packages installed successfully!')"
   ```

3. **Test scraper (optional):**
   ```cmd
   py scraper_viagogo.py
   ```

## 🚀 Step 5: Run Auto Scraper

Once everything is set up, run:

```cmd
py auto_scraper.py
```

This will:
- Run both scrapers in parallel
- Save prices to `prices.json` and `prices_ftn.json`
- Automatically commit and push to Git
- Wait 2 hours and repeat

## 🔧 Troubleshooting

### Issue: "python is not recognized"
**Solution:** Use `py` instead of `python`:
```cmd
py auto_scraper.py
```

### Issue: "No module named pip"
**Solution:** Install pip:
```cmd
py -m ensurepip --default-pip
py -m pip install --upgrade pip
```

### Issue: "WinError 32" or "WinError 183" (file lock)
**Solution:** This is normal when running scrapers in parallel. The scripts have retry logic built-in. If it persists:
- Close any Chrome browsers
- Wait a few seconds
- Try again

### Issue: Package installation fails
**Solution:** Try installing with `--no-cache-dir`:
```cmd
py -m pip install --no-cache-dir -r requirements_win7.txt
```

### Issue: Chrome/ChromeDriver compatibility
**Solution:** Make sure Chrome is up to date. `undetected-chromedriver` should handle driver compatibility automatically.

## 📝 Notes

- **Python 3.7.9** is the last version that supports Windows 7
- All scripts are compatible with Python 3.7.9
- The `auto_scraper.py` script automatically detects `py` or `python` command
- All scripts include Windows 7 encoding fixes

## 🔄 Updating

If you need to update packages later:
```cmd
py -m pip install --upgrade undetected-chromedriver selenium requests
```

**Note:** Be careful with updates - newer versions might not support Python 3.7.9 or Windows 7.

