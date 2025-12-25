@echo off
echo ============================================================
echo WINDOWS 7 SETUP - Ticket Price Scraper
echo ============================================================
echo.

REM Check Python version
echo [1/5] Checking Python installation...
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Please install Python 3.7.9 first:
    echo https://www.python.org/downloads/release/python-379/
    echo.
    echo Make sure to check "Add Python 3.7 to PATH" during installation!
    pause
    exit /b 1
)

echo [OK] Python found:
py --version
echo.

REM Check if Python 3.7.x
for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %PYTHON_VERSION% | findstr /R "^3\.7\." >nul
if errorlevel 1 (
    echo [WARNING] Python 3.7.x recommended for Windows 7
    echo Current version: %PYTHON_VERSION%
    echo.
    echo Python 3.8+ may not work properly on Windows 7!
    echo.
    pause
)

echo [2/5] Checking pip...
py -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] pip not found!
    echo.
    echo Please run INSTALL_PIP_WIN7.bat first to install pip.
    echo This is needed for usernames with special characters like $.
    echo.
    pause
    exit /b 1
)

echo [OK] pip found
py -m pip --version

echo Upgrading pip...
py -m pip install --upgrade pip --no-warn-script-location --quiet
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip, but continuing...
)
echo [OK] pip ready
echo.

echo [3/5] Installing required packages...
echo This may take a few minutes...
echo.

if exist requirements_win7.txt (
    py -m pip install -r requirements_win7.txt --no-warn-script-location
) else (
    echo [WARNING] requirements_win7.txt not found, using requirements.txt
    py -m pip install -r requirements.txt --no-warn-script-location
)

if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed!
    echo.
    echo Try installing manually:
    echo   py -m pip install undetected-chromedriver==3.5.4
    echo   py -m pip install selenium==4.15.2
    echo   py -m pip install requests==2.31.0
    pause
    exit /b 1
)

echo.
echo [OK] Packages installed
echo.

echo [4/5] Verifying installation...
py -c "import undetected_chromedriver; import selenium; import requests; print('All packages OK!')" 2>nul
if errorlevel 1 (
    echo [WARNING] Some packages may not be installed correctly
    echo Try running the verification manually:
    echo   py -c "import undetected_chromedriver; import selenium; import requests; print('OK')"
) else (
    echo [OK] All packages verified
)
echo.

echo [5/5] Setup complete!
echo.
echo ============================================================
echo You can now run:
echo   py auto_scraper.py
echo ============================================================
echo.
pause

