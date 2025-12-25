@echo off
echo ============================================================
echo FIX CHROMEDRIVER - ARCHITECTURE MISMATCH
echo ============================================================
echo.

REM Activate virtual environment
set VENV_DIR=C:\PythonEnvs\ticketlive
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo [1/4] Detecting system architecture...
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    echo [OK] System is 64-bit
    set ARCH=64
) else if "%PROCESSOR_ARCHITECTURE%"=="x86" (
    echo [OK] System is 32-bit
    set ARCH=32
) else (
    echo [WARNING] Could not detect architecture, assuming 64-bit
    set ARCH=64
)
echo.

echo [2/4] Checking Chrome installation...
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    echo [INFO] Found 32-bit Chrome in Program Files (x86)
    set CHROME_ARCH=32
) else if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    echo [INFO] Found 64-bit Chrome in Program Files
    set CHROME_ARCH=64
) else (
    echo [WARNING] Chrome not found in standard locations
    set CHROME_ARCH=64
)
echo.

echo [3/4] Clearing ChromeDriver cache...
python -c "import os, shutil; cache_dirs = [os.path.join(os.path.expanduser('~'), '.undetected_chromedriver'), os.path.join(os.getenv('LOCALAPPDATA', ''), 'undetected_chromedriver')]; [shutil.rmtree(d, ignore_errors=True) for d in cache_dirs]; print('Cache cleared')" 2>nul
echo [OK] Cache cleared
echo.

echo [4/4] Reinstalling undetected-chromedriver with correct settings...
pip uninstall -y undetected-chromedriver
pip install undetected-chromedriver==3.5.4 --no-cache-dir

if errorlevel 1 (
    echo [ERROR] Failed to reinstall
    pause
    exit /b 1
)

echo.
echo Testing ChromeDriver with explicit architecture handling...
echo.

REM Test with use_subprocess=False and explicit browser path
python -c "import undetected_chromedriver as uc; import os; chrome_path = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe' if os.path.exists(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe') else None; print(f'Chrome path: {chrome_path}'); driver = uc.Chrome(version_main=None, browser_executable_path=chrome_path, use_subprocess=False); print('SUCCESS!'); driver.quit()"

if errorlevel 1 (
    echo.
    echo [ERROR] Still failing. Trying alternative approach...
    echo.
    echo The issue might be that ChromeDriver needs to match Chrome's architecture.
    echo.
    echo SOLUTION: Manually download ChromeDriver
    echo 1. Check Chrome version: chrome://version
    echo 2. Download matching ChromeDriver from: https://chromedriver.chromium.org/downloads
    echo 3. Extract chromedriver.exe to: C:\PythonEnvs\ticketlive\Scripts\
    echo 4. Update scrapers to use: driver_executable_path=r'C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe'
    echo.
) else (
    echo.
    echo ============================================================
    echo SUCCESS! ChromeDriver is working
    echo ============================================================
)

echo.
pause

