@echo off
title SLN WMS - Frontend (Vite :5173)
cd /d "%~dp0warehouse_frontend"

if not exist "node_modules" (
    echo [INFO] node_modules not detected. Installing dependencies...
    call npm install
)

echo ======================================================
echo Starting SLN WMS Frontend on http://localhost:5173
echo ======================================================
call npm run dev
pause
