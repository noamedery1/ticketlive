@echo off
REM ============================================================
REM  TicketLive scraper - one-time setup on the Windows machine
REM  Needs: Python 3.8 (with py launcher), Chrome, Git for Windows.
REM  Run from the folder you extracted (e.g. C:\ticketlive).
REM ============================================================
cd /d "%~dp0"
set REPO=https://github.com/noamedery1/ticketlive.git
set VENV=C:\PythonEnvs\ticketlive

echo [1/6] Checking tools...
git --version >nul 2>&1 || (echo [ERROR] Git not found. Install Git for Windows, then rerun. & pause & exit /b 1)
set PYBASE=
py -3.8 --version >nul 2>&1 && set PYBASE=py -3.8
if not defined PYBASE python --version >nul 2>&1 && set PYBASE=python
if not defined PYBASE (echo [ERROR] Python not found. Install Python 3.8.10, then rerun. & pause & exit /b 1)

echo [2/6] Linking this folder to GitHub...
REM Only on first setup: a later rerun must not throw away unpushed price commits.
if exist ".git" goto linked
git init -q
git remote add origin %REPO%
git fetch --depth 1 origin main || (echo [ERROR] git fetch failed - check internet access. & pause & exit /b 1)
git symbolic-ref HEAD refs/heads/main
git reset -q --hard FETCH_HEAD
git branch -q --set-upstream-to=origin/main main
:linked
git config user.name >nul 2>&1 || git config user.name "ticketlive-scraper"
git config user.email >nul 2>&1 || git config user.email "scraper@ticketlive.local"

echo [3/6] Python environment in %VENV%...
if not exist "%VENV%\Scripts\python.exe" %PYBASE% -m venv "%VENV%"
"%VENV%\Scripts\python.exe" -m pip install -q --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -q -r requirements_win7.txt || (echo [ERROR] pip install failed. & pause & exit /b 1)

echo [4/6] ChromeDriver matching your Chrome...
"%VENV%\Scripts\python.exe" download_chromedriver.py || (echo [ERROR] ChromeDriver download failed - see SCRAPER_SETUP.md. & pause & exit /b 1)

echo [5/6] Scheduling a run every 3 hours (task "TicketLive Scraper")...
schtasks /create /f /tn "TicketLive Scraper" /tr "\"%~dp0RUN_ALL_TEAMS_ONCE.bat\"" /sc hourly /mo 3 >nul || echo [WARN] Could not create the scheduled task - add it by hand.

echo [6/6] First run now (takes a while; a Chrome window will open).
echo       On the first push Git asks for GitHub login - use your username and a token.
call :chrome_major
"%VENV%\Scripts\python.exe" auto_scraper_teams.py --once
set RC=%ERRORLEVEL%
echo.
if not "%RC%"=="0" (echo [WARN] Some teams failed - read the output above.) else (echo [OK] Done. The site updates a few minutes after the push.)
pause
exit /b 0

:chrome_major
REM Installed Chrome's major version, 109 if unknown (last Chrome for Windows 7).
set CHROME_MAJOR=109
for /f "tokens=3" %%v in ('reg query "HKCU\Software\Google\Chrome\BLBeacon" /v version 2^>nul ^| find "version"') do for /f "tokens=1 delims=." %%m in ("%%v") do set CHROME_MAJOR=%%m
exit /b 0
