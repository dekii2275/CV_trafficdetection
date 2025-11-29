@echo off
echo ========================================
echo Starting Backend Server
echo ========================================
cd backend
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r ..\requirements.txt
)
echo.
echo Starting FastAPI server on http://localhost:8000
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause

