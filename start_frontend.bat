@echo off
echo ========================================
echo Starting Frontend Server
echo ========================================
cd frontend
if not exist node_modules (
    echo Installing dependencies...
    call npm install
)
echo.
echo Starting Next.js server on http://localhost:3000
echo.
call npm run dev
pause

