@echo off
<<<<<<< .merge_file_a03884
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
=======
echo ============================================================
echo INSTALL REQUIRED PACKAGES
echo ============================================================
echo.

REM Check if pip is available
py -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed!
    echo.
    echo Please install pip first using one of these methods:
    echo   1. INSTALL_PIP_FINAL.bat
    echo   2. Use virtual environment (see WORKAROUND_SOLUTION.md)
    echo   3. Reinstall Python to C:\Python37
>>>>>>> .merge_file_a10296
    echo.
    pause
    exit /b 1
)

<<<<<<< .merge_file_a03884
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

=======
echo [OK] pip is available
py -m pip --version
echo.

echo [1/3] Installing undetected-chromedriver...
py -m pip install --no-warn-script-location undetected-chromedriver==3.5.4
if errorlevel 1 (
    echo [ERROR] Failed to install undetected-chromedriver
    pause
    exit /b 1
)
echo [OK] undetected-chromedriver installed
echo.

echo [2/3] Installing selenium...
py -m pip install --no-warn-script-location selenium==4.15.2
if errorlevel 1 (
    echo [ERROR] Failed to install selenium
    pause
    exit /b 1
)
echo [OK] selenium installed
echo.

echo [3/3] Installing requests...
py -m pip install --no-warn-script-location requests==2.31.0
if errorlevel 1 (
    echo [ERROR] Failed to install requests
    pause
    exit /b 1
)
echo [OK] requests installed
echo.

echo [VERIFY] Testing imports...
py -c "import undetected_chromedriver; import selenium; import requests; print('All packages OK!')"
if errorlevel 1 (
    echo [WARNING] Some packages may not be installed correctly
) else (
    echo.
    echo ============================================================
    echo SUCCESS! All packages installed
    echo You can now run: py auto_scraper.py
    echo ============================================================
)

echo.
pause
>>>>>>> .merge_file_a10296
