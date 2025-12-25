@echo off
echo ============================================================
echo RUN WORLD CUP SCRAPER - Viagogo
echo ============================================================
echo.

REM Check if virtual environment exists
if exist "C:\PythonEnvs\ticketlive\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call C:\PythonEnvs\ticketlive\Scripts\activate.bat
) else (
    echo [INFO] No virtual environment found, using system Python...
)

echo.
echo [START] Running World Cup scraper (Viagogo)...
echo.

REM Run once (not continuous loop) - includes git commit and push
python auto_scraper_worldcup.py --once

echo.
echo ============================================================
echo [DONE] World Cup scraper finished!
echo ============================================================
pause

