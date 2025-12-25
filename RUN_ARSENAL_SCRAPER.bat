@echo off
echo ============================================================
echo RUN ARSENAL SCRAPER - FootballTicketNet
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
echo [START] Running Arsenal scraper...
echo.

python scraper_ftn_teams.py arsenal

echo.
echo ============================================================
echo [DONE] Scraper finished!
echo ============================================================
pause

