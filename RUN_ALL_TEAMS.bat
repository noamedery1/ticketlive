@echo off
echo ============================================================
echo RUN ALL TEAMS SCRAPER - FootballTicketNet
echo ============================================================
echo.

REM Check Python (Windows 7 compatible)
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found!
        echo Please install Python 3.7.9 first.
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

REM Check if virtual environment exists
if exist "C:\PythonEnvs\ticketlive\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call C:\PythonEnvs\ticketlive\Scripts\activate.bat
    set PYTHON_CMD=python
) else (
    echo [INFO] No virtual environment found, using system Python...
)

echo.
echo [START] Running all teams from *_prices.json files...
echo.

REM Run once (not continuous loop)
%PYTHON_CMD% auto_scraper_teams.py --once

if errorlevel 1 (
    echo.
    echo [ERROR] Scraper failed with error code: %ERRORLEVEL%
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [DONE] All teams scraper finished!
echo ============================================================
pause

