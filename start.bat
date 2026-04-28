@echo off
echo === Validador MtM - Iniciando ===

REM Backend
start "Backend" cmd /k "cd /d %~dp0backend && python run.py"

REM Frontend
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
