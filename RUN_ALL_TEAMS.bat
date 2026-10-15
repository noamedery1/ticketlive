@echo off
REM Continuous loop in a console window (every 3 hours). Prefer RUN_ALL_TEAMS_ONCE.bat + Task Scheduler.
cd /d "%~dp0"
if exist "C:\PythonEnvs\ticketlive\Scripts\python.exe" (
    set PY=C:\PythonEnvs\ticketlive\Scripts\python.exe
) else (
    set PY=py
)
if not defined CHROME_MAJOR set CHROME_MAJOR=109
%PY% auto_scraper_teams.py
pause
