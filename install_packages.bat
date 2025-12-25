@echo off
echo ============================================================
echo INSTALL REQUIRED PACKAGES
echo ============================================================
echo.

REM Check if pip is available
py -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed!
    echo.
    echo Please install pip first using one of these methods:
    echo   1. INSTALL_PIP_FINAL.bat
    echo   2. Use virtual environment (see WORKAROUND_SOLUTION.md)
    echo   3. Reinstall Python to C:\Python37
    echo.
    pause
    exit /b 1
)

echo [OK] pip is available
py -m pip --version
echo.

echo [1/3] Installing undetected-chromedriver...
py -m pip install --no-warn-script-location undetected-chromedriver==3.5.4
if errorlevel 1 (
    echo [ERROR] Failed to install undetected-chromedriver
    pause
    exit /b 1
)
echo [OK] undetected-chromedriver installed
echo.

echo [2/3] Installing selenium...
py -m pip install --no-warn-script-location selenium==4.15.2
if errorlevel 1 (
    echo [ERROR] Failed to install selenium
    pause
    exit /b 1
)
echo [OK] selenium installed
echo.

echo [3/3] Installing requests...
py -m pip install --no-warn-script-location requests==2.31.0
if errorlevel 1 (
    echo [ERROR] Failed to install requests
    pause
    exit /b 1
)
echo [OK] requests installed
echo.

echo [VERIFY] Testing imports...
py -c "import undetected_chromedriver; import selenium; import requests; print('All packages OK!')"
if errorlevel 1 (
    echo [WARNING] Some packages may not be installed correctly
) else (
    echo.
    echo ============================================================
    echo SUCCESS! All packages installed
    echo You can now run: py auto_scraper.py
    echo ============================================================
)

echo.
pause
