# Manual Pip Installation for Windows 7 (Special Username Fix)

If your username contains special characters like `$` (e.g., `MSSQL$TIBASQL`), the automatic pip installation may fail.

## Quick Fix: Use INSTALL_PIP_WIN7.bat

1. **Run the special pip installer:**
   ```cmd
   INSTALL_PIP_WIN7.bat
   ```

2. **Then run the main setup:**
   ```cmd
   SETUP_WIN7.bat
   ```

## Alternative: Manual Installation

If the batch script doesn't work, follow these steps:

### Step 1: Download get-pip.py (Python 3.7 version)

1. Open your web browser
2. Go to: **https://bootstrap.pypa.io/pip/3.7/get-pip.py** (⚠️ Important: Use the 3.7 version!)
3. Right-click and "Save As..."
4. Save it in your project folder: `D:\tikcetLive\get-pip.py`

### Step 2: Install pip

Open Command Prompt and run:

```cmd
cd D:\tikcetLive
py get-pip.py --no-warn-script-location
```

### Step 3: Verify pip

```cmd
py -m pip --version
```

Should show something like: `pip 20.1.1 from ...`

### Step 4: Install packages

```cmd
py -m pip install --no-warn-script-location undetected-chromedriver==3.5.4
py -m pip install --no-warn-script-location selenium==4.15.2
py -m pip install --no-warn-script-location requests==2.31.0
```

Or use the requirements file:

```cmd
py -m pip install --no-warn-script-location -r requirements_win7.txt
```

## Why This Happens

The `$` character in your username (`MSSQL$TIBASQL`) causes Python's `distutils` to try to expand it as an environment variable, which fails. The `--no-warn-script-location` flag and using `get-pip.py` directly avoids this issue.

## Troubleshooting

### Issue: "py: command not found"
**Solution:** Use the full path:
```cmd
C:\Users\MSSQL$TIBASQL\AppData\Local\Programs\Python\Python37\python.exe get-pip.py
```

### Issue: "Permission denied"
**Solution:** Run Command Prompt as Administrator

### Issue: Still getting errors
**Solution:** Try installing with `--user` flag:
```cmd
py get-pip.py --user
py -m pip install --user --no-warn-script-location -r requirements_win7.txt
```

