@echo off
title SLN WMS Launcher
cd /d "%~dp0"

echo ======================================================
echo Launching SLN Warehouse Management System (Full Stack)
echo.
echo Backend API : http://127.0.0.1:8000 (Docs: /docs)
echo Frontend UI : http://localhost:5173
echo ======================================================
echo.

start "SLN WMS - Backend (FastAPI :8000)" cmd /k "call "%~dp0start_backend.bat""
start "SLN WMS - Frontend (Vite :5173)" cmd /k "call "%~dp0start_frontend.bat""

echo [SUCCESS] Backend and Frontend have been launched in separate console windows!
echo Keep those terminal windows open while developing.
echo To restart any service, simply restart its specific window or rerun start_dev.bat.
echo ======================================================
timeout /t 5
