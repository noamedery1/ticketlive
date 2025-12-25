@echo off
echo ============================================================
echo CREATE NEW TEAM TEMPLATE
echo ============================================================
echo.
echo This will create a template file for a new team.
echo.
set /p TEAM_KEY="Enter team key (e.g., manchester-united): "
set /p TEAM_NAME="Enter team name (e.g., Manchester United): "
set /p TEAM_URL="Enter team URL (home matches filter): "

echo.
echo Creating %TEAM_KEY%_prices.json...
echo.

(
echo {
echo   "team_name": "%TEAM_NAME%",
echo   "team_url": "%TEAM_URL%",
echo   "games": []
echo }
) > %TEAM_KEY%_prices.json

echo.
echo [OK] Created %TEAM_KEY%_prices.json
echo.
echo You can now edit this file or run the scraper to populate it.
echo.
pause

