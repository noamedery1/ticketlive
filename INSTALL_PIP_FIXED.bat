@echo off
echo ============================================================
echo INSTALL PIP - WORKAROUND FOR $ IN USERNAME
echo ============================================================
echo.

REM Download correct get-pip.py for Python 3.7
if not exist get-pip.py (
    echo [1/4] Downloading get-pip.py for Python 3.7...
    py -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/3.7/get-pip.py', 'get-pip.py')"
    if not exist get-pip.py (
        echo [ERROR] Failed to download
        pause
        exit /b 1
    )
    echo [OK] Downloaded
) else (
    echo [OK] get-pip.py exists
)
echo.

echo [2/4] Setting environment variables to avoid $ expansion issue...
REM Set environment variables to override distutils paths
set PYTHONUSERBASE=%USERPROFILE%\.python
set DISTUTILS_USE_SDK=1
set PYTHONNOUSERSITE=0
echo [OK] Environment configured
echo.

echo [3/4] Installing pip with isolated mode...
echo This may take a minute...
echo.

REM Try installing with --isolated flag first (avoids distutils config)
py get-pip.py --isolated --no-warn-script-location

if errorlevel 1 (
    echo.
    echo [WARNING] Isolated install failed, trying with custom prefix...
    REM Try installing to a custom location
    set INSTALL_PREFIX=%CD%\python_packages
    py get-pip.py --prefix=%INSTALL_PREFIX% --no-warn-script-location
    
    if errorlevel 1 (
        echo.
        echo [ERROR] All installation methods failed
        echo.
        echo Trying manual workaround...
        echo.
        REM Last resort: try to install pip using ensurepip with environment override
        set PYTHONUSERBASE=%USERPROFILE%\.python
        py -m ensurepip --user --default-pip 2>nul
        if errorlevel 1 (
            echo [ERROR] Could not install pip automatically
            echo.
            echo Please try installing pip manually using:
            echo   1. Download: https://bootstrap.pypa.io/pip/3.7/get-pip.py
            echo   2. Run: py get-pip.py --isolated
            echo.
            pause
            exit /b 1
        )
    )
)

echo.
echo [4/4] Verifying pip...
py -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] pip may not be in PATH
    echo.
    echo Try these commands:
    echo   py -m pip --version
    echo   python -m pip --version
    echo.
    echo If pip is installed but not found, you may need to add to PATH:
    echo   %USERPROFILE%\.python\Scripts
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

