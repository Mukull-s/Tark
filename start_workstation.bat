@echo off
echo ===================================================
echo   TARK — Autonomous Agentic Fraud Workstation
echo   Hacker House Goa 2026 / TigerGraph
echo ===================================================
echo.
echo Starting FastAPI Backend Server and Web Workstation...
echo URL: http://127.0.0.1:8000
echo.
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
pause
