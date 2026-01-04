@echo off
echo ============================================================
echo RESTART BACKEND SERVER
echo ============================================================
echo.
echo This will help you restart the backend server.
echo.
echo Step 1: Stop the current server (if running)
echo   - Find the terminal window running RUN_SERVER_ONLY.py
echo   - Press Ctrl+C to stop it
echo.
echo Step 2: Start the server again
echo   - Run: python RUN_SERVER_ONLY.py
echo   - Or double-click this file after stopping the server
echo.
echo ============================================================
echo.
pause
echo.
echo Starting server...
cd /d "%~dp0"
python RUN_SERVER_ONLY.py
pause

