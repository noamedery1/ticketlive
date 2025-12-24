@echo off
echo ============================================================
echo   INSTALL PIP AND PACKAGES - Windows 7
echo ============================================================
echo.

REM Find Python
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
        pause
        exit /b 1
    )
)

echo.
echo [STEP 1] Installing pip...
echo.

REM Check if pip exists
%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] pip is already installed
    %PYTHON_CMD% -m pip --version
) else (
    echo [INFO] pip not found, installing...
    echo Downloading get-pip.py...
    
    REM Download get-pip.py
    powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py" 2>nul
    if not exist get-pip.py (
        echo [ERROR] Failed to download get-pip.py
        echo.
        echo Please download manually from:
        echo https://bootstrap.pypa.io/get-pip.py
        echo.
        echo Then run: %PYTHON_CMD% get-pip.py
        pause
        exit /b 1
    )
    
    echo [OK] Downloaded get-pip.py
    echo Installing pip...
    %PYTHON_CMD% get-pip.py
    if errorlevel 1 (
        echo [ERROR] Failed to install pip
        echo.
        echo Try manually:
        echo   1. Download: https://bootstrap.pypa.io/get-pip.py
        echo   2. Run: %PYTHON_CMD% get-pip.py
        pause
        exit /b 1
    )
    
    REM Clean up
    if exist get-pip.py del get-pip.py
    echo [OK] pip installed successfully
)

echo.
echo [STEP 2] Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARN] Failed to upgrade pip, continuing anyway...
) else (
    echo [OK] pip upgraded
)

echo.
echo [STEP 3] Installing required packages...
echo This may take a few minutes...
echo.

%PYTHON_CMD% -m pip install undetected-chromedriver selenium requests
if errorlevel 1 (
    echo.
    echo [WARN] Installation failed, trying with trusted hosts...
    %PYTHON_CMD% -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org undetected-chromedriver selenium requests
    if errorlevel 1 (
        echo.
        echo [ERROR] Installation failed!
        echo Check your internet connection and try again.
        pause
        exit /b 1
    )
)
echo [OK] Packages installed

echo.
echo [STEP 4] Verifying installation...
%PYTHON_CMD% -c "import undetected_chromedriver; print('[OK] undetected_chromedriver')" 2>nul || echo [ERROR] undetected_chromedriver not found
%PYTHON_CMD% -c "import selenium; print('[OK] selenium')" 2>nul || echo [ERROR] selenium not found
%PYTHON_CMD% -c "import requests; print('[OK] requests')" 2>nul || echo [ERROR] requests not found

echo.
echo ============================================================
echo   INSTALLATION COMPLETE!
echo ============================================================
echo.
echo Run the scraper with:
echo   %PYTHON_CMD% auto_scraper.py
echo.
pause

