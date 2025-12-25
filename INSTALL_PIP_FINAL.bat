@echo off
echo ============================================================
echo INSTALL PIP - WORKAROUND FOR $ IN PATH
echo ============================================================
echo.

REM Download get-pip.py for Python 3.7
if not exist get-pip.py (
    echo [1/4] Downloading get-pip.py...
    py -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/3.7/get-pip.py', 'get-pip.py')"
    if not exist get-pip.py (
        echo [ERROR] Failed to download
        pause
        exit /b 1
    )
)
echo [OK] get-pip.py ready
echo.

echo [2/4] Setting environment variables to override problematic paths...
REM Set HOME to a path without $ to avoid distutils expansion
set HOME=%USERPROFILE%
set APPDATA=%USERPROFILE%\AppData\Roaming
set LOCALAPPDATA=%USERPROFILE%\AppData\Local

REM Override Python installation paths
set PYTHONHOME=
set PYTHONUSERBASE=%CD%\python_user
set PYTHONPATH=

REM Create a custom user base directory
if not exist "%CD%\python_user" mkdir "%CD%\python_user"
if not exist "%CD%\python_user\Scripts" mkdir "%CD%\python_user\Scripts"

echo [OK] Environment configured
echo   User packages will be installed to: %CD%\python_user
echo.

echo [3/4] Installing pip to custom location...
echo This may take a minute...
echo.

REM Install pip with explicit prefix to avoid path expansion
py get-pip.py --prefix="%CD%\python_user" --no-warn-script-location

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed with prefix method
    echo.
    echo Trying alternative: installing to system Python...
    echo.
    REM Try installing directly to Python's Scripts folder
    for /f "tokens=*" %%i in ('py -c "import sys; print(sys.executable)"') do set PYTHON_EXE=%%i
    for %%i in ("%PYTHON_EXE%") do set PYTHON_DIR=%%~dpi
    
    echo Installing to: %PYTHON_DIR%Scripts
    py get-pip.py --no-warn-script-location
    
    if errorlevel 1 (
        echo.
        echo [ERROR] All methods failed
        echo.
        echo The issue is the $ character in your username path.
        echo.
        echo SOLUTION: Install Python to a different location without $ in the path
        echo OR: Use a portable Python installation
        echo.
        pause
        exit /b 1
    )
)

echo.
echo [4/4] Verifying pip...
REM Check if pip is in the custom location
if exist "%CD%\python_user\Scripts\pip.exe" (
    echo [OK] pip installed to: %CD%\python_user\Scripts\pip.exe
    echo.
    echo To use pip, run:
    echo   %CD%\python_user\Scripts\pip.exe --version
    echo   %CD%\python_user\Scripts\pip.exe install package_name
    echo.
    echo Or add to PATH:
    echo   set PATH=%%PATH%%;%CD%\python_user\Scripts
) else (
    py -m pip --version >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] pip may not be in PATH
        echo Try: py -m pip --version
    ) else (
        echo [OK] pip is installed!
        py -m pip --version
    )
)

echo.
echo ============================================================
echo Installation attempt complete
echo ============================================================
pause

