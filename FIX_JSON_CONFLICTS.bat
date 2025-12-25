@echo off
echo ============================================================
echo FIX JSON MERGE CONFLICTS
echo ============================================================
echo.

REM Check if virtual environment exists
if exist "C:\PythonEnvs\ticketlive\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call C:\PythonEnvs\ticketlive\Scripts\activate.bat
) else (
    echo [INFO] No virtual environment found, using system Python...
)

echo.
echo [START] Fixing merge conflicts in JSON files...
echo.

REM Check Python (Windows 7 compatible)
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found!
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

%PYTHON_CMD% fix_json_merge_conflicts.py

echo.
echo ============================================================
echo [DONE] JSON conflicts fixed!
echo ============================================================
pause

