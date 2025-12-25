@echo off
echo ============================================================
echo RUN ALL TEAMS SCRAPER - FootballTicketNet
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
echo [START] Running all teams from teams_config.json...
echo.

REM Run once (not continuous loop)
python auto_scraper_teams.py --once

echo.
echo ============================================================
echo [DONE] All teams scraper finished!
echo ============================================================
pause

