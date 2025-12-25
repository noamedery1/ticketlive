@echo off
echo ============================================================
echo SIMPLE PIP INSTALL - BYPASS DISTUTILS
echo ============================================================
echo.

REM Download get-pip.py for Python 3.7
if not exist get-pip.py (
    echo Downloading get-pip.py...
    py -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/3.7/get-pip.py', 'get-pip.py')"
)

if not exist get-pip.py (
    echo [ERROR] get-pip.py not found
    pause
    exit /b 1
)

echo.
echo Installing pip with --isolated flag (bypasses distutils config)...
echo.

REM Use --isolated to avoid reading distutils config files
py get-pip.py --isolated

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed
    echo.
    echo Try running manually:
    echo   py get-pip.py --isolated
    echo.
    pause
    exit /b 1
)

echo.
echo Verifying...
py -m pip --version

if errorlevel 1 (
    echo [WARNING] pip command not found, but installation may have succeeded
    echo Try: py -m pip --version
) else (
    echo.
    echo ============================================================
    echo SUCCESS! pip is installed
    echo ============================================================
)

pause

