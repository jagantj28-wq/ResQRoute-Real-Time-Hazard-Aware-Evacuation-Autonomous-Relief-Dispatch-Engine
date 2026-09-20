@echo off
title ResQRoute - Autonomous Evacuation & Dispatch Engine
echo =====================================================================
echo  ResQRoute: Real-Time Hazard-Aware Evacuation & Dispatch Engine
echo =====================================================================
echo.

if exist .venv\Scripts\python.exe (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo Starting ResQRoute FastAPI Server on http://127.0.0.1:8000 ...
%PYTHON% -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
