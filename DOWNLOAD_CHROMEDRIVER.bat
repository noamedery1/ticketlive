@echo off
echo ============================================================
echo DOWNLOAD CORRECT CHROMEDRIVER (32-bit for 32-bit Chrome)
echo ============================================================
echo.

REM Activate virtual environment
set VENV_DIR=C:\PythonEnvs\ticketlive
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    pause
    exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"

echo [1/4] Getting Chrome version...
REM Get Chrome version from registry or executable
for /f "tokens=2 delims==" %%a in ('reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version 2^>nul') do set CHROME_VERSION=%%a
if "%CHROME_VERSION%"=="" (
    echo [WARNING] Could not get Chrome version from registry
    echo Please check Chrome version manually:
    echo   1. Open Chrome
    echo   2. Go to: chrome://version
    echo   3. Note the version number (e.g., 120.0.6099.109)
    echo.
    set /p CHROME_VERSION="Enter Chrome version (e.g., 120.0.6099.109): "
)

if "%CHROME_VERSION%"=="" (
    echo [ERROR] Chrome version required
    pause
    exit /b 1
)

echo [OK] Chrome version: %CHROME_VERSION%
echo.

REM Extract major version (e.g., 120 from 120.0.6099.109)
for /f "tokens=1 delims=." %%a in ("%CHROME_VERSION%") do set CHROME_MAJOR=%%a

echo [2/4] Downloading 32-bit ChromeDriver for Chrome %CHROME_VERSION%...
echo.

REM Use Python script for download (pass version as argument)
python download_chromedriver.py %CHROME_VERSION%

if errorlevel 1 (
    echo.
    echo [ERROR] Automatic download failed
    echo.
    echo Please download manually:
    echo   1. Go to: https://googlechromelabs.github.io/chrome-for-testing/
    echo   2. Find Chrome version %CHROME_MAJOR%
    echo   3. Download: chromedriver-win32.zip
    echo   4. Extract chromedriver.exe
    echo   5. Copy to: C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe
    echo.
    pause
    exit /b 1
)

echo.
echo [3/4] Verifying ChromeDriver...
if exist "C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe" (
    echo [OK] ChromeDriver found at: C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe
) else (
    echo [ERROR] ChromeDriver not found after download
    pause
    exit /b 1
)

echo.
echo [4/4] Testing ChromeDriver...
python -c "import undetected_chromedriver as uc; import os; chrome_path = r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'; driver_path = r'C:\PythonEnvs\ticketlive\Scripts\chromedriver.exe'; print(f'Testing with Chrome: {chrome_path}'); print(f'ChromeDriver: {driver_path}'); driver = uc.Chrome(browser_executable_path=chrome_path, driver_executable_path=driver_path, use_subprocess=False); print('SUCCESS!'); driver.quit()"

if errorlevel 1 (
    echo.
    echo [ERROR] ChromeDriver test failed
    echo.
    echo The ChromeDriver might still be wrong architecture.
    echo Try downloading from: https://chromedriver.chromium.org/downloads
    echo Make sure to download win32 (32-bit) version
    echo.
) else (
    echo.
    echo ============================================================
    echo SUCCESS! ChromeDriver is working
    echo ============================================================
    echo.
    echo The scrapers have been updated to use this ChromeDriver.
    echo You can now run: RUN_IN_VENV.bat
    echo ============================================================
)

echo.
pause

