@echo off
echo ============================================================
echo INSTALL PIP FOR WINDOWS 7 (Special Username Fix)
echo ============================================================
echo.
echo This script handles usernames with special characters like $
echo.

REM Check Python
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

echo [1/4] Downloading get-pip.py...
echo.

REM Download get-pip.py for Python 3.7
echo Downloading get-pip.py for Python 3.7...
py -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/3.7/get-pip.py', 'get-pip.py')" 2>nul
if not exist get-pip.py (
    echo [ERROR] Failed to download get-pip.py
    echo.
    echo Please download manually:
    echo 1. Go to: https://bootstrap.pypa.io/pip/3.7/get-pip.py
    echo 2. Save as: get-pip.py
    echo 3. Run: py get-pip.py --no-warn-script-location --user
    pause
    exit /b 1
)

echo [OK] Downloaded get-pip.py
echo.

echo [2/4] Installing pip...
echo This may take a minute...
echo.

REM Set environment variable to avoid $ expansion issues
set DISTUTILS_USE_SDK=1
py get-pip.py --no-warn-script-location

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install pip
    echo.
    echo Try alternative method:
    echo   py -m ensurepip --default-pip --user
    echo.
    del get-pip.py 2>nul
    pause
    exit /b 1
)

echo.
echo [OK] pip installed
echo.

echo [3/4] Verifying pip...
py -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] pip may not be in PATH
    echo Try: py -m pip --version
) else (
    echo [OK] pip is working
    py -m pip --version
)
echo.

echo [4/4] Upgrading pip...
py -m pip install --upgrade pip --no-warn-script-location
echo.

echo ============================================================
echo pip installation complete!
echo.
echo You can now run:
echo   SETUP_WIN7.bat
echo ============================================================
echo.

REM Cleanup
del get-pip.py 2>nul

pause

