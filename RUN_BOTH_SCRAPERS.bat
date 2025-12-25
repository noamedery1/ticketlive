@echo off
echo ============================================================
echo RUN BOTH SCRAPERS - Arsenal and Barcelona
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
echo ============================================================
echo [1/2] Running Arsenal scraper...
echo ============================================================
python scraper_ftn_teams.py arsenal

echo.
echo ============================================================
echo [2/2] Running Barcelona scraper...
echo ============================================================
python scraper_ftn_teams.py barcelona

echo.
echo ============================================================
echo [DONE] Both scrapers finished!
echo ============================================================
pause

