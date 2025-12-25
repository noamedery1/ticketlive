@echo off
echo ============================================================
echo QUICK PIP INSTALLATION
echo ============================================================
echo.

REM Check if get-pip.py exists
if not exist get-pip.py (
    echo [1/3] Downloading get-pip.py for Python 3.7...
    echo.
    
    REM Try using Python to download (Python 3.7 specific version)
    py -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/3.7/get-pip.py', 'get-pip.py')"
    
    if not exist get-pip.py (
        echo [ERROR] Failed to download get-pip.py automatically
        echo.
        echo Please download manually:
        echo 1. Open browser and go to: https://bootstrap.pypa.io/pip/3.7/get-pip.py
        echo 2. Right-click and "Save As..." to D:\tikcetLive\get-pip.py
        echo 3. Press any key after downloading...
        pause
    )
) else (
    echo [OK] get-pip.py already exists
)

if not exist get-pip.py (
    echo [ERROR] get-pip.py not found. Cannot continue.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing pip...
echo This may take a minute...
echo.

REM Set environment to avoid $ expansion issues
set DISTUTILS_USE_SDK=1
set PYTHONUSERBASE=
py get-pip.py --no-warn-script-location --user

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed. Trying alternative method...
    echo.
    py get-pip.py --no-warn-script-location
)

echo.
echo [3/3] Verifying pip installation...
py -m pip --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] pip may not be in PATH
    echo Trying to add user site-packages to PATH...
    echo.
    REM Try using full path
    for /f "tokens=*" %%i in ('py -c "import site; print(site.getusersitepackages())" 2^>nul') do set USER_SITE=%%i
    if defined USER_SITE (
        echo User site-packages: %USER_SITE%
        echo.
        echo Try running:
        echo   py -m pip --version
        echo.
        echo If that doesn't work, you may need to add this to PATH:
        echo   %USER_SITE%
    )
) else (
    echo [OK] pip is installed!
    py -m pip --version
    echo.
    echo ============================================================
    echo pip installation successful!
    echo You can now run: SETUP_WIN7.bat
    echo ============================================================
)

echo.
pause

