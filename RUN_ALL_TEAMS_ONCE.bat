@echo off
REM One scrape cycle, then exit. Use this from Windows Task Scheduler (no pause, logs to scraper.log).
cd /d "%~dp0"
if exist "C:\PythonEnvs\ticketlive\Scripts\python.exe" (
    set PY=C:\PythonEnvs\ticketlive\Scripts\python.exe
) else (
    set PY=py
)
REM Chrome 109 is the last Chrome on Windows 7 - keep chromedriver on the same major.
if not defined CHROME_MAJOR set CHROME_MAJOR=109
%PY% auto_scraper_teams.py --once >> scraper.log 2>&1
exit /b %ERRORLEVEL%
