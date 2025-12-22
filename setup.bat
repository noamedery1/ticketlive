@echo off
echo ==================================================
echo       VIAGOGO PROJECT SETUP FOR NEW PC
echo ==================================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.x from python.org
    pause
    exit /b
)

:: Check for Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo         Please install Node.js from nodejs.org
    echo         Note: If you just installed it, restart your terminal.
    pause
    exit /b
)

:: Check for NPM
call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 'npm' command not found, but 'node' is present.
    echo           This is unusual. Standard Node.js install includes npm.
    echo           Trying to proceed anyway...
)

echo.
echo [1/2] Installing Python Libraries...
pip install -r requirements.txt

echo.
echo [2/2] Installing Frontend Libraries...
cd frontend
if not exist node_modules (
    call npm install
) else (
    echo Node modules already installed.
)
call npm run build
cd ..

echo.
echo ==================================================
echo           SETUP COMPLETE! READY TO RUN.
echo ==================================================
echo To start the dashboard, run: python RUN_EVERYTHING.py
pause
