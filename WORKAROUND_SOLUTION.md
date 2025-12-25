# Workaround for Username with $ Character

The issue is that your username contains `$` (`MSSQL$TIBASQL`), which causes Python's distutils to fail when trying to expand environment variables in paths.

## ⚠️ Root Cause

Python's distutils tries to expand `$TIBASQL` as an environment variable in the path `C:\Users\MSSQL$TIBASQL\...`, which fails.

## ✅ Solutions (in order of preference)

### Solution 1: Install Python to a Different Location (RECOMMENDED)

**Best long-term solution** - Install Python to a path without `$`:

1. **Uninstall current Python** (optional, or install alongside)
2. **Download Python 3.7.9 installer**
3. **During installation**, choose "Customize installation"
4. **Set installation path to**: `C:\Python37` (or any path without `$`)
5. **Check "Add Python to PATH"**
6. **Install**
7. **Then run**: `INSTALL_PIP_SIMPLE.bat`

### Solution 2: Use Portable Python

1. Download **Portable Python 3.7.9**:
   - Search for "Python 3.7.9 portable" or "WinPython 3.7.9"
   - Extract to: `C:\Python37` (or any path without `$`)
2. Add to PATH: `C:\Python37; C:\Python37\Scripts`
3. Then install pip normally

### Solution 3: Manual pip Installation with Custom Path

If you must keep Python in the current location:

1. **Create a custom user directory** (without `$` in path):
   ```cmd
   mkdir C:\PythonPackages
   ```

2. **Set environment variable**:
   ```cmd
   set PYTHONUSERBASE=C:\PythonPackages
   ```

3. **Install pip**:
   ```cmd
   py get-pip.py --prefix=C:\PythonPackages --no-warn-script-location
   ```

4. **Add to PATH**:
   ```cmd
   set PATH=%PATH%;C:\PythonPackages\Scripts
   ```

5. **Use pip**:
   ```cmd
   C:\PythonPackages\Scripts\pip.exe install package_name
   ```

### Solution 4: Use Virtual Environment (Workaround)

Create a virtual environment in a path without `$`:

1. **Create venv in a safe location**:
   ```cmd
   mkdir C:\PythonEnvs
   py -m venv C:\PythonEnvs\ticketlive
   ```

2. **Activate it**:
   ```cmd
   C:\PythonEnvs\ticketlive\Scripts\activate.bat
   ```

3. **Install pip in venv** (should work):
   ```cmd
   python get-pip.py
   ```

4. **Install packages**:
   ```cmd
   pip install -r requirements_win7.txt
   ```

5. **Run scripts from venv**:
   ```cmd
   python auto_scraper.py
   ```

## 🎯 Recommended Action

**I strongly recommend Solution 1** - reinstalling Python to `C:\Python37` or similar. This will:
- ✅ Fix the pip installation issue permanently
- ✅ Avoid future path-related problems
- ✅ Make your Python environment more stable
- ✅ Take only 5-10 minutes

## Quick Test After Fix

Once pip is installed, verify:
```cmd
py -m pip --version
```

Then install packages:
```cmd
py -m pip install --no-warn-script-location -r requirements_win7.txt
```

