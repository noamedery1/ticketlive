@echo off
echo ============================================================
echo   SETUP SCRIPT FOR WINDOWS 7
echo   Installing Python packages for ticket scraper
echo ============================================================
echo.

REM Try to find Python command
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    echo [OK] Using Python launcher (py)
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
        echo [OK] Using python command
    ) else (
        echo ERROR: Python is not installed or not in PATH
        echo Please install Python 3.7 or higher first
        echo Download from: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo [OK] Python found:
%PYTHON_CMD% --version
echo.

REM Upgrade pip first
echo [1/3] Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARN] Failed to upgrade pip, continuing anyway...
)
echo.

REM Install required packages
echo [2/3] Installing required packages...
echo This may take a few minutes...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install packages!
    echo.
    echo Try installing manually:
    echo   %PYTHON_CMD% -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org undetected-chromedriver selenium requests
    pause
    exit /b 1
)
echo.

REM Verify installation
echo [3/3] Verifying installation...
%PYTHON_CMD% -c "import undetected_chromedriver; print('[OK] undetected_chromedriver installed')" 2>nul || echo [ERROR] undetected_chromedriver not found
%PYTHON_CMD% -c "import selenium; print('[OK] selenium installed')" 2>nul || echo [ERROR] selenium not found
%PYTHON_CMD% -c "import requests; print('[OK] requests installed')" 2>nul || echo [ERROR] requests not found
echo.

echo ============================================================
echo   SETUP COMPLETE!
echo ============================================================
echo.
echo You can now run the scraper with:
echo   %PYTHON_CMD% auto_scraper.py
echo.
pause

