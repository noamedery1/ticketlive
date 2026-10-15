@echo off
REM One scrape cycle, then exit. Use this from Windows Task Scheduler (no pause, logs to scraper.log).
cd /d "%~dp0"
if exist "C:\PythonEnvs\ticketlive\Scripts\python.exe" (
    set PY=C:\PythonEnvs\ticketlive\Scripts\python.exe
) else (
    set PY=py
)
REM Installed Chrome major version, 109 if unknown (last Chrome for Windows 7).
set CHROME_MAJOR=109
for /f "tokens=3" %%v in ('reg query "HKCU\Software\Google\Chrome\BLBeacon" /v version 2^>nul ^| find "version"') do for /f "tokens=1 delims=." %%m in ("%%v") do set CHROME_MAJOR=%%m
%PY% auto_scraper_teams.py --once >> scraper.log 2>&1
exit /b %ERRORLEVEL%
