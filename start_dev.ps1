# PowerShell Launcher for SLN Warehouse Management System
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Starting SLN Warehouse Management System (Full Stack)" -ForegroundColor Green
Write-Host " Backend API : http://127.0.0.1:8000 (Docs: /docs)" -ForegroundColor Yellow
Write-Host " Frontend UI : http://localhost:5173" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Cyan

# Launch Backend in a separate window
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "`"$rootDir\start_backend.bat`"" -WorkingDirectory "$rootDir\warehouse"

# Launch Frontend in a separate window
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", "`"$rootDir\start_frontend.bat`"" -WorkingDirectory "$rootDir\warehouse_frontend"

Write-Host "`n[SUCCESS] Backend and Frontend launched in dedicated windows." -ForegroundColor Green
