@echo off
echo ============================================================
echo FIX CHROMEDRIVER ISSUE
echo ============================================================
echo.

REM Activate virtual environment
set VENV_DIR=C:\PythonEnvs\ticketlive
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo Please run SETUP_VENV.bat first
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo [1/3] Clearing ChromeDriver cache...
REM Clear undetected-chromedriver cache
python -c "import os; import shutil; cache_dir = os.path.join(os.path.expanduser('~'), '.undetected_chromedriver'); print(f'Cache: {cache_dir}'); shutil.rmtree(cache_dir, ignore_errors=True); print('Cache cleared')" 2>nul
if errorlevel 1 (
    echo [WARNING] Could not clear cache automatically
    echo.
    echo Please manually delete:
    echo   %USERPROFILE%\.undetected_chromedriver
)

REM Also try clearing from AppData
python -c "import os; import shutil; cache_dir = os.path.join(os.getenv('LOCALAPPDATA', ''), 'undetected_chromedriver'); print(f'Cache: {cache_dir}'); shutil.rmtree(cache_dir, ignore_errors=True); print('Cache cleared')" 2>nul

echo [OK] Cache cleared
echo.

echo [2/3] Checking Chrome installation...
where chrome >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Chrome not found in PATH
    echo.
    echo Please make sure Google Chrome is installed
    echo Download from: https://www.google.com/chrome/
) else (
    echo [OK] Chrome found
    where chrome
)
echo.

echo [3/3] Testing ChromeDriver download...
echo This will download the correct ChromeDriver for your system...
echo.

python -c "import undetected_chromedriver as uc; import os; print('Testing ChromeDriver...'); driver = uc.Chrome(version_main=None, use_subprocess=False); print('SUCCESS! ChromeDriver works'); driver.quit()"

if errorlevel 1 (
    echo.
    echo [ERROR] ChromeDriver test failed
    echo.
    echo Possible solutions:
    echo 1. Make sure Chrome is installed and up to date
    echo 2. Check if you have 32-bit or 64-bit Windows
    echo 3. Try reinstalling undetected-chromedriver:
    echo    pip uninstall undetected-chromedriver
    echo    pip install undetected-chromedriver==3.5.4
    echo.
) else (
    echo.
    echo ============================================================
    echo SUCCESS! ChromeDriver is working
    echo You can now run: RUN_IN_VENV.bat
    echo ============================================================
)

echo.
pause

