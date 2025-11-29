@echo off
echo ========================================
echo Starting Traffic Detection Project
echo ========================================
echo.
echo This will start both backend and frontend in separate windows.
echo.
echo Press any key to continue...
pause >nul

start "Backend Server" cmd /k "start_backend.bat"
timeout /t 3 /nobreak >nul
start "Frontend Server" cmd /k "start_frontend.bat"

echo.
echo ========================================
echo Both servers are starting...
echo ========================================
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit this window (servers will keep running)...
pause >nul

