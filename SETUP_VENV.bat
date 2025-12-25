@echo off
echo ============================================================
echo SETUP VIRTUAL ENVIRONMENT (Workaround for $ in username)
echo ============================================================
echo.

REM Create venv in a safe location (without $ in path)
set VENV_DIR=C:\PythonEnvs\ticketlive

echo [1/4] Creating virtual environment...
echo Location: %VENV_DIR%
echo.

if exist "%VENV_DIR%" (
    echo [WARNING] Virtual environment already exists
    echo Do you want to recreate it? (Y/N)
    set /p RECREATE=
    if /i "%RECREATE%"=="Y" (
        echo Removing old environment...
        rmdir /s /q "%VENV_DIR%"
    ) else (
        echo Using existing environment...
        goto activate
    )
)

py -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    echo.
    echo Make sure you have write access to C:\PythonEnvs
    echo Or run this script as Administrator
    pause
    exit /b 1
)

echo [OK] Virtual environment created
echo.

:activate
echo [2/4] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

echo [3/4] Installing pip in virtual environment...
python get-pip.py
if errorlevel 1 (
    echo [WARNING] get-pip.py not found, downloading...
    python -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/3.7/get-pip.py', 'get-pip.py')"
    if exist get-pip.py (
        python get-pip.py
    ) else (
        echo [ERROR] Could not download get-pip.py
        echo Please download manually: https://bootstrap.pypa.io/pip/3.7/get-pip.py
        pause
        exit /b 1
    )
)
echo [OK] pip installed
echo.

echo [4/4] Installing required packages...
echo This may take a few minutes...
echo.

pip install -r requirements_win7.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed
    echo.
    echo Try installing individually:
    echo   pip install undetected-chromedriver==3.5.4
    echo   pip install selenium==4.15.2
    echo   pip install requests==2.31.0
    pause
    exit /b 1
)

echo.
echo [VERIFY] Testing imports...
python -c "import undetected_chromedriver; import selenium; import requests; print('All packages OK!')"
if errorlevel 1 (
    echo [WARNING] Some packages may not be installed correctly
) else (
    echo.
    echo ============================================================
    echo SUCCESS! Virtual environment is ready
    echo ============================================================
    echo.
    echo To use the virtual environment:
    echo   1. Activate it: C:\PythonEnvs\ticketlive\Scripts\activate.bat
    echo   2. Run scripts: python auto_scraper.py
    echo   3. Deactivate when done: deactivate
    echo.
    echo Or use RUN_IN_VENV.bat to run scripts automatically
    echo ============================================================
)

echo.
pause

