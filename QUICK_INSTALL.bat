@echo off
echo ============================================================
echo   QUICK INSTALL - Python Packages for Windows 7
echo ============================================================
echo.

REM Find working Python command
set PYTHON_CMD=
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    echo [OK] Found Python launcher
    py --version
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
        echo [OK] Found Python
        python --version
    ) else (
        echo [ERROR] Python not found!
        echo.
        echo Install Python from: https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH"
        pause
        exit /b 1
    )
)

echo.
echo Installing packages...
echo This may take a few minutes...
echo.

REM Check and install pip if missing
echo [1/4] Checking pip...
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] pip not found, installing...
    echo Downloading get-pip.py...
    powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py" 2>nul
    if exist get-pip.py (
        %PYTHON_CMD% get-pip.py
        if exist get-pip.py del get-pip.py
        echo [OK] pip installed
    ) else (
        echo [ERROR] Failed to download get-pip.py
        echo Please download manually: https://bootstrap.pypa.io/get-pip.py
        pause
        exit /b 1
    )
) else (
    echo [OK] pip found
    echo [2/4] Upgrading pip...
    %PYTHON_CMD% -m pip install --upgrade pip --quiet
    echo [OK] pip upgraded
)

REM Install packages
echo [3/4] Installing packages...
%PYTHON_CMD% -m pip install undetected-chromedriver selenium requests
if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed!
    echo.
    echo Trying with trusted hosts (for Windows 7 SSL issues)...
    %PYTHON_CMD% -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org undetected-chromedriver selenium requests
    if errorlevel 1 (
        echo.
        echo [ERROR] Still failed. Check your internet connection.
        pause
        exit /b 1
    )
)
echo [OK] Packages installed

REM Verify
echo [4/4] Verifying...
%PYTHON_CMD% -c "import undetected_chromedriver; print('[OK] undetected_chromedriver')" 2>nul || echo [WARN] undetected_chromedriver check failed
%PYTHON_CMD% -c "import selenium; print('[OK] selenium')" 2>nul || echo [WARN] selenium check failed
%PYTHON_CMD% -c "import requests; print('[OK] requests')" 2>nul || echo [WARN] requests check failed

echo.
echo ============================================================
echo   INSTALLATION COMPLETE!
echo ============================================================
echo.
echo Run the scraper with:
echo   %PYTHON_CMD% auto_scraper.py
echo.
pause

