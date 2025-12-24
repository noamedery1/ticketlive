@echo off
echo Testing Python installation...
echo.

REM Try py first (Windows Python launcher)
where py >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Found: py
    py --version
    echo.
    echo Testing package imports...
    py -c "import sys; print('Python version:', sys.version)"
    py -c "import undetected_chromedriver; print('[OK] undetected_chromedriver')" 2>nul || echo [MISSING] undetected_chromedriver
    py -c "import selenium; print('[OK] selenium')" 2>nul || echo [MISSING] selenium
    py -c "import requests; print('[OK] requests')" 2>nul || echo [MISSING] requests
    echo.
    echo Use this command to run scripts: py auto_scraper.py
) else (
    echo [ERROR] 'py' command not found
    echo.
    REM Try python
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Found: python
        python --version
        echo.
        echo Use this command to run scripts: python auto_scraper.py
    ) else (
        echo [ERROR] Python not found!
        echo.
        echo Please install Python from python.org
        echo Make sure to check "Add Python to PATH"
    )
)

echo.
pause

