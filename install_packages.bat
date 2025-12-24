@echo off
echo Installing Python packages for Windows 7...
echo.

REM Try to find Python command and verify it works
set PYTHON_CMD=

REM Try py launcher first
where py >nul 2>&1
if %errorlevel% equ 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
        echo [OK] Using Python launcher (py)
        py --version
    )
)

REM If py didn't work, try python
if "%PYTHON_CMD%"=="" (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        python --version >nul 2>&1
        if %errorlevel% equ 0 (
            set PYTHON_CMD=python
            echo [OK] Using python command
            python --version
        )
    )
)

REM If still nothing, error out
if "%PYTHON_CMD%"=="" (
    echo.
    echo [ERROR] Python not found or not working!
    echo.
    echo Please install Python 3.7 or higher from python.org
    echo Download: https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo.
echo [1/2] Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARN] Failed to upgrade pip, continuing anyway...
)
echo.

echo [2/2] Installing required packages...
echo This may take a few minutes...
%PYTHON_CMD% -m pip install undetected-chromedriver selenium requests
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed!
    echo.
    echo Try manually:
    echo   %PYTHON_CMD% -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org undetected-chromedriver selenium requests
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   INSTALLATION COMPLETE!
echo ============================================================
echo.
echo You can now run the scraper with:
echo   %PYTHON_CMD% auto_scraper.py
echo.
pause

