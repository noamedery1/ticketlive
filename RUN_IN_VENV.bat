@echo off
REM Run auto_scraper.py in virtual environment
set VENV_DIR=C:\PythonEnvs\ticketlive

if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at: %VENV_DIR%
    echo.
    echo Please run SETUP_VENV.bat first to create the virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

echo.
echo Running auto_scraper.py...
echo.

REM Change to script directory
cd /d "%~dp0"

python auto_scraper.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Script exited with error
    pause
)

