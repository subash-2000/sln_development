@echo off
title SLN WMS - Backend (FastAPI :8000)
cd /d "%~dp0warehouse"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at warehouse\venv!
    echo Please ensure the Python venv is installed.
    pause
    exit /b 1
)

echo ======================================================
echo Starting SLN WMS FastAPI Backend on http://127.0.0.1:8000
echo Swagger UI: http://127.0.0.1:8000/docs
echo ======================================================
venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
