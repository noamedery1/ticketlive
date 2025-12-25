@echo off
REM Change to the script's directory
cd /d "%~dp0"

echo ============================================================
echo RUN WORLD CUP SCRAPER - Viagogo (ONE TIME)
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
echo [START] Running World Cup scraper (Viagogo) - one time...
echo.

REM Check if the script exists
if not exist "auto_scraper_worldcup.py" (
    echo [ERROR] auto_scraper_worldcup.py not found in current directory!
    echo Current directory: %CD%
    echo.
    echo Please make sure you're running this from the project root directory.
    pause
    exit /b 1
)

REM Run once (not continuous loop) - includes git commit and push
%PYTHON_CMD% auto_scraper_worldcup.py --once

if errorlevel 1 (
    echo.
    echo [ERROR] Scraper failed with error code: %ERRORLEVEL%
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo [DONE] World Cup scraper finished!
echo ============================================================
pause

