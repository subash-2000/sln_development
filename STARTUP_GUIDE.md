# SLN WMS - Startup & Rerun Guide

This workspace includes dedicated runner scripts for quick, one-click execution and future reruns of both backend and frontend.

---

## 🚀 Quick Start (Rerun Scripts)

| Script | Purpose | Description |
| :--- | :--- | :--- |
| **`start_dev.bat`** | **Run Both (Recommended)** | Double-click or run from terminal. Launches Backend and Frontend in separate dedicated CMD windows for easy log inspection. |
| **`start_backend.bat`** | **Backend Only** | Starts FastAPI backend on port `8000` (`http://127.0.0.1:8000`). |
| **`start_frontend.bat`** | **Frontend Only** | Starts Vite React frontend on port `5173` (`http://localhost:5173`). |
| **`start_dev.ps1`** | **PowerShell Launcher** | For PowerShell users (`.\start_dev.ps1`). |
| **`npm run dev`** | **Concurrent Terminal** | Runs both concurrently in a single terminal session (configured in root `package.json`). |

---

## 🌐 URLs & Service Endpoints

- **Frontend Web UI**: [http://localhost:5173](http://localhost:5173)
- **Backend API Server**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **FastAPI Interactive Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **FastAPI Alternative Docs (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🛑 How to Stop Services

- **Separate Windows (`start_dev.bat` / individual scripts)**: Simply close the Command Prompt windows or press `Ctrl + C` inside them.
- **Single Terminal (`npm run dev`)**: Press `Ctrl + C` in the running terminal.
